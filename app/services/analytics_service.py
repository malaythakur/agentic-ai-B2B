"""
Analytics Dashboard Service

Provides platform-wide analytics for admin:
- Overall automation performance
- Email metrics (sent, opened, responded)
- Provider engagement metrics
- ROI tracking
- Trend analysis
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import ServiceProvider, BuyerCompany, Match

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for platform analytics"""
    
    def __init__(self, db: Session):
        """
        Initialize analytics service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_platform_overview(self) -> Dict:
        """
        Get platform-wide overview metrics
        
        Returns:
            Dict with platform metrics
        """
        # Total counts
        total_providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).count()
        
        total_buyers = self.db.query(BuyerCompany).filter(
            BuyerCompany.active == True
        ).count()
        
        total_matches = self.db.query(Match).count()
        
        # Automation status
        providers_with_automation = self.db.query(ServiceProvider).filter(
            ServiceProvider.auto_outreach_enabled == True
        ).count()
        
        # Outreach metrics
        outreach_sent = self.db.query(Match).filter(
            Match.intro_sent_at.isnot(None)
        ).count()
        
        responses_received = self.db.query(Match).filter(
            Match.response_received == True
        ).count()
        
        meetings_booked = self.db.query(Match).filter(
            Match.meeting_booked_at.isnot(None)
        ).count()
        
        # Recent activity (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_matches = self.db.query(Match).filter(
            Match.created_at >= seven_days_ago
        ).count()
        
        recent_outreach = self.db.query(Match).filter(
            Match.intro_sent_at >= seven_days_ago
        ).count()
        
        return {
            "providers": {
                "total": total_providers,
                "with_automation": providers_with_automation,
                "automation_rate": round(providers_with_automation / total_providers * 100, 1) if total_providers > 0 else 0
            },
            "buyers": {
                "total": total_buyers
            },
            "matches": {
                "total": total_matches,
                "recent": recent_matches
            },
            "outreach": {
                "total_sent": outreach_sent,
                "recent": recent_outreach,
                "response_rate": round(responses_received / outreach_sent * 100, 1) if outreach_sent > 0 else 0,
                "responses": responses_received,
                "meetings_booked": meetings_booked
            }
        }
    
    def get_provider_performance(self, limit: int = 20) -> List[Dict]:
        """
        Get top performing providers
        
        Args:
            limit: Number of providers to return
            
        Returns:
            List of provider performance metrics
        """
        providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True,
            ServiceProvider.auto_outreach_enabled == True
        ).all()
        
        performance = []
        
        for provider in providers:
            matches = self.db.query(Match).filter(
                Match.provider_id == provider.provider_id
            ).all()
            
            outreach_sent = len([m for m in matches if m.intro_sent_at])
            responses = len([m for m in matches if m.response_received])
            meetings = len([m for m in matches if m.meeting_booked_at])
            
            performance.append({
                "provider_id": provider.provider_id,
                "company_name": provider.company_name,
                "matches": len(matches),
                "outreach_sent": outreach_sent,
                "responses": responses,
                "meetings": meetings,
                "response_rate": round(responses / outreach_sent * 100, 1) if outreach_sent > 0 else 0
            })
        
        # Sort by response rate
        performance.sort(key=lambda x: x['response_rate'], reverse=True)
        
        return performance[:limit]
    
    def get_email_trends(self, days: int = 30) -> Dict:
        """
        Get email sending trends over time
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with daily email counts
        """
        trends = {}
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            # Count emails sent on this date
            count = self.db.query(Match).filter(
                func.date(Match.intro_sent_at) == date.date()
            ).count()
            
            trends[date_str] = count
        
        return {
            "period_days": days,
            "daily_counts": dict(sorted(trends.items(), reverse=True))
        }
    
    def get_roi_metrics(self) -> Dict:
        """
        Get ROI metrics
        
        Returns:
            Dict with ROI calculations
        """
        # Calculate total deal value from closed deals
        closed_deals = self.db.query(Match).filter(
            Match.status == "deal_closed",
            Match.deal_value.isnot(None)
        ).all()
        
        total_deal_value = sum([m.deal_value or 0 for m in closed_deals])
        total_revenue_share = sum([m.revenue_share_amount or 0 for m in closed_deals])
        
        return {
            "total_deals": len(closed_deals),
            "total_deal_value": total_deal_value,
            "platform_revenue": total_revenue_share,
            "average_deal_value": round(total_deal_value / len(closed_deals), 2) if closed_deals else 0
        }
    
    def get_engagement_metrics(self) -> Dict:
        """
        Get engagement metrics
        
        Returns:
            Dict with engagement statistics
        """
        # Provider engagement
        providers_with_consent = self.db.query(ServiceProvider).filter(
            ServiceProvider.outreach_consent_status == "consented"
        ).count()
        
        # Buyer engagement
        buyers_responded = self.db.query(Match).filter(
            Match.response_received == True
        ).distinct(Match.buyer_id).count()
        
        return {
            "provider_engagement": {
                "total_providers": self.db.query(ServiceProvider).count(),
                "with_consent": providers_with_consent,
                "consent_rate": round(providers_with_consent / self.db.query(ServiceProvider).count() * 100, 1)
            },
            "buyer_engagement": {
                "total_buyers": self.db.query(BuyerCompany).count(),
                "responded": buyers_responded,
                "response_rate": round(buyers_responded / self.db.query(BuyerCompany).count() * 100, 1)
            }
        }
