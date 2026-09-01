"""Validate canonical suites, schemas, and explicitly historical artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from arete_evals import plugin as plugin  # noqa: F401
from arete_evals.validation import (
    validate_historical_record,
    validate_public_bundle,
    validate_suite,
)

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    suite_paths = sorted((ROOT / "suites").glob("*.yaml"))
    if not suite_paths:
        raise ValueError("no canonical suites found")
    summaries = [validate_suite(path) for path in suite_paths]

    schema_paths = sorted((ROOT / "schemas").glob("*.json"))
    for path in schema_paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ValueError(f"{path}: unsupported or missing JSON Schema version")

    legacy_suite = yaml.safe_load(
        (ROOT / "case-studies" / "benchgoblins-ask" / "suite-v0.yaml").read_text(
            encoding="utf-8"
        )
    )
    historical_cases = {case["name"] for case in legacy_suite["cases"]}
    validate_historical_record(
        ROOT / "results" / "benchgoblins-ask-6ea664d3.json", historical_cases
    )
    public_bundles = sorted((ROOT / "runs" / "public").glob("*/manifest.json"))
    for manifest in public_bundles:
        validate_public_bundle(manifest.parent)
    total_cases = sum(item["cases"] for item in summaries)
    suite_summary = (
        f"validated {len(summaries)} canonical suite(s), "
        f"{total_cases} versioned cases, "
    )
    print(
        suite_summary
        + f"{len(schema_paths)} schemas, {len(public_bundles)} public bundle(s), "
        "and 1 historical record"
    )


if __name__ == "__main__":
    main()
