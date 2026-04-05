"""Tests for job stage tracking endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select
from sqlmodel.pool import StaticPool
from database import SQLModel, Job, JobStage, utcnow, get_session
from server import app


@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh in-memory database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
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
    job = Job(url="http://test.com", company="TestCo", title="SWE", status="applied")
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


def test_update_job_stages_unchecks_existing_stage(session: Session, client: TestClient):
    """Test unchecking a previously completed stage."""
    # Create job with existing stage
    job = Job(url="http://test.com", company="TestCo", title="SWE", status="active")
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
    job = Job(url="http://test.com", company="TestCo", title="SWE", status="active")
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