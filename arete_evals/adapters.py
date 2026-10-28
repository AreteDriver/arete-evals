"""Target adapters owned by the suite rather than the evaluation engine."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from evalcore import models
from evalcore.adapters import base


@base.register("public_project_http")
class PublicProjectHttpAdapter:
    """Invoke an explicitly configured public-project evaluation endpoint.

    The endpoint receives the versioned case input and opaque variant knobs.
    It must return either a structured response object or
    ``{"response": <structured object>}``. Credentials are named in config but
    read only from the environment; they are never serialized into run files.
    """

    def __init__(
        self,
        *,
        url_env: str,
        token_env: str | None = None,
        token_required: bool = False,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.url_env = url_env
        self.token_env = token_env
        self.token_required = token_required
        self.timeout_seconds = timeout_seconds

    async def invoke(self, case: models.Case, variant: models.Variant) -> models.Output:
        url = os.environ.get(self.url_env)
        if not url:
            return models.Output(error=f"missing environment variable {self.url_env}")

        payload = json.dumps(
            {"case_id": case.id, "input": case.input, "variant": variant.knobs},
            separators=(",", ":"),
        ).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "arete-evals-suite/0.1",
        }
        if self.token_env:
            token = os.environ.get(self.token_env)
            if not token and self.token_required:
                return models.Output(
                    error=f"missing environment variable {self.token_env}"
                )
            if token:
                headers["Authorization"] = f"Bearer {token}"

        request = urllib.request.Request(
            url, data=payload, headers=headers, method="POST"
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return models.Output(
                error=f"target returned HTTP {exc.code}",
                retryable=exc.code == 429 or 500 <= exc.code < 600,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        except (urllib.error.URLError, TimeoutError) as exc:
            return models.Output(
                error=f"target request failed: {type(exc).__name__}",
                retryable=True,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return models.Output(
                error=f"target returned invalid JSON: {type(exc).__name__}",
                latency_ms=(time.perf_counter() - started) * 1000,
            )

        if not isinstance(body, dict):
            return models.Output(
                error="target JSON must be an object",
                raw=body,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        structured: Any = body.get("response", body)
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else None
        return models.Output(
            fields={"response": structured},
            raw=body,
            latency_ms=(time.perf_counter() - started) * 1000,
            tokens=usage,
            cost=body.get("cost_usd")
            if isinstance(body.get("cost_usd"), int | float)
            else None,
        )


@base.register("context_hygiene_cli")
class ContextHygieneCliAdapter:
    """Run the public ``context-hygiene`` CLI in an isolated workspace.

    The executable is supplied through an environment variable so a live run
    can point at a clean environment installed from the exact target commit.
    Conversation content and model configuration exist only in a temporary
    directory. API and license credentials are inherited by the child process
    but are never included in the command, output object, or run bundle.
    """

    def __init__(
        self,
        *,
        executable_env: str = "CONTEXT_HYGIENE_EXECUTABLE",
        timeout_seconds: float = 180.0,
    ) -> None:
        self.executable_env = executable_env
        self.timeout_seconds = timeout_seconds

    async def invoke(self, case: models.Case, variant: models.Variant) -> models.Output:
        executable = os.environ.get(self.executable_env)
        if not executable:
            return models.Output(
                error=f"missing environment variable {self.executable_env}"
            )
        if not Path(executable).is_file():
            return models.Output(error="context-hygiene executable not found")

        content = case.input.get("content")
        if not isinstance(content, str) or not content.strip():
            return models.Output(error="case input.content must be non-empty text")
        extension = case.input.get("extension", ".md")
        if extension not in {".md", ".txt", ".json", ".jsonl"}:
            return models.Output(error="case input.extension is unsupported")

        treatment = variant.knobs.get("treatment", {})
        config = treatment.get("config", {}) if isinstance(treatment, dict) else {}
        analysis_mode = config.get("analysis_mode")
        if analysis_mode not in {"fast", "deep"}:
            return models.Output(
                error="variant treatment.config.analysis_mode must be fast or deep"
            )
        model = variant.knobs.get("model")
        provider = config.get("provider", "anthropic")
        max_tokens = config.get("max_tokens", 1024)
        max_retries = config.get("provider_max_retries", 0)
        if (
            not isinstance(max_tokens, int)
            or max_tokens < 1
            or not isinstance(max_retries, int)
            or max_retries < 0
        ):
            return models.Output(error="variant provider limits are invalid")
        if analysis_mode == "deep" and (
            not isinstance(model, str) or not model.strip()
        ):
            return models.Output(error="deep mode requires an exact model identifier")

        started = time.perf_counter()
        try:
            completed = await asyncio.to_thread(
                self._run,
                executable,
                content,
                extension,
                analysis_mode,
                provider,
                model,
                max_tokens,
                max_retries,
            )
        except subprocess.TimeoutExpired:
            return models.Output(
                error="context-hygiene invocation timed out",
                retryable=True,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        except OSError as exc:
            return models.Output(
                error=f"context-hygiene invocation failed: {type(exc).__name__}",
                latency_ms=(time.perf_counter() - started) * 1000,
            )

        latency_ms = (time.perf_counter() - started) * 1000
        if completed.returncode != 0:
            return models.Output(
                error=f"context-hygiene exited with code {completed.returncode}",
                retryable=False,
                latency_ms=latency_ms,
            )
        try:
            report = json.loads(completed.stdout)
        except (TypeError, json.JSONDecodeError):
            return models.Output(
                error="context-hygiene returned invalid JSON",
                latency_ms=latency_ms,
            )
        if not isinstance(report, dict):
            return models.Output(
                error="context-hygiene report must be a JSON object",
                raw=report,
                latency_ms=latency_ms,
            )
        return models.Output(
            fields={"report": report},
            raw=report,
            latency_ms=latency_ms,
            tokens=(
                report.get("usage") if isinstance(report.get("usage"), dict) else None
            ),
        )

    def _run(
        self,
        executable: str,
        content: str,
        extension: str,
        analysis_mode: str,
        provider: str,
        model: Any,
        max_tokens: int,
        max_retries: int,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="arete-context-hygiene-") as root:
            root_path = Path(root)
            input_path = root_path / f"case{extension}"
            input_path.write_text(content, encoding="utf-8")
            config: dict[str, Any] = {"llm_provider": provider}
            if analysis_mode == "deep":
                config[f"{provider}_model"] = model
                config[f"{provider}_max_tokens"] = max_tokens
                config[f"{provider}_max_retries"] = max_retries
            (root_path / "config.yaml").write_text(
                json.dumps(config, sort_keys=True), encoding="utf-8"
            )
            environment = os.environ.copy()
            environment["CONTEXT_HYGIENE_DIR"] = str(root_path)
            command = [executable, "audit", str(input_path), "--format", "json"]
            if analysis_mode == "deep":
                command.append("--deep")
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=environment,
                check=False,
            )
