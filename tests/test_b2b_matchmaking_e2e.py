"""
End-to-End Test for B2B Matchmaking Platform

Tests the complete workflow:
1. Provider onboarding & subscription
2. Buyer registration
3. AI matchmaking scoring
4. Match creation & approval
5. Intro generation
6. Meeting booking & billing
7. Deal closing & success fees
8. Revenue analytics
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
from app.database import SessionLocal, engine
from app.models import (
    ServiceProvider, ProviderSubscription, BuyerCompany, Match, 
    ProviderBilling, PlatformRevenueSummary
)
from app.services.provider_management import ProviderManagementService
from app.services.buyer_management import BuyerManagementService
from app.services.matchmaking_engine import MatchmakingEngine
from app.services.intro_generator import IntroGenerator
from app.services.platform_billing import PlatformBillingService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the database migration for B2B matchmaking tables"""
    logger.info("=" * 80)
    logger.info("STEP 1: Running Database Migration")
    logger.info("=" * 80)
    
    db = SessionLocal()
    try:
        from sqlalchemy import text
        
        # First, drop tables if they exist (clean slate)
        tables_to_drop = [
            'provider_billing',
            'platform_revenue_summary',
            'matches',
            'buyer_companies',
            'provider_subscriptions',
            'service_providers'
        ]
        
        for table in tables_to_drop:
            try:
                db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                logger.info(f"Dropped table: {table}")
            except Exception as e:
                logger.warning(f"Warning dropping {table}: {e}")
        
        db.commit()
        
        # Now create the tables using SQLAlchemy models
        from app.models import ServiceProvider, BuyerCompany, Match, ProviderSubscription, ProviderBilling, PlatformRevenueSummary
        
        # Create all tables
        ServiceProvider.__table__.create(bind=engine, checkfirst=True)
        BuyerCompany.__table__.create(bind=engine, checkfirst=True)
        ProviderSubscription.__table__.create(bind=engine, checkfirst=True)
        Match.__table__.create(bind=engine, checkfirst=True)
        ProviderBilling.__table__.create(bind=engine, checkfirst=True)
        PlatformRevenueSummary.__table__.create(bind=engine, checkfirst=True)
        
        logger.info("✓ Database migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_provider_onboarding():
    """Test provider creation and subscription"""
    logger.info("=" * 80)
    logger.info("STEP 2: Testing Provider Onboarding & Subscription")
    logger.info("=" * 80)
    
    db = SessionLocal()
    try:
        service = ProviderManagementService(db)
        
        # Create a service provider
        provider = service.create_provider(
            company_name="CloudMigration Pro",
            contact_email="sales@cloudmigrationpro.com",
            billing_email="billing@cloudmigrationpro.com",
            services=["AWS Migration", "Azure Migration", "Cloud Strategy", "Cost Optimization"],
            industries=["SaaS", "Fintech", "Healthcare"],
            website="https://cloudmigrationpro.com",
            description="Expert cloud migration services for growing companies",
            icp_criteria={
                "funding_stage": ["Series A+", "Series B"],
                "employees": "50-500",
                "signals": ["recent_funding", "hiring_engineers"]
            },
            case_studies=[
                {
                    "title": "Migrated 50+ companies to AWS",
                    "result": "Average 40% cost reduction"
                }
            ],
            differentiator="Zero-downtime migration guarantee"
        )
        
        provider_id = provider.provider_id
        logger.info(f"✓ Provider created: {provider_id}")
        logger.info(f"  - Company: {provider.company_name}")
        logger.info(f"  - Email: {provider.contact_email}")
        logger.info(f"  - Services: {provider.services}")
        
        # Subscribe to Premium plan
        subscription = service.create_subscription(provider_id, "premium")
        
        logger.info(f"✓ Subscription created: {subscription.subscription_id}")
        logger.info(f"  - Plan: {subscription.plan_type}")
        logger.info(f"  - Monthly: ${subscription.monthly_amount / 100}")
        logger.info(f"  - Intro fee: ${subscription.intro_fee_per_meeting / 100}")
        logger.info(f"  - Max matches: {subscription.max_matches_per_month}")
        
        # Check usage
        usage = service.check_usage_limits(provider_id)
        logger.info(f"✓ Usage limits: {usage}")
        
        db.commit()
        return provider_id, subscription.subscription_id
    except Exception as e:
        logger.error(f"✗ Provider onboarding failed: {e}")
        db.rollback()
        return None, None
    finally:
        db.close()


def test_buyer_registration():
    """Test buyer company registration"""
    logger.info("=" * 80)
    logger.info("STEP 3: Testing Buyer Company Registration")
    logger.info("=" * 80)
    
    db = SessionLocal()
    try:
        service = BuyerManagementService(db)
        
        # Create a buyer company
        buyer = service.create_buyer(
            company_name="TechStartup XYZ",
            website="https://techstartupxyz.com",
            industry="SaaS",
            employee_count=120,
            funding_stage="Series B",
            total_funding="$20M",
            requirements=["cloud_migration", "devops", "infrastructure"],
            budget_range="$50K-$100K",
            timeline="3_months",
            signals=["recent_funding", "hiring_engineers", "expansion"],
            decision_maker_name="John Smith",
            decision_maker_title="CTO",
            decision_maker_email="john.smith@techstartupxyz.com",
            verified=True
        )
        
        buyer_id = buyer.buyer_id
        logger.info(f"✓ Buyer created: {buyer_id}")
        logger.info(f"  - Company: {buyer.company_name}")
        logger.info(f"  - Industry: {buyer.industry}")
        logger.info(f"  - Funding: {buyer.funding_stage} - {buyer.total_funding}")
        logger.info(f"  - Requirements: {buyer.requirements}")
        logger.info(f"  - Signals: {buyer.signals}")
        
        # Verify the buyer
        buyer = service.verify_buyer(buyer_id)
        logger.info(f"✓ Buyer verified: {buyer.verified}")
        
        db.commit()
        return buyer_id
    except Exception as e:
        logger.error(f"✗ Buyer registration failed: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def test_matchmaking_engine(provider_id, buyer_id):
    """Test AI matchmaking scoring and match creation"""
    logger.info("=" * 80)
    logger.info("STEP 4: Testing AI Matchmaking Engine")
    logger.info("=" * 80)
    
    db = SessionLocal()
    try:
        engine = MatchmakingEngine(db)
        
        # Fetch objects in this session
        from app.models import ServiceProvider, BuyerCompany
        provider = db.query(ServiceProvider).filter(ServiceProvider.provider_id == provider_id).first()
        buyer = db.query(BuyerCompany).filter(BuyerCompany.buyer_id == buyer_id).first()
        
        if not provider or not buyer:
            logger.error(f"Provider or buyer not found: provider_id={provider_id}, buyer_id={buyer_id}")
            return None
        
        # Calculate match score
        score, breakdown, reason = engine.calculate_match_score(provider, buyer)
        
        logger.info(f"✓ Match score calculated: {score}/100")
        logger.info(f"  - Service fit: {breakdown.get('service_fit', 0)}%")
        logger.info(f"  - Size fit: {breakdown.get('size_fit', 0)}%")
        logger.info(f"  - Timing: {breakdown.get('timing', 0)}%")
        logger.info(f"  - Budget: {breakdown.get('budget', 0)}%")
        logger.info(f"  - Signals: {breakdown.get('signals', 0)}%")
        logger.info(f"  - Match reason: {reason}")
        
        # Create match
        match = engine.create_match(provider_id, buyer_id, auto_approve=True)
        
        match_id = match.match_id
        logger.info(f"✓ Match created: {match_id}")
        logger.info(f"  - Provider: {provider.company_name}")
        logger.info(f"  - Buyer: {buyer.company_name}")
        logger.info(f"  - Score: {match.match_score}")
        logger.info(f"  - Status: {match.status}")
        logger.info(f"  - Approved: {match.provider_approved}")
        
        db.commit()
        return match_id
    except Exception as e:
        logger.error(f"✗ Matchmaking failed: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def test_match_approval(match_id):
    """Test match approval workflow"""
    logger.info("=" * 80)
    logger.info("STEP 5: Testing Match Approval Workflow")
    logger.info("=" * 80)
    
    db = SessionLocal()
    try:
        from app.models import Match
        engine = MatchmakingEngine(db)
        
        # Fetch match
        match = db.query(Match).filter(Match.match_id == match_id).first()
        
        # Approve match (if not already approved)
        if match and not match.provider_approved:
            approved_match = engine.approve_match(match_id)
            logger.info(f"✓ Match approved: {approved_match.match_id}")
            logger.info(f"  - Status: {approved_match.status}")
            db.commit()
            return approved_match  # Return object for further use in same session
        elif match:
            logger.info(f"✓ Match already approved")
            return match
        else:
            logger.error(f"Match not found: {match_id}")
            return None
    except Exception as e:
        logger.error(f"✗ Match approval failed: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def test_intro_generation(match_id):
    """Test intro email generation"""
    logger.info("=" * 80)
    logger.info("STEP 6: Testing Intro Email Generation")
    logger.info("=" * 80)
    
    db = SessionLocal()
    try:
        generator = IntroGenerator(db)
        
        # Preview intro
        preview = generator.preview_intro(match_id)
        
        logger.info(f"✓ Intro preview generated")
        logger.info(f"  - Subject: {preview.get('subject')}")
        logger.info(f"  - To: {preview.get('to_email')}")
        logger.info(f"  - From: {preview.get('from_email')}")
        logger.info(f"  - Body preview: {preview.get('body', '')[:200]}...")
        
        return preview
    except Exception as e:
        logger.error(f"✗ Intro generation failed: {e}")
        return None
    finally:
        db.close()


def test_meeting_booking(match_id):
    """Test meeting booking and intro fee billing"""
    logger.info("=" * 80)
    logger.info("STEP 7: Testing Meeting Booking & Intro Fee Billing")
    logger.info("=" * 80)
    
    db = SessionLocal()
    try:
        from app.models import Match
        from app.services.provider_management import ProviderManagementService
        from app.services.platform_billing import PlatformBillingService
        
        # Update match to book meeting
        match = db.query(Match).filter(Match.match_id == match_id).first()
        meeting_date = datetime.utcnow() + timedelta(days=7)
        
        match.meeting_booked_at = datetime.utcnow()
        match.meeting_date = meeting_date
        match.meeting_status = "scheduled"
        match.status = "meeting_booked"
        
        # Increment provider meeting count
        provider_service = ProviderManagementService(db)
        provider_service.increment_meeting_booked(match.provider_id)
        
        # Record intro fee billing
        billing_service = PlatformBillingService(db)
        billing = billing_service.record_intro_fee(match_id)
        
        logger.info(f"✓ Meeting booked: {match.match_id}")
        logger.info(f"  - Meeting date: {meeting_date}")
        logger.info(f"  - Status: {match.status}")
        
        if billing:
            logger.info(f"✓ Intro fee billing created")
            logger.info(f"  - Billing ID: {billing.billing_id}")
            logger.info(f"  - Amount: ${billing.amount / 100}")
            logger.info(f"  - Charge type: {billing.charge_type}")
            logger.info(f"  - Description: {billing.description}")
        
        db.commit()
        return match_id, billing  # Return ID instead of object
    except Exception as e:
        logger.error(f"✗ Meeting booking failed: {e}")
        db.rollback()
        return None, None
    finally:
        db.close()


def test_deal_closing(match_id):
    """Test deal closing and success fee billing"""
    logger.info("=" * 80)
    logger.info("STEP 8: Testing Deal Closing & Success Fee")
    logger.info("=" * 80)
    
    db = SessionLocal()
    try:
        from app.models import Match
        from app.services.platform_billing import PlatformBillingService
        
        # Update match to close deal
        match = db.query(Match).filter(Match.match_id == match_id).first()
        deal_value = 7500000  # $75,000 deal
        platform_percentage = 5.0
        
        match.status = "closed_won"
        match.deal_value = deal_value
        match.deal_closed_at = datetime.utcnow()
        
        # Calculate and record success fee
        billing_service = PlatformBillingService(db)
        billing = billing_service.record_success_fee(
            match_id, deal_value, platform_percentage
        )
        
        logger.info(f"✓ Deal closed: {match.match_id}")
        logger.info(f"  - Deal value: ${deal_value / 100}")
        logger.info(f"  - Platform percentage: {platform_percentage}%")
        logger.info(f"  - Status: {match.status}")
        
        if billing:
            logger.info(f"✓ Success fee billing created")
            logger.info(f"  - Billing ID: {billing.billing_id}")
            logger.info(f"  - Amount: ${billing.amount / 100}")
            logger.info(f"  - Charge type: {billing.charge_type}")
            logger.info(f"  - Description: {billing.description}")
        
        db.commit()
        return match_id, billing  # Return ID instead of object
    except Exception as e:
        logger.error(f"✗ Deal closing failed: {e}")
        db.rollback()
        return None, None
    finally:
        db.close()


def test_revenue_analytics():
    """Test revenue dashboard and analytics"""
    logger.info("=" * 80)
    logger.info("STEP 9: Testing Revenue Dashboard & Analytics")
    logger.info("=" * 80)
    
    db = SessionLocal()
    try:
        from app.models import ServiceProvider, BuyerCompany, Match, ProviderSubscription
        from app.services.platform_billing import PlatformBillingService
        
        billing_service = PlatformBillingService(db)
        
        # Get outstanding bills
        outstanding = billing_service.get_outstanding_bills()
        logger.info(f"✓ Outstanding bills: {len(outstanding)}")
        for bill in outstanding[:3]:
            logger.info(f"  - {bill['billing_id']}: ${bill['amount']} ({bill['charge_type']})")
        
        # Get monthly revenue
        now = datetime.utcnow()
        monthly_revenue = billing_service.calculate_monthly_revenue(now.year, now.month)
        logger.info(f"✓ Monthly revenue ({now.year}-{now.month:02d}):")
        logger.info(f"  - Subscription: ${monthly_revenue['subscription_revenue']}")
        logger.info(f"  - Intro fees: ${monthly_revenue['intro_fee_revenue']}")
        logger.info(f"  - Success fees: ${monthly_revenue['success_fee_revenue']}")
        logger.info(f"  - Total: ${monthly_revenue['total_revenue']}")
        logger.info(f"  - Active providers: {monthly_revenue['active_providers']}")
        
        # Get revenue forecast
        forecast = billing_service.get_revenue_forecast(months=3)
        logger.info(f"✓ 3-month revenue forecast:")
        for month in forecast:
            logger.info(f"  - {month['month']}: ${month['total_projected']} total")
        
        # Get unit economics
        economics = billing_service.get_unit_economics()
        logger.info(f"✓ Unit economics:")
        logger.info(f"  - ARPU (monthly): ${economics.get('arpu_monthly', 0)}")
        logger.info(f"  - LTV: ${economics.get('estimated_ltv', 0)}")
        logger.info(f"  - CAC: ${economics.get('estimated_cac', 0)}")
        logger.info(f"  - LTV/CAC: {economics.get('ltv_cac_ratio', 0)}x")
        
        # Get platform dashboard
        total_providers = db.query(ServiceProvider).filter(ServiceProvider.active == True).count()
        total_buyers = db.query(BuyerCompany).filter(BuyerCompany.active == True).count()
        total_matches = db.query(Match).count()
        deals_closed = db.query(Match).filter(Match.status == "closed_won").count()
        
        logger.info(f"✓ Platform dashboard:")
        logger.info(f"  - Active providers: {total_providers}")
        logger.info(f"  - Active buyers: {total_buyers}")
        logger.info(f"  - Total matches: {total_matches}")
        logger.info(f"  - Deals closed: {deals_closed}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Revenue analytics failed: {e}")
        return False
    finally:
        db.close()


def run_e2e_test():
    """Run the complete end-to-end test"""
    logger.info("\n" + "=" * 80)
    logger.info("B2B MATCHMAKING PLATFORM - END-TO-END TEST")
    logger.info("=" * 80 + "\n")
    
    results = {}
    
    # Step 1: Run migration
    if not run_migration():
        logger.error("Migration failed - aborting test")
        return False
    results['migration'] = 'PASS'
    
    # Step 2: Provider onboarding
    provider_id, subscription_id = test_provider_onboarding()
    if not provider_id:
        logger.error("Provider onboarding failed - aborting test")
        return False
    results['provider_onboarding'] = 'PASS'
    
    # Step 3: Buyer registration
    buyer_id = test_buyer_registration()
    if not buyer_id:
        logger.error("Buyer registration failed - aborting test")
        return False
    results['buyer_registration'] = 'PASS'
    
    # Step 4: Matchmaking engine
    match_id = test_matchmaking_engine(provider_id, buyer_id)
    if not match_id:
        logger.error("Matchmaking failed - aborting test")
        return False
    results['matchmaking'] = 'PASS'
    
    # Step 5: Match approval
    approved_match = test_match_approval(match_id)
    if not approved_match:
        logger.error("Match approval failed")
        results['match_approval'] = 'FAIL'
    else:
        results['match_approval'] = 'PASS'
    
    # Step 6: Intro generation
    preview = test_intro_generation(match_id)
    if not preview:
        logger.error("Intro generation failed")
        results['intro_generation'] = 'FAIL'
    else:
        results['intro_generation'] = 'PASS'
    
    # Step 7: Meeting booking
    booked_match_id, billing = test_meeting_booking(match_id)
    if not booked_match_id:
        logger.error("Meeting booking failed")
        results['meeting_booking'] = 'FAIL'
    else:
        results['meeting_booking'] = 'PASS'
    
    # Step 8: Deal closing
    closed_match_id, success_billing = test_deal_closing(match_id)
    if not closed_match_id:
        logger.error("Deal closing failed")
        results['deal_closing'] = 'FAIL'
    else:
        results['deal_closing'] = 'PASS'
    
    # Step 9: Revenue analytics
    if test_revenue_analytics():
        results['revenue_analytics'] = 'PASS'
    else:
        results['revenue_analytics'] = 'FAIL'
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    for step, status in results.items():
        symbol = "✓" if status == "PASS" else "✗"
        logger.info(f"{symbol} {step}: {status}")
    
    passed = sum(1 for s in results.values() if s == "PASS")
    total = len(results)
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! B2B Matchmaking Platform is working end-to-end.")
        return True
    else:
        logger.error(f"\n❌ {total - passed} test(s) failed.")
        return False


if __name__ == "__main__":
    success = run_e2e_test()
    sys.exit(0 if success else 1)
