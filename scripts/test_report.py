"""Run this repository's trusted unittest suite and retain truthful counts."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


def main() -> int:
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
    }
    report["passed"] = (
        result.wasSuccessful()
        and result.testsRun > 0
        and not result.skipped
        and not result.expectedFailures
    )
    Path(sys.argv[1]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
