"""
Transactional Billing Service

Transaction-based revenue model for outbound-first operations:
- Pay-per-intro: $500 per qualified intro sent
- Pay-per-meeting: $1,000 per meeting booked
- Pay-for-insights: $200/mo for prospect database access
- Success fee: 5% of closed deals
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import SessionLocal
from app.models import ProviderBilling, PlatformRevenueSummary

logger = logging.getLogger(__name__)


class TransactionalBillingService:
    """Service for transaction-based billing"""
    
    # Pricing configuration
    PRICING = {
        "intro_fee": 50000,  # $500 in cents
        "meeting_fee": 100000,  # $1,000 in cents
        "insights_subscription": 20000,  # $200/mo in cents
        "success_fee_percentage": 5.0,  # 5%
    }
    
    def __init__(self):
        """Initialize transactional billing service"""
        pass
    
    def record_intro_fee(
        self,
        prospect_id: str,
        provider_id: str,
        outreach_id: Optional[str] = None
    ) -> Optional[ProviderBilling]:
        """
        Record fee for sending a qualified intro
        
        Args:
            prospect_id: Prospect ID
            provider_id: Provider ID
            outreach_id: Outreach message ID
            
        Returns:
            Billing record
        """
        db = SessionLocal()
        try:
            billing = ProviderBilling(
                billing_id=f"bill-intro-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                provider_id=provider_id,
                charge_type="intro_fee",
                amount=self.PRICING["intro_fee"],
                currency="USD",
                description=f"Qualified intro to prospect {prospect_id}",
                status="pending",
                metadata={
                    "prospect_id": prospect_id,
                    "outreach_id": outreach_id,
                    "fee_type": "intro"
                },
                created_at=datetime.utcnow()
            )
            
            db.add(billing)
            db.commit()
            
            logger.info(f"Recorded intro fee: ${self.PRICING['intro_fee']/100} for provider {provider_id}")
            return billing
            
        except Exception as e:
            logger.error(f"Failed to record intro fee: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    def record_meeting_fee(
        self,
        prospect_id: str,
        provider_id: str,
        outreach_id: Optional[str] = None
    ) -> Optional[ProviderBilling]:
        """
        Record fee for booking a meeting
        
        Args:
            prospect_id: Prospect ID
            provider_id: Provider ID
            outreach_id: Outreach message ID
            
        Returns:
            Billing record
        """
        db = SessionLocal()
        try:
            billing = ProviderBilling(
                billing_id=f"bill-meeting-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                provider_id=provider_id,
                charge_type="meeting_fee",
                amount=self.PRICING["meeting_fee"],
                currency="USD",
                description=f"Meeting booked with prospect {prospect_id}",
                status="pending",
                metadata={
                    "prospect_id": prospect_id,
                    "outreach_id": outreach_id,
                    "fee_type": "meeting"
                },
                created_at=datetime.utcnow()
            )
            
            db.add(billing)
            db.commit()
            
            logger.info(f"Recorded meeting fee: ${self.PRICING['meeting_fee']/100} for provider {provider_id}")
            return billing
            
        except Exception as e:
            logger.error(f"Failed to record meeting fee: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    def record_success_fee(
        self,
        prospect_id: str,
        provider_id: str,
        deal_value_cents: int,
        percentage: Optional[float] = None
    ) -> Optional[ProviderBilling]:
        """
        Record success fee on closed deal
        
        Args:
            prospect_id: Prospect ID
            provider_id: Provider ID
            deal_value_cents: Deal value in cents
            percentage: Success fee percentage (default from config)
            
        Returns:
            Billing record
        """
        db = SessionLocal()
        try:
            percentage = percentage or self.PRICING["success_fee_percentage"]
            fee_cents = int(deal_value_cents * (percentage / 100))
            
            billing = ProviderBilling(
                billing_id=f"bill-success-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                provider_id=provider_id,
                charge_type="success_fee",
                amount=fee_cents,
                currency="USD",
                description=f"Success fee ({percentage}%) on ${deal_value_cents/100:,.0f} deal with prospect {prospect_id}",
                status="pending",
                metadata={
                    "prospect_id": prospect_id,
                    "deal_value_cents": deal_value_cents,
                    "percentage": percentage,
                    "fee_type": "success"
                },
                created_at=datetime.utcnow()
            )
            
            db.add(billing)
            db.commit()
            
            logger.info(f"Recorded success fee: ${fee_cents/100:,.0f} ({percentage}% of ${deal_value_cents/100:,.0f})")
            return billing
            
        except Exception as e:
            logger.error(f"Failed to record success fee: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    def record_insights_subscription(
        self,
        provider_id: str,
        months: int = 1
    ) -> Optional[ProviderBilling]:
        """
        Record insights subscription fee
        
        Args:
            provider_id: Provider ID
            months: Number of months
            
        Returns:
            Billing record
        """
        db = SessionLocal()
        try:
            amount = self.PRICING["insights_subscription"] * months
            
            billing = ProviderBilling(
                billing_id=f"bill-insights-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                provider_id=provider_id,
                charge_type="insights_subscription",
                amount=amount,
                currency="USD",
                description=f"Prospect database access ({months} month{'s' if months > 1 else ''})",
                status="pending",
                metadata={
                    "months": months,
                    "fee_type": "insights"
                },
                created_at=datetime.utcnow()
            )
            
            db.add(billing)
            db.commit()
            
            logger.info(f"Recorded insights subscription: ${amount/100} for {months} month(s)")
            return billing
            
        except Exception as e:
            logger.error(f"Failed to record insights subscription: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    def get_provider_outstanding_balance(self, provider_id: str) -> Dict:
        """
        Get outstanding balance for a provider
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Balance dict
        """
        db = SessionLocal()
        try:
            outstanding = db.query(ProviderBilling).filter(
                ProviderBilling.provider_id == provider_id,
                ProviderBilling.status == "pending"
            ).all()
            
            total_cents = sum(b.amount for b in outstanding)
            
            # Breakdown by charge type
            breakdown = {}
            for bill in outstanding:
                charge_type = bill.charge_type
                breakdown[charge_type] = breakdown.get(charge_type, 0) + bill.amount
            
            return {
                "provider_id": provider_id,
                "total_outstanding_cents": total_cents,
                "total_outstanding_usd": total_cents / 100,
                "item_count": len(outstanding),
                "breakdown": {k: v/100 for k, v in breakdown.items()}
            }
            
        except Exception as e:
            logger.error(f"Failed to get outstanding balance: {e}")
            return {
                "provider_id": provider_id,
                "total_outstanding_cents": 0,
                "total_outstanding_usd": 0,
                "item_count": 0,
                "breakdown": {}
            }
        finally:
            db.close()
    
    def mark_bill_paid(self, billing_id: str) -> bool:
        """
        Mark a bill as paid
        
        Args:
            billing_id: Billing ID
            
        Returns:
            Success status
        """
        db = SessionLocal()
        try:
            billing = db.query(ProviderBilling).filter(
                ProviderBilling.billing_id == billing_id
            ).first()
            
            if billing:
                billing.status = "paid"
                billing.paid_at = datetime.utcnow()
                db.commit()
                logger.info(f"Marked bill {billing_id} as paid")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to mark bill as paid: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def calculate_monthly_revenue(self, year: int, month: int) -> Dict:
        """
        Calculate revenue for a specific month
        
        Args:
            year: Year
            month: Month
            
        Returns:
            Revenue breakdown
        """
        db = SessionLocal()
        try:
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)
            
            bills = db.query(ProviderBilling).filter(
                ProviderBilling.created_at >= start_date,
                ProviderBilling.created_at < end_date
            ).all()
            
            # Breakdown by charge type
            breakdown = {
                "intro_fee": 0,
                "meeting_fee": 0,
                "success_fee": 0,
                "insights_subscription": 0
            }
            
            for bill in bills:
                charge_type = bill.charge_type
                if charge_type in breakdown:
                    breakdown[charge_type] += bill.amount
            
            total = sum(breakdown.values())
            
            return {
                "year": year,
                "month": month,
                "intro_fee_revenue": breakdown["intro_fee"] / 100,
                "meeting_fee_revenue": breakdown["meeting_fee"] / 100,
                "success_fee_revenue": breakdown["success_fee"] / 100,
                "insights_revenue": breakdown["insights_subscription"] / 100,
                "total_revenue": total / 100,
                "transaction_count": len(bills)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate monthly revenue: {e}")
            return {
                "year": year,
                "month": month,
                "intro_fee_revenue": 0,
                "meeting_fee_revenue": 0,
                "success_fee_revenue": 0,
                "insights_revenue": 0,
                "total_revenue": 0,
                "transaction_count": 0
            }
        finally:
            db.close()
    
    def get_revenue_forecast(self, months: int = 3) -> List[Dict]:
        """
        Forecast revenue for upcoming months
        
        Args:
            months: Number of months to forecast
            
        Returns:
            List of monthly forecasts
        """
        forecast = []
        now = datetime.utcnow()
        
        for i in range(months):
            forecast_date = now + timedelta(days=30 * (i + 1))
            year = forecast_date.year
            month = forecast_date.month
            
            # Simple forecast: assume same as previous month's revenue
            # In production, this would use historical trends and pipeline analysis
            previous_month = forecast_date - timedelta(days=30)
            historical = self.calculate_monthly_revenue(previous_month.year, previous_month.month)
            
            # Apply growth factor (conservative 10% month-over-month)
            growth_factor = 1.1
            
            forecast.append({
                "month": f"{year}-{month:02d}",
                "projected_revenue": historical["total_revenue"] * growth_factor,
                "projected_transactions": int(historical["transaction_count"] * growth_factor),
                "confidence": "medium"
            })
        
        return forecast


# Example usage
if __name__ == "__main__":
    service = TransactionalBillingService()
    
    # Record intro fee
    bill = service.record_intro_fee("prospect-123", "provider-456", "outreach-789")
    print(f"Intro fee recorded: {bill.billing_id}")
    
    # Record meeting fee
    bill = service.record_meeting_fee("prospect-123", "provider-456", "outreach-789")
    print(f"Meeting fee recorded: {bill.billing_id}")
    
    # Record success fee
    bill = service.record_success_fee("prospect-123", "provider-456", 7500000)  # $75,000 deal
    print(f"Success fee recorded: {bill.billing_id}")
    
    # Get outstanding balance
    balance = service.get_provider_outstanding_balance("provider-456")
    print(f"Outstanding balance: ${balance['total_outstanding_usd']}")
