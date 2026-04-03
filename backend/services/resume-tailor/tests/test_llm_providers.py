from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm_providers import StubProvider
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


if __name__ == "__main__":
    unittest.main()
