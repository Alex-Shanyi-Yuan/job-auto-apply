from pathlib import Path
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session
from datetime import datetime, timezone
import os
from sqlalchemy import event
from sqlalchemy.engine import make_url


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Settings(SQLModel, table=True):
    """Key-value store for application settings."""
    key: str = Field(primary_key=True)
    value: str
    updated_at: datetime = Field(default_factory=utcnow)


class JobSource(SQLModel, table=True):
    """Represents a job board search URL to scan for job listings."""
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str  # The search results page URL
    name: str  # Friendly name for the source (e.g., "LinkedIn - Python Jobs")
    filter_prompt: Optional[str] = None  # Optional AI prompt specific to this source
    last_scraped_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Job(SQLModel, table=True):
    """Represents a job application or suggestion."""
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    company: str
    title: str
    status: str = "suggested"  # suggested, processing, active, rejected, dismissed, failed
    requirements: Optional[str] = None  # JSON string of key requirements
    pdf_path: Optional[str] = None
    score: Optional[int] = None  # Match score 0-100
    source_id: Optional[int] = Field(default=None, foreign_key="jobsource.id")
    error_message: Optional[str] = None  # Error message if processing failed
    retry_count: int = 0  # Track automatic retry attempts
    rejection_stage: Optional[str] = None  # 'applied' | 'oa' | 'interview' | 'offer'
    rejection_reason: Optional[str] = None  # Free-form rejection notes
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class JobStage(SQLModel, table=True):
    """Tracks individual stages in the interview pipeline for a job."""
    __tablename__ = "jobstage"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", ondelete="CASCADE")
    stage_name: str  # 'applied' | 'oa' | 'interview' | 'offer'
    completed_at: Optional[datetime] = None  # When stage was completed
    notes: Optional[str] = None  # User notes for this stage
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


DEFAULT_POSTGRES_URL = "postgresql://user:password@postgres:5432/autocareer"
DEFAULT_SQLITE_URL = "sqlite:///./data/autocareer.db"


def _normalize_backend(value: Optional[str]) -> str:
    backend = (value or "postgres").strip().lower()
    if backend not in {"postgres", "sqlite", "hybrid"}:
        return "postgres"
    return backend


DATABASE_BACKEND = _normalize_backend(os.getenv("DATABASE_BACKEND"))
POSTGRES_DATABASE_URL = os.getenv("POSTGRES_DATABASE_URL") or os.getenv("DATABASE_URL") or DEFAULT_POSTGRES_URL
SQLITE_DATABASE_URL = os.getenv("SQLITE_DATABASE_URL") or DEFAULT_SQLITE_URL


def get_active_backend() -> str:
    return DATABASE_BACKEND


def get_active_database_url() -> str:
    # Hybrid mode uses SQLite as the live runtime store and syncs with Postgres when available.
    if DATABASE_BACKEND in {"sqlite", "hybrid"}:
        return SQLITE_DATABASE_URL
    return POSTGRES_DATABASE_URL


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def create_engine_for_url(url: str):
    if _is_sqlite_url(url):
        parsed_url = make_url(url)
        database_path = parsed_url.database
        if database_path and database_path != ":memory:":
            Path(database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

        engine_obj = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine_obj, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine_obj

    return create_engine(url)


def _touch_updated_at(mapper, connection, target):
    target.updated_at = utcnow()


event.listen(JobSource, "before_update", _touch_updated_at)
event.listen(Job, "before_update", _touch_updated_at)
event.listen(Settings, "before_update", _touch_updated_at)


engine = create_engine_for_url(get_active_database_url())


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def create_db_and_tables_for_engine(engine_obj):
    SQLModel.metadata.create_all(engine_obj)


def get_sqlite_engine():
    return create_engine_for_url(SQLITE_DATABASE_URL)


def get_postgres_engine():
    return create_engine_for_url(POSTGRES_DATABASE_URL)


def get_session():
    with Session(engine) as session:
        yield session
