from __future__ import annotations

from ..generic.extractor import clean_html_for_llm as generic_clean_html_for_llm
from ..generic.extractor import clean_text as generic_clean_text


def clean_html_for_llm(soup, base_url: str) -> str:
    return generic_clean_html_for_llm(soup, base_url)


def clean_text(soup) -> str:
    return generic_clean_text(soup)
