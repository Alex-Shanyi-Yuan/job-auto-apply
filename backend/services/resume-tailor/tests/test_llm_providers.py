from pathlib import Path
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm_providers import ClaudeAgentProvider, StubProvider
from core.models import DiscoveryResult, JobPosting, JobScore


class StubProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = StubProvider()

    def test_generate_structured_job_posting(self):
        prompt = """
        Raw Job Description:
        Build reliable systems.

        Extract:
        1. Company Name (if not explicitly stated, infer from context or use "Unknown Company")
        2. Job Title
        """

        result = self.provider.generate_structured(prompt, JobPosting)

        self.assertEqual(result.company_name, "StubCorp")
        self.assertEqual(result.job_title, "Software Engineer")
        self.assertEqual(result.key_requirements, ["Python", "Testing", "Automation"])

    def test_generate_structured_discovery(self):
        result = self.provider.generate_structured("discover jobs", DiscoveryResult)

        self.assertEqual(len(result.jobs), 2)
        self.assertEqual(result.jobs[0].company, "StubCorp")

    def test_generate_structured_job_score(self):
        result = self.provider.generate_structured("score job", JobScore)

        self.assertEqual(result.score, 75)
        self.assertIn("Stub provider", result.reasoning)


def _install_fake_sdk(
    *,
    structured_output=None,
    result_text=None,
    assistant_text=None,
    subtype="success",
    capture=None,
):
    """Register a fake ``claude_agent_sdk`` module for the provider to import."""
    module = types.ModuleType("claude_agent_sdk")

    class ClaudeAgentOptions:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            if capture is not None:
                capture["options"] = kwargs

    class TextBlock:
        def __init__(self, text):
            self.text = text

    class AssistantMessage:
        def __init__(self, content):
            self.content = content

    class ResultMessage:
        def __init__(self, structured_output=None, result=None, subtype="success"):
            self.structured_output = structured_output
            self.result = result
            self.subtype = subtype

    async def query(*, prompt, options):
        if capture is not None:
            capture["prompt"] = prompt
        if assistant_text is not None:
            yield AssistantMessage([TextBlock(assistant_text)])
        yield ResultMessage(
            structured_output=structured_output, result=result_text, subtype=subtype
        )

    module.ClaudeAgentOptions = ClaudeAgentOptions
    module.TextBlock = TextBlock
    module.AssistantMessage = AssistantMessage
    module.ResultMessage = ResultMessage
    module.query = query
    return mock.patch.dict(sys.modules, {"claude_agent_sdk": module})


class ClaudeAgentProviderTests(unittest.TestCase):
    def setUp(self):
        self._env = mock.patch.dict(
            "os.environ",
            {"CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat01-test"},
            clear=False,
        )
        self._env.start()
        # Ensure no real API key is present to shadow the token during tests.
        import os

        os.environ.pop("ANTHROPIC_API_KEY", None)

    def tearDown(self):
        self._env.stop()

    def test_constructor_requires_oauth_token(self):
        import os

        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                ClaudeAgentProvider()
        self.assertTrue(True)  # token restored by env patch in tearDown

    def test_generate_structured_returns_job_score(self):
        with _install_fake_sdk(structured_output={"score": 88, "reasoning": "Strong match"}):
            provider = ClaudeAgentProvider()
            result = provider.generate_structured("score this job", JobScore)

        self.assertEqual(result.score, 88)
        self.assertEqual(result.reasoning, "Strong match")

    def test_generate_structured_passes_json_schema(self):
        capture = {}
        with _install_fake_sdk(
            structured_output={"score": 50, "reasoning": "ok"}, capture=capture
        ):
            ClaudeAgentProvider().generate_structured("score", JobScore)

        output_format = capture["options"].get("output_format")
        self.assertEqual(output_format["type"], "json_schema")
        self.assertIn("properties", output_format["schema"])
        # Non-agentic, isolated configuration (no tools, no filesystem settings).
        self.assertEqual(capture["options"]["allowed_tools"], [])
        self.assertEqual(capture["options"]["setting_sources"], [])
        # max_turns must NOT be pinned to 1 — it breaks structured output.
        self.assertNotEqual(capture["options"].get("max_turns"), 1)

    def test_generate_structured_raises_without_structured_output(self):
        with _install_fake_sdk(
            structured_output=None, subtype="error_max_structured_output_retries"
        ):
            provider = ClaudeAgentProvider()
            provider._STRUCTURED_RETRIES = 1  # avoid backoff sleeps in tests
            with self.assertRaises(RuntimeError):
                provider.generate_structured("score", JobScore)

    def test_generate_text_strips_code_fences(self):
        fenced = "```latex\n\\documentclass{article}\n```"
        with _install_fake_sdk(result_text=fenced):
            text = ClaudeAgentProvider().generate_text("tailor this")

        self.assertEqual(text, "\\documentclass{article}")

    def test_generate_text_falls_back_to_assistant_blocks(self):
        with _install_fake_sdk(result_text=None, assistant_text="plain answer"):
            text = ClaudeAgentProvider().generate_text("hello")

        self.assertEqual(text, "plain answer")


if __name__ == "__main__":
    unittest.main()
