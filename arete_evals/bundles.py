"""Immutable run-bundle creation for replay and live suite executions."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import evalcore
from evalcore import compare, report

from arete_evals.validation import treatment_fingerprint, validate_suite


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _score_rows(run: evalcore.models.RunResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in run.results:
        for score in result.scores:
            rows.append(
                {
                    "run_id": run.run_id,
                    "variant": result.variant_name,
                    "case_id": result.case.id,
                    "sample_idx": result.sample_idx,
                    "grader": score.grader,
                    "metric": score.metric,
                    "value": score.value,
                    "passed": score.passed,
                    "detail": score.detail,
                }
            )
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def create_bundle(
    *,
    suite_path: Path,
    output_root: Path,
    baseline_name: str = "baseline",
    candidate_name: str = "candidate",
    mode: str = "replay",
    revision: str | None = None,
    created_at: str | None = None,
    bundle_id: str | None = None,
) -> Path:
    """Run both variants and persist a non-overwritable evidence bundle."""
    resolved_id = bundle_id or (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    bundle = output_root / resolved_id
    if bundle.exists():
        raise FileExistsError(bundle)
    if mode != "replay" and not revision:
        raise ValueError("live runs require --revision for target provenance")
    validation = validate_suite(suite_path)
    suite = evalcore.load_suite(suite_path)
    if mode != "replay":
        placeholders = {"recorded-fixture", "target-configured", "unknown"}
        for name in (baseline_name, candidate_name):
            model = suite.variants[name].get("model")
            if not isinstance(model, str) or model in placeholders:
                raise ValueError(
                    f"live variant {name!r} requires an exact model identifier"
                )
    timestamp = created_at or datetime.now(UTC).isoformat()
    baseline = evalcore.run_suite_sync(
        suite,
        baseline_name,
        mode=mode,
        revision=revision,
        created_at=timestamp,
    )
    candidate = evalcore.run_suite_sync(
        suite,
        candidate_name,
        mode=mode,
        revision=revision,
        created_at=timestamp,
    )
    comparison = compare.compare(
        baseline.scorecard, candidate.scorecard, suite.thresholds
    )

    bundle.mkdir(parents=True, exist_ok=False)

    baseline_path = bundle / "baseline.run.json"
    candidate_path = bundle / "candidate.run.json"
    comparison_path = bundle / "comparison.json"
    scores_path = bundle / "scores.jsonl"
    report_path = bundle / "report.md"
    _write_json(baseline_path, baseline.model_dump(mode="json"))
    _write_json(candidate_path, candidate.model_dump(mode="json"))
    _write_json(comparison_path, comparison.model_dump(mode="json"))
    _write_jsonl(scores_path, _score_rows(baseline) + _score_rows(candidate))
    report_path.write_text(
        "\n\n".join(
            [
                report.render_scorecard(baseline.scorecard),
                report.render_scorecard(candidate.scorecard),
                report.render_comparison(comparison),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    artifacts = {
        path.name: {"sha256": _sha256_file(path), "bytes": path.stat().st_size}
        for path in [
            baseline_path,
            candidate_path,
            comparison_path,
            scores_path,
            report_path,
        ]
    }
    treatments = {}
    for name in (baseline_name, candidate_name):
        treatment = suite.variants[name]["treatment"]
        treatments[name] = {
            **treatment,
            "fingerprint": treatment_fingerprint(treatment),
        }
    manifest = {
        "schema_version": "run-manifest-v1",
        "bundle_id": resolved_id,
        "created_at": timestamp,
        "project": suite.project,
        "suite": suite.suite,
        "suite_hash": validation["suite_hash"],
        "dataset_version": suite.dataset_version,
        "dataset_hash": validation["dataset_hash"],
        "engine": {"name": "evalcore", "version": evalcore.__version__},
        "mode": mode,
        "revision": revision,
        "outputs_truncated": False,
        "privacy": {
            "classification": "private-full-output",
            "public_export_reviewed": False,
        },
        "treatments": treatments,
        "verdict": comparison.verdict,
        "artifacts": artifacts,
    }
    _write_json(bundle / "manifest.json", manifest)
    return bundle
