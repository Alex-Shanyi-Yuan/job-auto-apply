from pydantic import BaseModel, Field
from typing import List, Optional


class JobPosting(BaseModel):
    """Structured representation of a job posting."""
    company_name: str = Field(..., description="Name of the company hiring")
    job_title: str = Field(..., description="Title of the position")
    summary: str = Field(..., description="Brief summary of the role and responsibilities")
    key_requirements: List[str] = Field(..., description="List of key words for to ace the ATS system")
    raw_text: Optional[str] = Field(None, description="The original raw text of the job description")


class DiscoveredJob(BaseModel):
    """A job listing discovered from a job board search page."""
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    url: str = Field(..., description="Direct URL to the job posting")


class DiscoveryResult(BaseModel):
    """Result of job discovery from a search page."""
    jobs: List[DiscoveredJob] = Field(default_factory=list, description="List of discovered job listings")


class JobScore(BaseModel):
    """Score result for a job posting."""
    score: int = Field(..., ge=0, le=100, description="Match score from 0 to 100")
    reasoning: str = Field(..., description="Brief explanation of the score")
