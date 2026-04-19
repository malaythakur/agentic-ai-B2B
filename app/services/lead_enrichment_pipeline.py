"""
Lead Enrichment Pipeline

Automated pipeline for enriching leads with signals from multiple sources:
- GitHub (tech stack, activity, hiring)
- Crunchbase (funding, investors)
- Gemini AI (company analysis, signal extraction)
- NewsAPI (recent news, press releases)
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from app.integrations.github_enrichment import GitHubEnrichmentService
from app.integrations.gemini_analysis import GeminiAnalysisService
from app.integrations.crunchbase_enrichment import CrunchbaseEnrichmentService

logger = logging.getLogger(__name__)


class LeadEnrichmentPipeline:
    """Automated pipeline for enriching leads with signals"""
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        crunchbase_api_key: Optional[str] = None,
        newsapi_key: Optional[str] = None
    ):
        """
        Initialize lead enrichment pipeline
        
        Args:
            github_token: GitHub API token
            gemini_api_key: Gemini API key
            crunchbase_api_key: Crunchbase API key
            newsapi_key: NewsAPI key
        """
        self.github = GitHubEnrichmentService(github_token)
        self.gemini = GeminiAnalysisService(gemini_api_key)
        self.crunchbase = CrunchbaseEnrichmentService(crunchbase_api_key)
        self.newsapi_key = newsapi_key or None
    
    def enrich_lead(self, lead: Dict) -> Dict:
        """
        Enrich a single lead with all available signals
        
        Args:
            lead: Lead data (company_name, website, etc.)
            
        Returns:
            Enriched lead with all signals
        """
        logger.info(f"Enriching lead: {lead.get('company_name')}")
        
        enriched_lead = lead.copy()
        enriched_lead["enrichment_started_at"] = datetime.utcnow().isoformat()
        
        # Step 1: GitHub enrichment
        if lead.get("repository"):
            try:
                enriched_lead = self._enrich_with_github(enriched_lead)
            except Exception as e:
                logger.error(f"GitHub enrichment failed: {e}")
        
        # Step 2: Crunchbase enrichment
        if lead.get("website") and self.crunchbase.api_key:
            try:
                enriched_lead = self._enrich_with_crunchbase(enriched_lead)
            except Exception as e:
                logger.error(f"Crunchbase enrichment failed: {e}")
        
        # Step 3: Gemini AI enrichment
        if lead.get("description"):
            try:
                enriched_lead = self._enrich_with_gemini(enriched_lead)
            except Exception as e:
                logger.error(f"Gemini enrichment failed: {e}")
        
        # Step 4: NewsAPI enrichment
        if lead.get("company_name") and self.newsapi_key:
            try:
                enriched_lead = self._enrich_with_newsapi(enriched_lead)
            except Exception as e:
                logger.error(f"NewsAPI enrichment failed: {e}")
        
        enriched_lead["enrichment_completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Lead enriched: {lead.get('company_name')}")
        return enriched_lead
    
    def _enrich_with_github(self, lead: Dict) -> Dict:
        """Enrich lead with GitHub data"""
        if not lead.get("repository"):
            # Try to find GitHub repo from website
            if lead.get("website"):
                # Extract potential repo from website
                website = lead["website"].replace("https://", "").replace("http://", "").split("/")[0]
                lead["repository"] = f"{website}/{website}"
        
        if lead.get("repository"):
            try:
                owner, repo = lead["repository"].split("/")
                
                # Get repository activity
                activity = self.github.get_repository_activity(owner, repo, days=30)
                lead["github_activity"] = activity
                
                # Extract tech stack
                tech_stack = self.github.extract_tech_stack_from_repo(owner, repo)
                lead["tech_stack"] = tech_stack
                
                # Detect hiring signals
                hiring_signals = self.github.detect_hiring_signals(owner, repo)
                lead["hiring_signals"] = hiring_signals
                
                # Get repo details
                repo_data = self.github._make_request(f"/repos/{owner}/{repo}")
                if repo_data:
                    lead["github_stars"] = repo_data.get("stargazers_count")
                    lead["github_forks"] = repo_data.get("forks_count")
                    lead["github_updated_at"] = repo_data.get("updated_at")
                
            except Exception as e:
                logger.error(f"GitHub enrichment error: {e}")
        
        return lead
    
    def _enrich_with_crunchbase(self, lead: Dict) -> Dict:
        """Enrich lead with Crunchbase data"""
        if lead.get("website"):
            try:
                domain = lead["website"].replace("https://", "").replace("http://", "").split("/")[0]
                company_data = self.crunchbase.get_company_by_domain(domain)
                
                if company_data:
                    lead["crunchbase_data"] = company_data
                    
                    # Extract funding signals
                    org_id = company_data.get("properties", {}).get("identifier", {}).get("uuid")
                    if org_id:
                        funding_signals = self.crunchbase.extract_funding_signals(org_id)
                        lead["funding_signals"] = funding_signals
                        
                        # Get investors
                        investors = self.crunchbase.get_investors(org_id)
                        lead["investors"] = investors[:10]  # Limit to top 10
                        
                        # Get funding rounds
                        funding_rounds = self.crunchbase.get_funding_rounds(org_id)
                        lead["funding_rounds"] = funding_rounds[:5]  # Limit to top 5
                
            except Exception as e:
                logger.error(f"Crunchbase enrichment error: {e}")
        
        return lead
    
    def _enrich_with_gemini(self, lead: Dict) -> Dict:
        """Enrich lead with Gemini AI analysis"""
        if lead.get("description"):
            try:
                # Analyze company description
                ai_analysis = self.gemini.analyze_company_description(lead["description"])
                lead["ai_analysis"] = ai_analysis
                
                # Extract signals from description
                signals = self.gemini.extract_signals_from_text(
                    lead["description"],
                    ["funding", "hiring", "growth", "expansion", "product_launch"]
                )
                lead["signals"] = signals
                
                # Classify company stage
                employee_count = lead.get("employee_count", 0)
                funding = lead.get("funding", "$0")
                stage = self.gemini.classify_company_stage(
                    lead["description"],
                    employee_count,
                    funding
                )
                lead["stage_classification"] = stage
                
                # Extract value signals
                value_signals = self.gemini.extract_value_signals(
                    lead["description"],
                    lead.get("website", "")
                )
                lead["value_signals"] = value_signals
                
            except Exception as e:
                logger.error(f"Gemini enrichment error: {e}")
        
        return lead
    
    def _enrich_with_newsapi(self, lead: Dict) -> Dict:
        """Enrich lead with recent news from NewsAPI"""
        if not self.newsapi_key:
            return lead
        
        import requests
        
        try:
            url = f"https://newsapi.org/v2/everything"
            params = {
                "q": lead["company_name"],
                "apiKey": self.newsapi_key,
                "sortBy": "publishedAt",
                "pageSize": 10,
                "language": "en"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("articles"):
                # Filter for recent news (last 30 days)
                thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                recent_articles = []
                
                for article in data["articles"][:20]:
                    try:
                        published_at = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
                        if published_at > thirty_days_ago:
                            recent_articles.append({
                                "title": article["title"],
                                "description": article["description"],
                                "url": article["url"],
                                "published_at": article["publishedAt"],
                                "source": article["source"]["name"]
                            })
                    except:
                        continue
                
                lead["recent_news"] = recent_articles[:5]  # Limit to 5 recent articles
                
                # Extract signals from news
                news_signals = self._extract_signals_from_news(recent_articles)
                lead["news_signals"] = news_signals
                
        except Exception as e:
            logger.error(f"NewsAPI enrichment error: {e}")
        
        return lead
    
    def _extract_signals_from_news(self, articles: List[Dict]) -> List[Dict]:
        """Extract signals from news articles"""
        signals = []
        
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}".lower()
            
            # Funding signals
            if "funding" in text or "raised" in text or "investment" in text:
                signals.append({
                    "type": "funding",
                    "source": "news",
                    "title": article["title"],
                    "url": article["url"],
                    "confidence": 0.7
                })
            
            # Hiring signals
            if "hiring" in text or "job" in text or "recruit" in text:
                signals.append({
                    "type": "hiring",
                    "source": "news",
                    "title": article["title"],
                    "url": article["url"],
                    "confidence": 0.6
                })
            
            # Growth signals
            if "growth" in text or "expansion" in text or "launch" in text:
                signals.append({
                    "type": "growth",
                    "source": "news",
                    "title": article["title"],
                    "url": article["url"],
                    "confidence": 0.6
                })
        
        return signals
    
    def batch_enrich_leads(self, leads: List[Dict]) -> List[Dict]:
        """
        Enrich multiple leads in batch
        
        Args:
            leads: List of lead dicts
            
        Returns:
            List of enriched lead dicts
        """
        logger.info(f"Batch enriching {len(leads)} leads")
        
        enriched_leads = []
        for lead in leads:
            try:
                enriched_lead = self.enrich_lead(lead)
                enriched_leads.append(enriched_lead)
            except Exception as e:
                logger.error(f"Error enriching lead {lead.get('company_name')}: {e}")
                enriched_leads.append(lead)  # Keep original if enrichment fails
        
        logger.info(f"Batch enrichment completed: {len(enriched_leads)} leads")
        return enriched_leads
    
    def get_enrichment_summary(self, lead: Dict) -> Dict:
        """
        Get summary of enrichment data for a lead
        
        Args:
            lead: Enriched lead data
            
        Returns:
            Summary dict
        """
        return {
            "company_name": lead.get("company_name"),
            "enrichment_sources": [
                "github" if lead.get("github_activity") else None,
                "crunchbase" if lead.get("funding_signals") else None,
                "gemini" if lead.get("ai_analysis") else None,
                "newsapi" if lead.get("recent_news") else None
            ],
            "tech_stack": lead.get("tech_stack", []),
            "funding": lead.get("funding_signals", {}),
            "hiring_signals": len(lead.get("hiring_signals", [])),
            "recent_news": len(lead.get("recent_news", [])),
            "stage": lead.get("stage_classification", {}).get("stage"),
            "enrichment_completed": lead.get("enrichment_completed_at")
        }


# Example usage
if __name__ == "__main__":
    pipeline = LeadEnrichmentPipeline()
    
    # Example lead
    lead = {
        "company_name": "TechStartup",
        "website": "https://techstartup.com",
        "description": "AI-powered customer service platform for e-commerce",
        "repository": "techstartup/techstartup"
    }
    
    enriched = pipeline.enrich_lead(lead)
    summary = pipeline.get_enrichment_summary(enriched)
    
    print(f"Enrichment summary for {summary['company_name']}:")
    print(f"  Sources: {[s for s in summary['enrichment_sources'] if s]}")
    print(f"  Tech stack: {summary['tech_stack']}")
    print(f"  Funding: ${summary['funding'].get('total_funding', 0):,}")
    print(f"  Hiring signals: {summary['hiring_signals']}")
    print(f"  Recent news: {summary['recent_news']}")
    print(f"  Stage: {summary['stage']}")
