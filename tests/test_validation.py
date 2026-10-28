from __future__ import annotations

import unittest

from arete_evals.validation import _validate_exact_findings


class ExactFindingContractValidationTests(unittest.TestCase):
    def test_required_contract_cannot_be_omitted(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact finding contract is required"):
            _validate_exact_findings({}, source="case", required=True)

    def test_out_of_bounds_expected_index_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "in-bounds"):
            _validate_exact_findings(
                {
                    "total_segments": 2,
                    "stale_indices": [2],
                    "contradiction_pairs": [],
                    "deadweight_indices": [],
                    "compression_groups": [],
                },
                source="case",
                required=True,
            )

    def test_clean_exact_contract_is_valid(self) -> None:
        _validate_exact_findings(
            {
                "total_segments": 2,
                "stale_indices": [],
                "contradiction_pairs": [],
                "deadweight_indices": [],
                "compression_groups": [],
            },
            source="case",
            required=True,
        )


if __name__ == "__main__":
    unittest.main()
