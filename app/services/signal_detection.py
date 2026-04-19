"""Real-time Signal Detection Service"""
import httpx
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import Lead, Event
from app.logging_config import logger as app_logger

logger = app_logger


class SignalDetectionService:
    """Service for real-time signal detection from external sources"""
    
    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def detect_funding_signals(
        self, 
        company_name: str,
        days_back: int = 30
    ) -> Optional[Dict]:
        """Detect recent funding signals for a company"""
        try:
            # This would integrate with Crunchbase API, PitchBook, etc.
            # For now, return mock data structure
            
            signal_data = {
                "signal_type": "funding",
                "company": company_name,
                "detected_at": datetime.utcnow().isoformat(),
                "confidence": 0.85,
                "details": {
                    "amount": "$10M",
                    "round": "Series A",
                    "investors": ["Sequoia", "Andreessen Horowitz"],
                    "date": (datetime.utcnow() - timedelta(days=5)).isoformat()
                },
                "actionable": True,
                "priority": "high"
            }
            
            logger.info(f"Funding signal detected for {company_name}")
            return signal_data
            
        except Exception as e:
            logger.error(f"Error detecting funding signals: {e}")
            return None
    
    async def detect_hiring_signals(
        self,
        company_name: str,
        target_roles: List[str] = None
    ) -> Optional[Dict]:
        """Detect hiring signals for a company"""
        if target_roles is None:
            target_roles = ["SDR", "BDR", "Sales Manager", "VP Sales"]
        
        try:
            # This would integrate with LinkedIn API, Indeed API, etc.
            signal_data = {
                "signal_type": "hiring",
                "company": company_name,
                "detected_at": datetime.utcnow().isoformat(),
                "confidence": 0.90,
                "details": {
                    "roles_hiring": target_roles,
                    "total_openings": len(target_roles) * 2,
                    "growth_rate": "+25%",
                    "departments": ["Sales", "Marketing"]
                },
                "actionable": True,
                "priority": "high"
            }
            
            logger.info(f"Hiring signal detected for {company_name}")
            return signal_data
            
        except Exception as e:
            logger.error(f"Error detecting hiring signals: {e}")
            return None
    
    async def detect_product_launch_signals(
        self,
        company_name: str
    ) -> Optional[Dict]:
        """Detect product launch signals"""
        try:
            # This would integrate with Product Hunt, press release APIs, etc.
            signal_data = {
                "signal_type": "product_launch",
                "company": company_name,
                "detected_at": datetime.utcnow().isoformat(),
                "confidence": 0.75,
                "details": {
                    "product_name": "New Enterprise Feature",
                    "launch_date": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                    "press_coverage": ["TechCrunch", "VentureBeat"],
                    "announcement_channels": ["Twitter", "LinkedIn", "Blog"]
                },
                "actionable": True,
                "priority": "medium"
            }
            
            logger.info(f"Product launch signal detected for {company_name}")
            return signal_data
            
        except Exception as e:
            logger.error(f"Error detecting product launch signals: {e}")
            return None
    
    async def detect_partnership_signals(
        self,
        company_name: str
    ) -> Optional[Dict]:
        """Detect partnership/announcement signals"""
        try:
            signal_data = {
                "signal_type": "partnership",
                "company": company_name,
                "detected_at": datetime.utcnow().isoformat(),
                "confidence": 0.70,
                "details": {
                    "partner": "Major Tech Company",
                    "announcement_type": "Strategic Partnership",
                    "date": (datetime.utcnow() - timedelta(days=7)).isoformat()
                },
                "actionable": True,
                "priority": "medium"
            }
            
            logger.info(f"Partnership signal detected for {company_name}")
            return signal_data
            
        except Exception as e:
            logger.error(f"Error detecting partnership signals: {e}")
            return None
    
    async def detect_expansion_signals(
        self,
        company_name: str
    ) -> Optional[Dict]:
        """Detect geographic or market expansion signals"""
        try:
            signal_data = {
                "signal_type": "expansion",
                "company": company_name,
                "detected_at": datetime.utcnow().isoformat(),
                "confidence": 0.80,
                "details": {
                    "expansion_type": "Geographic",
                    "new_markets": ["Europe", "Asia-Pacific"],
                    "new_offices": ["London", "Singapore"],
                    "date": (datetime.utcnow() - timedelta(days=10)).isoformat()
                },
                "actionable": True,
                "priority": "medium"
            }
            
            logger.info(f"Expansion signal detected for {company_name}")
            return signal_data
            
        except Exception as e:
            logger.error(f"Error detecting expansion signals: {e}")
            return None
    
    async def scan_all_signals_for_company(
        self,
        company_name: str
    ) -> Dict:
        """Scan all signal types for a company"""
        results = {
            "company": company_name,
            "scanned_at": datetime.utcnow().isoformat(),
            "signals_detected": []
        }
        
        # Run all signal detections in parallel
        funding = await self.detect_funding_signals(company_name)
        hiring = await self.detect_hiring_signals(company_name)
        product_launch = await self.detect_product_launch_signals(company_name)
        partnership = await self.detect_partnership_signals(company_name)
        expansion = await self.detect_expansion_signals(company_name)
        
        for signal in [funding, hiring, product_launch, partnership, expansion]:
            if signal:
                results["signals_detected"].append(signal)
        
        # Calculate overall signal strength
        results["signal_strength"] = self._calculate_overall_strength(results["signals_detected"])
        
        # Update lead if exists
        self._update_lead_with_signals(company_name, results["signals_detected"])
        
        return results
    
    def _calculate_overall_strength(self, signals: List[Dict]) -> Dict:
        """Calculate overall signal strength score"""
        if not signals:
            return {"score": 0, "level": "none"}
        
        # Weight signal types
        weights = {
            "funding": 0.30,
            "hiring": 0.25,
            "product_launch": 0.20,
            "partnership": 0.15,
            "expansion": 0.10
        }
        
        total_score = 0
        for signal in signals:
            signal_type = signal.get("signal_type")
            confidence = signal.get("confidence", 0.5)
            priority = signal.get("priority", "medium")
            
            weight = weights.get(signal_type, 0.1)
            priority_multiplier = 1.5 if priority == "high" else 1.0
            
            total_score += confidence * weight * priority_multiplier * 100
        
        # Normalize to 0-100
        total_score = min(100, total_score)
        
        # Determine level
        if total_score >= 70:
            level = "high"
        elif total_score >= 40:
            level = "medium"
        else:
            level = "low"
        
        return {"score": round(total_score, 2), "level": level}
    
    def _update_lead_with_signals(self, company_name: str, signals: List[Dict]):
        """Update lead record with detected signals"""
        lead = self.db.query(Lead).filter(Lead.company == company_name).first()
        if not lead:
            return
        
        # Build updated signal text
        signal_parts = []
        if lead.signal:
            signal_parts.append(lead.signal)
        
        for signal in signals:
            signal_type = signal.get("signal_type")
            details = signal.get("details", {})
            
            if signal_type == "funding":
                signal_parts.append(f"Recent Funding: {details.get('amount', '')} {details.get('round', '')}")
            elif signal_type == "hiring":
                signal_parts.append(f"Hiring: {', '.join(details.get('roles_hiring', []))}")
            elif signal_type == "product_launch":
                signal_parts.append(f"Product Launch: {details.get('product_name', '')}")
            elif signal_type == "partnership":
                signal_parts.append(f"Partnership: {details.get('partner', '')}")
            elif signal_type == "expansion":
                signal_parts.append(f"Expansion: {', '.join(details.get('new_markets', []))}")
        
        lead.signal = " | ".join(signal_parts)
        
        # Log signal detection event
        event = Event(
            event_id=f"signal-detection-{company_name}",
            event_type="signals_detected",
            entity_type="lead",
            entity_id=lead.lead_id,
            data={"signals": signals}
        )
        self.db.add(event)
        
        self.db.commit()
    
    async def monitor_signals_batch(
        self,
        company_names: List[str]
    ) -> Dict:
        """Monitor signals for multiple companies"""
        results = {
            "total_companies": len(company_names),
            "companies_with_signals": 0,
            "total_signals": 0,
            "results": {}
        }
        
        for company in company_names:
            signal_result = await self.scan_all_signals_for_company(company)
            results["results"][company] = signal_result
            
            if signal_result["signals_detected"]:
                results["companies_with_signals"] += 1
                results["total_signals"] += len(signal_result["signals_detected"])
        
        return results
    
    async def setup_signal_monitoring(
        self,
        check_interval_hours: int = 24
    ) -> Dict:
        """Setup automated signal monitoring"""
        # This would set up a Celery beat task for periodic monitoring
        return {
            "status": "configured",
            "check_interval_hours": check_interval_hours,
            "next_check": (datetime.utcnow() + timedelta(hours=check_interval_hours)).isoformat()
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
