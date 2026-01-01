from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


class ScrapeRequest(BaseModel):
    url: str
    format: str = "text"  # "text" for clean text, "html" for cleaned HTML with links


class ScrapeResponse(BaseModel):
    title: str
    text: str
    url: str


def clean_html_for_llm(soup: BeautifulSoup, base_url: str) -> str:
    """
    Clean HTML while preserving structure useful for LLM parsing.
    Keeps: headings, paragraphs, links, lists, divs with job-like content.
    Removes: scripts, styles, SVGs, images, comments, hidden elements.
    """
    # Remove unwanted elements
    for element in soup(["script", "style", "svg", "img", "noscript", "iframe", "video", "audio"]):
        element.decompose()
    
    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
        comment.extract()
    
    # Remove hidden elements
    for element in soup.find_all(attrs={"style": re.compile(r"display:\s*none", re.I)}):
        element.decompose()
    for element in soup.find_all(attrs={"hidden": True}):
        element.decompose()
    
    # Clean up attributes - keep only href on links
    for tag in soup.find_all(True):
        if tag.name == 'a':
            href = tag.get('href', '')
            # Convert relative URLs to absolute
            if href and not href.startswith(('http://', 'https://', 'mailto:', 'javascript:')):
                if href.startswith('/'):
                    # Extract base domain from URL
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
            tag.attrs = {'href': href} if href else {}
        else:
            tag.attrs = {}
    
    # Get the body or the whole soup if no body
    body = soup.find('body') or soup
    
    return str(body)


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_job(request: ScrapeRequest):
    logger.info(f"Scraping URL: {request.url} (format: {request.format})")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Navigate to the URL
            await page.goto(request.url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for dynamic content to load
            await page.wait_for_timeout(3000)
            
            # Scroll down to trigger lazy loading (useful for job boards)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await page.wait_for_timeout(1000)
            
            # Get page content
            content = await page.content()
            title = await page.title()
            
            await browser.close()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            if request.format == "html":
                # Return cleaned HTML with structure preserved
                result_content = clean_html_for_llm(soup, request.url)
            else:
                # Default: Return clean text
                for script in soup(["script", "style", "svg", "img"]):
                    script.decompose()
                    
                text = soup.get_text(separator='\n')
                
                # Clean up text (remove extra whitespace)
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                result_content = '\n'.join(chunk for chunk in chunks if chunk)
            
            return ScrapeResponse(
                title=title,
                text=result_content,
                url=request.url
            )
            
    except Exception as e:
        logger.error(f"Error scraping {request.url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape URL: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
