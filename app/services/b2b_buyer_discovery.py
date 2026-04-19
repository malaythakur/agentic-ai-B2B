"""
B2B Buyer Discovery Service

Integrates autonomous discovery with B2B Matchmaking Platform:
- Discovers buyers from free data sources (GitHub, NewsAPI, Hacker News, Product Hunt, Job Boards)
- Enriches buyer data with Gemini AI
- Auto-creates BuyerCompany records
- Matches buyers to providers automatically
- All using FREE APIs only (no paid services)
"""

import asyncio
import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import BuyerCompany, ServiceProvider, Match, Event
from app.services.free_data_scrapers import (
    GitHubScraper,
    NewsAPIScraper,
    ProductHuntScraper,
    HackerNewsScraper,
    JobBoardScraper,
    RawLead
)
from app.services.gemini_enrichment import GeminiEnrichmentService
from app.services.matchmaking_engine import MatchmakingEngine
from app.logging_config import logger as app_logger

logger = app_logger


class B2BBuyerDiscoveryService:
    """
    Autonomous buyer discovery for B2B Matchmaking Platform
    
    Features:
    - Discovers potential buyers from 6+ free data sources
    - AI enrichment with Gemini (60 req/min FREE tier)
    - Auto-creates BuyerCompany records
    - Auto-matches to existing providers
    - Zero-cost operation (all free APIs)
    """
    
    def __init__(
        self,
        db: Session,
        gemini_api_key: str,
        newsapi_key: Optional[str] = None
    ):
        self.db = db
        self.gemini = GeminiEnrichmentService(gemini_api_key)
        self.matchmaking_engine = MatchmakingEngine(db)
        
        # Initialize scrapers (all FREE APIs)
        self.github = GitHubScraper()
        self.newsapi = NewsAPIScraper(newsapi_key) if newsapi_key else None
        self.producthunt = ProductHuntScraper()
        self.hackernews = HackerNewsScraper()
        self.jobboards = JobBoardScraper()
        
        # Discovery criteria
        self.min_priority_score = 60  # For B2B buyers
        self.target_industries = ["SaaS", "Fintech", "E-commerce", "AI", "Enterprise Software"]
        
    async def run_buyer_discovery(self) -> Dict:
        """
        Run full buyer discovery cycle
        
        Discovers, enriches, and auto-matches buyers to providers
        """
        logger.info("=== Starting B2B Buyer Discovery Cycle ===")
        
        results = {
            "cycle_start": datetime.utcnow().isoformat(),
            "sources": {},
            "discovered": 0,
            "enriched": 0,
            "qualified": 0,
            "created": 0,
            "matched": 0,
            "buyers": []
        }
        
        # Phase 1: Discover raw leads from free sources
        logger.info("Phase 1: Discovering potential buyers from free sources...")
        raw_leads = await self._discover_raw_buyers()
        results["discovered"] = len(raw_leads)
        
        # Phase 2: Deduplicate
        logger.info("Phase 2: Deduplicating buyers...")
        unique_leads = self._deduplicate_buyers(raw_leads)
        
        # Phase 3: Enrich with Gemini AI
        logger.info("Phase 3: Enriching buyers with Gemini AI...")
        enriched_buyers = await self._enrich_buyers(unique_leads)
        results["enriched"] = len(enriched_buyers)
        
        # Phase 4: Auto-qualify (use raw leads if no enrichment)
        logger.info("Phase 4: Auto-qualifying buyers...")
        buyers_to_process = enriched_buyers if enriched_buyers else [
            {"raw_lead": lead, "enriched_data": {}, "priority_score": 50} 
            for lead in unique_leads[:10]  # Limit to first 10 if no enrichment
        ]
        qualified_buyers = self._auto_qualify_buyers(buyers_to_process)
        results["qualified"] = len(qualified_buyers)
        
        # Phase 5: Create BuyerCompany records
        logger.info("Phase 5: Creating buyer records...")
        created_buyers = self._create_buyer_companies(qualified_buyers if qualified_buyers else buyers_to_process)
        results["created"] = len(created_buyers)
        results["buyers"] = [b["company_name"] for b in created_buyers]
        
        # Phase 6: Auto-match to providers
        logger.info("Phase 6: Auto-matching buyers to providers...")
        matches_created = await self._auto_match_to_providers(created_buyers)
        results["matched"] = matches_created
        
        # Log event
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type="b2b_buyer_discovery",
            entity_type="discovery_cycle",
            entity_id=str(uuid.uuid4()),
            data={
                "discovered": results["discovered"],
                "created": results["created"],
                "matched": results["matched"]
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"=== B2B Buyer Discovery Complete ===")
        logger.info(f"Discovered: {results['discovered']}, Created: {results['created']}, Matched: {results['matched']}")
        
        return results
    
    async def _discover_raw_buyers(self) -> List[RawLead]:
        """Discover raw leads from all free data sources"""
        all_leads = []
        
        # GitHub - Tech companies with recent activity (FREE: 60 req/hr)
        try:
            logger.info("  - Scraping GitHub...")
            github_leads = await self.github.find_hiring_companies(
                tech_stack=["Python", "React", "AI", "SaaS"],
                min_stars=50,
                max_results=50
            )
            logger.info(f"    Found {len(github_leads)} companies from GitHub")
            all_leads.extend(github_leads)
        except Exception as e:
            logger.error(f"GitHub scraping failed: {e}")
        
        # NewsAPI - Funding & hiring announcements (FREE: 100 req/day)
        if self.newsapi:
            try:
                logger.info("  - Scraping NewsAPI...")
                news_leads = await self.newsapi.find_funding_announcements(
                    days_back=7,
                    max_results=50
                )
                logger.info(f"    Found {len(news_leads)} companies from NewsAPI")
                all_leads.extend(news_leads)
            except Exception as e:
                logger.error(f"NewsAPI scraping failed: {e}")
        
        # Hacker News - "Who is Hiring" posts (FREE: unlimited)
        try:
            logger.info("  - Scraping Hacker News...")
            hn_leads = await self.hackernews.find_hiring_posts(
                max_results=30
            )
            logger.info(f"    Found {len(hn_leads)} companies from Hacker News")
            all_leads.extend(hn_leads)
        except Exception as e:
            logger.error(f"Hacker News scraping failed: {e}")
        
        # Product Hunt - New product launches (FREE: unlimited)
        try:
            logger.info("  - Scraping Product Hunt...")
            ph_leads = await self.producthunt.find_recent_launches(
                max_results=30
            )
            logger.info(f"    Found {len(ph_leads)} companies from Product Hunt")
            all_leads.extend(ph_leads)
        except Exception as e:
            logger.error(f"Product Hunt scraping failed: {e}")
        
        # Job Boards - Companies hiring target roles (FREE: unlimited)
        try:
            logger.info("  - Scraping Job Boards...")
            job_leads = await self.jobboards.find_companies_hiring(
                roles=["DevOps Engineer", "SRE", "Cloud Architect", "Engineering Manager"],
                max_results=40
            )
            logger.info(f"    Found {len(job_leads)} companies from Job Boards")
            all_leads.extend(job_leads)
        except Exception as e:
            logger.error(f"Job board scraping failed: {e}")
        
        logger.info(f"Total raw leads discovered: {len(all_leads)}")
        return all_leads
    
    def _deduplicate_buyers(self, leads: List[RawLead]) -> List[RawLead]:
        """Deduplicate leads by company name/domain"""
        seen_domains = set()
        unique_leads = []
        
        # Also check existing buyers in database
        existing_buyers = self.db.query(BuyerCompany).all()
        existing_domains = {b.website.lower() if b.website else "" for b in existing_buyers}
        
        for lead in leads:
            domain = lead.website.lower() if lead.website else lead.company.lower().replace(" ", "")
            
            if domain not in seen_domains and domain not in existing_domains:
                seen_domains.add(domain)
                unique_leads.append(lead)
        
        logger.info(f"Unique buyers after deduplication: {len(unique_leads)}")
        return unique_leads
    
    async def _enrich_buyers(self, leads: List[RawLead]) -> List[Dict]:
        """Enrich buyers with Gemini AI (FREE: 60 req/min)"""
        enriched = []
        
        for lead in leads:
            try:
                # Use Gemini to research company
                enriched_lead = await self.gemini.enrich_company(
                    company_name=lead.company,
                    known_signal=lead.signal
                )
                
                if enriched_lead:
                    enriched.append({
                        "raw_lead": lead,
                        "enriched_data": {
                            "industry": enriched_lead.industry,
                            "employees": enriched_lead.employees,
                            "decision_makers": [{"name": enriched_lead.decision_maker_name, "title": enriched_lead.decision_maker_title, "email": enriched_lead.decision_maker_email}],
                            "recent_news": enriched_lead.recent_news,
                            "pain_points": enriched_lead.pain_points,
                            "outreach_angle": enriched_lead.qualification_reason
                        },
                        "priority_score": enriched_lead.priority_score
                    })
                    
                    # Rate limiting for free tier (Gemini: 60 req/min)
                    await asyncio.sleep(2)  # 30 req/min to stay well under limit
                    
            except Exception as e:
                logger.error(f"Failed to enrich {lead.company}: {e}")
                continue
        
        logger.info(f"Successfully enriched {len(enriched)} buyers")
        return enriched
    
    def _auto_qualify_buyers(self, enriched_buyers: List[Dict]) -> List[Dict]:
        """Auto-qualify buyers based on priority score and criteria"""
        qualified = []
        
        for buyer in enriched_buyers:
            score = buyer.get("priority_score", 0)
            enriched_data = buyer.get("enriched_data", {})
            
            # Qualification criteria:
            # - Priority score >= 60 (for B2B)
            # - Has decision maker
            # - Has signals
            # - Company size 20-1000 employees
            
            if score >= self.min_priority_score:
                has_decision_maker = bool(enriched_data.get("decision_makers"))
                has_signals = bool(enriched_data.get("recent_news"))
                employees = enriched_data.get("employees", 0)
                size_fit = 20 <= employees <= 1000 if employees else True
                
                if has_decision_maker and has_signals and size_fit:
                    qualified.append(buyer)
        
        # Sort by priority score (highest first)
        qualified.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        logger.info(f"Qualified buyers: {len(qualified)}")
        return qualified
    
    def _create_buyer_companies(self, qualified_buyers: List[Dict]) -> List[Dict]:
        """Create BuyerCompany records in database"""
        created = []
        
        for buyer_data in qualified_buyers:
            try:
                raw_lead = buyer_data["raw_lead"]
                enriched = buyer_data["enriched_data"]
                
                # Check if buyer already exists
                existing = self.db.query(BuyerCompany).filter(
                    BuyerCompany.company_name.ilike(raw_lead.company)
                ).first()
                
                if existing:
                    logger.info(f"Buyer already exists: {raw_lead.company}")
                    continue
                
                # Get decision maker info
                decision_makers = enriched.get("decision_makers", [])
                primary_dm = decision_makers[0] if decision_makers else {}
                
                # Create buyer record
                buyer = BuyerCompany(
                    buyer_id=f"buyer-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{len(created)}",
                    company_name=raw_lead.company,
                    website=raw_lead.website,
                    industry=enriched.get("industry", "Technology"),
                    employee_count=enriched.get("employees", 0),
                    funding_stage=enriched.get("funding", {}).get("stage", "unknown"),
                    decision_maker_name=primary_dm.get("name", "Decision Maker"),
                    decision_maker_title=primary_dm.get("title", "Manager"),
                    decision_maker_email=primary_dm.get("email", f"contact@{raw_lead.website.replace('https://', '').replace('http://', '').split('/')[0] if raw_lead.website else 'example.com'}"),
                    signals=[raw_lead.signal] if raw_lead.signal else [],
                    requirements=enriched.get("pain_points", []),
                    active=True
                )
                
                self.db.add(buyer)
                created.append({
                    "buyer_id": buyer.buyer_id,
                    "company_name": buyer.company_name
                })
                
                logger.info(f"Created buyer: {buyer.company_name}")
                
            except Exception as e:
                logger.error(f"Failed to create buyer {raw_lead.company}: {e}")
                continue
        
        self.db.commit()
        logger.info(f"Created {len(created)} BuyerCompany records")
        return created
    
    async def _auto_match_to_providers(self, created_buyers: List[Dict]) -> int:
        """Auto-match newly created buyers to existing providers"""
        matches_created = 0
        
        # Get all active providers
        providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True,
            ServiceProvider.auto_outreach_enabled == True
        ).all()
        
        if not providers:
            logger.info("No active providers found for auto-matching")
            return 0
        
        for buyer_data in created_buyers:
            buyer = self.db.query(BuyerCompany).filter(
                BuyerCompany.buyer_id == buyer_data["buyer_id"]
            ).first()
            
            if not buyer:
                continue
            
            for provider in providers:
                try:
                    # Check if buyer matches provider's ICP
                    match_score = self._calculate_icp_match_score(buyer, provider)
                    
                    if match_score >= 70:  # Auto-approve threshold
                        # Create match
                        match_id = f"match-{provider.provider_id}-{buyer.buyer_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                        
                        existing_match = self.db.query(Match).filter(
                            Match.provider_id == provider.provider_id,
                            Match.buyer_id == buyer.buyer_id
                        ).first()
                        
                        if not existing_match:
                            from app.models import Match
                            match = Match(
                                match_id=match_id,
                                provider_id=provider.provider_id,
                                buyer_id=buyer.buyer_id,
                                match_score=match_score,
                                status="auto_approved",
                                provider_approved=True,
                                created_at=datetime.utcnow()
                            )
                            self.db.add(match)
                            matches_created += 1
                            
                            logger.info(f"Auto-matched: {buyer.company_name} -> {provider.company_name} (Score: {match_score})")
                            
                except Exception as e:
                    logger.error(f"Failed to match buyer {buyer.buyer_id} to provider {provider.provider_id}: {e}")
                    continue
        
        self.db.commit()
        logger.info(f"Auto-created {matches_created} matches")
        return matches_created
    
    def _calculate_icp_match_score(self, buyer: BuyerCompany, provider: ServiceProvider) -> int:
        """Calculate how well buyer matches provider's ICP"""
        icp = provider.icp_criteria or {}
        score = 0
        
        # Industry match (25%)
        target_industries = icp.get("industries", [])
        if target_industries and buyer.industry in target_industries:
            score += 25
        
        # Funding stage match (20%)
        target_stage = icp.get("funding_stage", "")
        if target_stage and buyer.funding_stage:
            if target_stage.lower() in buyer.funding_stage.lower():
                score += 20
        
        # Employee size match (15%)
        target_size = icp.get("employees", "")
        if target_size and buyer.employee_count:
            if "50-500" in target_size and 50 <= buyer.employee_count <= 500:
                score += 15
            elif "500+" in target_size and buyer.employee_count >= 500:
                score += 15
        
        # Signals match (25%)
        target_signals = icp.get("signals", [])
        if target_signals and buyer.signals:
            buyer_signals = buyer.signals if isinstance(buyer.signals, list) else []
            for signal in target_signals:
                if signal in buyer_signals:
                    score += 25
                    break
        
        # Requirements match (15%)
        if buyer.requirements and provider.services_offered:
            buyer_needs = set(buyer.requirements if isinstance(buyer.requirements, list) else [])
            provider_services = set(provider.services_offered if isinstance(provider.services_offered, list) else [])
            if buyer_needs & provider_services:  # Intersection
                score += 15
        
        return min(score, 100)
    
    def get_discovery_stats(self) -> Dict:
        """Get discovery statistics"""
        total_buyers = self.db.query(BuyerCompany).count()
        new_today = self.db.query(BuyerCompany).filter(
            BuyerCompany.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        by_source = {}
        for source in ["github", "newsapi", "hackernews", "producthunt", "jobboards"]:
            count = self.db.query(BuyerCompany).filter(
                BuyerCompany.discovery_source == source
            ).count()
            if count > 0:
                by_source[source] = count
        
        return {
            "total_buyers": total_buyers,
            "new_today": new_today,
            "by_source": by_source,
            "high_priority": self.db.query(BuyerCompany).filter(BuyerCompany.priority_score >= 80).count()
        }


class ContinuousB2BBuyerDiscovery:
    """
    Continuous buyer discovery manager
    
    Runs discovery cycles automatically every 6 hours
    """
    
    def __init__(
        self,
        db: Session,
        gemini_api_key: str,
        newsapi_key: Optional[str] = None,
        cycle_interval_hours: int = 6
    ):
        self.db = db
        self.discovery_service = B2BBuyerDiscoveryService(db, gemini_api_key, newsapi_key)
        self.cycle_interval = cycle_interval_hours
        self.running = False
    
    async def start_continuous_discovery(self):
        """Start continuous discovery loop"""
        self.running = True
        logger.info(f"Starting continuous B2B buyer discovery (interval: {self.cycle_interval}h)")
        
        while self.running:
            try:
                results = await self.discovery_service.run_buyer_discovery()
                logger.info(f"Discovery cycle complete: {results}")
                
                # Wait for next cycle
                await asyncio.sleep(self.cycle_interval * 3600)
                
            except Exception as e:
                logger.error(f"Discovery cycle failed: {e}")
                await asyncio.sleep(300)  # Wait 5 min on error
    
    def stop(self):
        """Stop continuous discovery"""
        self.running = False
        logger.info("Stopping continuous B2B buyer discovery")


# Celery task for scheduled discovery
from celery import shared_task

@shared_task
def run_b2b_buyer_discovery_task():
    """
    Celery task to run B2B buyer discovery
    
    Runs every 6 hours via Celery Beat schedule
    """
    from app.database import SessionLocal
    from app.settings import settings
    
    db = SessionLocal()
    try:
        service = B2BBuyerDiscoveryService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY,
            newsapi_key=getattr(settings, 'NEWSAPI_KEY', None)
        )
        
        # Run async discovery
        results = asyncio.run(service.run_buyer_discovery())
        
        return {
            "status": "success",
            "discovered": results["discovered"],
            "created": results["created"],
            "matched": results["matched"]
        }
        
    except Exception as e:
        logger.error(f"B2B buyer discovery task failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
