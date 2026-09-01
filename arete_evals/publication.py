"""Explicit, review-gated export from private run bundles to public artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _verify_private_bundle(bundle: Path, manifest: dict[str, Any]) -> None:
    for name, metadata in manifest.get("artifacts", {}).items():
        path = bundle / name
        if not path.is_file():
            raise ValueError(f"private bundle is missing {name}")
        if _sha256_bytes(path.read_bytes()) != metadata.get("sha256"):
            raise ValueError(f"private bundle checksum mismatch: {name}")


def _public_output_rows(
    run_path: Path, *, variant: str, include_outputs: bool
) -> list[dict[str, Any]]:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    rows = []
    for result in run["results"]:
        fields = result["output"].get("fields", {})
        response = fields.get("response")
        encoded = json.dumps(
            response, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        row = {
            "variant": variant,
            "case_id": result["case"]["id"],
            "sample_idx": result["sample_idx"],
            "response_sha256": _sha256_bytes(encoded),
            "response_bytes": len(encoded),
        }
        if include_outputs:
            row["response"] = response
        rows.append(row)
    return rows


def publish_bundle(
    *,
    private_bundle: Path,
    public_root: Path,
    reviewed_by: str,
    include_outputs: bool = False,
    published_at: str | None = None,
) -> Path:
    """Create a non-overwritable public derivative after human review."""
    if not reviewed_by.strip():
        raise ValueError("reviewed_by is required for public export")
    manifest_path = private_bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _verify_private_bundle(private_bundle, manifest)

    destination = public_root / manifest["bundle_id"]
    destination.mkdir(parents=True, exist_ok=False)
    public_artifacts: dict[str, dict[str, Any]] = {}
    for name in ("comparison.json", "scores.jsonl", "report.md"):
        source = private_bundle / name
        target = destination / name
        target.write_bytes(source.read_bytes())
        public_artifacts[name] = {
            "sha256": _sha256_bytes(target.read_bytes()),
            "bytes": target.stat().st_size,
        }

    rows = []
    rows.extend(
        _public_output_rows(
            private_bundle / "baseline.run.json",
            variant="baseline",
            include_outputs=include_outputs,
        )
    )
    rows.extend(
        _public_output_rows(
            private_bundle / "candidate.run.json",
            variant="candidate",
            include_outputs=include_outputs,
        )
    )
    outputs_path = destination / "outputs.jsonl"
    with outputs_path.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    public_artifacts[outputs_path.name] = {
        "sha256": _sha256_bytes(outputs_path.read_bytes()),
        "bytes": outputs_path.stat().st_size,
    }

    public_manifest = {
        "schema_version": "public-run-manifest-v1",
        "bundle_id": manifest["bundle_id"],
        "published_at": published_at or datetime.now(UTC).isoformat(),
        "reviewed_by": reviewed_by,
        "output_policy": "reviewed-full-output" if include_outputs else "hashes-only",
        "source_manifest_sha256": _sha256_bytes(manifest_path.read_bytes()),
        "suite": manifest["suite"],
        "suite_hash": manifest["suite_hash"],
        "dataset_version": manifest["dataset_version"],
        "dataset_hash": manifest["dataset_hash"],
        "engine": manifest["engine"],
        "mode": manifest["mode"],
        "revision": manifest.get("revision"),
        "verdict": manifest["verdict"],
        "treatments": manifest["treatments"],
        "artifacts": public_artifacts,
    }
    _write_json(destination / "manifest.json", public_manifest)
    return destination
