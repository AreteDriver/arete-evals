from __future__ import annotations

import asyncio
import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from evalcore import models

from arete_evals.adapters import ContextHygieneCliAdapter, PublicProjectHttpAdapter


class _Response:
    def __init__(self, value) -> None:
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.value).encode("utf-8")


class PublicProjectHttpAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = models.Case(id="case", input={"query": "test"})
        self.variant = models.Variant(name="candidate", knobs={})

    def test_missing_url_environment_variable_is_an_output_error(self) -> None:
        adapter = PublicProjectHttpAdapter(url_env="MISSING_TEST_URL")
        with mock.patch.dict(os.environ, {}, clear=True):
            output = asyncio.run(adapter.invoke(self.case, self.variant))
        self.assertIn("MISSING_TEST_URL", output.error or "")
        self.assertFalse(output.retryable)

    def test_success_normalizes_response_and_usage(self) -> None:
        adapter = PublicProjectHttpAdapter(url_env="TEST_URL")
        body = {
            "response": {
                "decision": "Proceed",
                "rationale": "The endpoint returned a complete structured response.",
            },
            "usage": {"input": 10, "output": 12},
            "cost_usd": 0.01,
        }
        with (
            mock.patch.dict(os.environ, {"TEST_URL": "https://example.test/eval"}),
            mock.patch("urllib.request.urlopen", return_value=_Response(body)),
        ):
            output = asyncio.run(adapter.invoke(self.case, self.variant))
        self.assertEqual(output.fields["response"]["decision"], "Proceed")
        self.assertEqual(output.tokens, {"input": 10, "output": 12})
        self.assertEqual(output.cost, 0.01)


class ContextHygieneCliAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = models.Case(
            id="stale",
            input={
                "content": "## User\nUse SQLite.\n\n## User\nActually use Postgres."
            },
        )

    def test_missing_executable_is_an_output_error(self) -> None:
        adapter = ContextHygieneCliAdapter(executable_env="MISSING_CTX_EXECUTABLE")
        variant = models.Variant(
            name="baseline",
            knobs={"treatment": {"config": {"analysis_mode": "fast"}}},
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            output = asyncio.run(adapter.invoke(self.case, variant))
        self.assertIn("MISSING_CTX_EXECUTABLE", output.error or "")

    def test_deep_mode_runs_isolated_cli_and_parses_report(self) -> None:
        adapter = ContextHygieneCliAdapter(executable_env="CTX_EXECUTABLE")
        variant = models.Variant(
            name="candidate",
            knobs={
                "model": "claude-sonnet-4-6",
                "treatment": {
                    "config": {"analysis_mode": "deep", "provider": "anthropic"}
                },
            },
        )
        report = {
            "total_segments": 2,
            "grade": "B",
            "staleness_results": [],
            "contradictions": [],
            "deadweight": [],
            "compression_candidates": [],
            "mode": "deep",
            "usage": {"input_tokens": 20, "output_tokens": 10, "requests": 4},
        }
        observed: dict[str, object] = {}

        def fake_run(command, **kwargs):
            observed["command"] = command
            observed["environment"] = kwargs["env"]
            observed["content"] = Path(command[2]).read_text(encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, json.dumps(report), "")

        with (
            mock.patch.dict(
                os.environ,
                {"CTX_EXECUTABLE": "/tmp/ctx-hygiene", "ANTHROPIC_API_KEY": "secret"},
                clear=True,
            ),
            mock.patch("pathlib.Path.is_file", return_value=True),
            mock.patch("subprocess.run", side_effect=fake_run),
        ):
            output = asyncio.run(adapter.invoke(self.case, variant))
        self.assertEqual(output.fields["report"]["mode"], "deep")
        self.assertEqual(output.tokens["requests"], 4)
        self.assertIn("--deep", observed["command"])
        self.assertIn("Actually use Postgres", observed["content"])
        self.assertNotIn("secret", str(observed["command"]))
        self.assertIn("CONTEXT_HYGIENE_DIR", observed["environment"])


if __name__ == "__main__":
    unittest.main()
