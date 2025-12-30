from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session
from datetime import datetime
import os


class Settings(SQLModel, table=True):
    """Key-value store for application settings."""
    key: str = Field(primary_key=True)
    value: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class JobSource(SQLModel, table=True):
    """Represents a job board search URL to scan for job listings."""
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str  # The search results page URL
    name: str  # Friendly name for the source (e.g., "LinkedIn - Python Jobs")
    filter_prompt: Optional[str] = None  # Optional AI prompt specific to this source
    last_scraped_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Job(SQLModel, table=True):
    """Represents a job application or suggestion."""
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    company: str
    title: str
    status: str = "suggested"  # suggested, applied, interviewing, rejected, offer, dismissed, failed
    requirements: Optional[str] = None  # JSON string of key requirements
    pdf_path: Optional[str] = None
    score: Optional[int] = None  # Match score 0-100
    source_id: Optional[int] = Field(default=None, foreign_key="jobsource.id")
    error_message: Optional[str] = None  # Error message if processing failed
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/autocareer")

engine = create_engine(DATABASE_URL)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
