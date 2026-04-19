"""
Prospect Discovery Service

Discovers potential providers and buyers using FREE data sources
(GitHub, NewsAPI, Gemini AI) and enriches them with signals.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.integrations.github_enrichment import GitHubEnrichmentService
from app.integrations.gemini_analysis import GeminiAnalysisService
# Crunchbase is no longer free, using GitHub + NewsAPI + Gemini instead

logger = logging.getLogger(__name__)


class ProspectDiscoveryService:
    """Service for discovering and enriching prospects"""
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        crunchbase_api_key: Optional[str] = None
    ):
        """
        Initialize prospect discovery service
        
        Args:
            github_token: GitHub API token
            gemini_api_key: Gemini API key
            crunchbase_api_key: Crunchbase API key (optional, using free sources instead)
        """
        self.github = GitHubEnrichmentService(github_token)
        self.gemini = GeminiAnalysisService(gemini_api_key)
        # Crunchbase is no longer free, using GitHub + NewsAPI + Gemini instead
        self.crunchbase = None
    
    def discover_providers(
        self,
        tech_stack: List[str],
        industries: List[str],
        min_stars: int = 50,
        limit: int = 50
    ) -> List[Dict]:
        """
        Discover service providers by tech stack and industry
        
        Args:
            tech_stack: Technologies to search for
            industries: Target industries
            min_stars: Minimum GitHub stars
            limit: Maximum results
            
        Returns:
            List of enriched provider prospects
        """
        logger.info(f"Discovering providers with tech stack: {tech_stack}")
        
        # Find companies using GitHub
        github_companies = self.github.find_companies_by_tech_stack(
            tech_stack=tech_stack,
            min_stars=min_stars,
            limit=limit
        )
        
        # Enrich with Gemini AI analysis
        enriched_providers = []
        for company in github_companies:
            try:
                # Analyze with Gemini
                if company.get("description"):
                    ai_analysis = self.gemini.analyze_company_description(company["description"])
                    company["ai_analysis"] = ai_analysis
                else:
                    company["ai_analysis"] = None
                
                # Add industry filter
                if company.get("ai_analysis") and company["ai_analysis"].get("industry"):
                    company["industry"] = company["ai_analysis"]["industry"]
                else:
                    company["industry"] = "unknown"
                
                # Filter by target industries if specified (but allow unknown)
                if industries and company["industry"] != "unknown" and company["industry"] not in industries:
                    continue
                
                # Mark as provider prospect
                company["prospect_type"] = "provider"
                company["discovered_at"] = datetime.utcnow().isoformat()
                company["source"] = "github"
                
                enriched_providers.append(company)
                
            except Exception as e:
                logger.error(f"Error enriching provider {company.get('company_name')}: {e}")
                continue
        
        logger.info(f"Discovered {len(enriched_providers)} provider prospects")
        return enriched_providers
    
    def discover_buyers(
        self,
        industries: List[str],
        funding_stage: Optional[str] = None,
        employee_range: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Discover buyer companies by industry and funding stage using FREE sources
        
        Args:
            industries: Target industries
            funding_stage: Funding stage (e.g., "series_b")
            employee_range: Employee count range (e.g., "50-200")
            limit: Maximum results
            
        Returns:
            List of enriched buyer prospects
        """
        logger.info(f"Discovering buyers in industries: {industries}, funding stage: {funding_stage}")
        
        enriched_buyers = []
        
        # Use FREE sources: GitHub + NewsAPI + Gemini
        logger.info("Using free sources: GitHub + NewsAPI + Gemini for buyer discovery")
        
        # Source 1: GitHub (companies with repos in target industries)
        for industry in industries:
            github_companies = self.github.search_repositories(
                query=industry,
                stars=10,
                per_page=limit // 2
            )
            
            for repo in github_companies:
                try:
                    company = {
                        "company_name": repo.get("owner", {}).get("login"),
                        "website": repo.get("owner", {}).get("html_url"),
                        "description": repo.get("description"),
                        "industry": industry,
                        "prospect_type": "buyer",
                        "discovered_at": datetime.utcnow().isoformat(),
                        "source": "github",
                        "stars": repo.get("stargazers_count", 0)
                    }
                    
                    # Enrich with Gemini
                    if company.get("description"):
                        ai_analysis = self.gemini.analyze_company_description(company["description"])
                        company["ai_analysis"] = ai_analysis
                        
                        value_signals = self.gemini.extract_value_signals(
                            company["description"],
                            company.get("website", "")
                        )
                        company["value_signals"] = value_signals
                        
                        # AI-estimate funding stage based on signals
                        stage_classification = self.gemini.classify_company_stage(
                            company["description"],
                            employee_range or 100,
                            0  # No funding data available from GitHub
                        )
                        company["stage_classification"] = stage_classification
                    
                    enriched_buyers.append(company)
                    
                    if len(enriched_buyers) >= limit:
                        break
                        
                except Exception as e:
                    logger.error(f"Error enriching buyer from GitHub: {e}")
                    continue
            
            if len(enriched_buyers) >= limit:
                break
        
        # Source 2: NewsAPI (companies mentioned in news for target industries)
        try:
            from app.integrations.newsapi_enrichment import NewsAPIEnrichmentService
            newsapi_service = NewsAPIEnrichmentService()
            
            for industry in industries:
                news_companies = newsapi_service.find_companies_in_news(
                    query=industry,
                    limit=limit // 2
                )
                
                for company in news_companies:
                    try:
                        # Check if already added
                        if any(b.get("company_name") == company.get("company_name") for b in enriched_buyers):
                            continue
                            
                        company["industry"] = industry
                        company["prospect_type"] = "buyer"
                        company["discovered_at"] = datetime.utcnow().isoformat()
                        company["source"] = "newsapi"
                        
                        # Enrich with Gemini
                        if company.get("description"):
                            ai_analysis = self.gemini.analyze_company_description(company["description"])
                            company["ai_analysis"] = ai_analysis
                            
                            value_signals = self.gemini.extract_value_signals(
                                company["description"],
                                company.get("website", "")
                            )
                            company["value_signals"] = value_signals
                        
                        enriched_buyers.append(company)
                        
                        if len(enriched_buyers) >= limit:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error enriching buyer from NewsAPI: {e}")
                        continue
                
                if len(enriched_buyers) >= limit:
                    break
                    
        except Exception as e:
            logger.warning(f"NewsAPI enrichment failed: {e}")
            
            # Fallback: Use GitHub to find companies
            for industry in industries:
                github_companies = self.github.search_repositories(
                    query=industry,
                    stars=10,
                    per_page=20
                )
                
                for repo in github_companies:
                    try:
                        company = {
                            "company_name": repo.get("owner", {}).get("login"),
                            "website": repo.get("owner", {}).get("html_url"),
                            "description": repo.get("description"),
                            "industry": industry,
                            "prospect_type": "buyer",
                            "discovered_at": datetime.utcnow().isoformat(),
                            "source": "github"
                        }
                        
                        # Enrich with Gemini
                        if company.get("description"):
                            ai_analysis = self.gemini.analyze_company_description(company["description"])
                            company["ai_analysis"] = ai_analysis
                        
                        enriched_buyers.append(company)
                        
                        if len(enriched_buyers) >= limit:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error enriching buyer from GitHub: {e}")
                        continue
                
                if len(enriched_buyers) >= limit:
                    break
        
        logger.info(f"Discovered {len(enriched_buyers)} buyer prospects")
        return enriched_buyers
    
    def discover_by_tech_need(
        self,
        tech_need: str,
        company_type: str = "buyer",
        limit: int = 50
    ) -> List[Dict]:
        """
        Discover companies by specific technology need
        
        Args:
            tech_need: Technology need (e.g., "kubernetes", "machine learning")
            company_type: "provider" or "buyer"
            limit: Maximum results
            
        Returns:
            List of enriched prospects
        """
        logger.info(f"Discovering {company_type}s by tech need: {tech_need}")
        
        # Find companies using this tech
        github_companies = self.github.find_companies_by_tech_stack(
            tech_stack=[tech_need],
            min_stars=10,
            limit=limit
        )
        
        enriched_prospects = []
        for company in github_companies:
            try:
                # Analyze with Gemini
                if company.get("description"):
                    ai_analysis = self.gemini.analyze_company_description(company["description"])
                    company["ai_analysis"] = ai_analysis
                    
                    # Extract signals
                    signals = self.gemini.extract_signals_from_text(
                        company["description"],
                        ["funding", "hiring", "growth", "expansion"]
                    )
                    company["signals"] = signals
                else:
                    company["ai_analysis"] = None
                    company["signals"] = []
                
                company["prospect_type"] = company_type
                company["discovered_at"] = datetime.utcnow().isoformat()
                company["source"] = "github"
                company["tech_need"] = tech_need
                
                enriched_prospects.append(company)
                
            except Exception as e:
                logger.error(f"Error enriching prospect {company.get('company_name')}: {e}")
                continue
        
        logger.info(f"Discovered {len(enriched_prospects)} {company_type} prospects for {tech_need}")
        return enriched_prospects
    
    def enrich_prospect(self, prospect: Dict) -> Dict:
        """
        Enrich a single prospect with FREE data sources (GitHub, Gemini, NewsAPI)
        
        Args:
            prospect: Prospect data dict
            
        Returns:
            Enriched prospect dict
        """
        logger.info(f"Enriching prospect: {prospect.get('company_name')}")
        
        # GitHub enrichment
        if prospect.get("repository"):
            try:
                owner, repo = prospect["repository"].split("/")
                activity = self.github.get_repository_activity(owner, repo)
                prospect["github_activity"] = activity
                
                tech_stack = self.github.extract_tech_stack_from_repo(owner, repo)
                prospect["tech_stack"] = tech_stack
                
                hiring_signals = self.github.detect_hiring_signals(owner, repo)
                prospect["hiring_signals"] = hiring_signals
            except Exception as e:
                logger.error(f"GitHub enrichment failed: {e}")
        
        # Gemini AI enrichment
        if prospect.get("description"):
            try:
                ai_analysis = self.gemini.analyze_company_description(prospect["description"])
                prospect["ai_analysis"] = ai_analysis
                
                value_signals = self.gemini.extract_value_signals(
                    prospect.get("description", ""),
                    prospect.get("website", "")
                )
                prospect["value_signals"] = value_signals
                
                stage = self.gemini.classify_company_stage(
                    prospect.get("description", ""),
                    prospect.get("employee_count", 100),
                    prospect.get("funding", "$0")
                )
                prospect["stage_classification"] = stage
            except Exception as e:
                logger.error(f"Gemini enrichment failed: {e}")
        
        # NewsAPI enrichment (FREE alternative to Crunchbase)
        if prospect.get("company_name"):
            try:
                from app.integrations.newsapi_enrichment import NewsAPIEnrichmentService
                newsapi_service = NewsAPIEnrichmentService()
                news_articles = newsapi_service.get_company_news(
                    prospect["company_name"],
                    limit=3
                )
                if news_articles:
                    prospect["news_articles"] = news_articles
                    prospect["has_recent_news"] = True
            except Exception as e:
                logger.error(f"NewsAPI enrichment failed: {e}")
        
        prospect["enriched_at"] = datetime.utcnow().isoformat()
        return prospect
    
    def batch_enrich_prospects(self, prospects: List[Dict]) -> List[Dict]:
        """
        Enrich multiple prospects in batch
        
        Args:
            prospects: List of prospect dicts
            
        Returns:
            List of enriched prospect dicts
        """
        logger.info(f"Batch enriching {len(prospects)} prospects")
        
        enriched = []
        for prospect in prospects:
            try:
                enriched_prospect = self.enrich_prospect(prospect)
                enriched.append(enriched_prospect)
            except Exception as e:
                logger.error(f"Error enriching prospect: {e}")
                enriched.append(prospect)  # Keep original if enrichment fails
        
        logger.info(f"Enriched {len(enriched)} prospects")
        return enriched


# Example usage
if __name__ == "__main__":
    service = ProspectDiscoveryService()
    
    # Discover providers
    providers = service.discover_providers(
        tech_stack=["react", "kubernetes"],
        industries=["SaaS", "Fintech"],
        limit=10
    )
    print(f"Found {len(providers)} providers")
    
    # Discover buyers
    buyers = service.discover_buyers(
        industries=["SaaS"],
        funding_stage="series_b",
        limit=10
    )
    print(f"Found {len(buyers)} buyers")
