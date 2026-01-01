from typing import Optional, List
import time
from .llm_client import GeminiClient
from .models import JobPosting, DiscoveryResult, DiscoveredJob, JobScore


class JobDiscoveryAgent:
    """Agent responsible for discovering jobs from search result pages."""
    
    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or GeminiClient()
    
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
                response_schema=DiscoveryResult,
                temperature=0.1
            )
            return result.jobs
        except Exception as e:
            print(f"Error in job discovery: {e}")
            return []


class JobScoringAgent:
    """Agent responsible for scoring job matches based on resume fit."""
    
    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or GeminiClient()
    
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
                response_schema=JobScore,
                temperature=0.2
            )
            return result
        except Exception as e:
            print(f"Error scoring job: {e}")
            return JobScore(score=50, reasoning="Unable to analyze - defaulting to moderate score")


class JobParsingAgent:
    """Agent responsible for parsing raw job descriptions into structured data."""
    
    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or GeminiClient()
        
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
        
        job_posting = self.client.generate_structured(
            prompt=prompt,
            response_schema=JobPosting
        )
        
        # Attach the raw text to the object for reference
        job_posting.raw_text = raw_text
        return job_posting


class ResumeTailorAgent:
    """Agent responsible for tailoring resumes to specific job postings."""
    
    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or GeminiClient()
        
    def tailor(self, master_resume: str, job_posting: JobPosting, max_retries: int = 3) -> str:
        """
        Tailor the master resume to the provided job posting.
        """
        # TODO: maybe add a instrecution targeting keyward frequency?
        prompt = f"""You are an expert resume writer and LaTeX specialist with over 20 years of experience.

I will provide you with:
1. A complete LaTeX resume file
2. A structured job analysis

Your task:
- Analyze the job requirements and skills
- Rewrite the resume content to highlight relevant experience and skills that match the job
- Tailor bullet points to emphasize achievements and experience relevant to this specific role
- Rewrite bullet points using the Google formula: "Accomplished [X] as measured by [Y], by doing [Z]"
- Adjust the professional summary or objective to align with the position
- Prioritize skills mentioned in the job description
- Keep the resume concise and impactful (strictly 1 page)
- Maintain ALL LaTeX formatting, commands, and document structure EXACTLY
- Do NOT add markdown formatting - use LaTeX commands only (e.g., \\textbf{{}} for bold)
- Output ONLY valid LaTeX code with no additional explanations or comments

Master Resume LaTeX:
```latex
{master_resume}
```

Job Analysis:
Company: {job_posting.company_name}
Title: {job_posting.job_title}
Summary: {job_posting.summary}
Key Requirements:
{chr(10).join(f"- {req}" for req in job_posting.key_requirements)}

Return the complete tailored LaTeX resume below:"""

        for attempt in range(max_retries):
            try:
                # We use max_retries=1 for the client call to avoid compounding retries
                # If the API fails, we catch it here and retry the whole process
                response = self.client.generate_content(prompt=prompt, max_retries=1)
                
                if not self._validate_latex(response):
                    raise ValueError("Generated content is not valid LaTeX")
                    
                return response
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Retry {attempt + 1}/{max_retries} after error: {str(e)}")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to tailor resume after {max_retries} attempts: {str(e)}")

    def _validate_latex(self, latex_content: str) -> bool:
        """
        Validate that the content appears to be LaTeX.
        """
        required_patterns = [
            r'\\documentclass',
            r'\\begin{document}',
            r'\\end{document}'
        ]
        
        import re
        for pattern in required_patterns:
            if not re.search(pattern, latex_content):
                return False
        
        return True
