import asyncio
from typing import List
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from ..models import JobPosting
from .base import BaseScraper

class YCombinatorScraper(BaseScraper):
    """
    Scraper for YCombinator (Hacker News) Jobs.
    Demonstrates using Playwright to load a page and extract data.
    """
    
    async def scrape(self, url: str = "https://news.ycombinator.com/jobs") -> List[JobPosting]:
        print(f"Starting scrape for: {url}")
        jobs = []
        
        async with async_playwright() as p:
            # Launch browser (headless=True by default, set False to see it in action)
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # Navigate to the page
                await page.goto(url, wait_until="domcontentloaded")
                
                # Wait for the job table to appear
                await page.wait_for_selector(".athing", timeout=10000)
                
                # Get the page content
                content = await page.content()
                
                # Parse with BeautifulSoup (often easier than Playwright locators for complex parsing)
                soup = BeautifulSoup(content, "html.parser")
                
                # Find all job rows
                job_rows = soup.select(".athing")
                
                for row in job_rows:
                    try:
                        title_element = row.select_one(".titleline > a")
                        if not title_element:
                            continue
                            
                        title_text = title_element.get_text().strip()
                        link = title_element.get("href")
                        
                        # Handle relative URLs
                        if link and not link.startswith("http"):
                            link = f"https://news.ycombinator.com/{link}"
                            
                        # YC jobs often have "Company is hiring..." format
                        # We'll do a naive split for this example
                        company = "YCombinator Startup"
                        title = title_text
                        
                        # Extract timestamp if available (it's in the next row usually, skipping for simplicity)
                        
                        job = JobPosting(
                            title=title,
                            company=company,
                            location="Remote/San Francisco", # Defaulting for this example
                            job_url=link or url,
                            source="YCombinator",
                            description=title_text # Using title as description for list view
                        )
                        jobs.append(job)
                        
                    except Exception as e:
                        print(f"Error parsing row: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error during scraping: {e}")
            finally:
                await browser.close()
                
        return jobs
