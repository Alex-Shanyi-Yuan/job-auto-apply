from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from .plugin_schema import SitePluginManifest


@dataclass
class LoadedPlugin:
    manifest: SitePluginManifest
    extractor: object
    resolver: object

    def extract_html(self, soup, base_url: str) -> str:
        extractor = getattr(self.extractor, "clean_html_for_llm", None)
        if extractor:
            return extractor(soup, base_url)
        raise AttributeError(f"Plugin {self.manifest.name} is missing clean_html_for_llm")

    def extract_text(self, soup) -> str:
        extractor = getattr(self.extractor, "clean_text", None)
        if extractor:
            return extractor(soup)
        text = soup.get_text(separator="\n")
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())

    def resolve_job_url(self, job_url: str, source_url: str) -> str:
        resolver = getattr(self.resolver, "resolve_job_url", None)
        if resolver:
            return resolver(job_url, source_url)
        return job_url


class PluginRegistry:
    def __init__(self):
        self._plugins_by_domain: Dict[str, LoadedPlugin] = {}
        self._generic_plugin: Optional[LoadedPlugin] = None

    def load_from_directory(self, plugin_root: Optional[Path] = None) -> None:
        plugin_root = plugin_root or Path(__file__).parent
        self._plugins_by_domain = {}
        self._generic_plugin = None

        for plugin_dir in plugin_root.iterdir():
            if not plugin_dir.is_dir():
                continue

            manifest_path = plugin_dir / "plugin.json"
            if not manifest_path.exists():
                continue

            try:
                manifest = self._load_manifest(manifest_path)
                extractor = self._load_module(plugin_dir, manifest.extractor_module)
                resolver = self._load_module(plugin_dir, manifest.resolver_module)
                loaded = LoadedPlugin(manifest=manifest, extractor=extractor, resolver=resolver)

                if manifest.name == "generic":
                    self._generic_plugin = loaded

                for domain in manifest.domains:
                    self._plugins_by_domain[domain.lower()] = loaded
            except Exception:
                # Invalid plugins are skipped so the service still starts.
                continue

        if self._generic_plugin is None:
            self._generic_plugin = self._build_builtin_generic(plugin_root)

    def get_plugin_for_url(self, url: str) -> LoadedPlugin:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower()

        if hostname in self._plugins_by_domain:
            return self._plugins_by_domain[hostname]

        for domain, plugin in self._plugins_by_domain.items():
            if hostname == domain or hostname.endswith(f".{domain}"):
                return plugin

        if self._generic_plugin is None:
            raise RuntimeError("Generic plugin not loaded")
        return self._generic_plugin

    def _load_manifest(self, manifest_path: Path) -> SitePluginManifest:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return SitePluginManifest(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            domains=data.get("domains", []),
            extractor_module=data.get("extractor_module", "extractor"),
            resolver_module=data.get("resolver_module", "resolver"),
            wait_selector=data.get("wait_selector"),
            pagination_strategy=data.get("pagination_strategy", "none"),
            requires_login=data.get("requires_login", False),
        )

    def _load_module(self, plugin_dir: Path, module_name: str):
        package_name = f"plugins.{plugin_dir.name}.{module_name}"
        return importlib.import_module(package_name)

    def _build_builtin_generic(self, plugin_root: Path) -> LoadedPlugin:
        generic_dir = plugin_root / "generic"
        manifest = SitePluginManifest(name="generic", version="1.0.0", domains=[])
        extractor = importlib.import_module("plugins.generic.extractor")
        resolver = importlib.import_module("plugins.generic.resolver")
        return LoadedPlugin(manifest=manifest, extractor=extractor, resolver=resolver)


plugin_registry = PluginRegistry()
