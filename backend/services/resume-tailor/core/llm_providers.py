"""LLM provider abstractions for resume tailoring.

This module keeps the AI-facing contract small so the rest of the pipeline can
be tested with deterministic stubs when live model access is unavailable.
"""

from __future__ import annotations

import json
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar

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
    return GeminiProvider()
