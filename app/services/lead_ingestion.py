"""Automated Lead Ingestion Service with External API Integrations"""
import httpx
import json
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import Lead, Event, LeadScore
from app.logging_config import logger as app_logger

logger = app_logger


class LeadIngestionService:
    """Service for automated lead ingestion from external sources"""
    
    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def ingest_from_crunchbase(
        self, 
        query: str,
        funding_stage: Optional[str] = None,
        industry: Optional[str] = None,
        limit: int = 100
    ) -> Dict:
        """Ingest leads from Crunchbase API"""
        # Note: Replace with actual Crunchbase API integration
        # This is a template structure
        
        results = {
            "source": "crunchbase",
            "query": query,
            "total_found": 0,
            "ingested": 0,
            "skipped": 0,
            "leads": []
        }
        
        try:
            # API call would go here
            # response = await self.client.get(
            #     "https://api.crunchbase.com/v4/search/organizations",
            #     params={"query": query, "limit": limit},
            #     headers={"X-CB-User-Key": settings.CRUNCHBASE_API_KEY}
            # )
            
            # For now, simulate with mock data
            mock_leads = self._generate_mock_crunchbase_leads(limit)
            results["total_found"] = len(mock_leads)
            
            for lead_data in mock_leads:
                if self._should_ingest_lead(lead_data):
                    lead = await self._create_lead_from_source(lead_data, "crunchbase")
                    results["ingested"] += 1
                    results["leads"].append(lead.lead_id)
                else:
                    results["skipped"] += 1
            
            self.db.commit()
            logger.info(f"Crunchbase ingestion complete: {results['ingested']} leads ingested")
            
        except Exception as e:
            logger.error(f"Error ingesting from Crunchbase: {e}")
            results["error"] = str(e)
        
        return results
    
    async def ingest_from_apollo(
        self,
        industry: Optional[str] = None,
        company_size: Optional[str] = None,
        limit: int = 100
    ) -> Dict:
        """Ingest leads from Apollo.io API"""
        results = {
            "source": "apollo",
            "total_found": 0,
            "ingested": 0,
            "skipped": 0,
            "leads": []
        }
        
        try:
            # API integration would go here
            mock_leads = self._generate_mock_apollo_leads(limit)
            results["total_found"] = len(mock_leads)
            
            for lead_data in mock_leads:
                if self._should_ingest_lead(lead_data):
                    lead = await self._create_lead_from_source(lead_data, "apollo")
                    results["ingested"] += 1
                    results["leads"].append(lead.lead_id)
                else:
                    results["skipped"] += 1
            
            self.db.commit()
            logger.info(f"Apollo ingestion complete: {results['ingested']} leads ingested")
            
        except Exception as e:
            logger.error(f"Error ingesting from Apollo: {e}")
            results["error"] = str(e)
        
        return results
    
    async def ingest_from_linkedin_sales_nav(
        self,
        keywords: str,
        company_size: Optional[str] = None,
        limit: int = 100
    ) -> Dict:
        """Ingest leads from LinkedIn Sales Navigator"""
        results = {
            "source": "linkedin_sales_nav",
            "keywords": keywords,
            "total_found": 0,
            "ingested": 0,
            "skipped": 0,
            "leads": []
        }
        
        try:
            # API integration would go here
            mock_leads = self._generate_mock_linkedin_leads(limit)
            results["total_found"] = len(mock_leads)
            
            for lead_data in mock_leads:
                if self._should_ingest_lead(lead_data):
                    lead = await self._create_lead_from_source(lead_data, "linkedin")
                    results["ingested"] += 1
                    results["leads"].append(lead.lead_id)
                else:
                    results["skipped"] += 1
            
            self.db.commit()
            logger.info(f"LinkedIn Sales Nav ingestion complete: {results['ingested']} leads ingested")
            
        except Exception as e:
            logger.error(f"Error ingesting from LinkedIn Sales Nav: {e}")
            results["error"] = str(e)
        
        return results
    
    def _should_ingest_lead(self, lead_data: Dict) -> bool:
        """AI-powered lead filtering based on ICP and quality signals"""
        # Check if lead already exists
        company = lead_data.get("company", "")
        existing = self.db.query(Lead).filter(Lead.company == company).first()
        if existing:
            return False
        
        # Check suppression list
        # This would check against your suppression list
        
        # Apply ICP filters
        icp_score = self._calculate_icp_score(lead_data)
        if icp_score < 50:  # Minimum threshold
            return False
        
        return True
    
    def _calculate_icp_score(self, lead_data: Dict) -> int:
        """Calculate ICP (Ideal Customer Profile) score"""
        score = 0
        
        # Industry match
        target_industries = ["SaaS", "Technology", "Software", "Fintech"]
        industry = lead_data.get("industry", "")
        if any(ind.lower() in industry.lower() for ind in target_industries):
            score += 30
        
        # Company size
        employees = lead_data.get("employees", 0)
        if 50 <= employees <= 500:  # Ideal size
            score += 25
        elif 10 <= employees < 50:
            score += 15
        
        # Funding stage
        funding_stage = lead_data.get("funding_stage", "")
        if funding_stage in ["Series A", "Series B", "Series C"]:
            score += 25
        elif funding_stage == "Seed":
            score += 15
        
        # Recent activity signals
        if lead_data.get("recent_funding"):
            score += 10
        if lead_data.get("hiring_growth"):
            score += 10
        
        return min(score, 100)
    
    async def _create_lead_from_source(
        self, 
        lead_data: Dict, 
        source: str
    ) -> Lead:
        """Create lead from external source data"""
        lead_id = f"{source}-{lead_data['company'].lower().replace(' ', '-')}"
        
        # Build signal from source data
        signal_parts = []
        if lead_data.get("recent_funding"):
            signal_parts.append(f"Recent funding: {lead_data['recent_funding']}")
        if lead_data.get("hiring_growth"):
            signal_parts.append(f"Hiring growth: {lead_data['hiring_growth']}")
        if lead_data.get("tech_stack"):
            signal_parts.append(f"Tech stack: {lead_data['tech_stack']}")
        if lead_data.get("industry"):
            signal_parts.append(f"Industry: {lead_data['industry']}")
        
        signal = " | ".join(signal_parts)
        
        lead = Lead(
            lead_id=lead_id,
            company=lead_data["company"],
            website=lead_data.get("website"),
            signal=signal,
            decision_maker=lead_data.get("decision_maker"),
            fit_score=self._calculate_icp_score(lead_data),
            status="new"
        )
        
        self.db.add(lead)
        
        # Create lead score record
        lead_score = LeadScore(
            lead_id=lead_id,
            signal_strength=self._calculate_signal_strength(lead_data),
            hiring_intensity=self._calculate_hiring_intensity(lead_data),
            funding_stage=self._map_funding_stage(lead_data.get("funding_stage")),
            company_size_fit=self._calculate_company_size_fit(lead_data),
            market_relevance=self._calculate_market_relevance(lead_data),
            priority_score=self._calculate_icp_score(lead_data),
            is_qualified=self._calculate_icp_score(lead_data) >= 70
        )
        self.db.add(lead_score)
        
        # Log ingestion event
        event = Event(
            event_id=f"ingestion-{lead_id}",
            event_type="lead_ingested",
            entity_type="lead",
            entity_id=lead_id,
            data={"source": source, "original_data": lead_data}
        )
        self.db.add(event)
        
        return lead
    
    def _calculate_signal_strength(self, lead_data: Dict) -> int:
        """Calculate signal strength score"""
        strength = 0
        if lead_data.get("recent_funding"):
            strength += 40
        if lead_data.get("hiring_growth"):
            strength += 30
        if lead_data.get("product_launch"):
            strength += 30
        return strength
    
    def _calculate_hiring_intensity(self, lead_data: Dict) -> int:
        """Calculate hiring intensity score"""
        if lead_data.get("hiring_growth") == "high":
            return 100
        elif lead_data.get("hiring_growth") == "medium":
            return 60
        elif lead_data.get("hiring_growth") == "low":
            return 30
        return 0
    
    def _map_funding_stage(self, funding_stage: Optional[str]) -> int:
        """Map funding stage to numeric score"""
        stages = {
            "Seed": 20,
            "Series A": 40,
            "Series B": 60,
            "Series C": 80,
            "Series D": 90,
            "IPO": 100
        }
        return stages.get(funding_stage, 0)
    
    def _calculate_company_size_fit(self, lead_data: Dict) -> int:
        """Calculate company size fit score"""
        employees = lead_data.get("employees", 0)
        if 50 <= employees <= 500:
            return 100
        elif 10 <= employees < 50:
            return 70
        elif 500 < employees <= 1000:
            return 60
        return 30
    
    def _calculate_market_relevance(self, lead_data: Dict) -> int:
        """Calculate market relevance score"""
        relevance = 50
        if lead_data.get("industry") in ["SaaS", "Technology", "Software"]:
            relevance += 30
        if lead_data.get("recent_funding"):
            relevance += 20
        return relevance
    
    # Mock data generators for testing
    def _generate_mock_crunchbase_leads(self, count: int) -> List[Dict]:
        """Generate mock Crunchbase leads for testing"""
        companies = [
            "TechFlow AI", "DataSync Solutions", "CloudScale", "QuantumSoft", "NexGen Analytics"
        ]
        leads = []
        for i in range(count):
            leads.append({
                "company": f"{companies[i % len(companies)]} {i}",
                "website": f"https://example{i}.com",
                "industry": "SaaS",
                "employees": 100 + (i * 10),
                "funding_stage": ["Seed", "Series A", "Series B"][i % 3],
                "recent_funding": f"${(i + 1) * 5}M",
                "hiring_growth": ["low", "medium", "high"][i % 3],
                "decision_maker": f"CEO {i}",
                "tech_stack": "Python, React, AWS"
            })
        return leads
    
    def _generate_mock_apollo_leads(self, count: int) -> List[Dict]:
        """Generate mock Apollo leads for testing"""
        leads = []
        for i in range(count):
            leads.append({
                "company": f"Enterprise {i}",
                "website": f"https://enterprise{i}.com",
                "industry": "Technology",
                "employees": 200 + (i * 15),
                "decision_maker": f"VP Sales {i}",
                "revenue": f"${(i + 1) * 10}M"
            })
        return leads
    
    def _generate_mock_linkedin_leads(self, count: int) -> List[Dict]:
        """Generate mock LinkedIn leads for testing"""
        leads = []
        for i in range(count):
            leads.append({
                "company": f"InnovateCo {i}",
                "website": f"https://innovate{i}.com",
                "industry": "Software",
                "employees": 150 + (i * 20),
                "decision_maker": f"CTO {i}",
                "headcount_growth": "+20%"
            })
        return leads
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
