from __future__ import annotations

from urllib.parse import urljoin, urlparse


def resolve_job_url(job_url: str, source_url: str) -> str:
    if job_url.startswith(("http://", "https://")):
        return job_url

    parsed = urlparse(source_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    if job_url.startswith("/"):
        return base_url + job_url

    return urljoin(base_url + "/", job_url)
