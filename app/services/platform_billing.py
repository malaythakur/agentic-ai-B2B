"""
Platform Billing & Revenue Service for B2B Matchmaking

Comprehensive revenue tracking, analytics, and billing management.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uuid

from app.models import (
    ServiceProvider, ProviderSubscription, ProviderBilling, Match,
    PlatformRevenueSummary, BuyerCompany
)


class PlatformBillingService:
    """Platform-wide billing and revenue management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_intro_fee(self, match_id: str) -> Optional[ProviderBilling]:
        """Record intro fee billing when intro is sent"""
        
        match = self.db.query(Match).filter(Match.match_id == match_id).first()
        if not match:
            return None
        
        sub = self.db.query(ProviderSubscription).filter(
            and_(
                ProviderSubscription.provider_id == match.provider_id,
                ProviderSubscription.status == "active"
            )
        ).first()
        
        if not sub or sub.intro_fee_per_meeting == 0:
            return None
        
        billing = ProviderBilling(
            billing_id=f"bill-{str(uuid.uuid4())[:8]}",
            provider_id=match.provider_id,
            charge_type="intro_fee",
            amount=sub.intro_fee_per_meeting,
            description=f"Intro fee for match with {match.buyer.company_name if match.buyer else 'Unknown'}",
            match_id=match_id,
            status="pending"
        )
        
        self.db.add(billing)
        self.db.commit()
        self.db.refresh(billing)
        
        return billing
    
    def record_success_fee(
        self,
        match_id: str,
        deal_value: int,
        percentage: float = 5.0
    ) -> Optional[ProviderBilling]:
        """Record success fee when deal closes (percentage of deal value)"""
        
        match = self.db.query(Match).filter(Match.match_id == match_id).first()
        if not match:
            return None
        
        # Calculate platform's take
        platform_fee = int(deal_value * (percentage / 100))
        
        billing = ProviderBilling(
            billing_id=f"bill-{str(uuid.uuid4())[:8]}",
            provider_id=match.provider_id,
            charge_type="success_fee",
            amount=platform_fee,
            description=f"Success fee ({percentage}%) on ${deal_value // 100} deal",
            match_id=match_id,
            status="pending"
        )
        
        self.db.add(billing)
        
        # Update match with deal value
        match.deal_value = deal_value
        match.revenue_share_amount = platform_fee
        match.deal_closed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(billing)
        
        return billing
    
    def mark_billing_paid(self, billing_id: str) -> Optional[ProviderBilling]:
        """Mark a billing record as paid"""
        
        billing = self.db.query(ProviderBilling).filter(
            ProviderBilling.billing_id == billing_id
        ).first()
        
        if not billing:
            return None
        
        billing.status = "paid"
        billing.paid_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(billing)
        
        return billing
    
    def get_outstanding_bills(self, provider_id: str = None) -> List[Dict]:
        """Get all unpaid bills"""
        
        query = self.db.query(ProviderBilling).filter(
            ProviderBilling.status == "pending"
        )
        
        if provider_id:
            query = query.filter(ProviderBilling.provider_id == provider_id)
        
        billings = query.order_by(ProviderBilling.created_at.desc()).all()
        
        return [
            {
                "billing_id": b.billing_id,
                "provider_id": b.provider_id,
                "provider_name": b.provider.company_name if b.provider else None,
                "charge_type": b.charge_type,
                "amount": b.amount / 100,
                "description": b.description,
                "created_at": b.created_at.isoformat() if b.created_at else None
            }
            for b in billings
        ]
    
    def calculate_monthly_revenue(self, year: int, month: int) -> Dict:
        """Calculate total revenue for a specific month"""
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # Get all billings in period
        billings = self.db.query(ProviderBilling).filter(
            and_(
                ProviderBilling.created_at >= start_date,
                ProviderBilling.created_at < end_date
            )
        ).all()
        
        subscription_revenue = sum(
            b.amount for b in billings 
            if b.charge_type == "subscription"
        )
        
        intro_fee_revenue = sum(
            b.amount for b in billings 
            if b.charge_type == "intro_fee"
        )
        
        success_fee_revenue = sum(
            b.amount for b in billings 
            if b.charge_type == "success_fee"
        )
        
        # Count unique providers
        provider_ids = set(b.provider_id for b in billings)
        
        return {
            "period": f"{year}-{month:02d}",
            "subscription_revenue": subscription_revenue / 100,
            "intro_fee_revenue": intro_fee_revenue / 100,
            "success_fee_revenue": success_fee_revenue / 100,
            "total_revenue": (subscription_revenue + intro_fee_revenue + success_fee_revenue) / 100,
            "active_providers": len(provider_ids),
            "total_transactions": len(billings)
        }
    
    def generate_revenue_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Generate comprehensive revenue report for date range"""
        
        # Revenue breakdown
        billings = self.db.query(ProviderBilling).filter(
            and_(
                ProviderBilling.created_at >= start_date,
                ProviderBilling.created_at <= end_date
            )
        ).all()
        
        # Revenue by type
        by_type = {}
        for b in billings:
            if b.charge_type not in by_type:
                by_type[b.charge_type] = {"count": 0, "amount": 0}
            by_type[b.charge_type]["count"] += 1
            by_type[b.charge_type]["amount"] += b.amount
        
        # Revenue by provider
        by_provider = {}
        for b in billings:
            pid = b.provider_id
            if pid not in by_provider:
                by_provider[pid] = {
                    "provider_name": b.provider.company_name if b.provider else "Unknown",
                    "total": 0
                }
            by_provider[pid]["total"] += b.amount
        
        # Sort by revenue
        top_providers = sorted(
            [
                {"provider_id": k, **v} 
                for k, v in by_provider.items()
            ],
            key=lambda x: x["total"],
            reverse=True
        )[:10]
        
        # MRR (Monthly Recurring Revenue)
        mrr = sum(
            b.amount for b in billings 
            if b.charge_type == "subscription"
        ) / 100
        
        # ARPU (Average Revenue Per User/Provider)
        unique_providers = len(by_provider)
        arpu = (sum(b.amount for b in billings) / 100) / unique_providers if unique_providers > 0 else 0
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_revenue": sum(b.amount for b in billings) / 100,
                "total_transactions": len(billings),
                "unique_providers": unique_providers,
                "mrr": mrr,
                "arpu": round(arpu, 2)
            },
            "by_charge_type": {
                k: {
                    "count": v["count"],
                    "amount": v["amount"] / 100
                }
                for k, v in by_type.items()
            },
            "top_providers": [
                {
                    "provider_id": p["provider_id"],
                    "name": p["provider_name"],
                    "revenue": p["total"] / 100
                }
                for p in top_providers
            ]
        }
    
    def save_revenue_summary(self, period_type: str, period_start: datetime) -> PlatformRevenueSummary:
        """Calculate and save revenue summary for a period"""
        
        if period_type == "daily":
            period_end = period_start + timedelta(days=1)
        elif period_type == "monthly":
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        else:
            period_end = period_start + timedelta(days=1)
        
        # Calculate metrics
        revenue_data = self.calculate_revenue_metrics(period_start, period_end)
        
        # Check if exists
        existing = self.db.query(PlatformRevenueSummary).filter(
            and_(
                PlatformRevenueSummary.period_type == period_type,
                PlatformRevenueSummary.period_start == period_start.date()
            )
        ).first()
        
        if existing:
            # Update
            existing.subscription_revenue = revenue_data["subscription_revenue"]
            existing.intro_fee_revenue = revenue_data["intro_fee_revenue"]
            existing.success_fee_revenue = revenue_data["success_fee_revenue"]
            existing.total_revenue = revenue_data["total_revenue"]
            existing.active_providers = revenue_data["active_providers"]
            existing.new_providers = revenue_data["new_providers"]
            existing.total_matches = revenue_data["total_matches"]
            existing.intros_sent = revenue_data["intros_sent"]
            existing.meetings_booked = revenue_data["meetings_booked"]
            existing.deals_closed = revenue_data["deals_closed"]
            
            self.db.commit()
            return existing
        
        # Create new
        summary = PlatformRevenueSummary(
            period_type=period_type,
            period_start=period_start.date(),
            subscription_revenue=revenue_data["subscription_revenue"],
            intro_fee_revenue=revenue_data["intro_fee_revenue"],
            success_fee_revenue=revenue_data["success_fee_revenue"],
            total_revenue=revenue_data["total_revenue"],
            active_providers=revenue_data["active_providers"],
            new_providers=revenue_data["new_providers"],
            total_matches=revenue_data["total_matches"],
            intros_sent=revenue_data["intros_sent"],
            meetings_booked=revenue_data["meetings_booked"],
            deals_closed=revenue_data["deals_closed"]
        )
        
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        
        return summary
    
    def calculate_revenue_metrics(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> Dict:
        """Calculate all revenue metrics for a period"""
        
        # Get billings
        billings = self.db.query(ProviderBilling).filter(
            and_(
                ProviderBilling.created_at >= period_start,
                ProviderBilling.created_at < period_end
            )
        ).all()
        
        subscription_revenue = sum(
            b.amount for b in billings if b.charge_type == "subscription"
        )
        
        intro_fee_revenue = sum(
            b.amount for b in billings if b.charge_type == "intro_fee"
        )
        
        success_fee_revenue = sum(
            b.amount for b in billings if b.charge_type == "success_fee"
        )
        
        # Active providers
        active_providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).count()
        
        # New providers
        new_providers = self.db.query(ServiceProvider).filter(
            and_(
                ServiceProvider.created_at >= period_start,
                ServiceProvider.created_at < period_end
            )
        ).count()
        
        # Matches
        total_matches = self.db.query(Match).filter(
            and_(
                Match.created_at >= period_start,
                Match.created_at < period_end
            )
        ).count()
        
        # Intros sent
        intros_sent = self.db.query(Match).filter(
            and_(
                Match.intro_sent_at >= period_start,
                Match.intro_sent_at < period_end
            )
        ).count()
        
        # Meetings booked
        meetings_booked = self.db.query(Match).filter(
            and_(
                Match.meeting_booked_at >= period_start,
                Match.meeting_booked_at < period_end
            )
        ).count()
        
        # Deals closed
        deals_closed = self.db.query(Match).filter(
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
            "total_matches": total_matches,
            "intros_sent": intros_sent,
            "meetings_booked": meetings_booked,
            "deals_closed": deals_closed
        }
    
    def get_provider_invoices(
        self,
        provider_id: str,
        status: str = None
    ) -> List[Dict]:
        """Get all invoices for a provider"""
        
        query = self.db.query(ProviderBilling).filter(
            ProviderBilling.provider_id == provider_id
        )
        
        if status:
            query = query.filter(ProviderBilling.status == status)
        
        billings = query.order_by(ProviderBilling.created_at.desc()).all()
        
        return [
            {
                "billing_id": b.billing_id,
                "charge_type": b.charge_type,
                "amount": b.amount / 100,
                "description": b.description,
                "status": b.status,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "paid_at": b.paid_at.isoformat() if b.paid_at else None
            }
            for b in billings
        ]
    
    def get_revenue_forecast(self, months: int = 3) -> List[Dict]:
        """Forecast revenue based on current subscriptions"""
        
        now = datetime.utcnow()
        forecasts = []
        
        for i in range(months):
            month_date = now + timedelta(days=30 * i)
            
            # Get MRR from active subscriptions
            subs = self.db.query(ProviderSubscription).filter(
                ProviderSubscription.status == "active"
            ).all()
            
            mrr = sum(s.monthly_amount for s in subs)
            
            # Estimate intro fees based on average
            avg_intros_per_provider = 5  # Conservative estimate
            total_intro_fees = sum(
                s.intro_fee_per_meeting * avg_intros_per_provider 
                for s in subs if s.intro_fee_per_meeting > 0
            )
            
            forecasts.append({
                "month": month_date.strftime("%Y-%m"),
                "projected_subscription": mrr / 100,
                "projected_intro_fees": total_intro_fees / 100,
                "total_projected": (mrr + total_intro_fees) / 100,
                "active_subscriptions": len(subs)
            })
        
        return forecasts
    
    def get_unit_economics(self) -> Dict:
        """Calculate unit economics (LTV, CAC, etc.)"""
        
        # Average revenue per provider per month
        active_providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).count()
        
        if active_providers == 0:
            return {"error": "No active providers"}
        
        # Get last 3 months revenue
        three_months_ago = datetime.utcnow() - timedelta(days=90)
        
        billings = self.db.query(ProviderBilling).filter(
            and_(
                ProviderBilling.created_at >= three_months_ago,
                ProviderBilling.status.in_(["pending", "paid"])
            )
        ).all()
        
        total_revenue = sum(b.amount for b in billings)
        arpu_monthly = (total_revenue / 3) / active_providers / 100  # 3 months
        
        # Average customer lifetime (simplified - assume 12 months)
        avg_lifetime_months = 12
        ltv = arpu_monthly * avg_lifetime_months
        
        # Assume CAC of $500 (marketing/sales cost to acquire)
        estimated_cac = 500
        
        return {
            "arpu_monthly": round(arpu_monthly, 2),
            "estimated_ltv": round(ltv, 2),
            "estimated_cac": estimated_cac,
            "ltv_cac_ratio": round(ltv / estimated_cac, 2) if estimated_cac > 0 else 0,
            "payback_period_months": round(estimated_cac / arpu_monthly, 1) if arpu_monthly > 0 else 0,
            "gross_margin_estimate": "70% (platform model)"
        }
