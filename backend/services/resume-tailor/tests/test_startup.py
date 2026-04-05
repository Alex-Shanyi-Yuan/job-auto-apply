from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool

import server
from database import SQLModel, get_session
from core.startup import StartupCheck, StartupHealthRunner


@pytest.fixture(name="session")
def session_fixture(monkeypatch):
    monkeypatch.setenv("TESTING", "true")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(server, "engine", engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        yield session

    server.app.dependency_overrides[get_session] = get_session_override
    client = TestClient(server.app)
    yield client
    server.app.dependency_overrides.clear()


def test_startup_health_runner_pass_path():
    checks = [
        StartupCheck("database_connectivity", True, lambda: (True, "ok", {})),
        StartupCheck("migrations_baseline", True, lambda: (True, "ok", {})),
        StartupCheck("master_resume_presence", True, lambda: (True, "ok", {})),
        StartupCheck("gemini_api_key_configured", True, lambda: (True, "ok", {})),
        StartupCheck("scraper_reachability", True, lambda: (True, "ok", {})),
        StartupCheck("pdflatex_availability", True, lambda: (True, "ok", {})),
    ]
    runner = StartupHealthRunner(checks=checks, fail_fast=False, block_apply_on_critical=True)

    report = runner.run()

    assert [check.name for check in report.checks] == [
        "database_connectivity",
        "migrations_baseline",
        "master_resume_presence",
        "gemini_api_key_configured",
        "scraper_reachability",
        "pdflatex_availability",
    ]
    assert report.status == "ok"
    assert report.critical_failures == []
    assert report.apply_blocked is False


def test_startup_health_runner_aggregates_critical_failures():
    checks = [
        StartupCheck("database_connectivity", True, lambda: (False, "db down", {})),
        StartupCheck("migrations_baseline", True, lambda: (False, "not at head", {})),
        StartupCheck("pdflatex_availability", False, lambda: (False, "missing", {})),
    ]
    runner = StartupHealthRunner(checks=checks, fail_fast=False, block_apply_on_critical=True)

    report = runner.run()

    assert report.status == "failed"
    assert report.critical_failures == ["database_connectivity", "migrations_baseline"]
    assert report.apply_blocked is True


def test_startup_health_runner_fail_fast_stops_at_first_critical():
    checks = [
        StartupCheck("database_connectivity", True, lambda: (False, "db down", {})),
        StartupCheck("migrations_baseline", True, lambda: (True, "ok", {})),
    ]
    runner = StartupHealthRunner(checks=checks, fail_fast=True, block_apply_on_critical=True)

    report = runner.run()

    assert [check.name for check in report.checks] == ["database_connectivity"]
    assert report.critical_failures == ["database_connectivity"]


def test_health_endpoint_returns_startup_report(client: TestClient):
    server.app.state.startup_health = {
        "status": "failed",
        "fail_fast_enabled": False,
        "critical_failures": ["database_connectivity"],
        "apply_blocked": True,
        "apply_block_reason": "database_connectivity failed",
        "checks": [],
    }

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "failed"
    assert response.json()["apply_blocked"] is True


def test_apply_is_blocked_when_startup_health_is_critical(client: TestClient):
    server.app.state.startup_health = {
        "status": "failed",
        "fail_fast_enabled": False,
        "critical_failures": ["database_connectivity"],
        "apply_blocked": True,
        "apply_block_reason": "database_connectivity failed",
        "checks": [],
    }

    response = client.post("/apply", json={"url": "http://blocked.com"})

    assert response.status_code == 503
    assert "startup health check" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_lifespan_sets_startup_health_on_success(monkeypatch):
    monkeypatch.setenv("TESTING", "false")

    async def fake_reconcile(_phase):
        return None

    runner = SimpleNamespace(
        fail_fast=True,
        run=lambda: SimpleNamespace(
            to_dict=lambda: {
                "status": "ok",
                "fail_fast_enabled": True,
                "critical_failures": [],
                "apply_blocked": False,
                "apply_block_reason": None,
                "checks": [],
            },
            critical_failures=[],
            apply_block_reason=None,
        ),
        skipped_report=lambda: SimpleNamespace(to_dict=lambda: {"status": "not_run", "checks": []}),
    )

    monkeypatch.setattr(server, "_run_db_reconcile", fake_reconcile)
    monkeypatch.setattr(server, "create_db_and_tables", lambda: None)
    monkeypatch.setattr(server, "startup_health_runner", runner)

    async with server.lifespan(server.app):
        assert server.app.state.startup_health["status"] == "ok"


@pytest.mark.asyncio
async def test_lifespan_raises_when_fail_fast_and_critical(monkeypatch):
    monkeypatch.setenv("TESTING", "false")

    async def fake_reconcile(_phase):
        return None

    runner = SimpleNamespace(
        fail_fast=True,
        run=lambda: SimpleNamespace(
            to_dict=lambda: {
                "status": "failed",
                "fail_fast_enabled": True,
                "critical_failures": ["database_connectivity"],
                "apply_blocked": True,
                "apply_block_reason": "Startup health checks failed: database_connectivity",
                "checks": [],
            },
            critical_failures=["database_connectivity"],
            apply_block_reason="Startup health checks failed: database_connectivity",
        ),
        skipped_report=lambda: SimpleNamespace(to_dict=lambda: {"status": "not_run", "checks": []}),
    )

    monkeypatch.setattr(server, "_run_db_reconcile", fake_reconcile)
    monkeypatch.setattr(server, "create_db_and_tables", lambda: None)
    monkeypatch.setattr(server, "startup_health_runner", runner)

    with pytest.raises(RuntimeError, match="Startup health checks failed"):
        async with server.lifespan(server.app):
            pass
