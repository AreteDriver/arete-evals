from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from arete_evals.project import InputError
from arete_evals.receipts import (
    canonical_bytes,
    finalize_receipt,
    load_document,
    render_receipt,
    validate_document,
    verified_envelope,
    verify_receipt,
)

ROOT = Path(__file__).resolve().parent.parent


class WorkReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.draft = self.root / "draft.json"
        self.out = self.root / "receipt.json"
        self.receipt = json.loads(
            (ROOT / "fixtures/work-receipt-unknown-v1.json").read_text()
        )
        self.write()

    def write(self):
        self.draft.write_text(json.dumps(self.receipt))

    def with_evidence(self):
        content = b'{"tests_run": 3, "passed": true}\n'
        (self.root / "tests.json").write_bytes(content)
        self.receipt["artifacts"] = [
            {
                "id": "test-evidence",
                "path": "tests.json",
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        ]
        self.receipt["subject_artifact"] = "test-evidence"
        self.receipt["tests"] = [
            {
                "id": "unit",
                "command": ["python", "-m", "unittest"],
                "outcome": "PASS",
                "counts": {"passed": 3, "failed": 0, "errors": 0, "skipped": 0},
                "evidence": ["test-evidence"],
            }
        ]
        self.write()

    def seal(self):
        return finalize_receipt(self.draft, self.out)

    def test_unknown_telemetry_is_retained_without_invented_pass(self):
        self.seal()
        document = verified_envelope(self.out)
        self.assertIsNone(document["receipt"]["telemetry"]["cost"])
        report = verify_receipt(self.out)
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["evidence_strength"], "RECORDED")
        self.assertEqual(report["work_acceptance"], "UNKNOWN")

    def test_finalization_does_not_execute_or_import_reported_commands(self):
        self.with_evidence()
        self.receipt["tests"][0]["command"] = ["touch", str(self.root / "OWNED")]
        self.write()
        with patch("subprocess.run", side_effect=AssertionError("must not execute")):
            self.seal()
            verify_receipt(self.out, artifacts_root=self.root)
        self.assertFalse((self.root / "OWNED").exists())

    def test_anchored_content_never_authenticates_the_reporter(self):
        self.with_evidence()
        digest = self.seal()
        report = verify_receipt(
            self.out, artifacts_root=self.root, expected_sha256=digest
        )
        self.assertEqual(report["status"], "PASS WITH CONDITIONS")
        self.assertEqual(report["evidence_strength"], "ANCHORED_CONTENT")
        for key in [
            "authenticity",
            "work_acceptance",
            "human_approval",
            "independent_reproduction",
        ]:
            self.assertEqual(report[key], "UNKNOWN")

    def test_unanchored_content_is_a_weaker_state(self):
        self.with_evidence()
        self.seal()
        self.assertEqual(
            verify_receipt(self.out, artifacts_root=self.root)["evidence_strength"],
            "CONTENT_CHECKED",
        )

    def test_missing_artifact_root_is_unknown_not_pass(self):
        self.with_evidence()
        self.seal()
        self.assertEqual(verify_receipt(self.out)["status"], "UNKNOWN")

    def test_missing_subject_cannot_be_bound(self):
        self.with_evidence()
        self.receipt["subject_artifact"] = None
        self.write()
        self.seal()
        self.assertEqual(
            verify_receipt(self.out, artifacts_root=self.root)["status"], "UNKNOWN"
        )

    def test_missing_and_changed_artifacts_fail(self):
        self.with_evidence()
        self.seal()
        (self.root / "tests.json").unlink()
        self.assertEqual(
            verify_receipt(self.out, artifacts_root=self.root)["status"], "FAIL"
        )
        (self.root / "tests.json").write_text("tampered")
        self.assertEqual(
            verify_receipt(self.out, artifacts_root=self.root)["status"], "FAIL"
        )

    def test_size_mismatch_fails_even_with_matching_digest(self):
        self.with_evidence()
        self.receipt["artifacts"][0]["bytes"] += 1
        self.write()
        self.seal()
        self.assertEqual(
            verify_receipt(self.out, artifacts_root=self.root)["status"], "FAIL"
        )

    def test_payload_tampering_is_rejected(self):
        self.seal()
        value = json.loads(self.out.read_text())
        value["receipt"]["task_id"] = "changed"
        self.out.write_text(json.dumps(value))
        with self.assertRaises(InputError):
            verified_envelope(self.out)

    def test_recomputed_self_digest_cannot_match_original_anchor(self):
        digest = self.seal()
        value = json.loads(self.out.read_text())
        value["receipt"]["task_id"] = "changed"
        value["integrity"]["sha256"] = hashlib.sha256(
            canonical_bytes(value["receipt"])
        ).hexdigest()
        self.out.write_text(json.dumps(value))
        verified_envelope(self.out)  # Consistency is not authenticity.
        with self.assertRaises(InputError):
            verified_envelope(self.out, digest)

    def test_finalization_is_deterministic_and_non_overwriting(self):
        digest = self.seal()
        other = self.root / "second.json"
        self.assertEqual(finalize_receipt(self.draft, other), digest)
        self.assertEqual(self.out.read_bytes(), other.read_bytes())
        before = self.out.read_bytes()
        with self.assertRaises(FileExistsError):
            self.seal()
        self.assertEqual(self.out.read_bytes(), before)

    def test_finalized_input_cannot_be_finalized_again(self):
        self.seal()
        with self.assertRaises(InputError):
            finalize_receipt(self.out, self.root / "again.json")

    def test_draft_is_not_verifiable_as_finalized(self):
        with self.assertRaises(InputError):
            verified_envelope(self.draft)

    def test_schema_rejects_missing_fields_wrong_types_and_extra_fields(self):
        original = copy.deepcopy(self.receipt)
        for field in original:
            with self.subTest(field=field):
                broken = copy.deepcopy(original)
                del broken[field]
                with self.assertRaises(InputError):
                    validate_document(broken)
        for value in [
            [],
            None,
            {**original, "authority": "approve"},
            {**original, "human_review_required": "false"},
            {**original, "schema_version": "v99"},
        ]:
            with self.assertRaises(InputError):
                validate_document(value)

    def test_control_characters_rejected_by_schema_and_reader(self):
        schema = json.loads(
            (ROOT / "arete_evals/schemas/work-receipt-v1.schema.json").read_text()
        )
        for value in ("\x00", "agent\n", "a\x1bb", "\x7f"):
            with self.subTest(value=repr(value)):
                self.receipt["agent"]["name"] = value
                self.assertFalse(Draft202012Validator(schema).is_valid(self.receipt))
                self.write()
                with self.assertRaises(InputError):
                    load_document(self.draft)
        self.receipt["agent"]["name"] = None
        self.receipt["task_id"] += "\n"
        with self.assertRaises(InputError):
            validate_document(self.receipt)

    def test_command_arguments_can_repeat_without_execution(self):
        self.with_evidence()
        command = ["pytest", "-v", "-v", "tests"]
        self.receipt["tests"][0]["command"] = command
        self.write()
        self.seal()
        self.assertEqual(
            verified_envelope(self.out)["receipt"]["tests"][0]["command"], command
        )

    def test_duplicate_keys_nonfinite_and_excessive_nesting_fail(self):
        for raw in [
            '{"task_id":1,"task_id":2}',
            '{"value":NaN}',
            '{"value":1e999}',
            "[" * 30 + "0" + "]" * 30,
        ]:
            self.draft.write_text(raw)
            with self.assertRaises(InputError):
                load_document(self.draft)

    def test_invalid_encoding_and_oversized_input_fail(self):
        for data in [b"\xff", b"x" * 1_048_577]:
            self.draft.write_bytes(data)
            with self.assertRaises(InputError):
                load_document(self.draft)

    def test_receipt_symlink_and_non_regular_file_rejected(self):
        self.draft.unlink()
        self.draft.symlink_to(ROOT / "fixtures/work-receipt-unknown-v1.json")
        with self.assertRaises(InputError):
            load_document(self.draft)
        self.draft.unlink()
        self.draft.mkdir()
        with self.assertRaises(InputError):
            load_document(self.draft)

    def test_traversal_absolute_sensitive_and_ambiguous_paths_rejected(self):
        self.with_evidence()
        for path in [
            "../outside",
            "/etc/passwd",
            "C:\\secret",
            ".env",
            ".ssh/id_rsa",
            "a/./b",
            "a//b",
            ".",
            "a/../b",
            "file.key",
        ]:
            with self.subTest(path=path):
                self.receipt["artifacts"][0]["path"] = path
                with self.assertRaises(InputError):
                    validate_document(self.receipt)

    def test_artifact_symlinks_and_oversized_files_fail(self):
        self.with_evidence()
        self.seal()
        target = self.root / "tests.json"
        target.unlink()
        target.symlink_to(self.draft)
        self.assertEqual(
            verify_receipt(self.out, artifacts_root=self.root)["status"], "FAIL"
        )
        target.unlink()
        target.write_bytes(b"x" * 1_048_577)
        self.assertEqual(
            verify_receipt(self.out, artifacts_root=self.root)["status"], "FAIL"
        )

    def test_symlinked_output_is_not_followed(self):
        self.out.symlink_to(self.draft)
        before = self.draft.read_bytes()
        with self.assertRaises((InputError, FileExistsError)):
            self.seal()
        self.assertEqual(self.draft.read_bytes(), before)

    def test_false_passes_and_unknown_references_fail(self):
        self.with_evidence()
        for counts in [
            None,
            {"passed": 0, "failed": 0, "errors": 0, "skipped": 0},
            {"passed": 2, "failed": 1, "errors": 0, "skipped": 0},
            {"passed": 2, "failed": 0, "errors": 0, "skipped": 1},
        ]:
            self.receipt["tests"][0]["counts"] = counts
            with self.assertRaises(InputError):
                validate_document(self.receipt)
        self.with_evidence()
        self.receipt["tests"][0]["evidence"] = []
        with self.assertRaises(InputError):
            validate_document(self.receipt)
        self.receipt["tests"][0]["evidence"] = ["unknown"]
        with self.assertRaises(InputError):
            validate_document(self.receipt)

    def test_duplicate_artifact_ids_and_paths_fail(self):
        self.with_evidence()
        other = {**self.receipt["artifacts"][0], "path": "other.json"}
        self.receipt["artifacts"].append(other)
        with self.assertRaises(InputError):
            validate_document(self.receipt)
        other["id"] = "second"
        other["path"] = "tests.json"
        with self.assertRaises(InputError):
            validate_document(self.receipt)

    def test_render_discloses_unknowns_and_does_not_read_artifacts(self):
        self.with_evidence()
        self.seal()
        (self.root / "tests.json").unlink()
        text = render_receipt(self.out)
        self.assertIn("not independently authenticated", text)
        self.assertIn("UNKNOWN", text)
        self.assertIn('"cost": null', text)
        self.assertIn("were not checked", text)

    def test_cli_lifecycle_and_fail_closed_exit(self):
        self.with_evidence()
        command = [sys.executable, "-m", "arete_evals.cli", "receipt"]
        env = {**os.environ, "PYTHONPATH": str(ROOT)}

        def call(*args):
            return subprocess.run(
                command + list(args),
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

        sealed = call("finalize", str(self.draft), "--out", str(self.out))
        self.assertEqual(sealed.returncode, 0, sealed.stdout)
        digest = json.loads(sealed.stdout)["sha256"]
        self.assertEqual(call("verify", str(self.out)).returncode, 1)
        checked = call(
            "verify",
            str(self.out),
            "--artifacts-root",
            str(self.root),
            "--expected-sha256",
            digest,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout)
        self.assertEqual(call("render", str(self.out)).returncode, 0)
        self.assertEqual(
            call("finalize", str(self.draft), "--out", str(self.out)).returncode, 1
        )
        self.draft.write_text('{"secret-value":true}')
        failed = call("finalize", str(self.draft), "--out", str(self.root / "new.json"))
        self.assertEqual(failed.returncode, 1)
        self.assertNotIn("secret-value", failed.stdout + failed.stderr)

    def test_schema_and_examples_are_valid(self):
        contract = json.loads(
            (ROOT / "arete_evals/schemas/work-receipt-v1.schema.json").read_text()
        )
        Draft202012Validator.check_schema(contract)
        validate_document(self.receipt)


class AcceptanceReceiptTests(unittest.TestCase):
    def test_observed_acceptance_receipt_preserves_knowns_and_unknowns(self):
        from scripts.receipt_for_acceptance import write_receipt

        for passed in [True, False]:
            with self.subTest(passed=passed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                report = {
                    "passed": passed,
                    "starting_revision": "a" * 40,
                    "revision": "b" * 40,
                    "source_sha256": {"source.py": "c" * 64},
                    "commands": [
                        {
                            "command": ["python", "tests"],
                            "exit_code": 0 if passed else 1,
                        }
                    ],
                }
                (root / "manifest.json").write_text(json.dumps(report))
                (root / "audit.json").write_text("{}")
                (root / "tests.json").write_text(
                    json.dumps(
                        {
                            "tests_run": 2,
                            "failures": 0 if passed else 1,
                            "errors": 0,
                            "skipped": 0,
                            "expected_failures": 0,
                            "unexpected_successes": 0,
                            "passed": passed,
                        }
                    )
                )
                write_receipt(root, report, {"source.py": "c" * 64}, 0.125)
                receipt = verified_envelope(root / "receipt.json")["receipt"]
                self.assertEqual(
                    receipt["tests"][0]["outcome"], "PASS" if passed else "FAIL"
                )
                self.assertEqual(receipt["files"]["modified"], [])
                self.assertIsNone(receipt["files"]["tests_added"])
                self.assertIsNone(receipt["telemetry"]["cost"])
                self.assertEqual(receipt["telemetry"]["elapsed_seconds"], 0.125)
                report_schema = json.loads(
                    (
                        ROOT / "arete_evals/schemas/receipt-verification-v1.schema.json"
                    ).read_text()
                )
                Draft202012Validator(report_schema).validate(
                    json.loads((root / "receipt-verification.json").read_text())
                )

    def test_crashed_test_runner_does_not_invent_test_results(self):
        from scripts.receipt_for_acceptance import write_receipt

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = {
                "passed": False,
                "starting_revision": None,
                "revision": None,
                "source_sha256": {},
                "commands": [{"command": ["python"], "exit_code": 1}],
            }
            (root / "manifest.json").write_text(json.dumps(report))
            (root / "audit.json").write_text("{}")
            write_receipt(root, report, {}, 0.0)
            receipt = verified_envelope(root / "receipt.json")["receipt"]
            self.assertIsNone(receipt["tests"])
            self.assertEqual(receipt["evaluations"][0]["outcome"], "FAIL")
