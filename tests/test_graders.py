from __future__ import annotations

import json
import unittest

from evalcore import models

from arete_evals.graders import ContextHygieneReportGrader, StructuredResponseGrader


class StructuredResponseGraderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.grader = StructuredResponseGrader()

    def grade(self, response, expected=None):
        case = models.Case(id="case", input={}, expected=expected or {})
        output = models.Output(fields={"response": response})
        return {score.metric: score for score in self.grader.grade(case, output)}

    def test_valid_plain_word_recommendations_is_not_a_leak(self) -> None:
        scores = self.grade(
            {
                "decision": "Recommend A",
                "rationale": (
                    "These recommendations are ordinary prose and contain no "
                    "embedded object."
                ),
            }
        )
        self.assertTrue(scores["no_serialized_json_leak"].passed)
        self.assertTrue(scores["contract_pass"].passed)

    def test_whitespace_prefixed_json_object_is_detected(self) -> None:
        scores = self.grade(
            {
                "decision": "Recommend A",
                "rationale": '   {"recommendations": ["A"], "summary": "Choose A"}',
            }
        )
        self.assertFalse(scores["no_serialized_json_leak"].passed)
        self.assertFalse(scores["contract_pass"].passed)

    def test_mid_string_escaped_key_shape_is_detected(self) -> None:
        scores = self.grade(
            {
                "decision": "Recommend A",
                "rationale": (
                    'prefix {"drop_candidates": ["C"]} suffix for the response'
                ),
            }
        )
        self.assertFalse(scores["no_serialized_json_leak"].passed)

    def test_json_encoded_response_object_is_accepted(self) -> None:
        response = json.dumps(
            {
                "decision": "Proceed",
                "rationale": (
                    "The response is encoded once and remains structurally valid."
                ),
            }
        )
        self.assertTrue(self.grade(response)["contract_pass"].passed)

    def test_invalid_json_fails_schema_and_contract(self) -> None:
        scores = self.grade("not json")
        self.assertFalse(scores["schema_valid"].passed)
        self.assertFalse(scores["contract_pass"].passed)

    def test_fallback_decision_fails(self) -> None:
        scores = self.grade(
            {
                "decision": "Unable to determine",
                "rationale": (
                    "This explanation is long enough but the decision is a fallback."
                ),
            }
        )
        self.assertFalse(scores["decision_valid"].passed)

    def test_case_specific_recommendation_count_is_enforced(self) -> None:
        scores = self.grade(
            {
                "decision": "Recommend A",
                "rationale": (
                    "Only two recommendations were returned when three were required."
                ),
                "details": {"recommendations": ["A", "B"]},
            },
            {"details_required": True, "min_recommendations": 3},
        )
        self.assertFalse(scores["details_valid"].passed)

    def test_case_specific_decision_pattern_is_enforced(self) -> None:
        scores = self.grade(
            {
                "decision": "Consider the proposal",
                "rationale": (
                    "The response avoids the explicit accept or reject determination."
                ),
            },
            {"decision_pattern": r"^(accept|reject)\b"},
        )
        self.assertFalse(scores["decision_valid"].passed)


class ContextHygieneReportGraderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.grader = ContextHygieneReportGrader()

    def grade(self, report, expected):
        case = models.Case(id="case", input={}, expected=expected)
        output = models.Output(fields={"report": report})
        return {score.metric: score for score in self.grader.grade(case, output)}

    def test_valid_report_recalls_frozen_findings(self) -> None:
        report = {
            "total_segments": 3,
            "grade": "C",
            "mode": "deep",
            "staleness_results": [
                {"segment_index": 0, "score": 0.8, "reasons": ["superseded"]}
            ],
            "contradictions": [{"segment_a": 0, "segment_b": 2, "confidence": 0.9}],
            "deadweight": [{"segment_index": 1, "reason": "acknowledgment"}],
            "compression_candidates": [],
        }
        scores = self.grade(
            report,
            {
                "total_segments": 3,
                "required_stale_indices": [0],
                "required_contradiction_pairs": [[0, 2]],
                "required_deadweight_indices": [1],
            },
        )
        self.assertTrue(scores["contract_pass"].passed)

    def test_exact_contract_penalizes_over_reporting(self) -> None:
        report = {
            "total_segments": 3,
            "grade": "C",
            "mode": "deep",
            "staleness_results": [
                {"segment_index": 0, "score": 0.8, "reasons": ["superseded"]}
            ],
            "contradictions": [],
            "deadweight": [{"segment_index": 1, "reason": "short"}],
            "compression_candidates": [],
        }
        scores = self.grade(
            report,
            {
                "total_segments": 3,
                "stale_indices": [0],
                "contradiction_pairs": [],
                "deadweight_indices": [],
                "compression_groups": [],
            },
        )
        self.assertEqual(scores["finding_precision"].value, 0.5)
        self.assertEqual(scores["finding_recall"].value, 1.0)
        self.assertAlmostEqual(scores["finding_f1"].value, 2 / 3)
        self.assertFalse(scores["contract_pass"].passed)

    def test_exact_contract_penalizes_missing_findings(self) -> None:
        report = {
            "total_segments": 2,
            "grade": "A",
            "mode": "deep",
            "staleness_results": [],
            "contradictions": [],
            "deadweight": [],
            "compression_candidates": [],
        }
        scores = self.grade(
            report,
            {
                "total_segments": 2,
                "stale_indices": [],
                "contradiction_pairs": [[0, 1]],
                "deadweight_indices": [],
                "compression_groups": [],
            },
        )
        self.assertEqual(scores["finding_precision"].value, 1.0)
        self.assertEqual(scores["finding_recall"].value, 0.0)
        self.assertEqual(scores["finding_f1"].value, 0.0)
        self.assertFalse(scores["contract_pass"].passed)

    def test_exact_clean_contract_scores_perfectly(self) -> None:
        report = {
            "total_segments": 2,
            "grade": "A",
            "mode": "deep",
            "staleness_results": [],
            "contradictions": [],
            "deadweight": [],
            "compression_candidates": [],
        }
        scores = self.grade(
            report,
            {
                "total_segments": 2,
                "stale_indices": [],
                "contradiction_pairs": [],
                "deadweight_indices": [],
                "compression_groups": [],
            },
        )
        self.assertEqual(scores["finding_precision"].value, 1.0)
        self.assertEqual(scores["finding_recall"].value, 1.0)
        self.assertEqual(scores["finding_f1"].value, 1.0)
        self.assertTrue(scores["contract_pass"].passed)

    def test_partial_exact_contract_is_rejected(self) -> None:
        report = {
            "total_segments": 2,
            "grade": "A",
            "mode": "deep",
            "staleness_results": [],
            "contradictions": [],
            "deadweight": [],
            "compression_candidates": [],
        }
        scores = self.grade(report, {"stale_indices": []})
        self.assertFalse(scores["expected_findings_valid"].passed)
        self.assertFalse(scores["contract_pass"].passed)

    def test_out_of_bounds_finding_fails_reference_check(self) -> None:
        report = {
            "total_segments": 2,
            "grade": "B",
            "mode": "fast",
            "staleness_results": [{"segment_index": 3, "score": 0.8}],
            "contradictions": [],
            "deadweight": [],
            "compression_candidates": [],
        }
        scores = self.grade(report, {"total_segments": 2})
        self.assertFalse(scores["finding_references_valid"].passed)
        self.assertFalse(scores["contract_pass"].passed)

    def test_missing_expected_finding_fails_recall(self) -> None:
        report = {
            "total_segments": 2,
            "grade": "A",
            "mode": "deep",
            "staleness_results": [],
            "contradictions": [],
            "deadweight": [],
            "compression_candidates": [],
        }
        scores = self.grade(report, {"required_deadweight_indices": [1]})
        self.assertFalse(scores["expected_findings_recalled"].passed)

    def test_malformed_expected_contract_fails_without_raising(self) -> None:
        report = {
            "total_segments": 2,
            "grade": "A",
            "mode": "deep",
            "staleness_results": [],
            "contradictions": [],
            "deadweight": [],
            "compression_candidates": [],
        }
        scores = self.grade(
            report,
            {
                "required_contradiction_pairs": [[0]],
                "minimum_staleness_score": "high",
                "minimum_compression_candidates": "one",
            },
        )
        self.assertFalse(scores["expected_findings_recalled"].passed)


if __name__ == "__main__":
    unittest.main()
