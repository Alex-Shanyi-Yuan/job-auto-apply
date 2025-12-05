"""
Module 2: Gemini LLM Client
Uses Google Gemini Pro to tailor LaTeX resumes to job descriptions.
"""

import os
import google.generativeai as genai
from typing import Optional
import time


class GeminiTailorClient:
    """Client for interacting with Google Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Google API key. If not provided, reads from GOOGLE_API_KEY env var.
            
        Raises:
            ValueError: If API key is not provided or found in environment
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found. "
                "Set it in .env file or pass as parameter."
            )
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
    
    def create_prompt(self, master_latex: str, job_description: str) -> str:
        """
        Create the tailoring prompt for Gemini.
        
        Args:
            master_latex: Complete LaTeX resume content
            job_description: Job description text
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert resume writer and LaTeX specialist.

I will provide you with:
1. A complete LaTeX resume file
2. A job description

Your task:
- Analyze the job description and identify key requirements, skills, and qualifications
- Rewrite the resume content to highlight relevant experience and skills that match the job
- Tailor bullet points to emphasize achievements and experience relevant to this specific role
- Adjust the professional summary or objective to align with the position
- Prioritize skills mentioned in the job description
- Keep the resume concise and impactful (1-2 pages)
- Maintain ALL LaTeX formatting, commands, and document structure EXACTLY
- Do NOT add markdown formatting - use LaTeX commands only (e.g., \\textbf{{}} for bold)
- Output ONLY valid LaTeX code with no additional explanations or comments

Master Resume LaTeX:
```latex
{master_latex}
```

Job Description:
```
{job_description}
```

Return the complete tailored LaTeX resume below:"""
        
        return prompt
    
    def tailor_resume(
        self,
        master_latex: str,
        job_description: str,
        max_retries: int = 3
    ) -> str:
        """
        Send resume and job description to Gemini for tailoring.
        
        Args:
            master_latex: Complete LaTeX resume content
            job_description: Job description text
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tailored LaTeX resume as string
            
        Raises:
            Exception: If API call fails or response is invalid
        """
        prompt = self.create_prompt(master_latex, job_description)
        
        for attempt in range(max_retries):
            try:
                # Generate content with Gemini
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=0.95,
                        top_k=40,
                        max_output_tokens=8192,
                    )
                )
                
                # Extract the generated text
                tailored_latex = response.text
                
                # Basic validation
                if not self._validate_latex(tailored_latex):
                    raise ValueError("Generated content is not valid LaTeX")
                
                # Clean up the response (remove markdown code blocks if present)
                tailored_latex = self._clean_response(tailored_latex)
                
                return tailored_latex
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Retry {attempt + 1}/{max_retries} after error: {str(e)}")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to tailor resume after {max_retries} attempts: {str(e)}")
    
    def _validate_latex(self, latex_content: str) -> bool:
        """
        Validate that the content appears to be LaTeX.
        
        Args:
            latex_content: Content to validate
            
        Returns:
            True if content appears to be valid LaTeX
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
    
    def _clean_response(self, response: str) -> str:
        """
        Clean up the API response, removing markdown code blocks if present.
        
        Args:
            response: Raw response from API
            
        Returns:
            Cleaned LaTeX content
        """
        # Remove markdown code blocks
        import re
        
        # Pattern to match ```latex ... ``` or ``` ... ```
        pattern = r'```(?:latex)?\s*(.*?)\s*```'
        match = re.search(pattern, response, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        return response.strip()


# Convenience function for direct use
def tailor_resume(master_latex: str, job_description: str, api_key: Optional[str] = None) -> str:
    """
    Tailor a LaTeX resume to a job description using Gemini.
    
    Args:
        master_latex: Complete LaTeX resume content
        job_description: Job description text
        api_key: Optional Google API key
        
    Returns:
        Tailored LaTeX resume as string
    """
    client = GeminiTailorClient(api_key=api_key)
    return client.tailor_resume(master_latex, job_description)


if __name__ == "__main__":
    # Test the client
    test_latex = r"""
    \documentclass{article}
    \begin{document}
    \section{Summary}
    Experienced software engineer.
    \end{document}
    """
    
    test_jd = "Looking for a Python developer with Django experience."
    
    try:
        result = tailor_resume(test_latex, test_jd)
        print("Tailored resume:")
        print(result[:200])
    except ValueError as e:
        print(f"Error: {e}")
        print("Make sure GOOGLE_API_KEY is set in your .env file")
