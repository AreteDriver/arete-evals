"""Validate arete-evals suite and run-record artifacts without evalcore."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _mapping(value: Any, *, source: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{source.relative_to(ROOT)} must contain a mapping")
    return value


def _named_items(
    value: Any,
    *,
    field: str,
    name_field: str,
    source: Path,
) -> set[str]:
    if not isinstance(value, list):
        raise TypeError(f"{source.relative_to(ROOT)} field {field!r} must be a list")
    names: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or not isinstance(item.get(name_field), str):
            raise TypeError(
                f"{source.relative_to(ROOT)} {field}[{index}] must have a string {name_field}"
            )
        names.append(item[name_field])
    if len(names) != len(set(names)):
        raise ValueError(f"{source.relative_to(ROOT)} has duplicate {field} names")
    return set(names)


def validate_suites() -> dict[str, set[str]]:
    suites: dict[str, set[str]] = {}
    for path in sorted((ROOT / "suites").glob("*.yaml")):
        document = _mapping(
            yaml.safe_load(path.read_text(encoding="utf-8")), source=path
        )
        name = document.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{path.relative_to(ROOT)} must define a non-empty name")
        if name in suites:
            raise ValueError(f"duplicate suite name: {name}")
        metrics = document.get("metrics")
        if not isinstance(metrics, list) or not metrics:
            raise ValueError(
                f"{path.relative_to(ROOT)} must define at least one metric"
            )
        suites[name] = _named_items(
            document.get("cases"), field="cases", name_field="name", source=path
        )
    if not suites:
        raise ValueError("no suite YAML files found")
    return suites


def validate_results(suites: dict[str, set[str]]) -> int:
    count = 0
    for path in sorted((ROOT / "results").glob("*.json")):
        document = _mapping(json.loads(path.read_text(encoding="utf-8")), source=path)
        suite_name = document.get("suite_name")
        if suite_name not in suites:
            raise ValueError(
                f"{path.relative_to(ROOT)} references unknown suite {suite_name!r}"
            )
        result_names = _named_items(
            document.get("results"),
            field="results",
            name_field="case_name",
            source=path,
        )
        unknown = sorted(result_names - suites[suite_name])
        if unknown:
            raise ValueError(
                f"{path.relative_to(ROOT)} contains unknown cases: {', '.join(unknown)}"
            )
        count += 1
    if count == 0:
        raise ValueError("no JSON run records found")
    return count


def main() -> None:
    suites = validate_suites()
    result_count = validate_results(suites)
    case_count = sum(len(cases) for cases in suites.values())
    print(
        f"validated {len(suites)} suite(s), {case_count} case(s), {result_count} run record(s)"
    )


if __name__ == "__main__":
    main()
