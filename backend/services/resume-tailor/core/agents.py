from typing import Optional, List
import logging
from .llm_providers import LLMProvider, create_default_provider
from .models import JobPosting, DiscoveryResult, DiscoveredJob, JobScore
from .resume_model import ResumeContent

logger = logging.getLogger(__name__)


class JobDiscoveryAgent:
    """Agent responsible for discovering jobs from search result pages."""
    
    def __init__(self, client: Optional[LLMProvider] = None):
        self.client = client or create_default_provider()
    
    def discover(self, html_content: str, filter_prompt: str) -> List[DiscoveredJob]:
        """
        Parse HTML from a job board search page and extract matching job listings.
        
        Args:
            html_content: Cleaned HTML from a job board search results page
            filter_prompt: User's criteria for filtering jobs (e.g., "Remote Python developer roles")
            
        Returns:
            List of discovered job listings that match the filter criteria
        """
        # Truncate HTML if too long (keep first ~40k chars to leave room for prompt)
        max_html_length = 40000
        if len(html_content) > max_html_length:
            html_content = html_content[:max_html_length] + "\n... (content truncated)"
        
        prompt = f"""You are a job discovery agent. Analyze the following HTML content from a job board search results page.

Your task:
1. Extract ALL job listings visible on the page
2. For each job, extract: title, company name, and the direct URL to the job posting
3. Filter the results to only include jobs matching this criteria: "{filter_prompt}"
4. If a URL is relative (starts with /), keep it as-is (we will resolve it later)
5. Only include jobs where you can find a valid URL link

Important:
- Look for patterns like job cards, list items, or repeated structures that contain job info
- The URL should lead to the individual job posting, not the search results
- If company name is not visible, use "Unknown Company"
- Be thorough - extract ALL matching jobs you can find

HTML Content:
{html_content}

Return the matching jobs as a structured JSON object."""

        try:
            result = self.client.generate_structured(
                prompt=prompt,
                schema=DiscoveryResult,
                temperature=0.1
            )
            if not result.jobs and len(html_content) > 1000:
                # Non-trivial HTML but nothing extracted — likely a parse failure
                # rather than a genuinely empty page; surface it for debugging.
                logger.warning(
                    "Job discovery returned 0 jobs from %d chars of HTML", len(html_content)
                )
            return result.jobs
        except Exception as e:
            logger.error("Error in job discovery: %s", e, exc_info=True)
            return []


class JobScoringAgent:
    """Agent responsible for scoring job matches based on resume fit."""
    
    def __init__(self, client: Optional[LLMProvider] = None):
        self.client = client or create_default_provider()
    
    def score(self, job_description: str, master_resume: str) -> JobScore:
        """
        Score how well a job matches the candidate's background.
        
        The score represents the likelihood of success after tailoring the resume,
        not just a simple keyword match.
        
        Args:
            job_description: Full text of the job posting
            master_resume: The candidate's master resume (LaTeX or plain text)
            
        Returns:
            JobScore with score (0-100) and reasoning
        """
        prompt = f"""You are an expert career advisor and resume analyst.

Analyze how well this candidate would fit the job posting, considering:
1. Skills match (both explicit and transferable skills)
2. Experience level alignment
3. Industry/domain relevance
4. Potential for resume tailoring to highlight relevant experience

The score should reflect the candidate's chances of getting an interview AFTER we tailor their resume to this specific job.

Scoring guide:
- 90-100: Excellent match, nearly all requirements met, strong background
- 70-89: Good match, most key requirements met, some tailoring needed
- 50-69: Moderate match, has relevant transferable skills
- 30-49: Weak match, significant gaps but some relevant experience
- 0-29: Poor match, missing critical requirements

JOB DESCRIPTION:
{job_description[:8000]}

CANDIDATE'S MASTER RESUME:
{master_resume[:6000]}

Provide a score and brief reasoning (2-3 sentences)."""

        try:
            result = self.client.generate_structured(
                prompt=prompt,
                schema=JobScore,
                temperature=0.2
            )
            return result
        except Exception as e:
            logger.error("Error scoring job: %s", e, exc_info=True)
            return JobScore(score=50, reasoning="Unable to analyze - defaulting to moderate score")


class JobParsingAgent:
    """Agent responsible for parsing raw job descriptions into structured data."""
    
    def __init__(self, client: Optional[LLMProvider] = None):
        self.client = client or create_default_provider()
        
    def parse(self, raw_text: str) -> JobPosting:
        """
        Parse raw job description text into a structured JobPosting object.
        """
        prompt = f"""
        You are an expert HR assistant. Analyze the following job description text and extract the key information.
        
        Raw Job Description:
        {raw_text}
        
        Extract:
        1. Company Name (if not explicitly stated, infer from context or use "Unknown Company")
        2. Job Title
        3. A concise summary of the role (2-3 sentences)
        4. A list of key requirements (skills, experience, qualifications)
        
        Return the result as a structured JSON object matching the schema.
        """

        try:
            job_posting = self.client.generate_structured(
                prompt=prompt,
                schema=JobPosting,
            )
        except Exception as e:
            # Don't crash the apply pipeline opaquely or fabricate a posting —
            # raise a clear error so the job is marked failed with a real reason.
            logger.error("Error parsing job description: %s", e, exc_info=True)
            raise ValueError(f"Failed to parse job description: {e}") from e

        # Attach the raw text to the object for reference
        job_posting.raw_text = raw_text
        return job_posting


class ResumeTailorAgent:
    """Agent that tailors a structured resume to a specific job.

    The LLM receives the candidate's full content pool (all experiences/projects)
    and the parsed job, and returns a tailored ``ResumeContent``: the most relevant
    subset, ordered by relevance and reworded to mirror the job's keywords. It never
    emits LaTeX — ``core/resume_renderer.render_resume`` turns the result into an
    always-compilable, ATS-clean document. A deterministic guardrail then enforces a
    one-page budget and preserves the header exactly.
    """

    # One-page budget. The LLM is asked to select; these are hard caps applied
    # afterwards so a bad selection can't overflow the page.
    MAX_EXPERIENCE = 5
    MAX_PROJECTS = 5
    MAX_BULLETS_PER_EXPERIENCE = 5
    MAX_BULLETS_PER_PROJECT = 3
    MAX_SKILL_GROUPS = 5

    def __init__(self, client: Optional[LLMProvider] = None):
        self.client = client or create_default_provider()

    def tailor(self, master: ResumeContent, job_posting: JobPosting) -> ResumeContent:
        """Return a tailored, one-page ``ResumeContent`` for this job."""
        requirements = "\n".join(f"- {req}" for req in job_posting.key_requirements) or "- (none provided)"
        prompt = f"""You are an expert resume writer optimizing for ATS keyword match and recruiter callbacks.

You are given a candidate's FULL resume content as JSON (the pool of every experience and project) and a target job. Produce a tailored, single-page resume as JSON that maximizes the chance a recruiter or ATS shortlists THIS candidate for THIS job.

Rules:
- SELECT the most relevant experiences and projects for this job and DROP the least relevant. Target a single page: roughly up to {self.MAX_EXPERIENCE} experiences and {self.MAX_PROJECTS} projects total, fewer if bullets run long.
- ORDER experiences and projects by relevance to the job (most relevant first).
- REWRITE bullet points to mirror the job's key requirements and terminology wherever it is truthful, keeping them quantified and in the "Accomplished X as measured by Y, by doing Z" style.
- Reorder and trim the skills to surface the most job-relevant ones first.
- Keep the header EXACTLY as given (name, phone, email, links, citizenship).
- Keep the education entries.
- NEVER fabricate experience, employers, skills, or metrics. Only reuse and rephrase what is in the pool.
- Plain text only in every field — no markdown and no LaTeX commands.

TARGET JOB:
Company: {job_posting.company_name}
Title: {job_posting.job_title}
Summary: {job_posting.summary}
Key requirements:
{requirements}

CANDIDATE RESUME POOL (JSON):
{master.model_dump_json(indent=2)}

Return the tailored resume as a JSON object matching the schema."""

        tailored = self.client.generate_structured(prompt=prompt, schema=ResumeContent)
        return self._enforce_budget(tailored, master)

    def _enforce_budget(self, tailored: ResumeContent, master: ResumeContent) -> ResumeContent:
        """Deterministically guarantee a one-page result and a trustworthy header."""
        # Never let the model alter contact details — restore the authored header.
        tailored.header = master.header

        # Guard against an empty selection by falling back to the pool.
        if not tailored.experience and not tailored.projects:
            logger.warning("Tailoring returned no experience/projects; falling back to master content")
            tailored.experience = master.experience
            tailored.projects = master.projects
        if not tailored.education:
            tailored.education = master.education
        if not tailored.skills:
            tailored.skills = master.skills

        tailored.experience = tailored.experience[: self.MAX_EXPERIENCE]
        for exp in tailored.experience:
            exp.bullets = exp.bullets[: self.MAX_BULLETS_PER_EXPERIENCE]
        tailored.projects = tailored.projects[: self.MAX_PROJECTS]
        for proj in tailored.projects:
            proj.bullets = proj.bullets[: self.MAX_BULLETS_PER_PROJECT]
        tailored.skills = tailored.skills[: self.MAX_SKILL_GROUPS]
        return tailored
