from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session
from datetime import datetime
import os

class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    company: str
    title: str
    status: str = "applied"  # applied, interviewing, rejected, offer
    requirements: Optional[str] = None  # JSON string of key requirements
    pdf_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/autocareer")

engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
