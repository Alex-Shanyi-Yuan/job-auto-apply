import logging
from pathlib import Path

from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright

from plugins.plugin_registry import plugin_registry

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


@app.on_event("startup")
async def load_plugins() -> None:
    plugin_registry.load_from_directory(Path(__file__).parent / "plugins")
    logger.info("Loaded scraper plugins")


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_job(request: ScrapeRequest):
    logger.info(f"Scraping URL: {request.url} (format: {request.format})")
    try:
        plugin = plugin_registry.get_plugin_for_url(request.url)
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
                result_content = plugin.extract_html(soup, request.url)
            else:
                # Default: Return clean text
                result_content = plugin.extract_text(soup)
            
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
