import asyncio
import argparse
import json
from scrapers.ycombinator import YCombinatorScraper

async def run_scraper(scraper_name: str, url: str):
    if scraper_name.lower() == "ycombinator":
        scraper = YCombinatorScraper()
    else:
        print(f"Unknown scraper: {scraper_name}")
        return

    print(f"Running {scraper_name} scraper...")
    jobs = await scraper.scrape(url)
    
    print(f"Found {len(jobs)} jobs.")
    
    # Print first 3 jobs as JSON
    for job in jobs[:3]:
        print(json.dumps(job.model_dump(), indent=2, default=str))

def main():
    parser = argparse.ArgumentParser(description="Job Scraper CLI")
    parser.add_argument("--scraper", type=str, default="ycombinator", help="Name of the scraper to run")
    parser.add_argument("--url", type=str, default="https://news.ycombinator.com/jobs", help="URL to scrape")
    
    args = parser.parse_args()
    
    asyncio.run(run_scraper(args.scraper, args.url))

if __name__ == "__main__":
    main()
