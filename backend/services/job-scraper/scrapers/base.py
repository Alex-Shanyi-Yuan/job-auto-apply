from abc import ABC, abstractmethod
from typing import List
from models import JobPosting

class BaseScraper(ABC):
    """
    Abstract base class for all job scrapers.
    """
    
    @abstractmethod
    async def scrape(self, url: str) -> List[JobPosting]:
        """
        Scrape jobs from the given URL.
        
        Args:
            url: The URL to scrape (e.g., a search result page or company page)
            
        Returns:
            A list of JobPosting objects
        """
        pass
