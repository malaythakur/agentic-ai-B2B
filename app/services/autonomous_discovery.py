"""
Autonomous Lead Discovery Engine
Zero-touch lead generation using free data sources and Gemini AI
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Lead, LeadScore, Event
from app.logging_config import logger as app_logger
from app.services.free_data_scrapers import (
    GitHubScraper,
    NewsAPIScraper,
    ProductHuntScraper,
    HackerNewsScraper,
    JobBoardScraper,
    RawLead
)
from app.services.gemini_enrichment import GeminiEnrichmentService, EnrichedLead

logger = app_logger


class AutonomousDiscoveryEngine:
    """
    Fully autonomous lead discovery engine
    
    Billion-dollar thinking: 
    - Discovers leads from multiple free sources
    - Enriches with AI (Gemini)
    - Auto-qualifies with intelligent scoring
    - Self-improves based on conversion data
    - Runs 24/7 with zero human intervention
    """
    
    def __init__(
        self,
        db: Session,
        gemini_api_key: str,
        newsapi_key: Optional[str] = None
    ):
        self.db = db
        self.gemini = GeminiEnrichmentService(gemini_api_key)
        
        # Initialize scrapers
        self.github = GitHubScraper()
        self.newsapi = NewsAPIScraper(newsapi_key) if newsapi_key else None
        self.producthunt = ProductHuntScraper()
        self.hackernews = HackerNewsScraper()
        self.jobboards = JobBoardScraper()
        
        # Discovery configuration
        self.min_priority_score = 50  # Only ingest qualified leads
        self.target_tech_stacks = [
            "Python", "React", "Node.js", "Go", "Rust",
            "AI", "Machine Learning", "SaaS", "API"
        ]
        self.target_roles = [
            "SDR", "Sales Manager", "VP Sales", "Growth",
            "Business Development", "Sales Engineer"
        ]
    
    async def run_discovery_cycle(self) -> Dict:
        """
        Run one full discovery cycle
        
        This is the main entry point - discovers, enriches, and ingests leads
        """
        logger.info("=== Starting Autonomous Discovery Cycle ===")
        
        results = {
            "cycle_start": datetime.utcnow().isoformat(),
            "sources": {},
            "discovered": 0,
            "enriched": 0,
            "qualified": 0,
            "ingested": 0,
            "leads": []
        }
        
        # Phase 1: Discover raw leads from all sources
        logger.info("Phase 1: Discovering raw leads from free sources...")
        raw_leads = await self._discover_raw_leads()
        results["discovered"] = len(raw_leads)
        
        # Phase 2: Deduplicate
        logger.info("Phase 2: Deduplicating leads...")
        unique_leads = self._deduplicate_leads(raw_leads)
        
        # Phase 3: Enrich with Gemini AI
        logger.info("Phase 3: Enriching leads with Gemini AI...")
        enriched_leads = await self._enrich_leads(unique_leads)
        results["enriched"] = len(enriched_leads)
        
        # Phase 4: Auto-qualify (AI-powered filtering)
        logger.info("Phase 4: Auto-qualifying leads...")
        qualified_leads = self._auto_qualify(enriched_leads)
        results["qualified"] = len(qualified_leads)
        
        # Phase 5: Ingest qualified leads
        logger.info("Phase 5: Ingesting qualified leads...")
        ingested = await self._ingest_qualified_leads(qualified_leads)
        results["ingested"] = ingested
        results["leads"] = [l.company for l in qualified_leads]
        
        results["cycle_end"] = datetime.utcnow().isoformat()
        
        logger.info(f"=== Discovery Complete: {ingested} new qualified leads ===")
        
        return results
    
    async def _discover_raw_leads(self) -> List[RawLead]:
        """Discover leads from all free sources in parallel"""
        
        tasks = []
        
        # GitHub - tech companies with recent activity
        tasks.append(self._safe_scrape(
            self.github.find_hiring_companies(
                tech_stack=self.target_tech_stacks,
                max_results=30
            ),
            "github"
        ))
        
        # NewsAPI - funding announcements (if API key available)
        if self.newsapi:
            tasks.append(self._safe_scrape(
                self.newsapi.find_funding_announcements(
                    days_back=7,
                    max_results=20
                ),
                "newsapi"
            ))
            tasks.append(self._safe_scrape(
                self.newsapi.find_hiring_announcements(
                    days_back=7,
                    max_results=15
                ),
                "newsapi_hiring"
            ))
        
        # Product Hunt - new launches
        tasks.append(self._safe_scrape(
            self.producthunt.find_recent_launches(max_results=20),
            "producthunt"
        ))
        
        # Hacker News - hiring posts
        tasks.append(self._safe_scrape(
            self.hackernews.find_hiring_posts(max_results=25),
            "hackernews"
        ))
        
        # Job boards - companies hiring sales roles
        tasks.append(self._safe_scrape(
            self.jobboards.find_companies_hiring(
                roles=self.target_roles,
                max_results=30
            ),
            "jobboards"
        ))
        
        # Run all scrapers concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all leads
        all_leads = []
        for result in results:
            if isinstance(result, list):
                all_leads.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Scraper error: {result}")
        
        logger.info(f"Discovered {len(all_leads)} raw leads from all sources")
        return all_leads
    
    async def _safe_scrape(self, coro, source_name: str) -> List[RawLead]:
        """Wrapper to handle scraper exceptions"""
        try:
            result = await coro
            logger.info(f"Scraped {len(result)} leads from {source_name}")
            return result
        except Exception as e:
            logger.error(f"Error scraping {source_name}: {e}")
            return []
    
    def _deduplicate_leads(self, leads: List[RawLead]) -> List[RawLead]:
        """Remove duplicate leads and already-existing companies"""
        
        # Remove duplicates by company name (case-insensitive)
        seen = set()
        unique = []
        
        for lead in leads:
            company_key = lead.company.lower().strip()
            
            # Skip if already seen in this batch
            if company_key in seen:
                continue
            seen.add(company_key)
            
            # Skip if already in database
            existing = self.db.query(Lead).filter(
                Lead.company.ilike(lead.company)
            ).first()
            
            if existing:
                logger.debug(f"Skipping {lead.company} - already in database")
                continue
            
            unique.append(lead)
        
        logger.info(f"Deduplicated: {len(leads)} → {len(unique)} unique leads")
        return unique
    
    async def _enrich_leads(self, raw_leads: List[RawLead]) -> List[EnrichedLead]:
        """Enrich leads with Gemini AI"""
        
        enriched = []
        
        for raw_lead in raw_leads:
            try:
                # Enrich with Gemini
                enriched_lead = await self.gemini.enrich_company(
                    company_name=raw_lead.company,
                    known_signal=raw_lead.signal
                )
                
                # Merge raw data with enriched data
                if raw_lead.website and not enriched_lead.website:
                    enriched_lead.website = raw_lead.website
                
                enriched.append(enriched_lead)
                
                # Small delay to respect rate limits
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error enriching {raw_lead.company}: {e}")
                continue
        
        return enriched
    
    def _auto_qualify(self, enriched_leads: List[EnrichedLead]) -> List[EnrichedLead]:
        """
        AI-powered lead qualification
        
        Qualification criteria:
        - Priority score >= 50 (calculated by Gemini)
        - Must have valid company name
        - Should have some signals or recent news
        """
        qualified = []
        
        for lead in enriched_leads:
            # Skip low-quality leads
            if lead.priority_score < self.min_priority_score:
                logger.debug(f"Skipping {lead.company} - score {lead.priority_score} < {self.min_priority_score}")
                continue
            
            # Skip if no meaningful data
            if not lead.signals or lead.signals == ["Research needed"]:
                logger.debug(f"Skipping {lead.company} - insufficient data")
                continue
            
            # Skip if already contacted (check more thoroughly)
            existing = self.db.query(Lead).filter(
                Lead.company.ilike(lead.company)
            ).first()
            
            if existing:
                # Check suppression list
                if existing.status in ["suppressed", "lost", "unsubscribe"]:
                    logger.debug(f"Skipping {lead.company} - suppressed status")
                    continue
            
            qualified.append(lead)
            logger.info(f"Qualified: {lead.company} (score: {lead.priority_score})")
        
        # Sort by priority score (highest first)
        qualified.sort(key=lambda x: x.priority_score, reverse=True)
        
        logger.info(f"Qualified: {len(enriched_leads)} → {len(qualified)} leads")
        return qualified
    
    async def _ingest_qualified_leads(self, qualified_leads: List[EnrichedLead]) -> int:
        """Ingest qualified leads into the database"""
        
        ingested = 0
        
        for lead in qualified_leads:
            try:
                # Generate lead ID
                lead_id = f"auto-{lead.company.lower().replace(' ', '-').replace('.', '')[:30]}"
                
                # Create lead record
                db_lead = Lead(
                    lead_id=lead_id,
                    company=lead.company,
                    website=lead.website,
                    signal=" | ".join(lead.signals[:3]) if lead.signals else lead.qualification_reason,
                    decision_maker=lead.decision_makers[0]["name"] if lead.decision_makers else None,
                    fit_score=min(lead.priority_score, 10),  # Scale to 0-10
                    status="new",
                    created_at=datetime.utcnow()
                )
                
                self.db.add(db_lead)
                
                # Create lead score record
                lead_score = LeadScore(
                    lead_id=lead_id,
                    signal_strength=min(len(lead.signals) * 20, 100),
                    hiring_intensity=80 if any("hiring" in s.lower() for s in lead.signals) else 50,
                    funding_stage=self._map_funding_stage(lead.funding_stage),
                    company_size_fit=self._calculate_size_fit(lead.employees),
                    market_relevance=lead.priority_score,
                    priority_score=lead.priority_score,
                    is_qualified=True,
                    created_at=datetime.utcnow()
                )
                self.db.add(lead_score)
                
                # Log discovery event
                event = Event(
                    event_id=f"discovery-{lead_id}-{datetime.utcnow().timestamp()}",
                    event_type="autonomous_discovery",
                    entity_type="lead",
                    entity_id=lead_id,
                    data={
                        "source": "autonomous_discovery_engine",
                        "priority_score": lead.priority_score,
                        "signals": lead.signals,
                        "pain_points": lead.pain_points,
                        "tech_stack": lead.tech_stack,
                        "discovery_reason": lead.qualification_reason
                    }
                )
                self.db.add(event)
                
                ingested += 1
                logger.info(f"Ingested: {lead.company} (ID: {lead_id})")
                
            except Exception as e:
                logger.error(f"Error ingesting {lead.company}: {e}")
                continue
        
        # Commit all changes
        self.db.commit()
        return ingested
    
    def _map_funding_stage(self, funding_stage: Optional[str]) -> int:
        """Map funding stage to score"""
        if not funding_stage:
            return 50
        
        stage_lower = funding_stage.lower()
        if "series c" in stage_lower or "series d" in stage_lower or "ipo" in stage_lower:
            return 95
        elif "series b" in stage_lower:
            return 80
        elif "series a" in stage_lower:
            return 65
        elif "seed" in stage_lower:
            return 40
        else:
            return 50
    
    def _calculate_size_fit(self, employees: Optional[int]) -> int:
        """Calculate company size fit score"""
        if not employees:
            return 50
        
        if 50 <= employees <= 500:
            return 100
        elif 20 <= employees < 50:
            return 80
        elif 500 < employees <= 1000:
            return 70
        elif employees > 1000:
            return 60
        else:
            return 40
    
    async def close(self):
        """Close all connections"""
        await self.github.close()
        if self.newsapi:
            await self.newsapi.close()
        await self.producthunt.close()
        await self.hackernews.close()
        await self.jobboards.close()
        await self.gemini.close()
    
    # Self-improvement methods
    def get_discovery_analytics(self) -> Dict:
        """Get analytics on discovery performance for optimization"""
        
        # Get recent discoveries
        recent_discoveries = self.db.query(Event).filter(
            Event.event_type == "autonomous_discovery"
        ).order_by(Event.created_at.desc()).limit(100).all()
        
        # Calculate source performance
        source_stats = {}
        for event in recent_discoveries:
            source = event.data.get("source", "unknown")
            priority = event.data.get("priority_score", 0)
            
            if source not in source_stats:
                source_stats[source] = {"count": 0, "avg_score": 0, "total_score": 0}
            
            source_stats[source]["count"] += 1
            source_stats[source]["total_score"] += priority
            source_stats[source]["avg_score"] = source_stats[source]["total_score"] / source_stats[source]["count"]
        
        return {
            "total_discovered_24h": len(recent_discoveries),
            "source_performance": source_stats,
            "recommendations": self._generate_recommendations(source_stats)
        }
    
    def _generate_recommendations(self, source_stats: Dict) -> List[str]:
        """Generate recommendations based on source performance"""
        recommendations = []
        
        # Find best performing sources
        if source_stats:
            best_source = max(source_stats.items(), key=lambda x: x[1]["avg_score"])
            recommendations.append(f"Focus on {best_source[0]} - highest avg score ({best_source[1]['avg_score']:.1f})")
        
        # Check if we need more sources
        total_discovered = sum(s["count"] for s in source_stats.values())
        if total_discovered < 10:
            recommendations.append("Low discovery volume - consider adding more data sources")
        
        return recommendations


class ContinuousDiscoveryManager:
    """
    Manages continuous discovery in background
    Runs discovery cycles at scheduled intervals
    """
    
    def __init__(
        self,
        db: Session,
        gemini_api_key: str,
        newsapi_key: Optional[str] = None,
        cycle_interval_hours: int = 6
    ):
        self.db = db
        self.gemini_api_key = gemini_api_key
        self.newsapi_key = newsapi_key
        self.cycle_interval = cycle_interval_hours
        self.running = False
    
    async def run_continuous_discovery(self):
        """Run discovery continuously with specified interval"""
        self.running = True
        
        logger.info(f"=== Starting Continuous Discovery (interval: {self.cycle_interval}h) ===")
        
        while self.running:
            try:
                # Create engine instance for this cycle
                engine = AutonomousDiscoveryEngine(
                    db=self.db,
                    gemini_api_key=self.gemini_api_key,
                    newsapi_key=self.newsapi_key
                )
                
                # Run discovery cycle
                results = await engine.run_discovery_cycle()
                
                # Log results
                logger.info(f"Discovery cycle complete: {results['ingested']} leads ingested")
                
                # Close connections
                await engine.close()
                
                # Wait for next cycle
                if self.running:
                    wait_seconds = self.cycle_interval * 3600
                    logger.info(f"Waiting {self.cycle_interval} hours until next cycle...")
                    await asyncio.sleep(wait_seconds)
                    
            except Exception as e:
                logger.error(f"Error in continuous discovery: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    def stop(self):
        """Stop continuous discovery"""
        self.running = False
        logger.info("Continuous discovery stopped")
