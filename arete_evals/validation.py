"""Repository and suite-contract validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import evalcore
import yaml

REQUIRED_TREATMENT_FIELDS = {"id", "version", "kind", "config"}
TREATMENT_KINDS = {
    "baseline",
    "skill",
    "mcp",
    "instructions",
    "subagent",
    "runtime",
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def treatment_fingerprint(treatment: dict[str, Any]) -> str:
    return canonical_sha256(treatment)


def validate_treatment(value: Any, *, source: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{source}: treatment must be an object")
    missing = sorted(REQUIRED_TREATMENT_FIELDS - set(value))
    if missing:
        raise ValueError(f"{source}: treatment missing {', '.join(missing)}")
    if value["kind"] not in TREATMENT_KINDS:
        raise ValueError(f"{source}: unsupported treatment kind {value['kind']!r}")
    if not isinstance(value["config"], dict):
        raise ValueError(f"{source}: treatment config must be an object")
    return value


def validate_suite(path: Path) -> dict[str, Any]:
    suite = evalcore.load_suite(path)
    cases = evalcore.load_cases(suite.dataset)
    case_ids = [case.id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError(f"{path}: duplicate case IDs")

    variants = set(suite.variants)
    for name, knobs in suite.variants.items():
        validate_treatment(knobs.get("treatment"), source=f"{path}:{name}")

    if not suite.replay_fixtures:
        raise ValueError(f"{path}: replay_fixtures is required")
    fixture_path = Path(suite.replay_fixtures)
    fixture_data = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(fixture_data, dict):
        raise ValueError(f"{fixture_path}: fixtures must be an object")
    fixture_cases = set(fixture_data)
    expected_cases = set(case_ids)
    if fixture_cases != expected_cases:
        missing = sorted(expected_cases - fixture_cases)
        extra = sorted(fixture_cases - expected_cases)
        raise ValueError(
            f"{fixture_path}: fixture coverage missing={missing} extra={extra}"
        )
    for case_id, per_variant in fixture_data.items():
        if not isinstance(per_variant, dict):
            raise ValueError(f"{fixture_path}:{case_id} must map variants")
        missing_variants = sorted(variants - set(per_variant))
        if missing_variants:
            raise ValueError(
                f"{fixture_path}:{case_id} missing variants {missing_variants}"
            )
    return {
        "suite": suite.suite,
        "suite_hash": suite.suite_hash,
        "dataset_hash": evalcore.loader.dataset_hash(cases),
        "cases": len(cases),
        "variants": sorted(variants),
    }


def validate_historical_record(path: Path, expected_cases: set[str]) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("suite_name") != "benchgoblins-ask":
        raise ValueError(f"{path}: unexpected historical suite")
    results = document.get("results")
    if not isinstance(results, list):
        raise ValueError(f"{path}: results must be a list")
    result_cases = {item.get("case_name") for item in results if isinstance(item, dict)}
    if result_cases != expected_cases:
        raise ValueError(
            f"{path}: historical record must contain the complete case set"
        )


def validate_public_bundle(path: Path) -> None:
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "public-run-manifest-v1":
        raise ValueError(f"{manifest_path}: unsupported public manifest schema")
    if manifest.get("output_policy") not in {
        "hashes-only",
        "reviewed-full-output",
    }:
        raise ValueError(f"{manifest_path}: invalid output policy")
    if not str(manifest.get("reviewed_by", "")).strip():
        raise ValueError(f"{manifest_path}: reviewed_by is required")
    for name, metadata in manifest.get("artifacts", {}).items():
        artifact = path / name
        if not artifact.is_file():
            raise ValueError(f"{path}: missing public artifact {name}")
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if digest != metadata.get("sha256"):
            raise ValueError(f"{path}: checksum mismatch for {name}")
