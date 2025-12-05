"""
Module 1: Job Description Scraper
Fetches job descriptions from URLs or files.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import Optional


def fetch_from_url(url: str, timeout: int = 10) -> str:
    """
    Fetch job description from a URL.
    
    Args:
        url: The URL to fetch from
        timeout: Request timeout in seconds
        
    Returns:
        Cleaned text content from the webpage
        
    Raises:
        requests.RequestException: If the request fails
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()
        
        # Get text content
        text = soup.get_text(separator='\n')
        
        # Clean up whitespace
        text = clean_text(text)
        
        return text
        
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch URL: {str(e)}")


def read_from_file(file_path: str) -> str:
    """
    Read job description from a text file.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        Cleaned text content from the file
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If there's an error reading the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return clean_text(text)
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Job description file not found: {file_path}")
    except Exception as e:
        raise IOError(f"Error reading file: {str(e)}")


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text with normalized whitespace
    """
    # Replace multiple newlines with double newline
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove leading/trailing whitespace from entire text
    text = text.strip()
    
    return text


def fetch_job_description(
    url: Optional[str] = None,
    file_path: Optional[str] = None,
    text: Optional[str] = None
) -> str:
    """
    Fetch job description from URL, file, or direct text.
    
    Args:
        url: URL to fetch from
        file_path: Path to text file
        text: Direct text input
        
    Returns:
        Job description text
        
    Raises:
        ValueError: If no input source is provided or multiple sources given
    """
    sources = [url, file_path, text]
    provided = [s for s in sources if s is not None]
    
    if len(provided) == 0:
        raise ValueError("Must provide either url, file_path, or text")
    
    if len(provided) > 1:
        raise ValueError("Provide only one input source (url, file_path, or text)")
    
    if url:
        return fetch_from_url(url)
    elif file_path:
        return read_from_file(file_path)
    else:
        return clean_text(text)


if __name__ == "__main__":
    # Test the scraper
    test_text = """
    Software Engineer
    
    We are looking for a    talented engineer...
    
    
    Requirements:
    - Python
    - Docker
    """
    
    result = fetch_job_description(text=test_text)
    print("Cleaned text:")
    print(result)
