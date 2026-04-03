from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SitePluginManifest:
    name: str
    version: str
    domains: List[str] = field(default_factory=list)
    extractor_module: str = "extractor"
    resolver_module: str = "resolver"
    wait_selector: Optional[str] = None
    pagination_strategy: str = "none"
    requires_login: bool = False
