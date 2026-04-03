from __future__ import annotations

from urllib.parse import parse_qs, unquote, urljoin, urlparse


def resolve_job_url(job_url: str, source_url: str) -> str:
    parsed = urlparse(job_url)
    if parsed.scheme in {"http", "https"} and parsed.hostname and "google" in parsed.hostname.lower():
        query = parse_qs(parsed.query)
        for key in ("url", "q", "adurl"):
            if key in query and query[key]:
                candidate = unquote(query[key][0])
                if candidate.startswith(("http://", "https://")):
                    return candidate
                return _generic_resolve(candidate, source_url)
        return job_url

    if job_url.startswith("/url?"):
        query = parse_qs(parsed.query)
        for key in ("url", "q", "adurl"):
            if key in query and query[key]:
                candidate = unquote(query[key][0])
                if candidate.startswith(("http://", "https://")):
                    return candidate
                return _generic_resolve(candidate, source_url)

    return _generic_resolve(job_url, source_url)


def _generic_resolve(job_url: str, source_url: str) -> str:
    if job_url.startswith(("http://", "https://")):
        return job_url

    parsed = urlparse(source_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    if job_url.startswith("/"):
        return base_url + job_url

    return urljoin(base_url + "/", job_url)
