from typing import Optional
import time
from .llm_client import GeminiClient
from .models import JobPosting

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
