"""
Provider Management Service for B2B Matchmaking Platform

Handles CRUD operations for service providers, subscriptions, and onboarding.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uuid

from app.models import (
    ServiceProvider, ProviderSubscription, ProviderBilling, Match,
    PlatformRevenueSummary
)


# Subscription plan definitions
SUBSCRIPTION_PLANS = {
    "basic": {
        "name": "Basic",
        "monthly_amount": 50000,  # $500 in cents
        "intro_fee": 5000,  # $50 in cents
        "max_matches": 50,
        "max_intros": 100,
        "description": "50 matches/month, $50 per meeting"
    },
    "premium": {
        "name": "Premium",
        "monthly_amount": 200000,  # $2000 in cents
        "intro_fee": 0,  # No intro fee for premium
        "max_matches": 200,
        "max_intros": 500,
        "description": "Unlimited matches, no intro fees, priority placement"
    },
    "enterprise": {
        "name": "Enterprise",
        "monthly_amount": 500000,  # $5000 in cents
        "intro_fee": 0,
        "max_matches": 1000,
        "max_intros": 2000,
        "description": "Custom integrations, dedicated support, API access"
    }
}


class ProviderManagementService:
    """Manage service providers on the platform"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_provider(
        self,
        company_name: str,
        contact_email: str,
        services: List[str],
        website: str = None,
        description: str = None,
        industries: List[str] = None,
        icp_criteria: Dict = None,
        case_studies: List[Dict] = None,
        differentiator: str = None,
        billing_email: str = None
    ) -> ServiceProvider:
        """Create a new service provider"""
        
        provider = ServiceProvider(
            provider_id=f"prov-{str(uuid.uuid4())[:8]}",
            company_name=company_name,
            website=website,
            description=description,
            services=services,
            industries=industries or [],
            icp_criteria=icp_criteria or {},
            case_studies=case_studies or [],
            differentiator=differentiator,
            contact_email=contact_email,
            billing_email=billing_email or contact_email,
            active=True,
            onboarding_complete=False
        )
        
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        
        return provider
    
    def get_provider(self, provider_id: str) -> Optional[ServiceProvider]:
        """Get provider by ID"""
        return self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
    
    def list_providers(
        self,
        active_only: bool = True,
        plan_type: str = None,
        industry: str = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict:
        """List providers with filters"""
        
        query = self.db.query(ServiceProvider)
        
        if active_only:
            query = query.filter(ServiceProvider.active == True)
        
        if industry:
            query = query.filter(
                ServiceProvider.industries.contains([industry])
            )
        
        total = query.count()
        providers = query.offset((page - 1) * page_size).limit(page_size).all()
        
        # Get subscription info for each
        results = []
        for provider in providers:
            sub = self.db.query(ProviderSubscription).filter(
                ProviderSubscription.provider_id == provider.provider_id
            ).first()
            
            results.append({
                "provider_id": provider.provider_id,
                "company_name": provider.company_name,
                "website": provider.website,
                "services": provider.services,
                "industries": provider.industries,
                "active": provider.active,
                "onboarding_complete": provider.onboarding_complete,
                "plan": {
                    "type": sub.plan_type if sub else None,
                    "status": sub.status if sub else None,
                    "monthly_amount": sub.monthly_amount / 100 if sub else 0
                } if sub else None,
                "created_at": provider.created_at.isoformat() if provider.created_at else None
            })
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "providers": results
        }
    
    def update_provider(
        self,
        provider_id: str,
        **kwargs
    ) -> Optional[ServiceProvider]:
        """Update provider fields"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            return None
        
        allowed_fields = [
            "company_name", "website", "description", "services",
            "industries", "icp_criteria", "case_studies", "differentiator",
            "contact_email", "billing_email", "active", "onboarding_complete"
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(provider, field):
                setattr(provider, field, value)
        
        self.db.commit()
        self.db.refresh(provider)
        
        return provider
    
    def delete_provider(self, provider_id: str) -> bool:
        """Soft delete a provider (mark inactive)"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            return False
        
        provider.active = False
        
        # Cancel subscription
        sub = self.db.query(ProviderSubscription).filter(
            ProviderSubscription.provider_id == provider_id
        ).first()
        
        if sub:
            sub.status = "cancelled"
        
        self.db.commit()
        
        return True
    
    def create_subscription(
        self,
        provider_id: str,
        plan_type: str,
        start_date: datetime = None
    ) -> Optional[ProviderSubscription]:
        """Create a subscription for a provider"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            return None
        
        if plan_type not in SUBSCRIPTION_PLANS:
            return None
        
        plan = SUBSCRIPTION_PLANS[plan_type]
        
        # Check for existing active subscription
        existing = self.db.query(ProviderSubscription).filter(
            and_(
                ProviderSubscription.provider_id == provider_id,
                ProviderSubscription.status == "active"
            )
        ).first()
        
        if existing:
            # Cancel existing
            existing.status = "cancelled"
        
        start = start_date or datetime.utcnow()
        end = start + timedelta(days=30)
        
        subscription = ProviderSubscription(
            subscription_id=f"sub-{str(uuid.uuid4())[:8]}",
            provider_id=provider_id,
            plan_type=plan_type,
            plan_name=f"{plan['name']} - ${plan['monthly_amount'] // 100}/month",
            monthly_amount=plan["monthly_amount"],
            intro_fee_per_meeting=plan["intro_fee"],
            max_matches_per_month=plan["max_matches"],
            max_intros_per_month=plan["max_intros"],
            current_period_start=start,
            current_period_end=end,
            status="active"
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        # Create billing record for first month
        self.create_billing_record(
            provider_id=provider_id,
            charge_type="subscription",
            amount=plan["monthly_amount"],
            description=f"Monthly subscription - {plan['name']} Plan",
            period_start=start,
            period_end=end
        )
        
        return subscription
    
    def get_subscription(self, subscription_id: str) -> Optional[ProviderSubscription]:
        """Get subscription by ID"""
        return self.db.query(ProviderSubscription).filter(
            ProviderSubscription.subscription_id == subscription_id
        ).first()
    
    def get_provider_subscription(self, provider_id: str) -> Optional[ProviderSubscription]:
        """Get active subscription for provider"""
        return self.db.query(ProviderSubscription).filter(
            and_(
                ProviderSubscription.provider_id == provider_id,
                ProviderSubscription.status == "active"
            )
        ).first()
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription"""
        
        sub = self.get_subscription(subscription_id)
        if not sub:
            return False
        
        sub.status = "cancelled"
        self.db.commit()
        
        return True
    
    def reset_usage_counters(self):
        """Reset monthly usage counters for all subscriptions"""
        
        subscriptions = self.db.query(ProviderSubscription).filter(
            ProviderSubscription.status == "active"
        ).all()
        
        now = datetime.utcnow()
        
        for sub in subscriptions:
            # Check if period ended
            if sub.current_period_end and sub.current_period_end < now:
                # Reset counters
                sub.matches_used_this_month = 0
                sub.intros_sent_this_month = 0
                sub.meetings_booked_this_month = 0
                
                # Extend period
                sub.current_period_start = sub.current_period_end
                sub.current_period_end = sub.current_period_start + timedelta(days=30)
                
                # Create new billing record
                self.create_billing_record(
                    provider_id=sub.provider_id,
                    charge_type="subscription",
                    amount=sub.monthly_amount,
                    description=f"Monthly subscription renewal - {sub.plan_name}",
                    period_start=sub.current_period_start,
                    period_end=sub.current_period_end
                )
        
        self.db.commit()
    
    def check_usage_limits(self, provider_id: str) -> Dict:
        """Check if provider has available quota"""
        
        sub = self.get_provider_subscription(provider_id)
        
        if not sub:
            return {
                "has_active_subscription": False,
                "can_create_match": False,
                "can_send_intro": False,
                "limits": None
            }
        
        limits = {
            "matches": {
                "used": sub.matches_used_this_month,
                "limit": sub.max_matches_per_month,
                "available": max(0, sub.max_matches_per_month - sub.matches_used_this_month)
            },
            "intros": {
                "used": sub.intros_sent_this_month,
                "limit": sub.max_intros_per_month,
                "available": max(0, sub.max_intros_per_month - sub.intros_sent_this_month)
            },
            "meetings": {
                "booked": sub.meetings_booked_this_month
            }
        }
        
        return {
            "has_active_subscription": True,
            "can_create_match": limits["matches"]["available"] > 0,
            "can_send_intro": limits["intros"]["available"] > 0,
            "limits": limits
        }
    
    def increment_match_usage(self, provider_id: str) -> bool:
        """Increment match usage counter"""
        
        sub = self.get_provider_subscription(provider_id)
        if not sub:
            return False
        
        sub.matches_used_this_month += 1
        self.db.commit()
        
        return True
    
    def increment_intro_usage(self, provider_id: str) -> bool:
        """Increment intro sent counter and charge if needed"""
        
        sub = self.get_provider_subscription(provider_id)
        if not sub:
            return False
        
        sub.intros_sent_this_month += 1
        
        # Charge intro fee if applicable
        if sub.intro_fee_per_meeting > 0:
            self.create_billing_record(
                provider_id=provider_id,
                charge_type="intro_fee",
                amount=sub.intro_fee_per_meeting,
                description=f"Intro fee (${sub.intro_fee_per_meeting // 100})"
            )
        
        self.db.commit()
        
        return True
    
    def increment_meeting_booked(self, provider_id: str) -> bool:
        """Increment meeting booked counter"""
        
        sub = self.get_provider_subscription(provider_id)
        if not sub:
            return False
        
        sub.meetings_booked_this_month += 1
        self.db.commit()
        
        return True
    
    def create_billing_record(
        self,
        provider_id: str,
        charge_type: str,
        amount: int,
        description: str,
        match_id: str = None,
        period_start: datetime = None,
        period_end: datetime = None
    ) -> ProviderBilling:
        """Create a billing record"""
        
        billing = ProviderBilling(
            billing_id=f"bill-{str(uuid.uuid4())[:8]}",
            provider_id=provider_id,
            charge_type=charge_type,
            amount=amount,
            description=description,
            match_id=match_id,
            period_start=period_start,
            period_end=period_end,
            status="pending"
        )
        
        self.db.add(billing)
        self.db.commit()
        self.db.refresh(billing)
        
        return billing
    
    def get_provider_billing(self, provider_id: str, limit: int = 50) -> List[Dict]:
        """Get billing history for provider"""
        
        billings = self.db.query(ProviderBilling).filter(
            ProviderBilling.provider_id == provider_id
        ).order_by(
            ProviderBilling.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "billing_id": b.billing_id,
                "charge_type": b.charge_type,
                "amount": b.amount / 100,
                "currency": b.currency,
                "description": b.description,
                "status": b.status,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "paid_at": b.paid_at.isoformat() if b.paid_at else None
            }
            for b in billings
        ]
    
    def get_provider_stats(self, provider_id: str) -> Dict:
        """Get comprehensive stats for provider dashboard"""
        
        provider = self.get_provider(provider_id)
        if not provider:
            return None
        
        # Subscription info
        sub = self.get_provider_subscription(provider_id)
        usage = self.check_usage_limits(provider_id)
        
        # Match stats
        from app.services.matchmaking_engine import MatchmakingEngine
        engine = MatchmakingEngine(self.db)
        match_stats = engine.get_provider_match_stats(provider_id)
        
        # Billing this month
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_billing = self.db.query(ProviderBilling).filter(
            and_(
                ProviderBilling.provider_id == provider_id,
                ProviderBilling.created_at >= month_start
            )
        ).all()
        
        total_billed = sum(b.amount for b in monthly_billing if b.status in ["pending", "paid"])
        total_paid = sum(b.amount for b in monthly_billing if b.status == "paid")
        
        return {
            "provider": {
                "provider_id": provider.provider_id,
                "company_name": provider.company_name,
                "active": provider.active,
                "onboarding_complete": provider.onboarding_complete
            },
            "subscription": {
                "plan_type": sub.plan_type if sub else None,
                "plan_name": sub.plan_name if sub else None,
                "monthly_amount": sub.monthly_amount / 100 if sub else 0,
                "status": sub.status if sub else None,
                "period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None
            },
            "usage": usage["limits"] if usage["has_active_subscription"] else None,
            "matches": match_stats,
            "billing_this_month": {
                "total_billed": total_billed / 100,
                "total_paid": total_paid / 100,
                "outstanding": (total_billed - total_paid) / 100,
                "transaction_count": len(monthly_billing)
            }
        }
    
    def get_platform_revenue_summary(
        self,
        period_type: str = "monthly",
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[Dict]:
        """Get platform-wide revenue summary"""
        
        query = self.db.query(PlatformRevenueSummary).filter(
            PlatformRevenueSummary.period_type == period_type
        )
        
        if start_date:
            query = query.filter(PlatformRevenueSummary.period_start >= start_date)
        if end_date:
            query = query.filter(PlatformRevenueSummary.period_start <= end_date)
        
        summaries = query.order_by(PlatformRevenueSummary.period_start.desc()).all()
        
        return [
            {
                "period": s.period_start.isoformat(),
                "subscription_revenue": s.subscription_revenue / 100,
                "intro_fee_revenue": s.intro_fee_revenue / 100,
                "success_fee_revenue": s.success_fee_revenue / 100,
                "total_revenue": s.total_revenue / 100,
                "active_providers": s.active_providers,
                "new_providers": s.new_providers,
                "total_matches": s.total_matches,
                "intros_sent": s.intros_sent,
                "meetings_booked": s.meetings_booked,
                "deals_closed": s.deals_closed
            }
            for s in summaries
        ]
    
    def calculate_platform_revenue(self, period_start: datetime, period_end: datetime) -> Dict:
        """Calculate revenue for a specific period"""
        
        # Get all billings in period
        billings = self.db.query(ProviderBilling).filter(
            and_(
                ProviderBilling.created_at >= period_start,
                ProviderBilling.created_at < period_end
            )
        ).all()
        
        subscription_revenue = sum(
            b.amount for b in billings 
            if b.charge_type == "subscription" and b.status in ["pending", "paid"]
        )
        
        intro_fee_revenue = sum(
            b.amount for b in billings 
            if b.charge_type == "intro_fee" and b.status in ["pending", "paid"]
        )
        
        success_fee_revenue = sum(
            b.amount for b in billings 
            if b.charge_type == "success_fee" and b.status in ["pending", "paid"]
        )
        
        # Count metrics
        active_providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).count()
        
        new_providers = self.db.query(ServiceProvider).filter(
            and_(
                ServiceProvider.created_at >= period_start,
                ServiceProvider.created_at < period_end
            )
        ).count()
        
        matches = self.db.query(Match).filter(
            and_(
                Match.created_at >= period_start,
                Match.created_at < period_end
            )
        ).count()
        
        intros = self.db.query(Match).filter(
            and_(
                Match.intro_sent_at >= period_start,
                Match.intro_sent_at < period_end
            )
        ).count()
        
        meetings = self.db.query(Match).filter(
            and_(
                Match.meeting_booked_at >= period_start,
                Match.meeting_booked_at < period_end
            )
        ).count()
        
        closed_deals = self.db.query(Match).filter(
            and_(
                Match.status == "closed_won",
                Match.deal_closed_at >= period_start,
                Match.deal_closed_at < period_end
            )
        ).count()
        
        return {
            "subscription_revenue": subscription_revenue,
            "intro_fee_revenue": intro_fee_revenue,
            "success_fee_revenue": success_fee_revenue,
            "total_revenue": subscription_revenue + intro_fee_revenue + success_fee_revenue,
            "active_providers": active_providers,
            "new_providers": new_providers,
            "total_matches": matches,
            "intros_sent": intros,
            "meetings_booked": meetings,
            "deals_closed": closed_deals
        }
