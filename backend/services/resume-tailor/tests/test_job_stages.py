"""Tests for job stage tracking endpoints."""
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select
from sqlmodel.pool import StaticPool
from database import SQLModel, Job, JobStage, utcnow, get_session
from core.event_bus import JobEvent, EventType
import server
from server import app
from types import SimpleNamespace
from unittest.mock import AsyncMock

def test_get_jobs_includes_stages(session: Session, client: TestClient):
    """Test GET /jobs includes stages for all jobs."""
    # Create two jobs with stages
    job1 = Job(url="http://test1.com", company="Co1", title="SWE1", status="active", retry_count=0)
    job2 = Job(url="http://test2.com", company="Co2", title="SWE2", status="active", retry_count=0)
    session.add(job1)
    session.add(job2)
    session.commit()
    
    stage1 = JobStage(job_id=job1.id, stage_name="applied", completed_at=utcnow())
    stage2 = JobStage(job_id=job2.id, stage_name="applied", completed_at=utcnow())
    stage3 = JobStage(job_id=job2.id, stage_name="oa", completed_at=utcnow())
    session.add_all([stage1, stage2, stage3])
    session.commit()
    
    # Get all jobs
    response = client.get("/jobs")
    
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 2
    
    # Find job2 (has 2 stages)
    job2_data = next(j for j in jobs if j["id"] == job2.id)
    assert len(job2_data["stages"]) == 2
    assert job2_data["stages"][0]["stage_name"] in ["applied", "oa"]

@pytest.fixture(name="session")
def session_fixture(monkeypatch):
    """Create a fresh in-memory database for each test."""
    monkeypatch.setenv("TESTING", "true")  # Set test mode
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
    """Create a test client with dependency override."""
    def get_session_override():
        yield session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_update_job_stages_creates_new_stages(session: Session, client: TestClient):
    """Test creating new stages for a job."""
    # Create a test job
    job = Job(
        url="http://test.com", 
        company="TestCo", 
        title="SWE", 
        status="applied",
        retry_count=0  # Explicitly set to avoid missing column error
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    
    # Update stages via API
    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [
            {"name": "applied", "completed": True, "notes": "Applied online"},
            {"name": "oa", "completed": False}
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert len(data["stages"]) == 1  # Only completed stages returned
    assert data["stages"][0]["stage_name"] == "applied"
    assert data["stages"][0]["notes"] == "Applied online"
    
    # Verify database
    stages = session.exec(
        select(JobStage).where(
            JobStage.job_id == job.id,
            JobStage.completed_at.isnot(None)
        )
    ).all()
    assert len(stages) == 1
    assert stages[0].stage_name == "applied"
    assert stages[0].completed_at is not None

def test_get_job_includes_stages(session: Session, client: TestClient):
    """Test GET /jobs/{id} includes stages in response."""
    # Create job with stages
    job = Job(url="http://test.com", company="TestCo", title="SWE", status="active", retry_count=0)
    session.add(job)
    session.commit()
    
    stage1 = JobStage(job_id=job.id, stage_name="applied", completed_at=utcnow(), notes="Applied online")
    stage2 = JobStage(job_id=job.id, stage_name="oa", completed_at=utcnow())
    session.add(stage1)
    session.add(stage2)
    session.commit()
    
    # Get job via API
    response = client.get(f"/jobs/{job.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "stages" in data
    assert len(data["stages"]) == 2
    assert data["stages"][0]["stage_name"] == "applied"
    assert data["stages"][0]["notes"] == "Applied online"
    assert data["stages"][1]["stage_name"] == "oa"


def test_update_job_stages_unchecks_existing_stage(session: Session, client: TestClient):
    """Test unchecking a previously completed stage."""
    # Create job with existing stage
    job = Job(
        url="http://test.com", 
        company="TestCo", 
        title="SWE", 
        status="active",
        retry_count=0
    )
    session.add(job)
    session.commit()
    
    stage = JobStage(job_id=job.id, stage_name="applied", completed_at=utcnow())
    session.add(stage)
    session.commit()
    
    # Uncheck the stage
    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [
            {"name": "applied", "completed": False}
        ]
    })
    
    assert response.status_code == 200
    
    # Verify completed_at is cleared
    session.refresh(stage)
    assert stage.completed_at is None


def test_update_job_stages_with_rejection(session: Session, client: TestClient):
    """Test marking a job as rejected at a specific stage."""
    job = Job(
        url="http://test.com", 
        company="TestCo", 
        title="SWE", 
        status="active",
        retry_count=0
    )
    session.add(job)
    session.commit()
    
    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [
            {"name": "applied", "completed": True},
            {"name": "oa", "completed": True}
        ],
        "rejection_stage": "oa",
        "rejection_reason": "Failed technical assessment"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["rejection_stage"] == "oa"
    assert data["rejection_reason"] == "Failed technical assessment"


def test_update_job_stages_clears_rejection_with_null(session: Session, client: TestClient):
    """Test clearing rejection metadata when rejection_stage is explicitly null."""
    job = Job(
        url="http://test-clear-rejection.com",
        company="TestCo",
        title="SWE",
        status="rejected",
        rejection_stage="interview",
        rejection_reason="Initial rejection note",
        retry_count=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [{"name": "applied", "completed": True}],
        "rejection_stage": None,
        "rejection_reason": None
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["rejection_stage"] is None
    assert data["rejection_reason"] is None


def test_update_job_stages_rejects_invalid_rejection_stage(session: Session, client: TestClient):
    """Test enum validation rejects invalid rejection stage values."""
    job = Job(
        url="http://test-invalid-rejection.com",
        company="TestCo",
        title="SWE",
        status="active",
        retry_count=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [{"name": "applied", "completed": True}],
        "rejection_stage": "phone_screen",
        "rejection_reason": "Invalid stage value"
    })

    assert response.status_code == 422


def test_update_job_stages_clears_rejection_without_completed_stages(session: Session, client: TestClient):
    """Clearing rejection should move job back to active even when no stage remains completed."""
    job = Job(
        url="http://test-clear-no-stages.com",
        company="TestCo",
        title="SWE",
        status="rejected",
        rejection_stage="oa",
        rejection_reason="Failed OA",
        retry_count=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [{"name": "applied", "completed": False}],
        "rejection_stage": None,
        "rejection_reason": None
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["rejection_stage"] is None
    assert data["rejection_reason"] is None


def test_update_job_stages_without_rejection_field_preserves_existing_rejection(session: Session, client: TestClient):
    """Omitting rejection_stage should not silently clear existing rejection metadata."""
    job = Job(
        url="http://test-preserve-rejection.com",
        company="TestCo",
        title="SWE",
        status="rejected",
        rejection_stage="oa",
        rejection_reason="Failed OA",
        retry_count=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [{"name": "applied", "completed": True}]
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["rejection_stage"] == "oa"
    assert data["rejection_reason"] == "Failed OA"


def test_update_job_stages_sets_offer_status_when_offer_completed(session: Session, client: TestClient):
    """Completing offer stage should move job status to offer."""
    job = Job(
        url="http://test-offer.com",
        company="TestCo",
        title="SWE",
        status="active",
        retry_count=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [
            {"name": "applied", "completed": True},
            {"name": "oa", "completed": False},
            {"name": "interview", "completed": False},
            {"name": "offer", "completed": True},
        ]
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "offer"


def test_update_job_stages_unchecking_offer_returns_to_active(session: Session, client: TestClient):
    """Unchecking offer stage should return status to active when other completed stages remain."""
    job = Job(
        url="http://test-offer-uncheck.com",
        company="TestCo",
        title="SWE",
        status="offer",
        retry_count=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    session.add(JobStage(job_id=job.id, stage_name="applied", completed_at=utcnow()))
    session.add(JobStage(job_id=job.id, stage_name="offer", completed_at=utcnow()))
    session.commit()

    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [
            {"name": "applied", "completed": True},
            {"name": "oa", "completed": False},
            {"name": "interview", "completed": False},
            {"name": "offer", "completed": False},
        ]
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"


def test_update_job_stages_status_override_sets_turndown(session: Session, client: TestClient):
    """status_override should allow toggling to turndown."""
    job = Job(
        url="http://test-turndown.com",
        company="TestCo",
        title="SWE",
        status="active",
        retry_count=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [{"name": "applied", "completed": True}],
        "status_override": "turndown",
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "turndown"


def test_update_job_stages_status_override_rejected_sets_rejection_stage(session: Session, client: TestClient):
    """status_override rejected should set rejection_stage to latest completed stage when missing."""
    job = Job(
        url="http://test-status-rejected.com",
        company="TestCo",
        title="SWE",
        status="active",
        retry_count=0,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    session.add(JobStage(job_id=job.id, stage_name="applied", completed_at=utcnow()))
    session.add(JobStage(job_id=job.id, stage_name="oa", completed_at=utcnow()))
    session.commit()

    response = client.put(f"/jobs/{job.id}/stages", json={
        "stages": [
            {"name": "applied", "completed": True},
            {"name": "oa", "completed": True},
            {"name": "interview", "completed": False},
            {"name": "offer", "completed": False},
        ],
        "status_override": "rejected",
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["rejection_stage"] == "oa"


def test_apply_creates_initial_applied_stage(session: Session, client: TestClient, monkeypatch):
    """Test POST /apply creates initial applied stage immediately."""
    async def mock_process_application(job_id: int, url: str):
        return None

    monkeypatch.setattr(server, "process_application", mock_process_application)

    response = client.post("/apply", json={"url": "http://apply-test.com"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"

    job = session.exec(select(Job).where(Job.url == "http://apply-test.com")).first()
    assert job is not None
    assert job.status == "processing"

    stages = session.exec(
        select(JobStage).where(
            JobStage.job_id == job.id,
            JobStage.stage_name == "applied"
        )
    ).all()
    assert len(stages) == 1
    assert stages[0].completed_at is not None


def test_apply_existing_job_is_idempotent_for_applied_stage(session: Session, client: TestClient, monkeypatch):
    """Test repeated POST /apply does not create duplicate applied stages."""
    async def mock_process_application(job_id: int, url: str):
        return None

    monkeypatch.setattr(server, "process_application", mock_process_application)

    existing_job = Job(url="http://existing-job.com", company="TestCo", title="SWE", status="suggested", retry_count=0)
    session.add(existing_job)
    session.commit()
    session.refresh(existing_job)

    existing_stage = JobStage(job_id=existing_job.id, stage_name="applied", completed_at=utcnow())
    session.add(existing_stage)
    session.commit()

    first_response = client.post("/apply", json={"url": "http://existing-job.com"})
    second_response = client.post("/apply", json={"url": "http://existing-job.com"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    session.refresh(existing_job)
    assert existing_job.status == "processing"

    stages = session.exec(
        select(JobStage).where(
            JobStage.job_id == existing_job.id,
            JobStage.stage_name == "applied"
        )
    ).all()
    assert len(stages) == 1


def test_job_stream_endpoint_returns_sse_events(session: Session, client: TestClient, monkeypatch):
    """Test GET /jobs/{job_id}/stream returns event-stream payload."""
    job = Job(url="http://stream-test.com", company="TestCo", title="SWE", status="processing", retry_count=0)
    session.add(job)
    session.commit()
    session.refresh(job)

    queue = asyncio.Queue()
    queue.put_nowait(
        JobEvent(
            type=EventType.STEP_STARTED,
            timestamp=utcnow(),
            job_id=job.id,
            step="scraping",
        )
    )
    queue.put_nowait(
        JobEvent(
            type=EventType.PIPELINE_COMPLETED,
            timestamp=utcnow(),
            job_id=job.id,
        )
    )

    async def get_job_queue(_: int):
        return queue

    monkeypatch.setattr(server.event_bus, "get_job_queue", get_job_queue)
    create_queue_mock = AsyncMock(return_value=queue)
    monkeypatch.setattr(server.event_bus, "create_job_queue", create_queue_mock)

    with client.stream("GET", f"/jobs/{job.id}/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "\n".join([line for line in response.iter_lines() if line])

    create_queue_mock.assert_not_awaited()
    assert "event: step_started" in body
    assert "event: pipeline_completed" in body
    assert "\"step\": \"scraping\"" in body


def test_job_stream_endpoint_returns_404_when_job_missing(client: TestClient):
    """Test GET /jobs/{job_id}/stream returns 404 for unknown jobs."""
    response = client.get("/jobs/99999/stream")
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


def test_job_stream_endpoint_returns_409_for_non_processing_without_queue(
    session: Session, client: TestClient, monkeypatch
):
    """Non-processing jobs without an active queue should return explicit 409."""
    job = Job(url="http://stream-idle.com", company="TestCo", title="SWE", status="applied", retry_count=0)
    session.add(job)
    session.commit()
    session.refresh(job)

    get_queue_mock = AsyncMock(return_value=None)
    create_queue_mock = AsyncMock()
    monkeypatch.setattr(server.event_bus, "get_job_queue", get_queue_mock)
    monkeypatch.setattr(server.event_bus, "create_job_queue", create_queue_mock)

    response = client.get(f"/jobs/{job.id}/stream")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "No active event stream for this job because it is not processing"
    }
    create_queue_mock.assert_not_awaited()


def test_job_stream_endpoint_waits_briefly_for_processing_queue(session: Session, client: TestClient, monkeypatch):
    """Processing jobs should tolerate short queue creation races."""
    job = Job(url="http://stream-race.com", company="TestCo", title="SWE", status="processing", retry_count=0)
    session.add(job)
    session.commit()
    session.refresh(job)

    queue = asyncio.Queue()
    queue.put_nowait(
        JobEvent(
            type=EventType.PIPELINE_COMPLETED,
            timestamp=utcnow(),
            job_id=job.id,
        )
    )

    calls = {"count": 0}

    async def delayed_get_job_queue(_: int):
        calls["count"] += 1
        if calls["count"] == 1:
            return None
        return queue

    monkeypatch.setattr(server, "STREAM_QUEUE_WAIT_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(server, "STREAM_QUEUE_WAIT_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(server.event_bus, "get_job_queue", delayed_get_job_queue)
    create_queue_mock = AsyncMock(return_value=queue)
    monkeypatch.setattr(server.event_bus, "create_job_queue", create_queue_mock)

    with client.stream("GET", f"/jobs/{job.id}/stream") as response:
        assert response.status_code == 200
        body = "\n".join([line for line in response.iter_lines() if line])

    assert calls["count"] >= 2
    create_queue_mock.assert_not_awaited()
    assert "event: pipeline_completed" in body


@pytest.mark.asyncio
async def test_process_application_creates_queue_before_first_emit(session: Session, monkeypatch):
    """process_application should create per-job queue before the first emitted event."""
    job = Job(url="http://emit-order.com", company="Unknown", title="Unknown", status="processing", retry_count=0)
    session.add(job)
    session.commit()
    session.refresh(job)

    call_order: list[tuple[str, EventType | None]] = []

    async def create_job_queue(job_id: int):
        call_order.append(("create", None))
        return asyncio.Queue()

    async def capture_emit(event: JobEvent):
        call_order.append(("emit", event.type))

    class FakeScrapeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"text": "job description text"}

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return FakeScrapeResponse()

    monkeypatch.setattr(server.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        server,
        "JobParsingAgent",
        lambda: SimpleNamespace(
            parse=lambda _: SimpleNamespace(
                company_name="Acme",
                job_title="Software Engineer",
                key_requirements=["Python", "FastAPI"],
            )
        ),
    )
    monkeypatch.setattr(server, "load_master_resume", lambda _: "master")
    monkeypatch.setattr(server, "ResumeTailorAgent", lambda: SimpleNamespace(tailor=lambda *_: "tailored"))
    monkeypatch.setattr(server, "compile_pdf", lambda **_: "./output/acme.pdf")
    monkeypatch.setattr(server.event_bus, "create_job_queue", create_job_queue)
    monkeypatch.setattr(server.event_bus, "emit", capture_emit)
    monkeypatch.setattr(server.event_bus, "cleanup_job_queue", AsyncMock())

    await server.process_application(job.id, job.url)

    assert call_order[0] == ("create", None)
    assert call_order[1] == ("emit", EventType.PIPELINE_STARTED)


@pytest.mark.asyncio
async def test_process_application_emits_pipeline_events_on_success(session: Session, monkeypatch):
    """process_application should emit lifecycle and step events through event bus."""
    job = Job(url="http://emit-success.com", company="Unknown", title="Unknown", status="processing", retry_count=0)
    session.add(job)
    session.commit()
    session.refresh(job)

    emitted: list[JobEvent] = []

    async def capture_emit(event: JobEvent):
        emitted.append(event)

    class FakeScrapeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"text": "job description text"}

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return FakeScrapeResponse()

    monkeypatch.setattr(server.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        server,
        "JobParsingAgent",
        lambda: SimpleNamespace(
            parse=lambda _: SimpleNamespace(
                company_name="Acme",
                job_title="Software Engineer",
                key_requirements=["Python", "FastAPI"],
            )
        ),
    )
    monkeypatch.setattr(server, "load_master_resume", lambda _: "master")
    monkeypatch.setattr(server, "ResumeTailorAgent", lambda: SimpleNamespace(tailor=lambda *_: "tailored"))
    monkeypatch.setattr(server, "compile_pdf", lambda **_: "./output/acme.pdf")
    monkeypatch.setattr(server.event_bus, "emit", capture_emit)
    monkeypatch.setattr(server.event_bus, "create_job_queue", AsyncMock(return_value=asyncio.Queue()))
    cleanup_mock = AsyncMock()
    monkeypatch.setattr(server.event_bus, "cleanup_job_queue", cleanup_mock)

    await server.process_application(job.id, job.url)

    event_types = [event.type for event in emitted]
    assert event_types[0] == EventType.PIPELINE_STARTED
    assert event_types[-1] == EventType.PIPELINE_COMPLETED
    assert event_types.count(EventType.STEP_STARTED) == 4
    assert event_types.count(EventType.STEP_COMPLETED) == 4
    cleanup_mock.assert_awaited_once_with(job.id)


@pytest.mark.asyncio
async def test_process_application_emits_pipeline_failed_on_exception(session: Session, monkeypatch):
    """process_application should emit failure event when processing fails."""
    job = Job(url="http://emit-fail.com", company="Unknown", title="Unknown", status="processing", retry_count=0)
    session.add(job)
    session.commit()
    session.refresh(job)

    emitted: list[JobEvent] = []

    async def capture_emit(event: JobEvent):
        emitted.append(event)

    class FakeScrapeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"text": "job description text"}

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return FakeScrapeResponse()

    monkeypatch.setattr(server.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        server,
        "JobParsingAgent",
        lambda: SimpleNamespace(parse=lambda _: (_ for _ in ()).throw(ValueError("parse failed"))),
    )
    monkeypatch.setattr(server.event_bus, "emit", capture_emit)
    monkeypatch.setattr(server.event_bus, "create_job_queue", AsyncMock(return_value=asyncio.Queue()))
    cleanup_mock = AsyncMock()
    monkeypatch.setattr(server.event_bus, "cleanup_job_queue", cleanup_mock)

    await server.process_application(job.id, job.url)

    session.refresh(job)
    assert job.status == "failed"
    assert any(event.type == EventType.PIPELINE_FAILED for event in emitted)
    cleanup_mock.assert_awaited_once_with(job.id)
