"""Deterministic, structured graders for response-integrity suites."""

from __future__ import annotations

import json
import re
from typing import Any

from evalcore import models, refs
from evalcore.graders import base

_LEAKED_KEY = re.compile(
    r"(?:\{|,)\s*[\"'](?:recommendations|drop_candidates)[\"']\s*:",
    re.IGNORECASE,
)
_FALLBACK_DECISIONS = {"unable to determine", "unknown", "n/a"}


def _score(
    *, name: str, metric: str, case_id: str, passed: bool, detail: str
) -> models.Score:
    return models.Score(
        grader=name,
        metric=metric,
        value=1.0 if passed else 0.0,
        passed=passed,
        detail=detail,
        case_id=case_id,
    )


def _value_score(
    *,
    name: str,
    metric: str,
    case_id: str,
    value: float,
    passed: bool,
    detail: str,
) -> models.Score:
    return models.Score(
        grader=name,
        metric=metric,
        value=value,
        passed=passed,
        detail=detail,
        case_id=case_id,
    )


def _classification_metrics(
    expected: set[Any], predicted: set[Any]
) -> tuple[float, float, float, int, int, int]:
    """Return precision, recall, F1 and counts with useful empty-set semantics."""
    true_positives = len(expected & predicted)
    false_positives = len(predicted - expected)
    false_negatives = len(expected - predicted)
    precision = (
        true_positives / (true_positives + false_positives) if predicted else 1.0
    )
    recall = true_positives / len(expected) if expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1, true_positives, false_positives, false_negatives


def _decode_response(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if isinstance(value, dict):
        return value, None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None, "response is not valid JSON"
        if isinstance(parsed, dict):
            return parsed, None
    return None, "response must be a JSON object"


@base.register("structured_response")
class StructuredResponseGrader:
    """Validate decoded response structure and case-specific expectations.

    This grader intentionally operates on a parsed object. Regex is used only
    inside the decoded rationale to identify the historical nested-JSON leak;
    it is not used as a substitute for schema validation.
    """

    def __init__(
        self, field: str = "output.response", name: str = "structured_response"
    ) -> None:
        self.field = field
        self.name = name

    def grade(self, case: models.Case, output: models.Output) -> list[models.Score]:
        context = {
            "input": case.input,
            "expected": case.expected or {},
            "output": output.fields,
            "case": case.model_dump(),
        }
        response, decode_error = _decode_response(refs.resolve_ref(context, self.field))
        expected = case.expected or {}
        checks: list[tuple[str, bool, str]] = []

        schema_ok = response is not None and output.error is None
        checks.append(
            (
                "schema_valid",
                schema_ok,
                output.error or decode_error or "structured object",
            )
        )
        if response is None:
            checks.extend(
                [
                    ("decision_valid", False, "not evaluated: invalid schema"),
                    ("rationale_valid", False, "not evaluated: invalid schema"),
                    ("no_serialized_json_leak", False, "not evaluated: invalid schema"),
                    ("details_valid", False, "not evaluated: invalid schema"),
                ]
            )
            return self._finish(case.id, checks)

        decision = response.get("decision")
        decision_text = decision.strip() if isinstance(decision, str) else ""
        decision_ok = (
            bool(decision_text) and decision_text.casefold() not in _FALLBACK_DECISIONS
        )
        pattern = expected.get("decision_pattern")
        if decision_ok and isinstance(pattern, str):
            decision_ok = re.search(pattern, decision_text, re.IGNORECASE) is not None
        checks.append(
            (
                "decision_valid",
                decision_ok,
                "non-empty decision"
                if decision_ok
                else "missing, fallback, or unexpected decision",
            )
        )

        rationale = response.get("rationale")
        minimum = expected.get("rationale_min_chars", 20)
        rationale_ok = isinstance(rationale, str) and len(rationale.strip()) >= minimum
        checks.append(
            (
                "rationale_valid",
                rationale_ok,
                f"minimum {minimum} characters",
            )
        )

        leak = isinstance(rationale, str) and _LEAKED_KEY.search(rationale) is not None
        if isinstance(rationale, str) and rationale.lstrip().startswith(("{", "[")):
            try:
                nested = json.loads(rationale)
            except json.JSONDecodeError:
                nested = None
            leak = leak or isinstance(nested, dict | list)
        checks.append(
            (
                "no_serialized_json_leak",
                not leak,
                "nested JSON detected in rationale" if leak else "clean rationale",
            )
        )

        details = response.get("details")
        details_required = bool(expected.get("details_required"))
        details_ok = (
            isinstance(details, dict)
            if details_required
            else details is None or isinstance(details, dict)
        )
        if details_ok and isinstance(details, dict):
            min_recommendations = expected.get("min_recommendations")
            if isinstance(min_recommendations, int):
                recommendations = details.get("recommendations")
                details_ok = (
                    isinstance(recommendations, list)
                    and len(recommendations) >= min_recommendations
                )
            min_drops = expected.get("min_drop_candidates")
            if details_ok and isinstance(min_drops, int):
                drops = details.get("drop_candidates")
                details_ok = isinstance(drops, list) and len(drops) >= min_drops
        checks.append(
            (
                "details_valid",
                details_ok,
                "case-specific details contract",
            )
        )
        return self._finish(case.id, checks)

    def _finish(
        self, case_id: str, checks: list[tuple[str, bool, str]]
    ) -> list[models.Score]:
        scores = [
            _score(
                name=self.name,
                metric=metric,
                case_id=case_id,
                passed=passed,
                detail=detail,
            )
            for metric, passed, detail in checks
        ]
        failed = [metric for metric, passed, _ in checks if not passed]
        scores.append(
            _score(
                name=self.name,
                metric="contract_pass",
                case_id=case_id,
                passed=not failed,
                detail="all checks passed"
                if not failed
                else f"failed: {', '.join(failed)}",
            )
        )
        return scores


def _integer_set(values: Any) -> set[int] | None:
    if not isinstance(values, list) or any(
        not isinstance(item, int) for item in values
    ):
        return None
    return set(values)


def _pair_set(values: Any) -> set[tuple[int, int]] | None:
    if not isinstance(values, list):
        return None
    pairs: set[tuple[int, int]] = set()
    for pair in values:
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or any(not isinstance(index, int) for index in pair)
            or pair[0] == pair[1]
        ):
            return None
        pairs.add(tuple(sorted((pair[0], pair[1]))))
    return pairs


def _group_set(values: Any) -> set[tuple[int, ...]] | None:
    if not isinstance(values, list):
        return None
    groups: set[tuple[int, ...]] = set()
    for group in values:
        if (
            not isinstance(group, list)
            or len(group) < 2
            or any(not isinstance(index, int) for index in group)
            or len(set(group)) != len(group)
        ):
            return None
        groups.add(tuple(sorted(group)))
    return groups


@base.register("context_hygiene_report")
class ContextHygieneReportGrader:
    """Grade structural integrity and frozen expected findings in a hygiene report."""

    def __init__(
        self, field: str = "output.report", name: str = "context_hygiene_report"
    ) -> None:
        self.field = field
        self.name = name

    def grade(self, case: models.Case, output: models.Output) -> list[models.Score]:
        context = {
            "input": case.input,
            "expected": case.expected or {},
            "output": output.fields,
            "case": case.model_dump(),
        }
        report = refs.resolve_ref(context, self.field)
        expected = case.expected or {}
        checks: list[tuple[str, bool, str]] = []
        required_keys = {
            "total_segments",
            "grade",
            "staleness_results",
            "contradictions",
            "deadweight",
            "compression_candidates",
            "mode",
        }
        schema_ok = (
            output.error is None
            and isinstance(report, dict)
            and required_keys.issubset(report)
            and report.get("mode") in {"fast", "deep"}
            and report.get("grade") in {"A", "B", "C", "D", "F"}
            and all(
                isinstance(report.get(key), list)
                for key in (
                    "staleness_results",
                    "contradictions",
                    "deadweight",
                    "compression_candidates",
                )
            )
        )
        checks.append(
            (
                "report_schema_valid",
                schema_ok,
                output.error or "required report fields and types",
            )
        )
        if not schema_ok:
            checks.extend(
                [
                    (
                        "finding_references_valid",
                        False,
                        "not evaluated: invalid schema",
                    ),
                    (
                        "expected_findings_recalled",
                        False,
                        "not evaluated: invalid schema",
                    ),
                ]
            )
            return self._finish(case.id, checks)

        total = report["total_segments"]
        expected_total = expected.get("total_segments")
        total_ok = isinstance(total, int) and total >= 0
        if isinstance(expected_total, int):
            total_ok = total_ok and total == expected_total

        references: list[int] = []
        valid_shapes = True
        for item in report["staleness_results"]:
            if not isinstance(item, dict) or not isinstance(
                item.get("segment_index"), int
            ):
                valid_shapes = False
                continue
            references.append(item["segment_index"])
            score = item.get("score")
            valid_shapes = (
                valid_shapes and isinstance(score, int | float) and 0 <= score <= 1
            )
        for item in report["deadweight"]:
            if not isinstance(item, dict) or not isinstance(
                item.get("segment_index"), int
            ):
                valid_shapes = False
                continue
            references.append(item["segment_index"])
        for item in report["contradictions"]:
            if not isinstance(item, dict):
                valid_shapes = False
                continue
            pair = (item.get("segment_a"), item.get("segment_b"))
            if any(not isinstance(index, int) for index in pair) or pair[0] == pair[1]:
                valid_shapes = False
                continue
            references.extend(pair)
            confidence = item.get("confidence")
            valid_shapes = (
                valid_shapes
                and isinstance(confidence, int | float)
                and 0 <= confidence <= 1
            )
        for item in report["compression_candidates"]:
            if not isinstance(item, dict):
                valid_shapes = False
                continue
            indices = _integer_set(item.get("segment_indices"))
            if (
                indices is None
                or len(indices) < 2
                or len(indices) != len(item["segment_indices"])
            ):
                valid_shapes = False
                continue
            references.extend(indices)
        references_ok = (
            total_ok
            and valid_shapes
            and all(0 <= index < total for index in references)
        )
        checks.append(
            (
                "finding_references_valid",
                references_ok,
                "finding indices and numeric bounds",
            )
        )

        minimum_staleness = expected.get("minimum_staleness_score", 0.5)
        staleness_threshold_valid = (
            isinstance(minimum_staleness, int | float) and 0 <= minimum_staleness <= 1
        )
        threshold = minimum_staleness if staleness_threshold_valid else 0.5
        stale_found = {
            item["segment_index"]
            for item in report["staleness_results"]
            if isinstance(item, dict)
            and isinstance(item.get("segment_index"), int)
            and isinstance(item.get("score"), int | float)
            and item["score"] >= threshold
        }
        deadweight_found = {
            item["segment_index"]
            for item in report["deadweight"]
            if isinstance(item, dict) and isinstance(item.get("segment_index"), int)
        }
        contradictions_found = {
            tuple(sorted((item["segment_a"], item["segment_b"])))
            for item in report["contradictions"]
            if isinstance(item, dict)
            and isinstance(item.get("segment_a"), int)
            and isinstance(item.get("segment_b"), int)
        }
        compression_found = {
            tuple(sorted(indices))
            for item in report["compression_candidates"]
            if isinstance(item, dict)
            and (indices := _integer_set(item.get("segment_indices"))) is not None
        }

        exact_keys = {
            "stale_indices",
            "contradiction_pairs",
            "deadweight_indices",
            "compression_groups",
        }
        if exact_keys & set(expected):
            if not exact_keys.issubset(expected):
                missing = ", ".join(sorted(exact_keys - set(expected)))
                checks.append(
                    (
                        "expected_findings_valid",
                        False,
                        f"exact finding contract missing: {missing}",
                    )
                )
                return self._finish(case.id, checks)
            expected_sets = {
                "staleness": _integer_set(expected["stale_indices"]),
                "contradiction": _pair_set(expected["contradiction_pairs"]),
                "deadweight": _integer_set(expected["deadweight_indices"]),
                "compression": _group_set(expected["compression_groups"]),
            }
            if not staleness_threshold_valid or any(
                values is None for values in expected_sets.values()
            ):
                checks.append(
                    (
                        "expected_findings_valid",
                        False,
                        "exact finding contract contains invalid values",
                    )
                )
                return self._finish(case.id, checks)

            checks.append(("expected_findings_valid", True, "exact finding contract"))
            predicted_sets = {
                "staleness": stale_found,
                "contradiction": contradictions_found,
                "deadweight": deadweight_found,
                "compression": compression_found,
            }
            metric_scores: list[models.Score] = []
            total_tp = total_fp = total_fn = 0
            for category, expected_values in expected_sets.items():
                assert expected_values is not None
                precision, recall, f1, tp, fp, fn = _classification_metrics(
                    expected_values, predicted_sets[category]
                )
                total_tp += tp
                total_fp += fp
                total_fn += fn
                detail = f"tp={tp} fp={fp} fn={fn}"
                for metric, value in (
                    (f"{category}_precision", precision),
                    (f"{category}_recall", recall),
                    (f"{category}_f1", f1),
                ):
                    metric_scores.append(
                        _value_score(
                            name=self.name,
                            metric=metric,
                            case_id=case.id,
                            value=value,
                            passed=value == 1.0,
                            detail=detail,
                        )
                    )

            aggregate_precision = (
                total_tp / (total_tp + total_fp) if total_tp + total_fp else 1.0
            )
            aggregate_recall = (
                total_tp / (total_tp + total_fn) if total_tp + total_fn else 1.0
            )
            aggregate_f1 = (
                2
                * aggregate_precision
                * aggregate_recall
                / (aggregate_precision + aggregate_recall)
                if aggregate_precision + aggregate_recall
                else 0.0
            )
            aggregate_detail = f"micro tp={total_tp} fp={total_fp} fn={total_fn}"
            for metric, value in (
                ("finding_precision", aggregate_precision),
                ("finding_recall", aggregate_recall),
                ("finding_f1", aggregate_f1),
            ):
                metric_scores.append(
                    _value_score(
                        name=self.name,
                        metric=metric,
                        case_id=case.id,
                        value=value,
                        passed=value == 1.0,
                        detail=aggregate_detail,
                    )
                )
            metric_scores.append(
                _score(
                    name=self.name,
                    metric="expected_findings_recalled",
                    case_id=case.id,
                    passed=aggregate_recall == 1.0,
                    detail=aggregate_detail,
                )
            )
            base_scores = self._finish(case.id, checks)
            contract = base_scores.pop()
            exact_match = aggregate_precision == 1.0 and aggregate_recall == 1.0
            contract = _score(
                name=self.name,
                metric="contract_pass",
                case_id=case.id,
                passed=bool(contract.passed and exact_match),
                detail=(
                    "all checks passed"
                    if contract.passed and exact_match
                    else "finding set differs from exact expected outcome"
                ),
            )
            return base_scores + metric_scores + [contract]

        required_stale = _integer_set(expected.get("required_stale_indices", []))
        required_deadweight = _integer_set(
            expected.get("required_deadweight_indices", [])
        )
        required_pairs = _pair_set(expected.get("required_contradiction_pairs", []))
        minimum_compression = expected.get("minimum_compression_candidates", 0)
        compression_minimum_valid = (
            isinstance(minimum_compression, int) and minimum_compression >= 0
        )
        recall_ok = (
            staleness_threshold_valid
            and compression_minimum_valid
            and required_stale is not None
            and required_deadweight is not None
            and required_pairs is not None
            and required_stale.issubset(stale_found)
            and required_deadweight.issubset(deadweight_found)
            and required_pairs.issubset(contradictions_found)
            and len(report["compression_candidates"]) >= minimum_compression
        )
        checks.append(
            (
                "expected_findings_recalled",
                recall_ok,
                "frozen required findings",
            )
        )
        return self._finish(case.id, checks)

    def _finish(
        self, case_id: str, checks: list[tuple[str, bool, str]]
    ) -> list[models.Score]:
        scores = [
            _score(
                name=self.name,
                metric=metric,
                case_id=case_id,
                passed=passed,
                detail=detail,
            )
            for metric, passed, detail in checks
        ]
        failed = [metric for metric, passed, _ in checks if not passed]
        scores.append(
            _score(
                name=self.name,
                metric="contract_pass",
                case_id=case_id,
                passed=not failed,
                detail="all checks passed"
                if not failed
                else f"failed: {', '.join(failed)}",
            )
        )
        return scores
