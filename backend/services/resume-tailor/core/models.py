from pydantic import BaseModel, Field
from typing import List, Optional

class JobPosting(BaseModel):
    """Structured representation of a job posting."""
    company_name: str = Field(..., description="Name of the company hiring")
    job_title: str = Field(..., description="Title of the position")
    summary: str = Field(..., description="Brief summary of the role and responsibilities")
    key_requirements: List[str] = Field(..., description="List of key words for to ace the ATS system")
    raw_text: Optional[str] = Field(None, description="The original raw text of the job description")
