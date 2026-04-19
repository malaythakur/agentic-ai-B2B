"""
NewsAPI Enrichment Service

Discovers companies mentioned in news articles using NewsAPI (FREE tier)
"""

import logging
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class NewsAPIEnrichmentService:
    """Service for discovering companies from news articles"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NewsAPI enrichment service
        
        Args:
            api_key: NewsAPI key (defaults to NEWSAPI_KEY env var)
        """
        self.api_key = api_key or os.getenv("NEWSAPI_KEY")
        self.base_url = "https://newsapi.org/v2"
        
        if not self.api_key:
            logger.warning("NewsAPI key not provided, service will be limited")
    
    def find_companies_in_news(
        self,
        query: str,
        limit: int = 20,
        days_back: int = 7
    ) -> List[Dict]:
        """
        Find companies mentioned in news articles
        
        Args:
            query: Search query (industry, topic, etc.)
            limit: Maximum results
            days_back: How many days back to search
            
        Returns:
            List of company dicts from news
        """
        if not self.api_key:
            logger.warning("NewsAPI key not available, returning empty results")
            return []
        
        logger.info(f"Searching NewsAPI for: {query}")
        
        try:
            # Search for articles
            from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            
            url = f"{self.base_url}/everything"
            params = {
                "q": query,
                "from": from_date,
                "sortBy": "relevancy",
                "pageSize": limit,
                "apiKey": self.api_key,
                "language": "en"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "ok":
                logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
            
            articles = data.get("articles", [])
            companies = []
            
            for article in articles:
                try:
                    # Extract company info from article
                    company = self._extract_company_from_article(article, query)
                    if company:
                        companies.append(company)
                except Exception as e:
                    logger.error(f"Error extracting company from article: {e}")
                    continue
            
            logger.info(f"Found {len(companies)} companies from NewsAPI")
            return companies
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NewsAPI request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"NewsAPI enrichment failed: {e}")
            return []
    
    def _extract_company_from_article(self, article: Dict, query: str) -> Optional[Dict]:
        """
        Extract company information from news article
        
        Args:
            article: Article data from NewsAPI
            query: Original search query
            
        Returns:
            Company dict or None
        """
        title = article.get("title", "")
        description = article.get("description", "")
        source = article.get("source", {}).get("name", "")
        url = article.get("url", "")
        published_at = article.get("publishedAt", "")
        
        # Skip if no meaningful content
        if not title or title == "[Removed]":
            return None
        
        # Extract potential company name from title/description
        # This is a simple heuristic - in production, use NER (Named Entity Recognition)
        company_name = self._extract_company_name(title, description, source)
        
        if not company_name:
            return None
        
        # Build company dict
        company = {
            "company_name": company_name,
            "description": description or title,
            "website": self._extract_website(url),
            "source_name": source,
            "article_url": url,
            "published_at": published_at,
            "news_signals": {
                "recent_news": True,
                "news_source": source,
                "query_match": query
            }
        }
        
        return company
    
    def _extract_company_name(self, title: str, description: str, source: str) -> Optional[str]:
        """
        Extract company name from article text
        
        Args:
            title: Article title
            description: Article description
            source: News source name
            
        Returns:
            Company name or None
        """
        # Simple heuristic: use the source name if it looks like a company
        # In production, use proper NER (spaCy, etc.)
        
        # Skip generic news sources
        generic_sources = ["Reuters", "AP News", "BBC", "CNN", "Fox News", "CNBC"]
        if source in generic_sources:
            # Try to extract from title
            words = title.split()
            if len(words) >= 2:
                # First two words might be company name
                potential_name = " ".join(words[:2])
                # Filter out common words
                skip_words = ["The", "A", "An", "This", "That", "Here", "Why", "How"]
                if potential_name.split()[0] not in skip_words:
                    return potential_name
            return None
        
        # Use source as company name
        return source
    
    def _extract_website(self, url: str) -> str:
        """
        Extract website domain from URL
        
        Args:
            url: Article URL
            
        Returns:
            Website URL or empty string
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return ""
    
    def get_company_news(
        self,
        company_name: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get recent news about a specific company
        
        Args:
            company_name: Name of company
            limit: Maximum articles
            
        Returns:
            List of article dicts
        """
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_url}/everything"
            params = {
                "q": f'"{company_name}"',
                "sortBy": "publishedAt",
                "pageSize": limit,
                "apiKey": self.api_key,
                "language": "en"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "ok":
                return []
            
            return data.get("articles", [])
            
        except Exception as e:
            logger.error(f"Failed to get company news: {e}")
            return []


# Example usage
if __name__ == "__main__":
    service = NewsAPIEnrichmentService()
    
    # Find companies in SaaS news
    companies = service.find_companies_in_news("SaaS", limit=5)
    print(f"Found {len(companies)} companies")
    for company in companies:
        print(f"  - {company.get('company_name')}: {company.get('description', '')[:100]}...")
