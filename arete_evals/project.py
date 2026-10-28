"""Read-only, deterministic subset of the Arete project-folder standard.

Repository content is data: no project imports, shell, or manifest commands.
Human certification is deliberately not inferred from these mechanical checks.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tomllib
from datetime import date
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from arete_evals import __version__

MAX_BYTES = 1_048_576
MANIFEST = "PROJECT_MANIFEST.yaml"
GATES = (
    "Identity",
    "Boundary",
    "Canonical Source",
    "Current Reality",
    "Execution Direction",
    "Source Coherence",
    "Safety and Sensitivity",
)
MARKER = re.compile(r"<!-- arete:([a-z][a-z0-9_]*)=(.*?) -->")


class InputError(ValueError):
    """Unsafe, malformed, or unsupported project input."""


class StrictLoader(yaml.SafeLoader):
    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise InputError("YAML aliases are not supported")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise InputError("mapping keys must be unique strings")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


# Keep dates as strings so JSON Schema is the single type authority.
StrictLoader.yaml_implicit_resolvers = {
    key: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def safe_path(root: Path, name: str) -> Path:
    if (
        not isinstance(name, str)
        or not name
        or "\\" in name
        or ":" in name
        or any(ord(c) < 32 for c in name)
    ):
        raise InputError("invalid relative path")
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or ".git" in p.parts:
        raise InputError("path leaves permitted project content")
    if any(
        part
        in {
            ".env",
            ".env.local",
            ".ssh",
            ".gnupg",
            ".aws",
            "secrets.json",
            "id_rsa",
            "id_ed25519",
        }
        for part in p.parts
    ) or p.suffix in {".pem", ".key", ".p12"}:
        raise InputError("sensitive paths are not read by the audit")
    current = root
    for part in p.parts:
        current /= part
        if current.is_symlink():
            raise InputError("symlink paths are not accepted")
    if not current.resolve().is_relative_to(root):
        raise InputError("path escapes project root")
    return current


def read_file(root: Path, name: str) -> bytes:
    path = safe_path(root, name)
    if not stat.S_ISREG(path.stat().st_mode):
        raise InputError("expected a regular file")
    # O_NOFOLLOW also rejects a final component swapped after the path check.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as handle:
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise InputError("file exceeds 1 MiB limit")
    return data


def schema() -> dict[str, Any]:
    return json.loads(
        files("arete_evals")
        .joinpath("schemas/project-manifest-v1.schema.json")
        .read_text(encoding="utf-8")
    )


def load_manifest(root: Path) -> dict[str, Any]:
    try:
        raw = read_file(root, MANIFEST).decode("utf-8")
        # Bound parser work and nesting before object construction.
        depth = 0
        for event in yaml.parse(raw, Loader=StrictLoader):
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                if depth > 20:
                    raise InputError("YAML nesting exceeds 20 levels")
            elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
        value = yaml.load(raw, Loader=StrictLoader)
        errors = sorted(
            Draft202012Validator(schema(), format_checker=FormatChecker()).iter_errors(
                value
            ),
            key=lambda e: str(list(e.path)),
        )
        if errors:
            # Do not echo values: malformed manifests can contain credentials.
            issue = errors[0]
            location = "/".join(str(x) for x in issue.path) or "$"
            raise InputError(f"{location}: schema rule {issue.validator} failed")
        return value
    except (OSError, UnicodeError, yaml.YAMLError, RecursionError) as exc:
        raise InputError(
            f"manifest unreadable or malformed ({type(exc).__name__})"
        ) from exc


def _git(root: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_OPTIONAL_LOCKS="0",
        GIT_TERMINAL_PROMPT="0",
    )
    result = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(root),
            *args,
        ],
        capture_output=True,
        timeout=10,
        env=env,
        check=False,
    )
    if result.returncode or len(result.stdout) > MAX_BYTES:
        raise InputError("Git evidence unavailable")
    return result.stdout.decode("utf-8")


def audit_project(
    root: Path, *, as_of: date | None = None, require_clean: bool = False
) -> dict[str, Any]:
    root = root.resolve()
    today = as_of or date.today()
    findings: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    cache: dict[str, str] = {}
    bytes_read = 0

    def add(gate, status, code, message, path=MANIFEST, line=1):
        findings.append(
            dict(
                gate=gate,
                status=status,
                code=code,
                message=message,
                evidence={"path": path, "line": line},
            )
        )

    def read(name):
        nonlocal bytes_read
        if name not in cache:
            if len(cache) >= 256:
                raise InputError("too many source files")
            data = read_file(root, name)
            bytes_read += len(data)
            if bytes_read > 16 * MAX_BYTES:
                raise InputError("total source budget exceeded")
            hashes[name] = hashlib.sha256(data).hexdigest()
            cache[name] = data.decode("utf-8")
        return cache[name]

    manifest = None
    revision = None
    clean = None
    try:
        manifest = load_manifest(root)
        read(MANIFEST)
    except InputError as exc:
        add("Identity", "FAIL", "manifest.invalid", str(exc))
    if manifest is not None:
        m = manifest
        project = m["project"]
        reviewed = date.fromisoformat(project["last_reviewed"])
        age = (today - reviewed).days
        if age < 0 or age > project["review_after_days"]:
            add(
                "Current Reality",
                "FAIL",
                "review.stale",
                "review date is future or overdue",
            )
        if project["classification"] in {"paused", "archived"} and not m["lifecycle"]:
            add(
                "Execution Direction",
                "FAIL",
                "lifecycle.missing",
                "lifecycle disposition required",
            )
        for role, record in m["authority"].items():
            name = record["path"]
            try:
                text = read(name)
                if len(text.strip()) < 40 or text.strip().upper() in {"TODO", "TBD"}:
                    raise InputError("empty or placeholder authority")
            except (OSError, ValueError, UnicodeError):
                gate = {
                    "current_state": "Current Reality",
                    "roadmap": "Execution Direction",
                    "security": "Safety and Sensitivity",
                }.get(role, "Source Coherence")
                add(
                    gate,
                    "FAIL",
                    "authority.invalid",
                    f"missing or unsafe {role} authority",
                    name,
                )
        for name in m["agent"]["allowed_paths"] + m["agent"]["forbidden_paths"]:
            try:
                safe_path(root, name)
            except InputError:
                add("Boundary", "FAIL", "scope.unsafe", "invalid agent scope path")
        try:
            if not safe_path(root, m["canonical"]["documentation_root"]).is_dir():
                raise InputError("missing directory")
            read(m["standard"]["source"])
            if hashes[m["standard"]["source"]] != m["standard"]["sha256"]:
                raise InputError("standard fingerprint mismatch")
        except (OSError, ValueError, UnicodeError):
            add(
                "Source Coherence",
                "FAIL",
                "standard.invalid",
                "standard or documentation root invalid",
            )
        # Exact annotated claims; no semantic contradiction inference.
        claims = m["claims"]
        expected_docs = {
            "README.md",
            *(
                m["authority"][r]["path"]
                for r in ("current_state", "architecture", "roadmap", "agent")
            ),
        }
        claim_docs = set().union(*(set(c["documents"]) for c in claims.values()))
        for name in sorted(expected_docs - claim_docs):
            add(
                "Source Coherence",
                "FAIL",
                "claims.coverage",
                "canonical source lacks checked claims",
                name,
            )
        for key, claim in sorted(claims.items()):
            for name in claim["evidence"]:
                try:
                    read(name)
                except (OSError, ValueError, UnicodeError):
                    add(
                        "Current Reality",
                        "FAIL",
                        "claim.evidence",
                        "claim evidence unavailable",
                        name,
                    )
            for name in claim["documents"]:
                try:
                    text = read(name)
                    matches = [
                        (match, text.count("\n", 0, match.start()) + 1)
                        for match in MARKER.finditer(text)
                        if match[1] == key
                    ]
                    if len(matches) != 1 or matches[0][0][2] != claim["value"]:
                        add(
                            "Source Coherence",
                            "FAIL",
                            "claim.conflict",
                            f"claim {key} missing, duplicated or contradictory",
                            name,
                            matches[0][1] if matches else 1,
                        )
                except (OSError, ValueError, UnicodeError):
                    add(
                        "Source Coherence",
                        "FAIL",
                        "claim.source",
                        "claim source unavailable",
                        name,
                    )
        # Derive supported facts from code/config, rather than trusting agreement alone.
        if "package_version" in claims or "engine_version" in claims:
            try:
                package = tomllib.loads(read("pyproject.toml"))["project"]
                facts = {"package_version": package["version"]}
                pins = [
                    v.split("==")[1]
                    for v in package["dependencies"]
                    if v.startswith("evalcore==")
                ]
                facts["engine_version"] = pins[0] if len(pins) == 1 else None
                for key in sorted(facts.keys() & claims.keys()):
                    if claims[key]["value"] != facts[key]:
                        add(
                            "Current Reality",
                            "FAIL",
                            "claim.implementation",
                            f"{key} disagrees with package",
                            "pyproject.toml",
                        )
            except (OSError, ValueError, KeyError, TypeError):
                add(
                    "Current Reality",
                    "FAIL",
                    "package.invalid",
                    "package facts unavailable",
                    "pyproject.toml",
                )
        for name, text in sorted(cache.items()):
            for match in MARKER.finditer(text):
                if match[1] not in claims:
                    add(
                        "Source Coherence",
                        "FAIL",
                        "claim.undeclared",
                        "undeclared machine claim",
                        name,
                    )
        for command, argv in m["verification"].items():
            if argv is None:
                add(
                    "Execution Direction",
                    "WARNING",
                    "command.unknown",
                    f"{command} command UNKNOWN",
                )
        if m["verification"]["tests"] is None:
            add(
                "Execution Direction",
                "FAIL",
                "tests.missing",
                "test command is required",
            )
        try:
            ignored = read(".gitignore").splitlines()
            if ".env" not in ignored:
                raise InputError("missing .env exclusion")
        except (OSError, ValueError, UnicodeError):
            add(
                "Safety and Sensitivity",
                "FAIL",
                "secrets.policy",
                "missing .env exclusion",
                ".gitignore",
            )
        try:
            if (
                Path(_git(root, "rev-parse", "--show-toplevel").strip()).resolve()
                != root
            ):
                raise InputError("audit target is not repository root")
            try:
                _git(root, "check-ignore", "--no-index", ".env")
            except InputError:
                add(
                    "Safety and Sensitivity",
                    "FAIL",
                    "secrets.policy",
                    "Git does not exclude .env",
                    ".gitignore",
                )
            remote = _git(root, "remote", "get-url", "origin").strip()
            if remote.startswith("git@") and ":" in remote:
                host, repository = remote[4:].split(":", 1)
                remote = f"https://{host}/{repository}"
            remote = remote.removesuffix(".git").rstrip("/")
            canonical = m["canonical"]["repository"].removesuffix(".git").rstrip("/")
            if remote != canonical:
                add(
                    "Canonical Source",
                    "FAIL",
                    "canonical.conflict",
                    "origin disagrees with declared canonical repository",
                )
            revision = _git(root, "rev-parse", "HEAD").strip()
            clean = not bool(
                _git(
                    root, "status", "--porcelain=v1", "--untracked-files=normal"
                ).strip()
            )
            tracked = _git(root, "ls-files", "-z").split("\0")
            sensitive = [
                p
                for p in tracked
                if p
                and (
                    PurePosixPath(p).name
                    in {".env", ".env.local", "secrets.json", "id_rsa", "id_ed25519"}
                    or p.endswith((".pem", ".key", ".p12"))
                )
            ]
            if sensitive:
                # Deliberately do not read or reproduce suspected secret files.
                add(
                    "Safety and Sensitivity",
                    "FAIL",
                    "secrets.tracked",
                    "sensitive filenames tracked; inspect privately",
                )
            if not clean:
                add(
                    "Canonical Source",
                    "FAIL" if require_clean else "WARNING",
                    "git.dirty",
                    "working tree differs from revision",
                )
        except (OSError, ValueError, subprocess.SubprocessError, UnicodeError):
            add(
                "Canonical Source",
                "UNKNOWN",
                "git.unavailable",
                "revision/cleanliness unavailable",
            )
    gates = {}
    for gate in GATES:
        states = {f["status"] for f in findings if f["gate"] == gate}
        gates[gate] = (
            "FAIL"
            if "FAIL" in states
            else "UNKNOWN"
            if "UNKNOWN" in states
            else "WARNING"
            if "WARNING" in states
            else "PASS"
            if manifest is not None
            else "UNKNOWN"
        )
    blocked = any(v in {"FAIL", "UNKNOWN"} for v in gates.values())
    return {
        "schema_version": "project-audit-v1",
        "auditor": {
            "version": __version__,
            "implementation_sha256": hashlib.sha256(
                files("arete_evals").joinpath("project.py").read_bytes()
            ).hexdigest(),
            "manifest_schema_sha256": hashlib.sha256(
                files("arete_evals")
                .joinpath("schemas/project-manifest-v1.schema.json")
                .read_bytes()
            ).hexdigest(),
        },
        "profile": "deterministic-v1",
        "as_of": today.isoformat(),
        "project": manifest["project"]["name"] if manifest else None,
        "outcome": "FAIL" if blocked else "PASS WITH CONDITIONS",
        "automated_gates_passed": not blocked,
        "certification": "UNKNOWN",
        "score": None,
        "tests_executed": False,
        "revision": revision,
        "clean": clean,
        "gates": gates,
        "findings": findings,
        "input_sha256": dict(sorted(hashes.items())),
        "manual_review_required": [
            "orientation",
            "semantic contradiction review",
            "cold-agent review",
            "weighted classification scoring",
            "security content review",
            "hosted/local reconciliation",
        ],
    }


def render_audit(report: dict[str, Any]) -> str:
    lines = ["ARETE PROJECT AUDIT (deterministic-v1)"]
    lines += [f"{gate:25} {status}" for gate, status in report["gates"].items()]
    lines += [
        f"STATUS: {report['outcome']}",
        "Full certification: UNKNOWN; score: UNKNOWN",
        "Tests executed by audit: no",
    ]
    for item in report["findings"]:
        evidence = item["evidence"]
        lines.append(
            f"{item['status']} {item['code']}: {item['message']} "
            f"({evidence['path']}:{evidence['line']})"
        )
    lines.append(
        "Manual review required: " + ", ".join(report["manual_review_required"])
    )
    return "\n".join(lines)
