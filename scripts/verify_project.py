"""Trusted repository acceptance commands; never executes manifest commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path

from arete_evals.project import _git, audit_project

ROOT = Path(__file__).resolve().parent.parent


def snapshot() -> dict[str, str]:
    sources = {}
    names = _git(ROOT, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    for name in sorted(set(filter(None, names.split("\0")))):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("source snapshot requires regular files")
        sources[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return sources


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat)
    args = parser.parse_args()
    out = args.out.resolve()
    # Avoid evidence feeding back into its own source inventory.
    if out.is_relative_to(ROOT):
        parser.error("evidence output must be outside the repository")
    out.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    commands = [
        [sys.executable, "scripts/test_report.py", str(out / "tests.json")],
        [sys.executable, "-m", "ruff", "check", "arete_evals", "tests", "scripts"],
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "arete_evals",
            "tests",
            "scripts",
        ],
        [sys.executable, "scripts/validate_repo.py"],
        [sys.executable, "scripts/verify_fix.py"],
    ]
    before = snapshot()
    records = []
    for index, command in enumerate(commands):
        try:
            run = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                capture_output=True,
                timeout=180,
                check=False,
            )
            code = run.returncode
            output = run.stdout + run.stderr
        except subprocess.TimeoutExpired:
            code, output = 124, b"acceptance command timed out\n"
        (out / f"check-{index}.log").write_bytes(output)
        records.append(
            {
                "command": [
                    "python",
                    *[arg.replace(str(out), "<evidence>") for arg in command[1:]],
                ],
                "exit_code": code,
            }
        )
    audit = audit_project(ROOT, as_of=args.as_of)
    (out / "audit.json").write_text(json.dumps(audit, sort_keys=True, indent=2) + "\n")
    sources = snapshot()
    unchanged = sources == before
    artifacts = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(out.iterdir())
        if p.is_file()
    }
    passed = (
        all(r["exit_code"] == 0 for r in records)
        and audit["automated_gates_passed"]
        and unchanged
    )
    report = {
        "schema_version": "project-acceptance-v1",
        "passed": passed,
        "revision": audit["revision"],
        "clean": audit["clean"],
        "source_sha256": sources,
        "source_unchanged_during_verification": unchanged,
        "commands": records,
        "artifacts_sha256": artifacts,
        "full_certification": "UNKNOWN",
        "runtime": {
            "python": sys.version.split()[0],
            "packages": {
                name: version(name)
                for name in ("evalcore", "PyYAML", "jsonschema", "ruff")
            },
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps({"passed": passed, "out": str(out), "full_certification": "UNKNOWN"})
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
