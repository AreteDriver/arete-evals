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
EXACT_FINDING_FIELDS = {
    "stale_indices",
    "contradiction_pairs",
    "deadweight_indices",
    "compression_groups",
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


def _validate_index_list(value: Any, *, total: int, source: str) -> None:
    if (
        not isinstance(value, list)
        or any(not isinstance(index, int) for index in value)
        or len(set(value)) != len(value)
        or any(index < 0 or index >= total for index in value)
    ):
        raise ValueError(f"{source}: expected unique in-bounds segment indices")


def _validate_exact_findings(
    expected: Any, *, source: str, required: bool = False
) -> None:
    if not isinstance(expected, dict):
        raise ValueError(f"{source}: expected must be an object")
    present = EXACT_FINDING_FIELDS & set(expected)
    if not present:
        if required:
            raise ValueError(f"{source}: exact finding contract is required")
        return
    missing = sorted(EXACT_FINDING_FIELDS - set(expected))
    if missing:
        raise ValueError(
            f"{source}: exact finding contract missing {', '.join(missing)}"
        )
    total = expected.get("total_segments")
    if not isinstance(total, int) or total < 0:
        raise ValueError(f"{source}: total_segments must be a non-negative integer")
    threshold = expected.get("minimum_staleness_score", 0.5)
    if not isinstance(threshold, int | float) or not 0 <= threshold <= 1:
        raise ValueError(f"{source}: minimum_staleness_score must be between 0 and 1")
    _validate_index_list(
        expected["stale_indices"], total=total, source=f"{source}:stale_indices"
    )
    _validate_index_list(
        expected["deadweight_indices"],
        total=total,
        source=f"{source}:deadweight_indices",
    )
    pairs = expected["contradiction_pairs"]
    if not isinstance(pairs, list):
        raise ValueError(f"{source}:contradiction_pairs must be a list")
    normalized_pairs: set[tuple[int, int]] = set()
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2 or pair[0] == pair[1]:
            raise ValueError(
                f"{source}: contradiction pairs require two distinct indices"
            )
        _validate_index_list(pair, total=total, source=f"{source}:contradiction_pairs")
        normalized_pairs.add(tuple(sorted(pair)))
    if len(normalized_pairs) != len(pairs):
        raise ValueError(f"{source}: contradiction pairs must be unique")
    groups = expected["compression_groups"]
    if not isinstance(groups, list):
        raise ValueError(f"{source}:compression_groups must be a list")
    normalized_groups: set[tuple[int, ...]] = set()
    for group in groups:
        if not isinstance(group, list) or len(group) < 2:
            raise ValueError(
                f"{source}: compression groups require at least two indices"
            )
        _validate_index_list(group, total=total, source=f"{source}:compression_groups")
        normalized_groups.add(tuple(sorted(group)))
    if len(normalized_groups) != len(groups):
        raise ValueError(f"{source}: compression groups must be unique")


def validate_suite(path: Path) -> dict[str, Any]:
    suite = evalcore.load_suite(path)
    cases = evalcore.load_cases(suite.dataset)
    case_ids = [case.id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError(f"{path}: duplicate case IDs")
    exact_findings_required = suite.suite == "deep-analysis-finding-quality"
    for case in cases:
        _validate_exact_findings(
            case.expected,
            source=f"{suite.dataset}:{case.id}",
            required=exact_findings_required,
        )

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
