from __future__ import annotations

import re
from urllib.parse import urlparse

from typing import Any

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - import-time fallback for lightweight tests
    BeautifulSoup = Any


def clean_html_for_llm(soup: BeautifulSoup, base_url: str) -> str:
    for element in soup(["script", "style", "svg", "img", "noscript", "iframe", "video", "audio"]):
        element.decompose()

    for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith("<!--")):
        comment.extract()

    for element in soup.find_all(attrs={"style": re.compile(r"display:\s*none", re.I)}):
        element.decompose()
    for element in soup.find_all(attrs={"hidden": True}):
        element.decompose()

    for tag in soup.find_all(True):
        if tag.name == "a":
            href = tag.get("href", "")
            if href and not href.startswith(("http://", "https://", "mailto:", "javascript:")):
                if href.startswith("/"):
                    parsed = urlparse(base_url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
            tag.attrs = {"href": href} if href else {}
        else:
            tag.attrs = {}

    body = soup.find("body") or soup
    return str(body)


def clean_text(soup: BeautifulSoup) -> str:
    for script in soup(["script", "style", "svg", "img"]):
        script.decompose()

    text = soup.get_text(separator="\n")
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)
