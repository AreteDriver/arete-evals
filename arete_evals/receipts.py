"""Versioned work records; integrity evidence never authenticates work claims."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from arete_evals.project import MAX_BYTES, InputError, read_file, safe_path


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise InputError("duplicate JSON keys")
        value[key] = item
    return value


def _bounded(value: Any, depth: int = 0) -> None:
    if depth > 20:
        raise InputError("receipt nesting exceeds 20 levels")
    if isinstance(value, float) and not math.isfinite(value):
        raise InputError("nonfinite numbers are not supported")
    if isinstance(value, dict):
        for item in value.values():
            _bounded(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _bounded(item, depth + 1)


def load_document(path: Path) -> dict[str, Any]:
    try:
        data = read_file(path.parent.resolve(), path.name)
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
        _bounded(value)
        validate_document(value)
        return value
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, InputError):
            raise
        raise InputError("receipt is unreadable or invalid JSON") from exc


def _path(name: str) -> None:
    if PurePosixPath(name).as_posix() != name or name == ".":
        raise InputError("receipt paths must be canonical relative file paths")
    # Lexical/sensitive checks without consulting the current working directory.
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        raise InputError("receipt path escapes its artifact root")
    if any(
        part
        in {
            ".git",
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
    ):
        raise InputError("sensitive paths are not receipt evidence")
    if p.suffix in {".pem", ".key", ".p12"}:
        raise InputError("sensitive paths are not receipt evidence")


def validate_document(document: Any) -> None:
    _bounded(document)
    contract = json.loads(
        files("arete_evals")
        .joinpath("schemas/work-receipt-v1.schema.json")
        .read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(contract, format_checker=FormatChecker())
    if not validator.is_valid(document):
        # Values and arbitrary keys may contain sensitive input. Do not echo them.
        raise InputError(
            "work-receipt-v1 schema validation failed; check required fields and types"
        )
    receipt = document.get("receipt", document)
    artifacts = receipt["artifacts"]
    ids = [a["id"] for a in artifacts]
    paths = [a["path"] for a in artifacts]
    if len(set(ids)) != len(ids) or len(set(paths)) != len(paths):
        raise InputError("artifact IDs and paths must be unique")
    if sum(a["bytes"] for a in artifacts) > 16 * MAX_BYTES:
        raise InputError("declared artifacts exceed 16 MiB")
    for name in paths:
        _path(name)
    for names in receipt["files"].values():
        for name in names or []:
            _path(name)
    if (
        receipt["subject_artifact"] is not None
        and receipt["subject_artifact"] not in ids
    ):
        raise InputError("subject artifact is not declared")
    for category in ("tests", "evaluations"):
        checks = receipt[category] or []
        if len({c["id"] for c in checks}) != len(checks):
            raise InputError("check IDs must be unique within their category")
        for check in checks:
            if not set(check["evidence"]).issubset(ids):
                raise InputError("check refers to undeclared evidence")
            if check["outcome"] == "PASS":
                if not check["evidence"]:
                    raise InputError("reported PASS requires evidence references")
                if category == "tests":
                    counts = check["counts"]
                    if (
                        counts is None
                        or counts["passed"] == 0
                        or any(counts[k] for k in ("failed", "errors", "skipped"))
                    ):
                        raise InputError(
                            "reported PASS requires positive passes "
                            "and no failures/errors/skips"
                        )
    # FormatChecker enforces the timestamp; require an explicit offset as well.
    if (
        datetime.fromisoformat(
            receipt["provenance"]["recorded_at"].replace("Z", "+00:00")
        ).tzinfo
        is None
    ):
        raise InputError("recorded_at requires a timezone")


def canonical_bytes(receipt: dict[str, Any]) -> bytes:
    return json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def finalize_receipt(draft: Path, output: Path) -> str:
    receipt = load_document(draft)
    if receipt["schema_version"] != "agent-work-receipt-v1":
        raise InputError("finalize requires a draft receipt")
    digest = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
    envelope = {
        "schema_version": "finalized-work-receipt-v1",
        "receipt": receipt,
        "integrity": {
            "algorithm": "sha256",
            "canonicalization": "arete-json-v1",
            "sha256": digest,
        },
    }
    encoded = (
        json.dumps(envelope, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()
    if len(encoded) > MAX_BYTES:
        raise InputError("finalized receipt exceeds 1 MiB")
    destination = safe_path(output.parent.resolve(), output.name)
    fd = os.open(
        destination,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(fd, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return digest


def verified_envelope(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    document = load_document(path)
    if document["schema_version"] != "finalized-work-receipt-v1":
        raise InputError("verification requires a finalized receipt")
    digest = hashlib.sha256(canonical_bytes(document["receipt"])).hexdigest()
    if digest != document["integrity"]["sha256"]:
        raise InputError("receipt integrity mismatch")
    if expected_sha256 is not None and (
        not re.fullmatch(r"[a-f0-9]{64}", expected_sha256) or digest != expected_sha256
    ):
        raise InputError("receipt does not match the caller's expected digest")
    return document


def verify_receipt(
    path: Path,
    *,
    artifacts_root: Path | None = None,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    document = verified_envelope(path, expected_sha256)
    receipt = document["receipt"]
    artifacts = receipt["artifacts"]
    checks = []
    total = 0
    for artifact in artifacts:
        state = "UNKNOWN"
        if artifacts_root is not None:
            try:
                data = read_file(artifacts_root.resolve(), artifact["path"])
                total += len(data)
                state = (
                    "PASS"
                    if (
                        len(data) == artifact["bytes"]
                        and hashlib.sha256(data).hexdigest() == artifact["sha256"]
                    )
                    else "FAIL"
                )
                if total > 16 * MAX_BYTES:
                    raise InputError("artifact read budget exceeded")
            except (OSError, ValueError):
                state = "FAIL"
        checks.append({"id": artifact["id"], "status": state})
        if total > 16 * MAX_BYTES:
            break
    content_verified = bool(checks) and all(c["status"] == "PASS" for c in checks)
    subject_bound = content_verified and receipt["subject_artifact"] is not None
    strength = (
        "ANCHORED_CONTENT"
        if subject_bound and expected_sha256 is not None
        else "CONTENT_CHECKED"
        if content_verified
        else "RECORDED"
    )
    status = (
        "FAIL"
        if any(c["status"] == "FAIL" for c in checks)
        else ("PASS WITH CONDITIONS" if subject_bound else "UNKNOWN")
    )
    return {
        "schema_version": "receipt-verification-v1",
        "verification_scope": "receipt-and-artifact-integrity",
        "status": status,
        "receipt_sha256": document["integrity"]["sha256"],
        "integrity": "ANCHORED" if expected_sha256 is not None else "SELF_CONSISTENT",
        "evidence_strength": strength,
        "artifacts": checks,
        "subject_bound": subject_bound,
        "work_acceptance": "UNKNOWN",
        "authenticity": "UNKNOWN",
        "independent_reproduction": "UNKNOWN",
        "human_approval": "UNKNOWN",
        "human_review_required": receipt["human_review_required"],
    }


def render_receipt(path: Path) -> str:
    document = verified_envelope(path)
    r = document["receipt"]
    lines = [
        "AGENT WORK RECEIPT",
        f"Task: {r['task_id']}",
        f"Repository: {r['repository']}",
        f"Agent: {r['agent']['name'] or 'UNKNOWN'}; "
        f"model: {r['agent']['model'] or 'UNKNOWN'}",
        f"Start: {r['starting_revision'] or 'UNKNOWN'}",
        f"End: {r['ending_revision'] or 'UNKNOWN'}",
        f"Receipt SHA-256: {document['integrity']['sha256']}",
        "Claims below are reported, not independently authenticated.",
    ]
    for category in (
        "files",
        "findings",
        "telemetry",
        "provenance",
        "confidence",
        "subject_artifact",
        "artifacts",
    ):
        lines.append(f"{category}: " + json.dumps(r[category], sort_keys=True))
    for category in ("tests", "evaluations"):
        lines.append(f"{category}: " + json.dumps(r[category], sort_keys=True))
    lines.extend(
        [
            f"Human review required (reported): {r['human_review_required']}",
            "Work acceptance, authenticity, independent reproduction "
            "and human approval: UNKNOWN",
            "Artifact bytes were not checked by render; use receipt verify.",
        ]
    )
    return "\n".join(lines)
