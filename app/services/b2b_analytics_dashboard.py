"""
B2B Platform Analytics Dashboard Service

Platform-wide analytics and insights:
- Total providers, buyers, matches
- Outreach metrics (emails sent, reply rate, meeting rate)
- Top-performing providers by conversion rate
- Buyer engagement trends by industry
- Revenue tracking (subscriptions, meetings, success fees)
- ROI calculation and trends
- All using FREE data aggregation
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from collections import defaultdict

from app.models import (
    ServiceProvider, BuyerCompany, Match, ProviderSubscription,
    ProviderBilling, PlatformRevenueSummary, Event
)
from app.services.provider_management import ProviderManagementService
from app.logging_config import logger as app_logger

logger = app_logger


class B2BAnalyticsDashboardService:
    """
    B2B Platform Analytics Dashboard Service
    
    Provides platform-wide insights:
    - Overview metrics
    - Provider performance rankings
    - Buyer engagement trends
    - Revenue tracking
    - Conversion funnels
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.provider_mgmt = ProviderManagementService(db)
    
    def get_full_dashboard(self) -> Dict:
        """
        Get complete analytics dashboard
        
        Returns:
            Dict with all platform analytics
        """
        return {
            "overview": self._get_overview_metrics(),
            "providers": self._get_provider_analytics(),
            "buyers": self._get_buyer_analytics(),
            "outreach": self._get_outreach_analytics(),
            "revenue": self._get_revenue_analytics(),
            "trends": self._get_trend_analytics(),
            "conversion_funnel": self._get_conversion_funnel(),
            "top_performers": self._get_top_performers(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_overview_metrics(self) -> Dict:
        """Get platform overview metrics"""
        total_providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).count()
        
        total_buyers = self.db.query(BuyerCompany).filter(
            BuyerCompany.active == True
        ).count()
        
        total_matches = self.db.query(Match).count()
        
        active_providers = self.db.query(ServiceProvider).filter(
            and_(
                ServiceProvider.active == True,
                ServiceProvider.auto_outreach_enabled == True
            )
        ).count()
        
        # Today's activity
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        new_matches_today = self.db.query(Match).filter(
            Match.created_at >= today
        ).count()
        
        intros_sent_today = self.db.query(Match).filter(
            Match.intro_sent_at >= today
        ).count()
        
        responses_today = self.db.query(Match).filter(
            Match.buyer_response_date >= today
        ).count()
        
        return {
            "total_providers": total_providers,
            "active_providers": active_providers,
            "total_buyers": total_buyers,
            "total_matches": total_matches,
            "new_matches_today": new_matches_today,
            "intros_sent_today": intros_sent_today,
            "responses_today": responses_today
        }
    
    def _get_provider_analytics(self) -> Dict:
        """Get provider performance analytics"""
        # By plan
        plan_counts = {}
        plans = ["basic", "premium", "enterprise"]
        for plan in plans:
            count = self.db.query(ProviderSubscription).filter(
                and_(
                    ProviderSubscription.plan_type == plan,
                    ProviderSubscription.status == "active"
                )
            ).count()
            if count > 0:
                plan_counts[plan] = count
        
        # By consent status
        consent_status = {}
        for status in ["pending", "consented", "declined"]:
            count = self.db.query(ServiceProvider).filter(
                ServiceProvider.outreach_consent_status == status
            ).count()
            if count > 0:
                consent_status[status] = count
        
        # Top providers by matches
        top_by_matches = []
        providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).all()
        
        provider_stats = []
        for provider in providers:
            match_count = self.db.query(Match).filter(
                Match.provider_id == provider.provider_id
            ).count()
            
            if match_count > 0:
                provider_stats.append({
                    "provider_id": provider.provider_id,
                    "company_name": provider.company_name,
                    "match_count": match_count,
                    "industries": provider.industries
                })
        
        provider_stats.sort(key=lambda x: x["match_count"], reverse=True)
        top_by_matches = provider_stats[:10]
        
        # Provider growth over time
        growth = []
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            count = self.db.query(ServiceProvider).filter(
                func.date(ServiceProvider.created_at) == date.date()
            ).count()
            if count > 0:
                growth.append({
                    "date": date.date().isoformat(),
                    "new_providers": count
                })
        
        return {
            "by_plan": plan_counts,
            "consent_status": consent_status,
            "top_by_matches": top_by_matches,
            "growth": list(reversed(growth))
        }
    
    def _get_buyer_analytics(self) -> Dict:
        """Get buyer engagement analytics"""
        # By industry
        industry_counts = {}
        industries = ["SaaS", "Fintech", "E-commerce", "AI", "Healthcare", "Enterprise Software"]
        for industry in industries:
            count = self.db.query(BuyerCompany).filter(
                and_(
                    BuyerCompany.industry == industry,
                    BuyerCompany.active == True
                )
            ).count()
            if count > 0:
                industry_counts[industry] = count
        
        # By funding stage
        funding_counts = {}
        stages = ["Seed", "Series A", "Series B", "Series C", "Late Stage", "Public"]
        for stage in stages:
            count = self.db.query(BuyerCompany).filter(
                BuyerCompany.funding_stage == stage
            ).count()
            if count > 0:
                funding_counts[stage] = count
        
        # By priority score
        high_priority = self.db.query(BuyerCompany).filter(
            BuyerCompany.priority_score >= 80
        ).count()
        
        medium_priority = self.db.query(BuyerCompany).filter(
            and_(
                BuyerCompany.priority_score >= 60,
                BuyerCompany.priority_score < 80
            )
        ).count()
        
        low_priority = self.db.query(BuyerCompany).filter(
            BuyerCompany.priority_score < 60
        ).count()
        
        # Buyer discovery sources
        sources = {}
        for source in ["github", "newsapi", "hackernews", "producthunt", "jobboards", "manual"]:
            count = self.db.query(BuyerCompany).filter(
                BuyerCompany.discovery_source == source
            ).count()
            if count > 0:
                sources[source] = count
        
        # Engagement by industry
        engagement = {}
        for industry in industries:
            # Get response rate for this industry
            buyers_in_industry = self.db.query(BuyerCompany).filter(
                BuyerCompany.industry == industry
            ).all()
            
            buyer_ids = [b.buyer_id for b in buyers_in_industry]
            
            if buyer_ids:
                total_matches = self.db.query(Match).filter(
                    Match.buyer_id.in_(buyer_ids)
                ).count()
                
                responded_matches = self.db.query(Match).filter(
                    and_(
                        Match.buyer_id.in_(buyer_ids),
                        Match.buyer_responded == True
                    )
                ).count()
                
                response_rate = (responded_matches / total_matches * 100) if total_matches > 0 else 0
                
                if total_matches > 0:
                    engagement[industry] = {
                        "total_matches": total_matches,
                        "responded": responded_matches,
                        "response_rate": round(response_rate, 2)
                    }
        
        return {
            "by_industry": industry_counts,
            "by_funding_stage": funding_counts,
            "priority_distribution": {
                "high": high_priority,
                "medium": medium_priority,
                "low": low_priority
            },
            "discovery_sources": sources,
            "engagement_by_industry": engagement
        }
    
    def _get_outreach_analytics(self) -> Dict:
        """Get outreach performance analytics"""
        # Total stats
        total_intros = self.db.query(Match).filter(
            Match.intro_sent_at != None
        ).count()
        
        total_responses = self.db.query(Match).filter(
            Match.buyer_responded == True
        ).count()
        
        total_interested = self.db.query(Match).filter(
            Match.status == "buyer_interested"
        ).count()
        
        total_meetings = self.db.query(Match).filter(
            Match.status.in_(["meeting_booked", "closed_won"])
        ).count()
        
        # Calculate rates
        response_rate = (total_responses / total_intros * 100) if total_intros > 0 else 0
        interested_rate = (total_interested / total_responses * 100) if total_responses > 0 else 0
        meeting_rate = (total_meetings / total_interested * 100) if total_interested > 0 else 0
        
        # Daily trend (last 30 days)
        daily_stats = []
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            
            intros = self.db.query(Match).filter(
                func.date(Match.intro_sent_at) == date.date()
            ).count()
            
            responses = self.db.query(Match).filter(
                func.date(Match.buyer_response_date) == date.date()
            ).count()
            
            if intros > 0 or responses > 0:
                daily_stats.append({
                    "date": date.date().isoformat(),
                    "intros_sent": intros,
                    "responses": responses
                })
        
        # Follow-up stats
        followups_sent = self.db.query(Match).filter(
            Match.followup_count > 0
        ).count()
        
        avg_followups_per_match = self.db.query(
            func.avg(Match.followup_count)
        ).scalar() or 0
        
        return {
            "totals": {
                "intros_sent": total_intros,
                "responses": total_responses,
                "interested": total_interested,
                "meetings_booked": total_meetings
            },
            "rates": {
                "response_rate": round(response_rate, 2),
                "interested_rate": round(interested_rate, 2),
                "meeting_rate": round(meeting_rate, 2)
            },
            "daily_trend": list(reversed(daily_stats)),
            "followups": {
                "total_sent": followups_sent,
                "avg_per_match": round(avg_followups_per_match, 2)
            }
        }
    
    def _get_revenue_analytics(self) -> Dict:
        """Get revenue analytics"""
        # Monthly revenue (current month)
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_billings = self.db.query(ProviderBilling).filter(
            ProviderBilling.created_at >= month_start
        ).all()
        
        subscription_revenue = sum(
            b.amount for b in monthly_billings 
            if b.charge_type == "subscription" and b.status in ["pending", "paid"]
        ) / 100
        
        intro_fee_revenue = sum(
            b.amount for b in monthly_billings 
            if b.charge_type == "intro_fee" and b.status in ["pending", "paid"]
        ) / 100
        
        success_fee_revenue = sum(
            b.amount for b in monthly_billings 
            if b.charge_type == "success_fee" and b.status in ["pending", "paid"]
        ) / 100
        
        total_monthly = subscription_revenue + intro_fee_revenue + success_fee_revenue
        
        # Revenue by plan
        revenue_by_plan = {"basic": 0, "premium": 0, "enterprise": 0}
        
        subs = self.db.query(ProviderSubscription).filter(
            ProviderSubscription.status == "active"
        ).all()
        
        for sub in subs:
            plan = sub.plan_type
            if plan in revenue_by_plan:
                revenue_by_plan[plan] += sub.monthly_amount / 100
        
        # Historical revenue (last 6 months)
        historical = []
        for i in range(6):
            month = datetime.utcnow() - timedelta(days=i*30)
            month_start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            month_billings = self.db.query(ProviderBilling).filter(
                and_(
                    ProviderBilling.created_at >= month_start,
                    ProviderBilling.created_at < month_start + timedelta(days=30)
                )
            ).all()
            
            month_total = sum(b.amount for b in month_billings if b.status in ["pending", "paid"]) / 100
            
            historical.append({
                "month": month.strftime("%Y-%m"),
                "revenue": month_total
            })
        
        # ARR (Annual Recurring Revenue)
        arr = sum(s.monthly_amount for s in subs if s.status == "active") / 100 * 12
        
        return {
            "current_month": {
                "subscription": subscription_revenue,
                "intro_fees": intro_fee_revenue,
                "success_fees": success_fee_revenue,
                "total": total_monthly
            },
            "by_plan": revenue_by_plan,
            "historical": list(reversed(historical)),
            "arr": arr,
            "mrr": arr / 12
        }
    
    def _get_trend_analytics(self) -> Dict:
        """Get trend analytics"""
        # Match creation trend
        match_trend = []
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            count = self.db.query(Match).filter(
                func.date(Match.created_at) == date.date()
            ).count()
            
            if count > 0:
                match_trend.append({
                    "date": date.date().isoformat(),
                    "new_matches": count
                })
        
        # Response trend
        response_trend = []
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            count = self.db.query(Match).filter(
                func.date(Match.buyer_response_date) == date.date()
            ).count()
            
            if count > 0:
                response_trend.append({
                    "date": date.date().isoformat(),
                    "responses": count
                })
        
        # Meeting trend
        meeting_trend = []
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            count = self.db.query(Match).filter(
                func.date(Match.meeting_booked_at) == date.date()
            ).count()
            
            if count > 0:
                meeting_trend.append({
                    "date": date.date().isoformat(),
                    "meetings": count
                })
        
        return {
            "match_creation": list(reversed(match_trend)),
            "responses": list(reversed(response_trend)),
            "meetings": list(reversed(meeting_trend))
        }
    
    def _get_conversion_funnel(self) -> Dict:
        """Get conversion funnel analytics"""
        # Funnel stages
        stages = {
            "matches_created": self.db.query(Match).count(),
            "outreach_sent": self.db.query(Match).filter(
                Match.intro_sent_at != None
            ).count(),
            "buyer_responded": self.db.query(Match).filter(
                Match.buyer_responded == True
            ).count(),
            "buyer_interested": self.db.query(Match).filter(
                Match.status == "buyer_interested"
            ).count(),
            "meeting_booked": self.db.query(Match).filter(
                Match.status.in_(["meeting_booked", "closed_won"])
            ).count(),
            "deal_closed": self.db.query(Match).filter(
                Match.status == "closed_won"
            ).count()
        }
        
        # Calculate conversion rates between stages
        conversions = {}
        stage_names = list(stages.keys())
        
        for i in range(len(stage_names) - 1):
            current = stages[stage_names[i]]
            next_stage = stages[stage_names[i + 1]]
            
            rate = (next_stage / current * 100) if current > 0 else 0
            conversions[f"{stage_names[i]}_to_{stage_names[i+1]}"] = round(rate, 2)
        
        # Overall conversion (match to closed deal)
        overall = (stages["deal_closed"] / stages["matches_created"] * 100) if stages["matches_created"] > 0 else 0
        
        return {
            "stages": stages,
            "conversion_rates": conversions,
            "overall_conversion": round(overall, 2)
        }
    
    def _get_top_performers(self) -> Dict:
        """Get top performing providers"""
        providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).all()
        
        provider_scores = []
        
        for provider in providers:
            # Get provider stats
            total_matches = self.db.query(Match).filter(
                Match.provider_id == provider.provider_id
            ).count()
            
            if total_matches == 0:
                continue
            
            responses = self.db.query(Match).filter(
                and_(
                    Match.provider_id == provider.provider_id,
                    Match.buyer_responded == True
                )
            ).count()
            
            interested = self.db.query(Match).filter(
                and_(
                    Match.provider_id == provider.provider_id,
                    Match.status == "buyer_interested"
                )
            ).count()
            
            meetings = self.db.query(Match).filter(
                and_(
                    Match.provider_id == provider.provider_id,
                    Match.status.in_(["meeting_booked", "closed_won"])
                )
            ).count()
            
            response_rate = (responses / total_matches * 100) if total_matches > 0 else 0
            interested_rate = (interested / responses * 100) if responses > 0 else 0
            meeting_rate = (meetings / interested * 100) if interested > 0 else 0
            
            # Calculate performance score (weighted)
            performance_score = (
                response_rate * 0.3 +
                interested_rate * 0.4 +
                meeting_rate * 0.3
            )
            
            provider_scores.append({
                "provider_id": provider.provider_id,
                "company_name": provider.company_name,
                "industries": provider.industries,
                "total_matches": total_matches,
                "response_rate": round(response_rate, 2),
                "interested_rate": round(interested_rate, 2),
                "meeting_rate": round(meeting_rate, 2),
                "performance_score": round(performance_score, 2)
            })
        
        # Sort by performance score
        provider_scores.sort(key=lambda x: x["performance_score"], reverse=True)
        
        return {
            "top_10": provider_scores[:10],
            "total_ranked": len(provider_scores)
        }
    
    def get_provider_comparison(self, provider_ids: List[str]) -> Dict:
        """Compare multiple providers"""
        comparison = {
            "providers": [],
            "metrics": ["total_matches", "response_rate", "interested_rate", "meeting_rate"]
        }
        
        for provider_id in provider_ids:
            provider = self.provider_mgmt.get_provider(provider_id)
            if not provider:
                continue
            
            # Get stats
            total_matches = self.db.query(Match).filter(
                Match.provider_id == provider_id
            ).count()
            
            responses = self.db.query(Match).filter(
                and_(
                    Match.provider_id == provider_id,
                    Match.buyer_responded == True
                )
            ).count()
            
            interested = self.db.query(Match).filter(
                and_(
                    Match.provider_id == provider_id,
                    Match.status == "buyer_interested"
                )
            ).count()
            
            meetings = self.db.query(Match).filter(
                and_(
                    Match.provider_id == provider_id,
                    Match.status.in_(["meeting_booked", "closed_won"])
                )
            ).count()
            
            response_rate = (responses / total_matches * 100) if total_matches > 0 else 0
            interested_rate = (interested / responses * 100) if responses > 0 else 0
            meeting_rate = (meetings / interested * 100) if interested > 0 else 0
            
            comparison["providers"].append({
                "provider_id": provider_id,
                "company_name": provider.company_name,
                "metrics": {
                    "total_matches": total_matches,
                    "response_rate": round(response_rate, 2),
                    "interested_rate": round(interested_rate, 2),
                    "meeting_rate": round(meeting_rate, 2)
                }
            })
        
        return comparison
    
    def export_analytics_report(self) -> Dict:
        """Export full analytics report"""
        dashboard = self.get_full_dashboard()
        
        return {
            "report_type": "B2B Platform Analytics",
            "generated_at": datetime.utcnow().isoformat(),
            "period": "all_time",
            "data": dashboard
        }
