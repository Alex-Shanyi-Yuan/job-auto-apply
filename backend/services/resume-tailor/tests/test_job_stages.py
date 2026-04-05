"""Tests for job stage tracking endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select
from sqlmodel.pool import StaticPool
from database import SQLModel, Job, JobStage, utcnow, get_session
import server
from server import app

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
