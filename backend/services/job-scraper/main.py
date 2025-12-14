from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str

class ScrapeResponse(BaseModel):
    title: str
    text: str
    url: str

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_job(request: ScrapeRequest):
    logger.info(f"Scraping URL: {request.url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()
            
            # Navigate to the URL
            await page.goto(request.url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for a bit to let dynamic content load
            await page.wait_for_timeout(2000)
            
            # Get page content
            content = await page.content()
            title = await page.title()
            
            await browser.close()
            
            # Parse with BeautifulSoup to get clean text
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text(separator='\n')
            
            # Clean up text (remove extra whitespace)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return ScrapeResponse(
                title=title,
                text=clean_text,
                url=request.url
            )
            
    except Exception as e:
        logger.error(f"Error scraping {request.url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to scrape URL: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
