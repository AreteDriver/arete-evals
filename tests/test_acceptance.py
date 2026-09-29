"""Prove fixed acceptance evidence cannot turn failures or skips into success."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import test_report


class AcceptanceTests(unittest.TestCase):
    def run_case(self, method):
        case = type("SyntheticCase", (unittest.TestCase,), {"test_example": method})
        suite = unittest.TestSuite([case("test_example")])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            with (
                patch("sys.stderr", new_callable=io.StringIO),
                patch.object(sys, "argv", ["test_report", str(path)]),
                patch.object(
                    unittest.defaultTestLoader, "discover", return_value=suite
                ),
            ):
                code = test_report.main()
            return code, json.loads(path.read_text())

    def test_failed_test_fails_evidence(self):
        code, report = self.run_case(lambda test: test.fail("seeded failure"))
        self.assertEqual(code, 1)
        self.assertEqual(report["failures"], 1)
        self.assertFalse(report["passed"])

    def test_skipped_test_is_not_pass(self):
        code, report = self.run_case(lambda test: test.skipTest("seeded skip"))
        self.assertEqual(code, 1)
        self.assertEqual(report["skipped"], 1)
        self.assertFalse(report["passed"])

    def test_passing_test_is_recorded(self):
        code, report = self.run_case(lambda test: test.assertTrue(True))
        self.assertEqual(code, 0)
        self.assertEqual(report["tests_run"], 1)
