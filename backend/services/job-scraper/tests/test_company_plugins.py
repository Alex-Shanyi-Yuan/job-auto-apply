from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plugins.plugin_registry import plugin_registry


class CompanyPluginResolverTests(unittest.TestCase):
    def setUp(self):
        plugin_registry.load_from_directory(Path(__file__).resolve().parents[1] / "plugins")

    def test_linkedin_job_url_resolution(self):
        plugin = plugin_registry.get_plugin_for_url("https://www.linkedin.com/jobs/search/?keywords=ai")
        resolved = plugin.resolve_job_url(
            "/jobs/view/software-engineer-123",
            "https://www.linkedin.com/jobs/search/?keywords=ai",
        )

        self.assertEqual(plugin.manifest.name, "linkedin")
        self.assertEqual(resolved, "https://www.linkedin.com/jobs/view/software-engineer-123")

    def test_netflix_job_url_resolution(self):
        plugin = plugin_registry.get_plugin_for_url("https://jobs.netflix.com/search")
        resolved = plugin.resolve_job_url(
            "/jobs/790123456789",
            "https://jobs.netflix.com/search",
        )

        self.assertEqual(plugin.manifest.name, "netflix")
        self.assertEqual(resolved, "https://jobs.netflix.com/jobs/790123456789")

    def test_jane_street_job_url_resolution(self):
        plugin = plugin_registry.get_plugin_for_url("https://www.janestreet.com/join-jane-street/open-roles")
        resolved = plugin.resolve_job_url(
            "/join-jane-street/position/1234",
            "https://www.janestreet.com/join-jane-street/open-roles",
        )

        self.assertEqual(plugin.manifest.name, "jane_street")
        self.assertEqual(
            resolved,
            "https://www.janestreet.com/join-jane-street/position/1234",
        )

    def test_openai_job_url_resolution(self):
        plugin = plugin_registry.get_plugin_for_url("https://boards.greenhouse.io/openai")
        resolved = plugin.resolve_job_url(
            "/openai/jobs/12345",
            "https://boards.greenhouse.io/openai",
        )

        self.assertEqual(plugin.manifest.name, "openai")
        self.assertEqual(resolved, "https://boards.greenhouse.io/openai/jobs/12345")

    def test_anthropic_job_url_resolution(self):
        plugin = plugin_registry.get_plugin_for_url("https://www.anthropic.com/careers")
        resolved = plugin.resolve_job_url(
            "/careers/12345",
            "https://www.anthropic.com/careers",
        )

        self.assertEqual(plugin.manifest.name, "anthropic")
        self.assertEqual(resolved, "https://www.anthropic.com/careers/12345")


if __name__ == "__main__":
    unittest.main()
