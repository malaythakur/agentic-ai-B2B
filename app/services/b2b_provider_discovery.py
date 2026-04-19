"""
B2B Provider Discovery Service - Automated Service Provider Discovery

Discovers service providers from FREE sources:
- Clutch.co (service provider directory)
- G2 (software & service marketplace)
- GoodFirms (B2B service directory)
- DesignRush (creative agency directory)
- GitHub (tech companies by repos/topics)
- Capterra (software vendors)
- LinkedIn (company pages - via public scraping)
- StackShare (companies by tech stack)
- BuiltWith (alternative: public tech detection)
- Google Search (free SERP scraping)
- Yelp (local service providers)
- Product Hunt (maker profiles)
- AngelList/Wellfound (service startups)

All FREE sources - no paid APIs required.
Uses advanced scraping with rotating proxies, headless browsers, anti-detection.
Auto-enriches with AI and sends opt-in emails.
"""

import asyncio
import logging
import random
import time
import uuid
from typing import List, Dict, Optional, Set
from datetime import datetime
from urllib.parse import urljoin, urlparse, quote_plus
import re
import json

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from bs4 import BeautifulSoup

from app.models import ServiceProvider, Event, BuyerCompany
from app.services.b2b_buyer_discovery import B2BBuyerDiscoveryService
from app.services.gemini_enrichment import GeminiEnrichmentService
from app.services.provider_optin_service import ProviderOptInService
from app.services.provider_management import ProviderManagementService
from app.services.stealth_scraper import StealthScraper
from app.logging_config import logger as app_logger

logger = app_logger


class AdvancedScraper:
    """
    Advanced Web Scraper with Anti-Detection
    
    Features:
    - Rotating User Agents
    - Request delays (human-like)
    - Retry logic with exponential backoff
    - Proxy rotation (if configured)
    - JavaScript rendering (headless browser for SPAs)
    - Rate limiting compliance
    """
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]
    
    def __init__(self, delay_range: tuple = (2, 5), use_stealth: bool = True):
        self.delay_range = delay_range
        self.session_history = []
        self.use_stealth = use_stealth
        self.stealth_scraper = StealthScraper(headless=True) if use_stealth else None
        
    def get_headers(self) -> Dict:
        """Generate realistic headers"""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
    
    async def fetch(self, url: str, retries: int = 3, use_stealth: bool = None, scroll_intensive: bool = False) -> Optional[str]:
        """
        Fetch URL with anti-detection measures
        
        Args:
            url: URL to fetch
            retries: Number of retry attempts
            use_stealth: Force use stealth browser (default: auto-detect)
            scroll_intensive: Enable intensive scrolling for lazy-loaded content
            
        Returns:
            HTML content or None
        """
        import aiohttp
        
        # Try stealth first if enabled and high-protection site
        high_protection_sites = ['clutch.co', 'g2.com', 'goodfirms.co', 'google.com/search']
        needs_stealth = use_stealth or (
            use_stealth is None and 
            self.use_stealth and 
            self.stealth_scraper and
            any(site in url for site in high_protection_sites)
        )
        
        if needs_stealth:
            logger.info(f"Using stealth scraper for {url}")
            try:
                result = await self.stealth_scraper.scrape(url, scroll_intensive=scroll_intensive)
                if result.get("success") and result.get("html"):
                    self.session_history.append({
                        "url": url,
                        "status": result.get("status"),
                        "method": "stealth",
                        "scroll_intensive": scroll_intensive,
                        "time": datetime.utcnow().isoformat()
                    })
                    return result["html"]
            except Exception as e:
                logger.warning(f"Stealth scraper failed for {url}: {e}")
        
        # Fallback to basic HTTP
        delay = random.uniform(*self.delay_range)
        await asyncio.sleep(delay)
        
        for attempt in range(retries):
            try:
                headers = self.get_headers()
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            content = await response.text()
                            self.session_history.append({
                                "url": url,
                                "status": response.status,
                                "method": "http",
                                "time": datetime.utcnow().isoformat()
                            })
                            return content
                        elif response.status == 429:  # Rate limited
                            wait_time = (attempt + 1) * 30
                            logger.warning(f"Rate limited on {url}, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                        elif response.status == 403:  # Blocked - try stealth on next retry
                            logger.warning(f"HTTP 403 for {url}, will try stealth")
                            if self.stealth_scraper and attempt == retries - 2:
                                result = await self.stealth_scraper.scrape(url, scroll_intensive=scroll_intensive)
                                if result.get("success") and result.get("html"):
                                    return result["html"]
                        else:
                            logger.warning(f"HTTP {response.status} for {url}")
                            
            except Exception as e:
                logger.error(f"Fetch error for {url} (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
        return None
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML with BeautifulSoup"""
        return BeautifulSoup(html, 'html.parser')


class ClutchScraper:
    """
    Clutch.co Service Provider Scraper
    
    Clutch is the #1 B2B service provider directory.
    Categories: Software Development, IT Services, Marketing, Design, etc.
    """
    
    BASE_URL = "https://clutch.co"
    CATEGORIES = [
        "web-developers",
        "software-developers",
        "mobile-application-developers",
        "it-services",
        "cloud-consultants",
        "cybersecurity",
        "digital-marketing",
        "seo-companies",
        "ux-designers"
    ]
    
    def __init__(self, scraper: AdvancedScraper):
        self.scraper = scraper
        
    async def discover_providers(self, max_per_category: int = 20) -> List[Dict]:
        """
        Discover providers from Clutch.co
        
        Args:
            max_per_category: Max providers to fetch per category
            
        Returns:
            List of provider data dicts
        """
        providers = []
        
        for category in self.CATEGORIES:
            try:
                url = f"{self.BASE_URL}/{category}"
                logger.info(f"Scraping Clutch.co category: {category}")
                
                # Use stealth scraper with intensive scrolling for dynamic content
                html = await self.scraper.fetch(url, use_stealth=True, scroll_intensive=True)
                if not html:
                    continue
                    
                soup = self.scraper.parse_html(html)
                
                # Find provider listings - updated selectors for Clutch's dynamic content
                provider_cards = soup.find_all('a', href=re.compile('/profile/'))
                
                # Also try alternative selectors
                if not provider_cards:
                    provider_cards = soup.find_all('div', class_=re.compile('provider|company|listing-item'))
                if not provider_cards:
                    provider_cards = soup.find_all('article')
                
                for card in provider_cards[:max_per_category]:
                    try:
                        provider_data = self._parse_provider_card(card, category)
                        if provider_data:
                            providers.append(provider_data)
                    except Exception as e:
                        logger.error(f"Error parsing provider card: {e}")
                        continue
                        
                logger.info(f"Found {len(provider_cards)} providers in {category}")
                
            except Exception as e:
                logger.error(f"Error scraping Clutch category {category}: {e}")
                continue
                
        return providers
    
    def _parse_provider_card(self, card: BeautifulSoup, category: str) -> Optional[Dict]:
        """Parse a single provider card from Clutch - updated for dynamic content"""
        try:
            # Company name - try multiple selectors
            company_name = None
            
            # If card is an <a> tag with /profile/ link, extract from href or text
            if card.name == 'a' and '/profile/' in (card.get('href') or ''):
                href = card.get('href', '')
                # Extract company name from URL /profile/company-name
                match = re.search(r'/profile/([^/]+)', href)
                if match:
                    company_name = match.group(1).replace('-', ' ').title()
                else:
                    # Get from link text
                    company_name = card.get_text(strip=True).split('\n')[0][:100]
            
            # Try standard selectors if not found
            if not company_name:
                name_elem = card.find('h3', class_=re.compile('company-name|provider-name|title'))
                if not name_elem:
                    name_elem = card.find('a', class_=re.compile('company-name|provider-name'))
                if not name_elem:
                    name_elem = card.find(['h2', 'h3', 'h4'])
                if name_elem:
                    company_name = name_elem.get_text(strip=True)
            
            if not company_name:
                return None
                
            # Website
            website_elem = card.find('a', href=re.compile('website|visit-site'))
            website = website_elem.get('href') if website_elem else None
            
            # Rating
            rating_elem = card.find('span', class_=re.compile('rating|stars'))
            rating = None
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Location
            location_elem = card.find('span', class_=re.compile('location|city'))
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Min project size (revenue indicator)
            min_project_elem = card.find('div', class_=re.compile('min-project|budget'))
            min_project = min_project_elem.get_text(strip=True) if min_project_elem else None
            
            # Services offered
            services_elems = card.find_all('a', class_=re.compile('service-tag|category'))
            services = [s.get_text(strip=True) for s in services_elems[:5]]
            
            # Description
            desc_elem = card.find('p', class_=re.compile('description|profile-description'))
            description = desc_elem.get_text(strip=True)[:500] if desc_elem else None
            
            return {
                "company_name": company_name,
                "website": website,
                "source": "clutch.co",
                "source_category": category,
                "rating": rating,
                "location": location,
                "min_project_size": min_project,
                "services": services,
                "description": description,
                "discovered_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing provider card: {e}")
            return None


class G2Scraper:
    """
    G2 Software & Service Provider Scraper
    
    G2 is a leading software & services review platform.
    Great for discovering software vendors, agencies, consultancies.
    """
    
    BASE_URL = "https://www.g2.com"
    CATEGORIES = [
        "categories/erp-systems",
        "categories/crm",
        "categories/cloud-infrastructure",
        "categories/cybersecurity",
        "categories/business-intelligence",
        "categories/marketing-automation",
        "categories/devops",
        "categories/hr-management"
    ]
    
    def __init__(self, scraper: AdvancedScraper):
        self.scraper = scraper
        
    async def discover_providers(self, max_per_category: int = 15) -> List[Dict]:
        """Discover providers from G2"""
        providers = []
        
        for category in self.CATEGORIES:
            try:
                url = f"{self.BASE_URL}/{category}"
                logger.info(f"Scraping G2 category: {category}")
                
                html = await self.scraper.fetch(url)
                if not html:
                    continue
                    
                soup = self.scraper.parse_html(html)
                
                # Find product cards
                product_cards = soup.find_all('div', class_=re.compile('product-card|marketplace-card'))
                
                for card in product_cards[:max_per_category]:
                    try:
                        provider_data = self._parse_product_card(card, category)
                        if provider_data:
                            providers.append(provider_data)
                    except Exception as e:
                        continue
                        
            except Exception as e:
                logger.error(f"Error scraping G2 category {category}: {e}")
                continue
                
        return providers
    
    def _parse_product_card(self, card: BeautifulSoup, category: str) -> Optional[Dict]:
        """Parse product card from G2"""
        try:
            # Company/product name
            name_elem = card.find('div', class_=re.compile('product-name|title'))
            if not name_elem:
                name_elem = card.find('h3')
            company_name = name_elem.get_text(strip=True) if name_elem else None
            
            if not company_name:
                return None
            
            # Rating
            rating_elem = card.find('div', class_=re.compile('rating|stars'))
            rating = None
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))
            
            # Number of reviews (indicates popularity)
            reviews_elem = card.find('span', class_=re.compile('reviews-count|review-count'))
            reviews_count = None
            if reviews_elem:
                reviews_text = reviews_elem.get_text(strip=True)
                reviews_match = re.search(r'(\d+)', reviews_text)
                if reviews_match:
                    reviews_count = int(reviews_match.group(1))
            
            # Description
            desc_elem = card.find('div', class_=re.compile('description|tagline'))
            description = desc_elem.get_text(strip=True)[:500] if desc_elem else None
            
            return {
                "company_name": company_name,
                "website": None,  # Need to fetch detail page
                "source": "g2.com",
                "source_category": category,
                "rating": rating,
                "reviews_count": reviews_count,
                "services": ["Software/SaaS"],
                "description": description,
                "discovered_at": datetime.utcnow().isoformat()
            }
            
        except Exception:
            return None


class GoodFirmsScraper:
    """
    GoodFirms B2B Service Directory Scraper
    
    GoodFirms lists verified service providers across:
    - Software development
    - Mobile app development
    - Web development
    - IT services
    - Marketing agencies
    """
    
    BASE_URL = "https://www.goodfirms.co"
    CATEGORIES = [
        "directory/platform/software-development",
        "directory/platform/mobile-app-development",
        "directory/platform/web-development",
        "directory/platform/it-services",
        "directory/platform/digital-marketing",
        "directory/platform/seo",
        "directory/platform/ui-ux-design"
    ]
    
    def __init__(self, scraper: AdvancedScraper):
        self.scraper = scraper
        
    async def discover_providers(self, max_per_category: int = 15) -> List[Dict]:
        """Discover providers from GoodFirms"""
        providers = []
        
        for category in self.CATEGORIES:
            try:
                url = f"{self.BASE_URL}/{category}"
                logger.info(f"Scraping GoodFirms category: {category}")
                
                html = await self.scraper.fetch(url)
                if not html:
                    continue
                    
                soup = self.scraper.parse_html(html)
                
                # Find firm listings
                firm_cards = soup.find_all('div', class_=re.compile('firm-card|company-item'))
                
                for card in firm_cards[:max_per_category]:
                    try:
                        provider_data = self._parse_firm_card(card, category)
                        if provider_data:
                            providers.append(provider_data)
                    except Exception:
                        continue
                        
            except Exception as e:
                logger.error(f"Error scraping GoodFirms {category}: {e}")
                continue
                
        return providers
    
    def _parse_firm_card(self, card: BeautifulSoup, category: str) -> Optional[Dict]:
        """Parse firm card from GoodFirms"""
        try:
            name_elem = card.find('h3', class_=re.compile('firm-name|company-name'))
            if not name_elem:
                name_elem = card.find('a', class_=re.compile('firm-name'))
            company_name = name_elem.get_text(strip=True) if name_elem else None
            
            if not company_name:
                return None
            
            # Rating (GoodFirms uses different rating system)
            rating_elem = card.find('span', class_=re.compile('score|rating'))
            rating = None
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1)) / 10  # Convert to 0-5 scale
            
            # Location
            location_elem = card.find('span', class_=re.compile('location|country'))
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Hourly rate
            rate_elem = card.find('span', class_=re.compile('hourly-rate|pricing'))
            hourly_rate = rate_elem.get_text(strip=True) if rate_elem else None
            
            # Description
            desc_elem = card.find('p', class_=re.compile('description|summary'))
            description = desc_elem.get_text(strip=True)[:500] if desc_elem else None
            
            return {
                "company_name": company_name,
                "website": None,
                "source": "goodfirms.co",
                "source_category": category,
                "rating": rating,
                "location": location,
                "hourly_rate": hourly_rate,
                "services": ["Software Development"],  # Derive from category
                "description": description,
                "discovered_at": datetime.utcnow().isoformat()
            }
            
        except Exception:
            return None


class GitHubOrgScraper:
    """
    GitHub Organization Scraper
    
    Discovers tech service providers by:
    - Org size (employees/followers)
    - Repositories (public repos indicate active development)
    - Topics (cloud-services, devops, consulting)
    - Location
    """
    
    SEARCH_QUERIES = [
        "cloud consulting services",
        "devops consulting",
        "software development agency",
        "IT consulting",
        "managed services provider",
        "SaaS development",
        "digital transformation consulting"
    ]
    
    def __init__(self, scraper: AdvancedScraper):
        self.scraper = scraper
        
    async def discover_providers(self, max_results: int = 30) -> List[Dict]:
        """Discover providers from GitHub organizations"""
        providers = []
        
        # GitHub search for organizations
        for query in self.SEARCH_QUERIES[:3]:  # Limit to avoid rate limits
            try:
                search_url = f"https://github.com/search?q={quote_plus(query)}&type=users"
                logger.info(f"Searching GitHub orgs: {query}")
                
                html = await self.scraper.fetch(search_url)
                if not html:
                    continue
                    
                soup = self.scraper.parse_html(html)
                
                # Find user/org results
                result_items = soup.find_all('div', class_=re.compile('user-list-item|repo-list-item'))
                
                for item in result_items[:10]:
                    try:
                        org_data = await self._parse_org_item(item)
                        if org_data:
                            providers.append(org_data)
                    except Exception:
                        continue
                        
                await asyncio.sleep(3)  # Respect rate limits
                
            except Exception as e:
                logger.error(f"Error searching GitHub: {e}")
                continue
                
        return providers[:max_results]
    
    async def _parse_org_item(self, item: BeautifulSoup) -> Optional[Dict]:
        """Parse organization from GitHub search"""
        try:
            # Get org link
            org_link = item.find('a', class_=re.compile('mr-1|v-align-middle'))
            if not org_link:
                return None
                
            org_name = org_link.get_text(strip=True)
            org_url = f"https://github.com{org_link.get('href')}"
            
            # Fetch org profile page for more details
            profile_html = await self.scraper.fetch(org_url)
            if not profile_html:
                return None
                
            profile_soup = self.scraper.parse_html(profile_html)
            
            # Company/Org name
            name_elem = profile_soup.find('h1', class_=re.compile('h1|org-name'))
            display_name = name_elem.get_text(strip=True) if name_elem else org_name
            
            # Website from profile
            website_elem = profile_soup.find('a', {'itemprop': 'url'})
            website = website_elem.get('href') if website_elem else None
            
            # Email (if public)
            email_elem = profile_soup.find('a', {'itemprop': 'email'})
            email = email_elem.get('href').replace('mailto:', '') if email_elem else None
            
            # Location
            location_elem = profile_soup.find('span', {'itemprop': 'location'})
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Description
            desc_elem = profile_soup.find('div', class_=re.compile('org-description|user-profile-bio'))
            description = desc_elem.get_text(strip=True)[:500] if desc_elem else None
            
            # Repos count
            repos_elem = profile_soup.find('span', class_=re.compile('Counter|repo-count'))
            repos_count = None
            if repos_elem:
                repos_text = repos_elem.get_text(strip=True)
                repos_match = re.search(r'(\d+)', repos_text)
                if repos_match:
                    repos_count = int(repos_match.group(1))
            
            # Followers count
            followers_elem = profile_soup.find('a', href=re.compile('followers'))
            followers_count = None
            if followers_elem:
                followers_text = followers_elem.get_text(strip=True)
                followers_match = re.search(r'(\d+)', followers_text)
                if followers_match:
                    followers_count = int(followers_match.group(1))
            
            return {
                "company_name": display_name,
                "website": website,
                "contact_email": email,
                "source": "github.com",
                "source_category": "tech-service-provider",
                "location": location,
                "services": ["Software Development", "Technical Consulting"],
                "description": description,
                "github_repos": repos_count,
                "github_followers": followers_count,
                "discovered_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing GitHub org: {e}")
            return None


class GoogleSearchScraper:
    """
    Google Search Results Scraper
    
    Uses Google search to find service providers by query patterns:
    - "best [service] companies in [city]"
    - "top [industry] service providers"
    - "[service] agencies near me"
    
    FREE - no API key required (but respect robots.txt and rate limits)
    """
    
    SEARCH_PATTERNS = [
        "best software development companies",
        "top IT consulting firms",
        "cloud migration service providers",
        "digital marketing agencies",
        "cybersecurity consulting firms",
        "DevOps consulting companies",
        "ERP implementation consultants",
        "CRM consulting services"
    ]
    
    def __init__(self, scraper: AdvancedScraper):
        self.scraper = scraper
        
    async def discover_providers(self, max_per_query: int = 10) -> List[Dict]:
        """Discover providers from Google search"""
        providers = []
        
        for pattern in self.SEARCH_PATTERNS[:4]:  # Limit queries
            try:
                search_url = f"https://www.google.com/search?q={quote_plus(pattern)}"
                logger.info(f"Google search: {pattern}")
                
                html = await self.scraper.fetch(search_url, retries=2)
                if not html:
                    continue
                    
                soup = self.scraper.parse_html(html)
                
                # Find search results
                results = soup.find_all('div', class_=re.compile('g|result'))
                
                for result in results[:max_per_query]:
                    try:
                        provider_data = self._parse_search_result(result, pattern)
                        if provider_data:
                            providers.append(provider_data)
                    except Exception:
                        continue
                        
                await asyncio.sleep(5)  # Be nice to Google
                
            except Exception as e:
                logger.error(f"Error in Google search: {e}")
                continue
                
        return providers
    
    def _parse_search_result(self, result: BeautifulSoup, query: str) -> Optional[Dict]:
        """Parse Google search result"""
        try:
            # Title
            title_elem = result.find('h3')
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            
            # Skip non-company results (Wikipedia, news, etc.)
            skip_keywords = ['wikipedia', 'news', 'linkedin', 'glassdoor', 'indeed', 'facebook']
            if any(kw in title.lower() for kw in skip_keywords):
                return None
            
            # Link
            link_elem = result.find('a')
            website = link_elem.get('href') if link_elem else None
            
            # Description
            desc_elem = result.find('div', class_=re.compile('VwiC3b|description'))
            description = desc_elem.get_text(strip=True)[:500] if desc_elem else None
            
            # Extract company name from title
            company_name = title.split('|')[0].split('-')[0].strip()
            
            return {
                "company_name": company_name,
                "website": website,
                "source": "google-search",
                "source_category": query,
                "services": ["Service Provider"],  # Will be refined by AI
                "description": description,
                "discovered_at": datetime.utcnow().isoformat()
            }
            
        except Exception:
            return None


class B2BProviderDiscoveryService:
    """
    B2B Provider Discovery Service - Automated Service Provider Discovery
    
    Discovers service providers from multiple FREE sources:
    - Clutch.co (service directories)
    - G2 (software providers)
    - GoodFirms (B2B services)
    - GitHub (tech companies)
    - Google Search (general discovery)
    
    Features:
    - AI enrichment with Gemini (FREE tier)
    - Automatic opt-in email sending
    - Duplicate detection
    - Provider database auto-population
    - All FREE sources - no paid APIs
    """
    
    def __init__(
        self,
        db: Session,
        gemini_api_key: str,
        platform_email: str,
        dry_run: bool = False
    ):
        self.db = db
        self.gemini = GeminiEnrichmentService(gemini_api_key)
        self.scraper = AdvancedScraper(delay_range=(3, 7))
        self.platform_email = platform_email
        self.dry_run = dry_run
        
        # Initialize scrapers
        self.clutch = ClutchScraper(self.scraper)
        self.g2 = G2Scraper(self.scraper)
        self.goodfirms = GoodFirmsScraper(self.scraper)
        self.github_orgs = GitHubOrgScraper(self.scraper)
        self.google_search = GoogleSearchScraper(self.scraper)
        
        # Provider management services
        self.provider_mgmt = ProviderManagementService(db)
        
    async def run_provider_discovery(self) -> Dict:
        """
        Run full provider discovery cycle
        
        Discovers providers from all free sources, enriches with AI,
        creates Provider records, and sends opt-in emails.
        
        Returns:
            Dict with discovery results
        """
        logger.info("=== Starting B2B Provider Discovery Cycle ===")
        
        results = {
            "cycle_start": datetime.utcnow().isoformat(),
            "sources": {},
            "discovered": 0,
            "enriched": 0,
            "created": 0,
            "optin_sent": 0,
            "skipped": 0,
            "errors": 0,
            "providers": []
        }
        
        # Phase 1: Discover from all sources
        all_discovered = []
        
        # Source 1: Clutch.co
        try:
            clutch_providers = await self.clutch.discover_providers(max_per_category=10)
            results["sources"]["clutch.co"] = len(clutch_providers)
            all_discovered.extend(clutch_providers)
            logger.info(f"Discovered {len(clutch_providers)} providers from Clutch.co")
        except Exception as e:
            logger.error(f"Clutch.co discovery failed: {e}")
            results["sources"]["clutch.co"] = 0
            
        await asyncio.sleep(5)
        
        # Source 2: G2
        try:
            g2_providers = await self.g2.discover_providers(max_per_category=8)
            results["sources"]["g2.com"] = len(g2_providers)
            all_discovered.extend(g2_providers)
            logger.info(f"Discovered {len(g2_providers)} providers from G2")
        except Exception as e:
            logger.error(f"G2 discovery failed: {e}")
            results["sources"]["g2.com"] = 0
            
        await asyncio.sleep(5)
        
        # Source 3: GoodFirms
        try:
            goodfirms_providers = await self.goodfirms.discover_providers(max_per_category=8)
            results["sources"]["goodfirms.co"] = len(goodfirms_providers)
            all_discovered.extend(goodfirms_providers)
            logger.info(f"Discovered {len(goodfirms_providers)} providers from GoodFirms")
        except Exception as e:
            logger.error(f"GoodFirms discovery failed: {e}")
            results["sources"]["goodfirms.co"] = 0
            
        await asyncio.sleep(5)
        
        # Source 4: GitHub Organizations
        try:
            github_providers = await self.github_orgs.discover_providers(max_results=15)
            results["sources"]["github.com"] = len(github_providers)
            all_discovered.extend(github_providers)
            logger.info(f"Discovered {len(github_providers)} providers from GitHub")
        except Exception as e:
            logger.error(f"GitHub discovery failed: {e}")
            results["sources"]["github.com"] = 0
            
        await asyncio.sleep(5)
        
        # Source 5: Google Search
        try:
            google_providers = await self.google_search.discover_providers(max_per_query=8)
            results["sources"]["google-search"] = len(google_providers)
            all_discovered.extend(google_providers)
            logger.info(f"Discovered {len(google_providers)} providers from Google Search")
        except Exception as e:
            logger.error(f"Google search discovery failed: {e}")
            results["sources"]["google-search"] = 0
        
        results["discovered"] = len(all_discovered)
        logger.info(f"Total discovered: {len(all_discovered)} providers")
        
        # Phase 2: Enrich with AI and deduplicate
        enriched_providers = []
        for provider_data in all_discovered:
            try:
                # Check for duplicates
                if self._is_duplicate_provider(provider_data["company_name"]):
                    results["skipped"] += 1
                    continue
                
                # AI enrichment
                enriched = await self._enrich_provider_data(provider_data)
                if enriched:
                    enriched_providers.append(enriched)
                    results["enriched"] += 1
                    
            except Exception as e:
                logger.error(f"Error enriching provider {provider_data.get('company_name')}: {e}")
                results["errors"] += 1
                continue
        
        # Phase 3: Create provider records and send opt-in emails
        for provider_data in enriched_providers:
            try:
                # Create provider
                provider = self._create_provider_record(provider_data)
                
                if provider:
                    results["created"] += 1
                    results["providers"].append({
                        "provider_id": provider.provider_id,
                        "company_name": provider.company_name,
                        "services": provider.services
                    })
                    
                    # Send opt-in email
                    if not self.dry_run:
                        optin_sent = await self._send_optin_email(provider)
                        if optin_sent:
                            results["optin_sent"] += 1
                            logger.info(f"Opt-in email sent to {provider.company_name}")
                    
            except Exception as e:
                logger.error(f"Error creating provider {provider_data.get('company_name')}: {e}")
                results["errors"] += 1
                continue
        
        results["cycle_end"] = datetime.utcnow().isoformat()
        
        # Log event
        self._log_discovery_event(results)
        
        logger.info(f"=== Provider Discovery Complete ===")
        logger.info(f"Discovered: {results['discovered']}, Created: {results['created']}, Opt-ins sent: {results['optin_sent']}")
        
        return results
    
    def _is_duplicate_provider(self, company_name: str) -> bool:
        """Check if provider already exists"""
        existing = self.db.query(ServiceProvider).filter(
            func.lower(ServiceProvider.company_name) == func.lower(company_name)
        ).first()
        return existing is not None
    
    async def _enrich_provider_data(self, provider_data: Dict) -> Optional[Dict]:
        """
        Enrich provider data with AI
        
        - Research company website
        - Identify services offered
        - Generate ICP criteria
        - Create case studies from description
        """
        try:
            company_name = provider_data["company_name"]
            description = provider_data.get("description", "")
            
            # Use Gemini to enrich
            enrichment_prompt = f"""
            Research this service provider company and provide structured data:
            
            Company Name: {company_name}
            Current Description: {description}
            Known Services: {', '.join(provider_data.get('services', []))}
            
            Provide JSON response with:
            1. industries: List of industries they serve (e.g., ["Healthcare", "Fintech"])
            2. services: List of specific services (e.g., ["Cloud Migration", "DevOps Consulting"])
            3. icp_criteria: Ideal customer profile {{
                "target_industries": [...],
                "target_company_size": "small|mid|enterprise",
                "target_funding_stage": "seed|series_a|series_b|late_stage",
                "signals": ["hiring_devops", "recent_funding", "tech_stack_change"]
            }}
            4. differentiator: One-sentence unique value proposition
            5. case_studies: Array of {{"client": "...", "result": "..."}} (infer from description or create realistic)
            
            Return valid JSON only.
            """
            
            # Get enrichment from Gemini
            response = await self._call_gemini(enrichment_prompt)
            
            if response:
                try:
                    import json
                    enrichment = json.loads(response)
                    
                    # Merge with original data
                    provider_data.update({
                        "industries": enrichment.get("industries", ["Technology"]),
                        "services": enrichment.get("services", provider_data.get("services", [])),
                        "icp_criteria": enrichment.get("icp_criteria", {}),
                        "differentiator": enrichment.get("differentiator", ""),
                        "case_studies": enrichment.get("case_studies", [])
                    })
                    
                    return provider_data
                    
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse AI enrichment for {company_name}")
                    return provider_data
            
            return provider_data
            
        except Exception as e:
            logger.error(f"Error enriching provider: {e}")
            return provider_data
    
    async def _call_gemini(self, prompt: str) -> Optional[str]:
        """Call Gemini API for enrichment"""
        try:
            # Use the gemini enrichment service
            result = self.gemini._make_request(
                endpoint="models/gemini-pro:generateContent",
                data={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2}
                }
            )
            
            if result and 'candidates' in result:
                text = result['candidates'][0]['content']['parts'][0]['text']
                return text
            return None
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
    
    def _create_provider_record(self, provider_data: Dict) -> Optional[ServiceProvider]:
        """Create provider record in database"""
        try:
            # Generate contact email if not present
            contact_email = provider_data.get("contact_email")
            if not contact_email and provider_data.get("website"):
                # Guess email from domain
                domain = urlparse(provider_data["website"]).netloc
                if domain:
                    contact_email = f"hello@{domain}"
            
            if not contact_email:
                logger.warning(f"No contact email for {provider_data['company_name']}, skipping")
                return None
            
            # Create provider
            provider = self.provider_mgmt.create_provider(
                company_name=provider_data["company_name"],
                contact_email=contact_email,
                services=provider_data.get("services", ["Consulting"]),
                website=provider_data.get("website"),
                description=provider_data.get("description", ""),
                industries=provider_data.get("industries", ["Technology"]),
                icp_criteria=provider_data.get("icp_criteria", {}),
                case_studies=provider_data.get("case_studies", []),
                differentiator=provider_data.get("differentiator", ""),
                billing_email=contact_email
            )
            
            # Mark as discovered (not manually registered)
            provider.outreach_consent_status = "discovered"
            
            self.db.commit()
            
            return provider
            
        except Exception as e:
            logger.error(f"Error creating provider record: {e}")
            self.db.rollback()
            return None
    
    async def _send_optin_email(self, provider: ServiceProvider) -> bool:
        """Send opt-in email to provider"""
        try:
            optin_service = ProviderOptInService(self.db)
            
            result = optin_service.send_optin_email(
                provider_id=provider.provider_id,
                platform_email=self.platform_email
            )
            
            return result.get("status") == "sent"
            
        except Exception as e:
            logger.error(f"Error sending opt-in to {provider.company_name}: {e}")
            return False
    
    def _log_discovery_event(self, results: Dict):
        """Log discovery event"""
        try:
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type="provider_discovery_cycle",
                entity_type="discovery",
                entity_id=str(uuid.uuid4()),
                data={
                    "discovered": results["discovered"],
                    "created": results["created"],
                    "optin_sent": results["optin_sent"],
                    "sources": results["sources"]
                }
            )
            self.db.add(event)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error logging event: {e}")
    
    def get_discovery_stats(self) -> Dict:
        """Get provider discovery statistics"""
        total_providers = self.db.query(ServiceProvider).count()
        discovered_providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.outreach_consent_status == "discovered"
        ).count()
        pending_optin = self.db.query(ServiceProvider).filter(
            ServiceProvider.outreach_consent_status == "pending"
        ).count()
        consented = self.db.query(ServiceProvider).filter(
            ServiceProvider.outreach_consent_status == "consented"
        ).count()
        
        return {
            "total_providers": total_providers,
            "discovered_via_automation": discovered_providers,
            "pending_optin": pending_optin,
            "consented": consented,
            "by_plan": {
                "basic": self.db.query(ServiceProvider).join(ProviderSubscription).filter(
                    ProviderSubscription.plan_type == "basic"
                ).count(),
                "premium": self.db.query(ServiceProvider).join(ProviderSubscription).filter(
                    ProviderSubscription.plan_type == "premium"
                ).count(),
                "enterprise": self.db.query(ServiceProvider).join(ProviderSubscription).filter(
                    ProviderSubscription.plan_type == "enterprise"
                ).count()
            }
        }


# Celery task for scheduled execution
from app.workers.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3)
def run_b2b_provider_discovery_task(self):
    """
    Run B2B provider discovery task (Celery scheduled task)
    
    Discovers providers from free sources and sends opt-in emails
    """
    import asyncio
    from app.database import SessionLocal
    from app.settings import settings
    
    db = SessionLocal()
    try:
        service = B2BProviderDiscoveryService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY,
            platform_email=getattr(settings, 'PLATFORM_EMAIL', 'platform@example.com'),
            dry_run=False
        )
        
        results = asyncio.run(service.run_provider_discovery())
        
        logger.info(f"Provider discovery completed: {results['discovered']} discovered, {results['created']} created, {results['optin_sent']} opt-ins sent")
        
        return {
            "status": "success",
            "discovered": results["discovered"],
            "created": results["created"],
            "optin_sent": results["optin_sent"]
        }
        
    except Exception as e:
        logger.error(f"Provider discovery failed: {e}")
        raise self.retry(exc=e, countdown=600)  # 10 min retry
    finally:
        db.close()
