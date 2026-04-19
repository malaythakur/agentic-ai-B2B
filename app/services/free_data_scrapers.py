"""
Free Data Source Scrapers
Collects leads from free APIs and sources
"""
import httpx
import json
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import feedparser
from bs4 import BeautifulSoup


@dataclass
class RawLead:
    """Raw lead from external source"""
    company: str
    source: str
    signal: str
    website: Optional[str]
    discovered_at: datetime
    confidence: float
    metadata: Dict


class GitHubScraper:
    """Scrape GitHub for tech company signals"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.base_url = "https://api.github.com"
    
    async def find_hiring_companies(
        self,
        tech_stack: List[str],
        min_stars: int = 50,
        max_results: int = 50
    ) -> List[RawLead]:
        """
        Find companies hiring based on GitHub activity
        
        Free tier: 60 requests/hour (sufficient for discovery)
        """
        leads = []
        
        for tech in tech_stack[:5]:  # Limit to 5 technologies
            try:
                # Search for repos with recent activity
                url = f"{self.base_url}/search/repositories"
                params = {
                    "q": f"{tech} stars:>{min_stars} pushed:>{(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}",
                    "sort": "updated",
                    "order": "desc",
                    "per_page": 10
                }
                
                response = await self.client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    
                    for item in data.get("items", [])[:10]:
                        # Get repo details
                        owner = item.get("owner", {})
                        company_name = owner.get("login", "")
                        
                        if not company_name:
                            continue
                        
                        # Get company info from GitHub profile
                        company_info = await self._get_company_info(owner.get("url"))
                        
                        lead = RawLead(
                            company=company_name,
                            source="github",
                            signal=f"Active {tech} development with {item.get('stargazers_count', 0)} stars, recent commits",
                            website=company_info.get("blog") or owner.get("html_url"),
                            discovered_at=datetime.utcnow(),
                            confidence=0.7,
                            metadata={
                                "tech": tech,
                                "stars": item.get("stargazers_count"),
                                "repo": item.get("html_url"),
                                "company_type": company_info.get("type", "organization")
                            }
                        )
                        leads.append(lead)
                        
                        if len(leads) >= max_results:
                            return leads
                            
            except Exception as e:
                print(f"GitHub scraping error for {tech}: {e}")
                continue
        
        return leads
    
    async def _get_company_info(self, org_url: str) -> Dict:
        """Get company info from GitHub organization"""
        try:
            response = await self.client.get(org_url)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return {}
    
    async def close(self):
        await self.client.aclose()


class NewsAPIScraper:
    """Scrape news for funding announcements and company signals"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        self.base_url = "https://newsapi.org/v2"
    
    async def find_funding_announcements(
        self,
        days_back: int = 7,
        max_results: int = 50
    ) -> List[RawLead]:
        """
        Find funding announcements from news
        
        Free tier: 100 requests/day
        """
        leads = []
        
        queries = [
            "raised funding",
            "Series A funding",
            "Series B funding", 
            "seed funding",
            "venture capital funding"
        ]
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        for query in queries:
            try:
                url = f"{self.base_url}/everything"
                params = {
                    "q": query,
                    "from": from_date,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 20,
                    "apiKey": self.api_key
                }
                
                response = await self.client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    
                    for article in data.get("articles", []):
                        # Extract company name from title
                        title = article.get("title", "")
                        company_name = self._extract_company_from_title(title)
                        
                        if not company_name:
                            continue
                        
                        # Extract funding details
                        funding_details = self._parse_funding_from_text(title + " " + article.get("description", ""))
                        
                        lead = RawLead(
                            company=company_name,
                            source="newsapi",
                            signal=f"Funding news: {title}",
                            website=None,  # Will be enriched later
                            discovered_at=datetime.utcnow(),
                            confidence=0.8,
                            metadata={
                                "funding_details": funding_details,
                                "news_url": article.get("url"),
                                "published_at": article.get("publishedAt"),
                                "source": article.get("source", {}).get("name")
                            }
                        )
                        leads.append(lead)
                        
                        if len(leads) >= max_results:
                            return leads
                            
            except Exception as e:
                print(f"NewsAPI error: {e}")
                continue
        
        return leads
    
    async def find_hiring_announcements(
        self,
        days_back: int = 7,
        max_results: int = 30
    ) -> List[RawLead]:
        """Find hiring announcements from news"""
        leads = []
        
        queries = [
            "hiring spree",
            "expands team",
            "recruiting talent",
            "job openings",
            "plans to hire"
        ]
        
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        for query in queries:
            try:
                url = f"{self.base_url}/everything"
                params = {
                    "q": query + " tech company",
                    "from": from_date,
                    "sortBy": "relevancy",
                    "language": "en",
                    "pageSize": 15,
                    "apiKey": self.api_key
                }
                
                response = await self.client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    
                    for article in data.get("articles", []):
                        title = article.get("title", "")
                        company_name = self._extract_company_from_title(title)
                        
                        if not company_name:
                            continue
                        
                        lead = RawLead(
                            company=company_name,
                            source="newsapi_hiring",
                            signal=f"Hiring news: {title}",
                            website=None,
                            discovered_at=datetime.utcnow(),
                            confidence=0.7,
                            metadata={
                                "news_url": article.get("url"),
                                "published_at": article.get("publishedAt")
                            }
                        )
                        leads.append(lead)
                        
                        if len(leads) >= max_results:
                            return leads
                            
            except Exception as e:
                print(f"NewsAPI hiring error: {e}")
                continue
        
        return leads
    
    def _extract_company_from_title(self, title: str) -> Optional[str]:
        """Extract company name from article title"""
        # Common patterns
        patterns = [
            r"^([A-Z][A-Za-z\s]+?)\s+(raises|announced|secures|gets)",
            r"^([A-Z][A-Za-z\s]+?)\s+(hiring|expands|launches)",
            r"([A-Z][A-Za-z\s]+?)\s+raises\s+\$",
            r"^([A-Z][A-Za-z\s]+?),\s+a\s+"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                company = match.group(1).strip()
                # Clean up
                if len(company) > 3 and len(company) < 50:
                    return company
        
        return None
    
    def _parse_funding_from_text(self, text: str) -> Dict:
        """Parse funding amount and stage from text"""
        result = {}
        
        # Look for funding amounts
        amount_match = re.search(r'\$([\d.]+)\s*(M|million|B|billion)', text, re.IGNORECASE)
        if amount_match:
            result["amount"] = f"${amount_match.group(1)}{amount_match.group(2).upper()[0]}"
        
        # Look for funding stages
        stages = ["Series A", "Series B", "Series C", "Seed", "Pre-seed", "Series D"]
        for stage in stages:
            if stage.lower() in text.lower():
                result["stage"] = stage
                break
        
        return result
    
    async def close(self):
        await self.client.aclose()


class ProductHuntScraper:
    """Scrape Product Hunt for new product launches"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def find_recent_launches(
        self,
        max_results: int = 30
    ) -> List[RawLead]:
        """
        Find companies that recently launched on Product Hunt
        
        Product Hunt API has free tier
        """
        leads = []
        
        try:
            # Product Hunt GraphQL API (free tier available)
            url = "https://www.producthunt.com/frontend/graphql"
            
            # Simple approach: scrape the homepage
            response = await self.client.get("https://www.producthunt.com")
            if response.status_code == 200:
                # Parse products from page
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for product links and names
                # This is a simplified scraper - would need proper selectors for production
                product_links = soup.find_all('a', href=re.compile(r'/posts/'))
                
                for link in product_links[:max_results]:
                    try:
                        product_name = link.get_text(strip=True)
                        if not product_name or len(product_name) < 3:
                            continue
                        
                        lead = RawLead(
                            company=product_name,
                            source="producthunt",
                            signal="Recent product launch on Product Hunt",
                            website=f"https://www.producthunt.com{link.get('href', '')}",
                            discovered_at=datetime.utcnow(),
                            confidence=0.8,
                            metadata={
                                "platform": "Product Hunt",
                                "launch_type": "product_launch"
                            }
                        )
                        leads.append(lead)
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"Product Hunt scraping error: {e}")
        
        return leads
    
    async def close(self):
        await self.client.aclose()


class HackerNewsScraper:
    """Scrape Hacker News 'Who is Hiring' and 'Show HN'"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.base_url = "https://hacker-news.firebaseio.com/v0"
    
    async def find_hiring_posts(
        self,
        max_results: int = 30
    ) -> List[RawLead]:
        """
        Find hiring posts on Hacker News
        
        Completely free - official Firebase API
        """
        leads = []
        
        try:
            # Get "Who is Hiring" posts (monthly)
            # These are usually posts by user "whoishiring"
            url = f"{self.base_url}/user/whoishiring/submitted.json"
            
            response = await self.client.get(url)
            if response.status_code == 200:
                story_ids = response.json()[:5]  # Last 5 hiring posts
                
                for story_id in story_ids:
                    try:
                        # Get story details
                        story_url = f"{self.base_url}/item/{story_id}.json"
                        story_resp = await self.client.get(story_url)
                        
                        if story_resp.status_code == 200:
                            story = story_resp.json()
                            title = story.get("title", "")
                            
                            # Check if it's a hiring post
                            if "hiring" in title.lower():
                                # Get top-level comments (company posts)
                                comment_ids = story.get("kids", [])[:20]
                                
                                for comment_id in comment_ids:
                                    try:
                                        comment_url = f"{self.base_url}/item/{comment_id}.json"
                                        comment_resp = await self.client.get(comment_url)
                                        
                                        if comment_resp.status_code == 200:
                                            comment = comment_resp.json()
                                            text = comment.get("text", "")
                                            
                                            # Extract company from comment
                                            company_name = self._extract_company_from_hn_post(text)
                                            
                                            if company_name:
                                                lead = RawLead(
                                                    company=company_name,
                                                    source="hackernews",
                                                    signal=f"Hiring on Hacker News: {title}",
                                                    website=None,
                                                    discovered_at=datetime.utcnow(),
                                                    confidence=0.75,
                                                    metadata={
                                                        "hn_post_id": story_id,
                                                        "comment_id": comment_id,
                                                        "post_title": title
                                                    }
                                                )
                                                leads.append(lead)
                                                
                                                if len(leads) >= max_results:
                                                    return leads
                                    except Exception:
                                        continue
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"HackerNews scraping error: {e}")
        
        return leads
    
    def _extract_company_from_hn_post(self, text: str) -> Optional[str]:
        """Extract company name from HN hiring post"""
        # Common patterns
        lines = text.split('\n')
        
        # First line often contains company name
        if lines:
            first_line = lines[0].strip()
            
            # Remove HTML tags if present
            first_line = re.sub(r'<[^>]+>', '', first_line)
            
            # Look for patterns like "Company Name | Location | Role"
            if '|' in first_line:
                parts = first_line.split('|')
                if parts:
                    company = parts[0].strip()
                    # Clean up
                    company = re.sub(r'^\*\*?|\*\*?$', '', company)  # Remove markdown bold
                    if len(company) > 2 and len(company) < 50:
                        return company
            
            # Just use first line if it looks like a company name
            if len(first_line) > 2 and len(first_line) < 50 and not first_line.startswith('http'):
                return first_line
        
        return None
    
    async def close(self):
        await self.client.aclose()


class JobBoardScraper:
    """Scrape job boards for hiring signals"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def find_companies_hiring(
        self,
        roles: List[str],
        max_results: int = 40
    ) -> List[RawLead]:
        """
        Find companies actively hiring specific roles
        
        Uses public job board RSS feeds and APIs
        """
        leads = []
        
        # Try various job board RSS feeds
        job_boards = [
            ("stackoverflow_jobs", "https://stackoverflow.com/jobs/feed"),
            ("github_jobs", "https://jobs.github.com/positions.json"),
        ]
        
        for board_name, feed_url in job_boards:
            try:
                if "json" in feed_url:
                    # JSON API
                    response = await self.client.get(feed_url, timeout=10.0)
                    if response.status_code == 200:
                        jobs = response.json()
                        
                        for job in jobs[:20]:
                            company = job.get("company", "")
                            title = job.get("title", "").lower()
                            
                            # Check if it's a relevant role
                            if any(role.lower() in title for role in roles):
                                lead = RawLead(
                                    company=company,
                                    source=board_name,
                                    signal=f"Hiring {job.get('title')}",
                                    website=job.get("company_url"),
                                    discovered_at=datetime.utcnow(),
                                    confidence=0.85,
                                    metadata={
                                        "role": job.get("title"),
                                        "location": job.get("location"),
                                        "job_url": job.get("url")
                                    }
                                )
                                leads.append(lead)
                                
                                if len(leads) >= max_results:
                                    return leads
                else:
                    # RSS feed
                    response = await self.client.get(feed_url, timeout=10.0)
                    if response.status_code == 200:
                        feed = feedparser.parse(response.text)
                        
                        for entry in feed.entries[:20]:
                            # Extract company from entry
                            company = self._extract_company_from_job_entry(entry)
                            title = entry.get("title", "").lower()
                            
                            if company and any(role.lower() in title for role in roles):
                                lead = RawLead(
                                    company=company,
                                    source=board_name,
                                    signal=f"Hiring: {entry.get('title')}",
                                    website=None,
                                    discovered_at=datetime.utcnow(),
                                    confidence=0.8,
                                    metadata={
                                        "role": entry.get("title"),
                                        "link": entry.get("link")
                                    }
                                )
                                leads.append(lead)
                                
                                if len(leads) >= max_results:
                                    return leads
                                    
            except Exception as e:
                print(f"Job board error ({board_name}): {e}")
                continue
        
        return leads
    
    def _extract_company_from_job_entry(self, entry) -> Optional[str]:
        """Extract company name from job entry"""
        title = entry.get("title", "")
        
        # Common pattern: "Role at Company" or "Role - Company"
        patterns = [
            r"at\s+([A-Z][A-Za-z\s&]+)$",
            r"-\s+([A-Z][A-Za-z\s&]+)$",
            r"@\s*([A-Z][A-Za-z\s&]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                company = match.group(1).strip()
                if 2 < len(company) < 50:
                    return company
        
        return None
    
    async def close(self):
        await self.client.aclose()
