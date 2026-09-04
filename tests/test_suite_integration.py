from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import evalcore

from arete_evals import plugin as plugin  # noqa: F401
from arete_evals.bundles import create_bundle
from arete_evals.publication import publish_bundle
from arete_evals.validation import validate_suite

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "suites" / "structured-response-integrity.yaml"
CONTEXT_HYGIENE_SUITE = ROOT / "suites" / "context-hygiene-deep-analysis.yaml"


class SuiteIntegrationTests(unittest.TestCase):
    def test_suite_contract_has_complete_replay_coverage(self) -> None:
        summary = validate_suite(SUITE)
        self.assertEqual(summary["cases"], 10)
        self.assertEqual(summary["variants"], ["baseline", "candidate"])

    def test_replay_detects_seeded_regressions_and_candidate_passes(self) -> None:
        suite = evalcore.load_suite(SUITE)
        baseline = evalcore.run_suite_sync(suite, "baseline", mode="replay")
        candidate = evalcore.run_suite_sync(suite, "candidate", mode="replay")
        comparison = evalcore.compare.compare(
            baseline.scorecard, candidate.scorecard, suite.thresholds
        )
        self.assertEqual(baseline.scorecard.metrics["contract_pass"].value, 0.3)
        self.assertEqual(candidate.scorecard.metrics["contract_pass"].value, 1.0)
        self.assertEqual(
            candidate.scorecard.metrics["no_serialized_json_leak"].value, 1.0
        )
        self.assertEqual(comparison.verdict, "pass")

    def test_context_hygiene_replay_exercises_finding_quality(self) -> None:
        summary = validate_suite(CONTEXT_HYGIENE_SUITE)
        self.assertEqual(summary["cases"], 8)
        suite = evalcore.load_suite(CONTEXT_HYGIENE_SUITE)
        baseline = evalcore.run_suite_sync(suite, "baseline", mode="replay")
        candidate = evalcore.run_suite_sync(suite, "candidate", mode="replay")
        comparison = evalcore.compare.compare(
            baseline.scorecard, candidate.scorecard, suite.thresholds
        )
        self.assertEqual(baseline.scorecard.metrics["finding_precision"].value, 0.375)
        self.assertEqual(baseline.scorecard.metrics["finding_recall"].value, 0.75)
        self.assertEqual(baseline.scorecard.metrics["finding_f1"].value, 0.25)
        self.assertEqual(candidate.scorecard.metrics["finding_precision"].value, 1.0)
        self.assertEqual(candidate.scorecard.metrics["finding_recall"].value, 1.0)
        self.assertEqual(candidate.scorecard.metrics["finding_f1"].value, 1.0)
        self.assertEqual(comparison.verdict, "pass")

    def test_bundle_is_complete_checksummed_and_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = create_bundle(
                suite_path=SUITE,
                output_root=root,
                created_at="2026-08-31T12:00:00+00:00",
                bundle_id="test-bundle",
            )
            manifest = json.loads((bundle / "manifest.json").read_text())
            self.assertFalse(manifest["outputs_truncated"])
            self.assertEqual(manifest["engine"]["version"], "0.2.0")
            self.assertEqual(manifest["verdict"], "pass")
            for name, metadata in manifest["artifacts"].items():
                digest = hashlib.sha256((bundle / name).read_bytes()).hexdigest()
                self.assertEqual(metadata["sha256"], digest)
            with self.assertRaises(FileExistsError):
                create_bundle(
                    suite_path=SUITE,
                    output_root=root,
                    created_at="2026-08-31T12:00:00+00:00",
                    bundle_id="test-bundle",
                )

    def test_live_run_requires_target_revision(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "revision"),
        ):
            create_bundle(
                suite_path=SUITE,
                output_root=Path(directory),
                mode="http",
            )

    def test_live_run_rejects_placeholder_model_identity(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "exact model identifier"),
        ):
            create_bundle(
                suite_path=SUITE,
                output_root=Path(directory),
                mode="http",
                revision="public-project-commit",
            )

    def test_public_export_defaults_to_hashes_not_model_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = create_bundle(
                suite_path=SUITE,
                output_root=root / "private",
                bundle_id="publish-test",
                created_at="2026-08-31T12:00:00+00:00",
            )
            public = publish_bundle(
                private_bundle=private,
                public_root=root / "public",
                reviewed_by="test-reviewer",
                published_at="2026-08-31T12:01:00+00:00",
            )
            manifest = json.loads((public / "manifest.json").read_text())
            self.assertEqual(manifest["output_policy"], "hashes-only")
            first_output = json.loads(
                (public / "outputs.jsonl").read_text().splitlines()[0]
            )
            self.assertIn("response_sha256", first_output)
            self.assertNotIn("response", first_output)


if __name__ == "__main__":
    unittest.main()
