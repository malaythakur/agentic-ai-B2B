"""
B2B Provider Dashboard Service

Comprehensive dashboard for service providers:
- Automation status control (pause/resume)
- Match viewing with scores and details
- Outreach results (sent, replies, meetings)
- Settings management (max emails/day, min match score)
- Analytics (reply rate, conversion rate, ROI)
- All using existing data models
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models import (
    ServiceProvider, BuyerCompany, Match, ProviderSubscription,
    ProviderBilling, Event
)
from app.services.provider_management import ProviderManagementService
from app.services.matchmaking_engine import MatchmakingEngine
from app.logging_config import logger as app_logger

logger = app_logger


class B2BProviderDashboardService:
    """
    Provider Dashboard Service
    
    Provides comprehensive dashboard functionality for service providers:
    - View automation status and control
    - See matched buyers with scores
    - Track outreach results
    - Adjust settings
    - View analytics and ROI
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.provider_mgmt = ProviderManagementService(db)
        self.matchmaking = MatchmakingEngine(db)
    
    def get_dashboard(self, provider_id: str) -> Optional[Dict]:
        """
        Get complete provider dashboard data
        
        Returns:
            Dict with all dashboard data or None if provider not found
        """
        provider = self.provider_mgmt.get_provider(provider_id)
        if not provider:
            return None
        
        return {
            "provider_id": provider_id,
            "overview": self._get_overview(provider),
            "automation": self._get_automation_status(provider),
            "matches": self._get_matches_summary(provider_id),
            "outreach": self._get_outreach_summary(provider_id),
            "analytics": self._get_analytics(provider_id),
            "settings": self._get_settings(provider),
            "subscription": self._get_subscription_info(provider_id),
            "recent_activity": self._get_recent_activity(provider_id)
        }
    
    def _get_overview(self, provider: ServiceProvider) -> Dict:
        """Get provider overview"""
        return {
            "company_name": provider.company_name,
            "website": provider.website,
            "services": provider.services,
            "industries": provider.industries,
            "contact_email": provider.contact_email,
            "active": provider.active,
            "onboarding_complete": provider.onboarding_complete,
            "consent_status": provider.outreach_consent_status,
            "joined_at": provider.created_at.isoformat() if provider.created_at else None
        }
    
    def _get_automation_status(self, provider: ServiceProvider) -> Dict:
        """Get automation status and controls"""
        total_matches = self.db.query(Match).filter(
            Match.provider_id == provider.provider_id
        ).count()
        
        pending_matches = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider.provider_id,
                Match.status == "pending"
            )
        ).count()
        
        return {
            "enabled": provider.auto_outreach_enabled,
            "status": "active" if provider.auto_outreach_enabled else "paused",
            "consent_date": provider.outreach_consent_date.isoformat() if provider.outreach_consent_date else None,
            "total_matches": total_matches,
            "pending_matches": pending_matches,
            "can_pause": provider.auto_outreach_enabled,
            "can_resume": not provider.auto_outreach_enabled and provider.outreach_consent_status == "consented"
        }
    
    def pause_automation(self, provider_id: str) -> bool:
        """Pause provider automation"""
        provider = self.provider_mgmt.get_provider(provider_id)
        if not provider:
            return False
        
        provider.auto_outreach_enabled = False
        self.db.commit()
        
        # Log event
        event = Event(
            event_type="automation_paused",
            entity_type="provider",
            entity_id=provider_id,
            data={"timestamp": datetime.utcnow().isoformat()}
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Automation paused for provider: {provider_id}")
        return True
    
    def resume_automation(self, provider_id: str) -> bool:
        """Resume provider automation"""
        provider = self.provider_mgmt.get_provider(provider_id)
        if not provider:
            return False
        
        if provider.outreach_consent_status != "consented":
            logger.warning(f"Cannot resume automation - no consent: {provider_id}")
            return False
        
        provider.auto_outreach_enabled = True
        self.db.commit()
        
        # Log event
        event = Event(
            event_type="automation_resumed",
            entity_type="provider",
            entity_id=provider_id,
            data={"timestamp": datetime.utcnow().isoformat()}
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Automation resumed for provider: {provider_id}")
        return True
    
    def _get_matches_summary(self, provider_id: str) -> Dict:
        """Get matches summary for provider"""
        # Total matches
        total = self.db.query(Match).filter(Match.provider_id == provider_id).count()
        
        # By status
        status_counts = {}
        for status in ["pending", "outreach_sent", "buyer_interested", "buyer_declined", 
                       "meeting_booked", "closed_won", "unsubscribed"]:
            count = self.db.query(Match).filter(
                and_(Match.provider_id == provider_id, Match.status == status)
            ).count()
            if count > 0:
                status_counts[status] = count
        
        # Recent matches (last 30 days)
        recent = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider_id,
                Match.created_at >= datetime.utcnow() - timedelta(days=30)
            )
        ).count()
        
        # High-score matches (>= 80)
        high_score = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider_id,
                Match.match_score >= 80
            )
        ).count()
        
        # Recent matches list (last 10)
        recent_matches = self.db.query(Match).filter(
            Match.provider_id == provider_id
        ).order_by(
            Match.created_at.desc()
        ).limit(10).all()
        
        recent_list = []
        for match in recent_matches:
            buyer = self.db.query(BuyerCompany).filter(
                BuyerCompany.buyer_id == match.buyer_id
            ).first()
            
            if buyer:
                recent_list.append({
                    "match_id": match.match_id,
                    "buyer_company": buyer.company_name,
                    "buyer_industry": buyer.industry,
                    "match_score": match.match_score,
                    "status": match.status,
                    "created_at": match.created_at.isoformat() if match.created_at else None
                })
        
        return {
            "total": total,
            "by_status": status_counts,
            "recent_count": recent,
            "high_score_count": high_score,
            "recent_matches": recent_list
        }
    
    def get_match_details(self, provider_id: str, match_id: str) -> Optional[Dict]:
        """Get detailed info about a specific match"""
        match = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider_id,
                Match.match_id == match_id
            )
        ).first()
        
        if not match:
            return None
        
        buyer = self.db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == match.buyer_id
        ).first()
        
        if not buyer:
            return None
        
        return {
            "match_id": match.match_id,
            "match_score": match.match_score,
            "status": match.status,
            "created_at": match.created_at.isoformat() if match.created_at else None,
            "intro_sent_at": match.intro_sent_at.isoformat() if match.intro_sent_at else None,
            "buyer_response_date": match.buyer_response_date.isoformat() if match.buyer_response_date else None,
            "buyer": {
                "company_name": buyer.company_name,
                "website": buyer.website,
                "industry": buyer.industry,
                "employee_count": buyer.employee_count,
                "funding_stage": buyer.funding_stage,
                "decision_maker": {
                    "name": buyer.decision_maker_name,
                    "title": buyer.decision_maker_title,
                    "email": buyer.decision_maker_email
                },
                "signals": buyer.signals,
                "priority_score": buyer.priority_score
            },
            "icp_match_details": match.icp_match_details if hasattr(match, 'icp_match_details') else {}
        }
    
    def _get_outreach_summary(self, provider_id: str) -> Dict:
        """Get outreach summary for provider"""
        # Total intros sent
        sent = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider_id,
                Match.intro_sent_at != None
            )
        ).count()
        
        # Responses received
        responded = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider_id,
                Match.buyer_responded == True
            )
        ).count()
        
        # Interested responses
        interested = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider_id,
                Match.status == "buyer_interested"
            )
        ).count()
        
        # Meetings booked
        meetings = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider_id,
                Match.status.in_(["meeting_booked", "closed_won"])
            )
        ).count()
        
        # Calculate rates
        response_rate = (responded / sent * 100) if sent > 0 else 0
        interested_rate = (interested / responded * 100) if responded > 0 else 0
        meeting_rate = (meetings / interested * 100) if interested > 0 else 0
        
        # Follow-ups sent
        followups = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider_id,
                Match.followup_count > 0
            )
        ).count()
        
        # Last 30 days activity
        recent_sent = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider_id,
                Match.intro_sent_at >= datetime.utcnow() - timedelta(days=30)
            )
        ).count()
        
        return {
            "intros_sent": sent,
            "responses": responded,
            "interested": interested,
            "meetings_booked": meetings,
            "followups_sent": followups,
            "response_rate": round(response_rate, 2),
            "interested_rate": round(interested_rate, 2),
            "meeting_rate": round(meeting_rate, 2),
            "recent_sent": recent_sent
        }
    
    def _get_analytics(self, provider_id: str) -> Dict:
        """Get analytics and ROI for provider"""
        # Get outreach data
        outreach = self._get_outreach_summary(provider_id)
        
        # Calculate pipeline value (estimated)
        avg_deal_size = 50000  # $50K average deal
        potential_deals = outreach["interested"]
        pipeline_value = potential_deals * avg_deal_size
        
        # Get subscription cost
        sub = self.provider_mgmt.get_provider_subscription(provider_id)
        monthly_cost = sub.monthly_amount / 100 if sub else 500  # Default $500
        
        # Calculate ROI
        # Assume 20% of interested become customers, avg deal $50K
        estimated_customers = int(outreach["interested"] * 0.2)
        estimated_revenue = estimated_customers * avg_deal_size
        
        roi = ((estimated_revenue - (monthly_cost * 3)) / (monthly_cost * 3) * 100) if monthly_cost > 0 else 0
        
        # Time series data (last 90 days)
        daily_data = []
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            day_sent = self.db.query(Match).filter(
                and_(
                    Match.provider_id == provider_id,
                    func.date(Match.intro_sent_at) == date.date()
                )
            ).count()
            
            if day_sent > 0:
                daily_data.append({
                    "date": date.date().isoformat(),
                    "intros_sent": day_sent
                })
        
        return {
            "pipeline_value": pipeline_value,
            "estimated_customers": estimated_customers,
            "estimated_revenue": estimated_revenue,
            "monthly_cost": monthly_cost,
            "roi_percentage": round(roi, 2),
            "cost_per_lead": round((monthly_cost / outreach["intros_sent"]), 2) if outreach["intros_sent"] > 0 else monthly_cost,
            "cost_per_interested": round((monthly_cost / outreach["interested"]), 2) if outreach["interested"] > 0 else monthly_cost,
            "daily_activity": list(reversed(daily_data))  # Oldest first
        }
    
    def _get_settings(self, provider: ServiceProvider) -> Dict:
        """Get provider automation settings"""
        settings = provider.automation_settings or {}
        
        return {
            "max_emails_per_day": settings.get("max_emails_per_day", 30),
            "min_match_score": settings.get("min_match_score", 70),
            "auto_approve_matches": settings.get("auto_approve_matches", True),
            "template_type": settings.get("template_type", "intro"),
            "follow_up_enabled": settings.get("follow_up_enabled", True),
            "max_followups": settings.get("max_followups", 3),
            "icp_criteria": provider.icp_criteria or {}
        }
    
    def update_settings(self, provider_id: str, settings: Dict) -> bool:
        """Update provider automation settings"""
        provider = self.provider_mgmt.get_provider(provider_id)
        if not provider:
            return False
        
        # Validate settings
        valid_settings = {}
        
        if "max_emails_per_day" in settings:
            value = int(settings["max_emails_per_day"])
            valid_settings["max_emails_per_day"] = max(5, min(value, 50))  # 5-50 range
        
        if "min_match_score" in settings:
            value = int(settings["min_match_score"])
            valid_settings["min_match_score"] = max(50, min(value, 95))  # 50-95 range
        
        if "auto_approve_matches" in settings:
            valid_settings["auto_approve_matches"] = bool(settings["auto_approve_matches"])
        
        if "follow_up_enabled" in settings:
            valid_settings["follow_up_enabled"] = bool(settings["follow_up_enabled"])
        
        if "max_followups" in settings:
            value = int(settings["max_followups"])
            valid_settings["max_followups"] = max(0, min(value, 5))  # 0-5 range
        
        # Update ICP criteria if provided
        if "icp_criteria" in settings:
            provider.icp_criteria = settings["icp_criteria"]
        
        # Merge with existing settings
        current = provider.automation_settings or {}
        current.update(valid_settings)
        provider.automation_settings = current
        
        self.db.commit()
        
        # Log event
        event = Event(
            event_type="settings_updated",
            entity_type="provider",
            entity_id=provider_id,
            data={"updated_settings": list(valid_settings.keys())}
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Settings updated for provider: {provider_id}")
        return True
    
    def _get_subscription_info(self, provider_id: str) -> Dict:
        """Get subscription information"""
        return self.provider_mgmt.check_usage_limits(provider_id)
    
    def _get_recent_activity(self, provider_id: str) -> List[Dict]:
        """Get recent activity for provider"""
        # Get recent events
        events = self.db.query(Event).filter(
            and_(
                Event.entity_type.in_(["match", "provider"]),
                Event.data.contains({"provider_id": provider_id}) if False else True
            )
        ).order_by(
            Event.created_at.desc()
        ).limit(20).all()
        
        # For simplicity, return recent matches
        recent_matches = self.db.query(Match).filter(
            Match.provider_id == provider_id
        ).order_by(
            Match.updated_at.desc()
        ).limit(10).all()
        
        activity = []
        for match in recent_matches:
            buyer = self.db.query(BuyerCompany).filter(
                BuyerCompany.buyer_id == match.buyer_id
            ).first()
            
            if buyer:
                activity.append({
                    "type": "match_update",
                    "match_id": match.match_id,
                    "buyer_company": buyer.company_name,
                    "status": match.status,
                    "timestamp": match.updated_at.isoformat() if match.updated_at else None
                })
        
        return activity
    
    def export_data(self, provider_id: str, format: str = "json") -> Dict:
        """Export provider data"""
        # Get all matches
        matches = self.db.query(Match).filter(
            Match.provider_id == provider_id
        ).all()
        
        data = {
            "provider_id": provider_id,
            "export_date": datetime.utcnow().isoformat(),
            "total_matches": len(matches),
            "matches": []
        }
        
        for match in matches:
            buyer = self.db.query(BuyerCompany).filter(
                BuyerCompany.buyer_id == match.buyer_id
            ).first()
            
            if buyer:
                data["matches"].append({
                    "match_id": match.match_id,
                    "buyer_company": buyer.company_name,
                    "buyer_email": buyer.decision_maker_email,
                    "match_score": match.match_score,
                    "status": match.status,
                    "intro_sent_at": match.intro_sent_at.isoformat() if match.intro_sent_at else None,
                    "buyer_responded": match.buyer_responded,
                    "created_at": match.created_at.isoformat() if match.created_at else None
                })
        
        return data
