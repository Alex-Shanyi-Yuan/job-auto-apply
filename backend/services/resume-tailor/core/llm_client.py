"""
Module 2: Gemini LLM Client
Generic client for interacting with Google Gemini Pro.
"""

import os
import time
import re
from typing import Optional, Type, TypeVar, Any
from google import genai
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class GeminiClient:
    """Generic client for interacting with Google Gemini API."""
    
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
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = 'gemini-3-flash-preview' 
    
    def generate_content(
        self,
        prompt: str,
        max_retries: int = 3,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text content from a prompt.
        
        Args:
            prompt: The prompt to send to the model
            max_retries: Maximum number of retry attempts
            temperature: Creativity of the model
            
        Returns:
            Generated text content
        """
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        top_p=0.95,
                        top_k=40,
                        max_output_tokens=8192,
                    )
                )
                return self._clean_response(response.text)
                
            except Exception as e:
                self._handle_retry(attempt, max_retries, e)
                
        raise Exception(f"Failed to generate content after {max_retries} attempts")

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        max_retries: int = 3,
        temperature: float = 0.1
    ) -> T:
        """
        Generate structured data matching a Pydantic model.
        
        Args:
            prompt: The prompt to send to the model
            response_schema: The Pydantic model class to enforce structure
            max_retries: Maximum number of retry attempts
            temperature: Creativity (lower is better for structured data)
            
        Returns:
            Instance of the response_schema model
        """
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type='application/json',
                        response_schema=response_schema,
                    )
                )
                
                # The SDK might return a parsed object or we might need to parse it
                # Depending on the SDK version, response.parsed might be available
                # If not, we parse response.text
                if hasattr(response, 'parsed') and response.parsed:
                     # If the SDK returns a dict or object that matches the schema
                    if isinstance(response.parsed, response_schema):
                        return response.parsed
                    # If it returns a dict, parse it
                    return response_schema.model_validate(response.parsed)
                
                # Fallback to parsing text
                import json
                data = json.loads(response.text)
                return response_schema.model_validate(data)
                
            except Exception as e:
                self._handle_retry(attempt, max_retries, e)

        raise Exception(f"Failed to generate structured content after {max_retries} attempts")

    def _handle_retry(self, attempt: int, max_retries: int, error: Exception):
        """Handle retry logic with exponential backoff."""
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            print(f"Retry {attempt + 1}/{max_retries} after error: {str(error)}")
            time.sleep(wait_time)
        else:
            raise error

    def _clean_response(self, response: str) -> str:
        """Clean up the API response, removing markdown code blocks if present."""
        pattern = r'```(?:latex)?\s*(.*?)\s*```'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()
