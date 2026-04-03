from __future__ import annotations

from ..generic.resolver import resolve_job_url as generic_resolve_job_url


def resolve_job_url(job_url: str, source_url: str) -> str:
    return generic_resolve_job_url(job_url, source_url)
