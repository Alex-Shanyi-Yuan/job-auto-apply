from __future__ import annotations

from urllib.parse import parse_qs, unquote, urljoin, urlparse


def _generic_resolve(job_url: str, source_url: str) -> str:
    if job_url.startswith(("http://", "https://")):
        return job_url

    parsed = urlparse(source_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    if job_url.startswith("/"):
        return base_url + job_url

    return urljoin(base_url + "/", job_url)


def _resolve_google_job_url(job_url: str, source_url: str) -> str:
    parsed_url = urlparse(job_url)
    hostname = (parsed_url.hostname or "").lower()
    if parsed_url.scheme in {"http", "https"} and "google" in hostname:
        query = parse_qs(parsed_url.query)
        for key in ("url", "q", "adurl"):
            if key in query and query[key]:
                candidate = unquote(query[key][0])
                if candidate.startswith(("http://", "https://")):
                    return candidate
                return _generic_resolve(candidate, source_url)
        return job_url

    if job_url.startswith("/url?"):
        query = parse_qs(parsed_url.query)
        for key in ("url", "q", "adurl"):
            if key in query and query[key]:
                candidate = unquote(query[key][0])
                if candidate.startswith(("http://", "https://")):
                    return candidate
                return _generic_resolve(candidate, source_url)

    return _generic_resolve(job_url, source_url)


def _resolve_linkedin_job_url(job_url: str, source_url: str) -> str:
    return _generic_resolve(job_url, source_url)


def _resolve_greenhouse_job_url(job_url: str, source_url: str) -> str:
    return _generic_resolve(job_url, source_url)


def _resolve_nflx_job_url(job_url: str, source_url: str) -> str:
    return _generic_resolve(job_url, source_url)


def _resolve_jane_street_job_url(job_url: str, source_url: str) -> str:
    return _generic_resolve(job_url, source_url)


def _resolve_openai_job_url(job_url: str, source_url: str) -> str:
    return _generic_resolve(job_url, source_url)


def _resolve_anthropic_job_url(job_url: str, source_url: str) -> str:
    return _generic_resolve(job_url, source_url)


def resolve_job_url(job_url: str, source_url: str) -> str:
    hostname = (urlparse(source_url).hostname or "").lower()

    if hostname.endswith("google.com"):
        return _resolve_google_job_url(job_url, source_url)
    if hostname.endswith("linkedin.com"):
        return _resolve_linkedin_job_url(job_url, source_url)
    if hostname.endswith("greenhouse.io") or hostname.endswith("boards.greenhouse.io"):
        return _resolve_greenhouse_job_url(job_url, source_url)
    if hostname.endswith("netflix.com") or hostname.endswith("jobs.netflix.com") or hostname.endswith("netflex.com"):
        return _resolve_nflx_job_url(job_url, source_url)
    if hostname.endswith("janestreet.com") or hostname.endswith("www.janestreet.com"):
        return _resolve_jane_street_job_url(job_url, source_url)
    if hostname.endswith("openai.com"):
        return _resolve_openai_job_url(job_url, source_url)
    if hostname.endswith("anthropic.com"):
        return _resolve_anthropic_job_url(job_url, source_url)

    return _generic_resolve(job_url, source_url)
