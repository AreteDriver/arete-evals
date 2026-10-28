"""Record only observations made by the fixed repository acceptance script."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from arete_evals.receipts import finalize_receipt, render_receipt, verify_receipt


def write_receipt(out: Path, report: dict, before: dict, elapsed: float) -> None:
    artifacts = []
    for name in ("manifest.json", "audit.json", "tests.json"):
        path = out / name
        if path.is_file():
            data = path.read_bytes()
            artifacts.append(
                {
                    "id": name,
                    "path": name,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    tests = None
    if (out / "tests.json").is_file():
        measured = json.loads((out / "tests.json").read_text())
        excluded = sum(
            measured[k]
            for k in (
                "failures",
                "errors",
                "skipped",
                "expected_failures",
                "unexpected_successes",
            )
        )
        tests = [
            {
                "id": "repository-tests",
                "command": report["commands"][0]["command"],
                "outcome": "PASS"
                if measured["passed"] and report["commands"][0]["exit_code"] == 0
                else "FAIL",
                "counts": {
                    "passed": measured["tests_run"] - excluded,
                    "failed": measured["failures"] + measured["unexpected_successes"],
                    "errors": measured["errors"],
                    "skipped": measured["skipped"] + measured["expected_failures"],
                },
                "evidence": ["tests.json"],
            }
        ]
    after = report["source_sha256"]
    modified = sorted(
        name for name in set(before) | set(after) if before.get(name) != after.get(name)
    )
    receipt = {
        "schema_version": "agent-work-receipt-v1",
        "task_id": "fixed-project-acceptance",
        "agent": {"name": "arete-evals-fixed-verifier", "model": None},
        "repository": "https://github.com/AreteDriver/arete-evals",
        "starting_revision": report["starting_revision"],
        "ending_revision": report["revision"],
        "subject_artifact": "manifest.json",
        "files": {
            "inspected": sorted(set(before) | set(after)),
            "modified": modified,
            "tests_added": None,
        },
        "tests": tests,
        "evaluations": [
            {
                "id": "bounded-acceptance",
                "outcome": "PASS" if report["passed"] else "FAIL",
                "evidence": ["manifest.json", "audit.json"],
            }
        ],
        "findings": {"scope_violations": None, "regressions": None, "security": None},
        "telemetry": {
            "retries": 0,
            "human_interventions": None,
            "input_tokens": None,
            "output_tokens": None,
            "elapsed_seconds": elapsed,
            "cost": None,
        },
        "provenance": {
            "recorded_at": datetime.now(UTC).isoformat(),
            "recorder": "scripts/verify_project.py",
            "method": "verifier-observed",
            "source_run_id": None,
        },
        "confidence": None,
        "human_review_required": True,
        "artifacts": artifacts,
    }
    draft = out / "receipt.draft.json"
    draft.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    finalized = out / "receipt.json"
    digest = finalize_receipt(draft, finalized)
    checked = verify_receipt(finalized, artifacts_root=out, expected_sha256=digest)
    if checked["status"] != "PASS WITH CONDITIONS":
        raise ValueError("generated receipt evidence verification failed")
    (out / "receipt-verification.json").write_text(
        json.dumps(checked, indent=2, sort_keys=True) + "\n"
    )
    (out / "receipt.txt").write_text(render_receipt(finalized) + "\n")
