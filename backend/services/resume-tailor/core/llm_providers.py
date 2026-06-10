"""LLM provider abstractions for resume tailoring.

This module keeps the AI-facing contract small so the rest of the pipeline can
be tested with deterministic stubs when live model access is unavailable.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar

try:
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - lightweight fallback for offline tests
    class BaseModel:
        @classmethod
        def model_validate(cls, data):
            if isinstance(data, dict):
                return cls(**data)
            if hasattr(data, "__dict__"):
                return cls(**data.__dict__)
            raise TypeError(f"Cannot validate data of type {type(data)!r}")

from .models import DiscoveryResult, DiscoveredJob, JobPosting, JobScore

T = TypeVar("T", bound=BaseModel)


def _run_coro(coro: "Any", timeout: Optional[float] = None) -> Any:
    """Run an async coroutine to completion from synchronous code.

    The agents call providers synchronously, sometimes from the FastAPI event
    loop (background tasks) and sometimes from a worker thread (parallel
    scoring). ``asyncio.run`` cannot be used while a loop is already running in
    the current thread, so in that case we drive the coroutine on a dedicated
    thread that owns its own loop.

    A ``timeout`` (seconds) bounds the call so a hung ``claude`` subprocess can't
    block a worker thread forever; it raises ``TimeoutError`` on expiry.
    """

    async def _with_timeout() -> Any:
        if timeout is None:
            return await coro
        return await asyncio.wait_for(coro, timeout)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_with_timeout())

    box: dict[str, Any] = {}

    def _runner() -> None:
        try:
            box["value"] = asyncio.run(_with_timeout())
        except BaseException as exc:  # propagate to the caller's thread
            box["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box["value"]


class LLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        raise NotImplementedError

    def generate_content(self, prompt: str, max_retries: int = 1, temperature: float = 0.7) -> str:
        """Backward-compatible alias used by older agent code."""
        last_error: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                return self.generate_text(prompt=prompt, temperature=temperature)
            except Exception as exc:  # pragma: no cover - exercised with real provider
                last_error = exc
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        if last_error:
            raise last_error
        raise RuntimeError("generate_content failed without raising a provider error")

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: Optional[Type[T]] = None,
        temperature: float = 0.1,
        response_schema: Optional[Type[T]] = None,
    ) -> T:
        raise NotImplementedError


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        from google import genai

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found. Set it in .env file or pass as parameter.")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name or os.getenv("GEMINI_MODEL_NAME", "gemini-3-flash-preview")

    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            ),
        )
        return self._clean_response(response.text)

    def generate_structured(
        self,
        prompt: str,
        schema: Optional[Type[T]] = None,
        temperature: float = 0.1,
        response_schema: Optional[Type[T]] = None,
    ) -> T:
        from google.genai import types

        resolved_schema = schema or response_schema
        if resolved_schema is None:
            raise ValueError("generate_structured requires either schema or response_schema")

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=resolved_schema,
            ),
        )

        if hasattr(response, "parsed") and response.parsed:
            if isinstance(response.parsed, resolved_schema):
                return response.parsed
            return resolved_schema.model_validate(response.parsed)

        data = json.loads(response.text)
        return resolved_schema.model_validate(data)

    def _clean_response(self, response: str) -> str:
        match = re.search(r"```(?:latex)?\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()


class ClaudeAgentProvider(LLMProvider):
    """LLM provider backed by the Claude Agent SDK.

    Authenticates with a Claude Pro/Max subscription via the long-lived OAuth
    token produced by ``claude setup-token`` (``CLAUDE_CODE_OAUTH_TOKEN``),
    so inference is billed against the subscription rather than a metered API
    key. The SDK shells out to the ``claude`` CLI per call, so each request is
    heavier than a plain HTTP API call; that is acceptable for this workload.

    Each query is configured as a single-shot, non-agentic call: no tools and
    no filesystem settings are loaded, so it behaves like a plain prompt ->
    response (or prompt -> validated JSON) completion.
    """

    _STRUCTURED_RETRIES = 3

    def __init__(self, oauth_token: Optional[str] = None, model_name: Optional[str] = None):
        self.oauth_token = oauth_token or os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
        if not self.oauth_token:
            raise ValueError(
                "CLAUDE_CODE_OAUTH_TOKEN not found. Run `claude setup-token` and set it "
                "in your .env file (or pass it as a parameter)."
            )
        # Make sure the SDK's CLI subprocess inherits the token.
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = self.oauth_token
        self.model_name = model_name or os.getenv("CLAUDE_MODEL", "sonnet")
        # Bound each call so a hung CLI subprocess can't block a worker thread.
        self.call_timeout = float(os.getenv("CLAUDE_CALL_TIMEOUT", "120"))

    def _invoke(
        self,
        prompt: str,
        *,
        output_schema: Optional[Type[T]] = None,
    ) -> tuple[Any, str]:
        """Run a single non-agentic query, returning (result_message, text)."""
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            TextBlock,
            query,
        )

        option_kwargs: dict[str, Any] = dict(
            model=self.model_name,
            system_prompt=None,
            setting_sources=[],  # do not load CLAUDE.md / project / user settings
            allowed_tools=[],  # no agentic tool-use loop; the call_timeout bounds runaways.
            # NOTE: do NOT set max_turns=1 — structured output (output_format) enforces
            # the schema via an internal tool call that needs more than one turn.
        )
        if output_schema is not None:
            option_kwargs["output_format"] = {
                "type": "json_schema",
                "schema": output_schema.model_json_schema(),
            }
        options = ClaudeAgentOptions(**option_kwargs)

        async def _collect() -> tuple[Any, str]:
            result_message = None
            texts: list[str] = []
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            texts.append(block.text)
                elif isinstance(message, ResultMessage):
                    result_message = message
            return result_message, "".join(texts)

        return _run_coro(_collect(), timeout=self.call_timeout)

    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        # The Agent SDK does not expose a sampling temperature; the argument is
        # accepted for interface compatibility with other providers and ignored.
        result_message, streamed_text = self._invoke(prompt)
        text = getattr(result_message, "result", None) or streamed_text
        if not text:
            raise RuntimeError("Claude Agent SDK returned no text response")
        return self._clean_response(text)

    def generate_structured(
        self,
        prompt: str,
        schema: Optional[Type[T]] = None,
        temperature: float = 0.1,
        response_schema: Optional[Type[T]] = None,
    ) -> T:
        resolved_schema = schema or response_schema
        if resolved_schema is None:
            raise ValueError("generate_structured requires either schema or response_schema")

        last_error: Optional[Exception] = None
        for attempt in range(self._STRUCTURED_RETRIES):
            try:
                result_message, _ = self._invoke(prompt, output_schema=resolved_schema)
                structured = getattr(result_message, "structured_output", None)
                if structured is None:
                    subtype = getattr(result_message, "subtype", "unknown")
                    raise RuntimeError(
                        f"Claude Agent SDK returned no structured output (subtype={subtype})"
                    )
                return resolved_schema.model_validate(structured)
            except Exception as exc:  # transient subprocess / validation failures
                last_error = exc
                if attempt < self._STRUCTURED_RETRIES - 1:
                    time.sleep(2 ** attempt)
        assert last_error is not None
        raise last_error

    def _clean_response(self, response: str) -> str:
        match = re.search(r"```(?:latex)?\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()


class StubProvider(LLMProvider):
    """Deterministic provider for local development and tests."""

    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        lower_prompt = prompt.lower()
        if "master resume latex" in lower_prompt and "job analysis" in lower_prompt:
            return self._tailor_resume(prompt)
        return "Stub response"

    def generate_structured(
        self,
        prompt: str,
        schema: Optional[Type[T]] = None,
        temperature: float = 0.1,
        response_schema: Optional[Type[T]] = None,
    ) -> T:
        resolved_schema = schema or response_schema
        if resolved_schema is None:
            raise ValueError("generate_structured requires either schema or response_schema")

        if resolved_schema is JobPosting:
            return resolved_schema(
                company_name=self._extract_company(prompt),
                job_title=self._extract_title(prompt),
                summary="Stubbed job description summary for offline testing.",
                key_requirements=["Python", "Testing", "Automation"],
                raw_text=self._extract_raw_text(prompt),
            )

        if resolved_schema is DiscoveryResult:
            return resolved_schema(
                jobs=[
                    DiscoveredJob(title="Software Engineer", company="StubCorp", url="/jobs/123"),
                    DiscoveredJob(title="Platform Engineer", company="StubCorp", url="/jobs/456"),
                ]
            )

        if resolved_schema is JobScore:
            return resolved_schema(score=75, reasoning="Stub provider score for deterministic testing.")

        # Resume tailoring: return a small, valid ResumeContent so the
        # render/compile path can be exercised offline.
        from .resume_model import ResumeContent

        if resolved_schema is ResumeContent:
            return resolved_schema(
                header={"name": "Stub Candidate", "email": "stub@example.com", "links": []},
                education=[
                    {
                        "institution": "Stub University",
                        "location": "Remote",
                        "degree": "B.Sc. Computer Science",
                        "dates": "2018 -- 2022",
                        "highlights": [],
                    }
                ],
                skills=[{"category": "Languages", "items": ["Python", "Testing"]}],
                summary="Stubbed tailored summary for offline testing.",
                experience=[
                    {
                        "company": "StubCorp",
                        "location": "Remote",
                        "roles": [{"title": "Software Engineer", "dates": "2022 -- Present"}],
                        "bullets": ["Built automation tooling that saved time."],
                    }
                ],
                projects=[
                    {
                        "name": "Stub Project",
                        "tech": ["Python"],
                        "bullets": ["Implemented a deterministic test fixture."],
                    }
                ],
            )

        raise ValueError(f"StubProvider does not know how to construct {resolved_schema.__name__}")

    def _extract_company(self, prompt: str) -> str:
        return "StubCorp"

    def _extract_title(self, prompt: str) -> str:
        return "Software Engineer"

    def _extract_raw_text(self, prompt: str) -> str:
        match = re.search(r"Raw Job Description:\s*(.*?)\s*Extract:", prompt, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "Stub raw job description"

    def _tailor_resume(self, prompt: str) -> str:
        return r"""\documentclass{article}
\begin{document}
Stub tailored resume.
\end{document}"""


def create_default_provider() -> LLMProvider:
    if os.getenv("RESUME_TAILOR_LLM_MODE", "real").lower() in {"stub", "test", "offline"}:
        return StubProvider()
    provider = os.getenv("LLM_PROVIDER", "claude").lower()
    if provider == "gemini":
        return GeminiProvider()
    return ClaudeAgentProvider()
