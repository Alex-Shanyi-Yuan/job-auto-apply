from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class JobPosting(BaseModel):
    """
    Standardized data model for a job posting.
    """
    title: str
    company: str
    location: str
    job_url: str
    salary_range: Optional[str] = None
    description: Optional[str] = None
    posted_date: Optional[str] = None
    source: str = Field(..., description="The name of the platform (e.g., 'LinkedIn', 'YCombinator')")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
