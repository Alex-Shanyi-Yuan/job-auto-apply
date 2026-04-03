from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.site_plugins import resolve_job_url


class SitePluginResolverTests(unittest.TestCase):
    def test_google_jobs_redirect_is_unwrapped(self):
        resolved = resolve_job_url(
            "https://www.google.com/url?q=https%3A%2F%2Fcareers.example.com%2Fjobs%2F123&sa=U",
            "https://www.google.com/search?q=jobs",
        )

        self.assertEqual(resolved, "https://careers.example.com/jobs/123")

    def test_generic_relative_resolution_still_works(self):
        resolved = resolve_job_url("/jobs/123", "https://jobs.example.com/search")

        self.assertEqual(resolved, "https://jobs.example.com/jobs/123")

    def test_linkedin_relative_path_resolution(self):
        resolved = resolve_job_url(
            "/jobs/view/software-engineer-123",
            "https://www.linkedin.com/jobs/search/?keywords=software",
        )

        self.assertEqual(resolved, "https://www.linkedin.com/jobs/view/software-engineer-123")

    def test_netflix_relative_path_resolution(self):
        resolved = resolve_job_url(
            "/jobs/790123456789",
            "https://jobs.netflix.com/search",
        )

        self.assertEqual(resolved, "https://jobs.netflix.com/jobs/790123456789")

    def test_jane_street_relative_path_resolution(self):
        resolved = resolve_job_url(
            "/join-jane-street/position/1234",
            "https://www.janestreet.com/join-jane-street/open-roles/",
        )

        self.assertEqual(
            resolved,
            "https://www.janestreet.com/join-jane-street/position/1234",
        )

    def test_openai_greenhouse_relative_path_resolution(self):
        resolved = resolve_job_url(
            "/openai/jobs/12345",
            "https://boards.greenhouse.io/openai",
        )

        self.assertEqual(resolved, "https://boards.greenhouse.io/openai/jobs/12345")

    def test_anthropic_relative_path_resolution(self):
        resolved = resolve_job_url(
            "/careers/12345",
            "https://www.anthropic.com/careers",
        )

        self.assertEqual(resolved, "https://www.anthropic.com/careers/12345")


if __name__ == "__main__":
    unittest.main()
