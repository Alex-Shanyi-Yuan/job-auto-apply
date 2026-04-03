from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plugins.plugin_registry import plugin_registry


class PluginRegistryTests(unittest.TestCase):
    def setUp(self):
        plugin_registry.load_from_directory(Path(__file__).resolve().parents[1] / "plugins")

    def test_generic_plugin_selected_for_unknown_domain(self):
        plugin = plugin_registry.get_plugin_for_url("https://example.com/jobs/123")

        self.assertEqual(plugin.manifest.name, "generic")

    def test_linkedin_plugin_selected(self):
        plugin = plugin_registry.get_plugin_for_url("https://www.linkedin.com/jobs/search/?keywords=python")

        self.assertEqual(plugin.manifest.name, "linkedin")

    def test_netflix_plugin_selected(self):
        plugin = plugin_registry.get_plugin_for_url("https://jobs.netflix.com/search")

        self.assertEqual(plugin.manifest.name, "netflix")

    def test_jane_street_plugin_selected(self):
        plugin = plugin_registry.get_plugin_for_url("https://www.janestreet.com/join-jane-street/open-roles")

        self.assertEqual(plugin.manifest.name, "jane_street")

    def test_openai_plugin_selected(self):
        plugin = plugin_registry.get_plugin_for_url("https://boards.greenhouse.io/openai")

        self.assertEqual(plugin.manifest.name, "openai")

    def test_anthropic_plugin_selected(self):
        plugin = plugin_registry.get_plugin_for_url("https://www.anthropic.com/careers")

        self.assertEqual(plugin.manifest.name, "anthropic")


if __name__ == "__main__":
    unittest.main()
