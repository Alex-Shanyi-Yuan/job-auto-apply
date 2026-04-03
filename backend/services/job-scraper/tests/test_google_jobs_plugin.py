from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plugins.plugin_registry import plugin_registry


class GoogleJobsPluginTests(unittest.TestCase):
    def setUp(self):
        plugin_registry.load_from_directory(Path(__file__).resolve().parents[1] / "plugins")

    def test_google_jobs_plugin_selected_for_google_domain(self):
        plugin = plugin_registry.get_plugin_for_url("https://www.google.com/search?q=jobs")

        self.assertEqual(plugin.manifest.name, "google_jobs")

    def test_google_jobs_resolver_unwraps_google_redirect(self):
        plugin = plugin_registry.get_plugin_for_url("https://www.google.com/search?q=jobs")
        resolved = plugin.resolve_job_url(
            "https://www.google.com/url?q=https%3A%2F%2Fcareers.example.com%2Fjobs%2F123&sa=U&ved=2ahUKE",
            "https://www.google.com/search?q=jobs",
        )

        self.assertEqual(resolved, "https://careers.example.com/jobs/123")


if __name__ == "__main__":
    unittest.main()
