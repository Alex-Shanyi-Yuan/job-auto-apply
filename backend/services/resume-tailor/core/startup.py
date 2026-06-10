from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
import os
import subprocess

import httpx
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from database import engine
from core.db_sync import get_alembic_version


SERVICE_ROOT = Path(__file__).resolve().parents[1]


CheckFn = Callable[[], tuple[bool, str, dict[str, Any]]]


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class StartupCheck:
    name: str
    critical: bool
    fn: CheckFn


@dataclass
class StartupCheckResult:
    name: str
    critical: bool
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "critical": self.critical,
            "ok": self.ok,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class StartupHealthReport:
    checks: list[StartupCheckResult]
    status: str
    critical_failures: list[str]
    fail_fast_enabled: bool
    apply_blocked: bool
    apply_block_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "fail_fast_enabled": self.fail_fast_enabled,
            "critical_failures": self.critical_failures,
            "apply_blocked": self.apply_blocked,
            "apply_block_reason": self.apply_block_reason,
            "checks": [check.to_dict() for check in self.checks],
        }


class StartupHealthRunner:
    def __init__(
        self,
        checks: list[StartupCheck],
        *,
        fail_fast: bool,
        block_apply_on_critical: bool,
    ):
        self.checks = checks
        self.fail_fast = fail_fast
        self.block_apply_on_critical = block_apply_on_critical

    def run(self) -> StartupHealthReport:
        results: list[StartupCheckResult] = []
        critical_failures: list[str] = []

        for check in self.checks:
            try:
                ok, message, details = check.fn()
            except Exception as exc:
                ok = False
                message = str(exc)
                details = {}

            results.append(
                StartupCheckResult(
                    name=check.name,
                    critical=check.critical,
                    ok=ok,
                    message=message,
                    details=details,
                )
            )

            if not ok and check.critical:
                critical_failures.append(check.name)
                if self.fail_fast:
                    break

        status = "ok"
        if critical_failures:
            status = "failed"
        elif any(not result.ok for result in results):
            status = "degraded"

        apply_blocked = self.block_apply_on_critical and bool(critical_failures)
        apply_block_reason = (
            f"Startup health checks failed: {', '.join(critical_failures)}"
            if apply_blocked
            else None
        )

        return StartupHealthReport(
            checks=results,
            status=status,
            critical_failures=critical_failures,
            fail_fast_enabled=self.fail_fast,
            apply_blocked=apply_blocked,
            apply_block_reason=apply_block_reason,
        )

    def skipped_report(self) -> StartupHealthReport:
        return StartupHealthReport(
            checks=[],
            status="not_run",
            critical_failures=[],
            fail_fast_enabled=self.fail_fast,
            apply_blocked=False,
            apply_block_reason=None,
        )


def _check_database_connectivity() -> tuple[bool, str, dict[str, Any]]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True, "Database reachable", {}


def _check_migrations_baseline() -> tuple[bool, str, dict[str, Any]]:
    config_path = SERVICE_ROOT / "alembic.ini"
    if not config_path.exists():
        return False, "alembic.ini not found", {"path": str(config_path)}

    alembic_config = Config(str(config_path))
    script = ScriptDirectory.from_config(alembic_config)
    expected_heads = script.get_heads()
    current_revision = get_alembic_version(engine)

    if current_revision in expected_heads:
        return True, "Database migration baseline is at head", {"current_revision": current_revision}

    return False, "Database migration baseline is not at head", {
        "current_revision": current_revision,
        "expected_heads": expected_heads,
    }


def _check_master_resume_presence() -> tuple[bool, str, dict[str, Any]]:
    configured_path = os.getenv("MASTER_RESUME_PATH", "./data/master.tex")
    resume_path = Path(configured_path)
    if not resume_path.is_absolute():
        resume_path = (SERVICE_ROOT / resume_path).resolve()

    if resume_path.exists():
        return True, "Master resume file exists", {"path": str(resume_path)}
    return False, "Master resume file is missing", {"path": str(resume_path)}


def _check_gemini_api_key_configured() -> tuple[bool, str, dict[str, Any]]:
    key = (os.getenv("GOOGLE_API_KEY") or "").strip()
    if not key:
        return False, "GOOGLE_API_KEY is not configured", {}
    if "your_gemini_api_key_here" in key:
        return False, "GOOGLE_API_KEY is still using a placeholder value", {}
    return True, "GOOGLE_API_KEY is configured", {}


def _check_claude_auth_configured() -> tuple[bool, str, dict[str, Any]]:
    token = (os.getenv("CLAUDE_CODE_OAUTH_TOKEN") or "").strip()
    if not token:
        return False, (
            "CLAUDE_CODE_OAUTH_TOKEN is not configured. Run `claude setup-token` and set it."
        ), {}
    if "your_oauth_token_here" in token or "sk-ant-oat01-..." in token:
        return False, "CLAUDE_CODE_OAUTH_TOKEN is still using a placeholder value", {}
    # An API key present in the same process shadows the OAuth token and bills
    # pay-per-token instead of the subscription, so refuse to start on it.
    if (os.getenv("ANTHROPIC_API_KEY") or "").strip():
        return False, (
            "ANTHROPIC_API_KEY is set and would override CLAUDE_CODE_OAUTH_TOKEN "
            "(billing pay-per-token instead of your subscription). Unset it."
        ), {}
    return True, "CLAUDE_CODE_OAUTH_TOKEN is configured", {}


def _check_claude_cli_available() -> tuple[bool, str, dict[str, Any]]:
    proc = subprocess.run(
        ["claude", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        first_line = proc.stdout.splitlines()[0] if proc.stdout else "claude available"
        return True, "claude CLI is available", {"version": first_line}
    return False, "claude CLI is unavailable", {"returncode": proc.returncode}


def _check_scraper_reachability() -> tuple[bool, str, dict[str, Any]]:
    base_url = os.getenv("SCRAPER_SERVICE_URL", "http://scraper:8001").rstrip("/")
    timeout = float(os.getenv("STARTUP_SCRAPER_TIMEOUT_SECONDS", "5"))
    health_url = f"{base_url}/health"

    response = httpx.get(health_url, timeout=timeout)
    if 200 <= response.status_code < 300:
        return True, "Scraper service is reachable", {"url": health_url, "status_code": response.status_code}
    return False, "Scraper service healthcheck failed", {"url": health_url, "status_code": response.status_code}


def _check_pdflatex_availability() -> tuple[bool, str, dict[str, Any]]:
    proc = subprocess.run(
        ["pdflatex", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        first_line = proc.stdout.splitlines()[0] if proc.stdout else "pdflatex available"
        return True, "pdflatex is available", {"version": first_line}
    return False, "pdflatex is unavailable", {"returncode": proc.returncode}


def _llm_provider_checks() -> list[StartupCheck]:
    """Auth checks for the active LLM provider (Claude by default)."""
    if os.getenv("LLM_PROVIDER", "claude").lower() == "gemini":
        return [
            StartupCheck("gemini_api_key_configured", True, _check_gemini_api_key_configured),
        ]
    return [
        StartupCheck("claude_auth_configured", True, _check_claude_auth_configured),
        StartupCheck("claude_cli_available", True, _check_claude_cli_available),
    ]


def default_startup_checks() -> list[StartupCheck]:
    return [
        StartupCheck("database_connectivity", True, _check_database_connectivity),
        StartupCheck("migrations_baseline", True, _check_migrations_baseline),
        StartupCheck("master_resume_presence", True, _check_master_resume_presence),
        *_llm_provider_checks(),
        StartupCheck("scraper_reachability", True, _check_scraper_reachability),
        StartupCheck("pdflatex_availability", True, _check_pdflatex_availability),
    ]


def build_startup_health_runner() -> StartupHealthRunner:
    return StartupHealthRunner(
        checks=default_startup_checks(),
        fail_fast=_env_bool("STARTUP_FAIL_FAST", True),
        block_apply_on_critical=_env_bool("STARTUP_BLOCK_APPLY_ON_CRITICAL", True),
    )
