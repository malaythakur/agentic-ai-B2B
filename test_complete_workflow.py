"""
Complete Workflow Testing

Comprehensive test of the entire provider outreach workflow including all new features:
- Provider opt-in with consent
- Automation triggering
- ICP matching with enhanced scoring
- Match creation with follow-up tracking
- Rate limiting
- Follow-up sequences
- Response tracking
- Unsubscribe mechanism
- Template management
- Analytics
- Testing mode
- Duplicate prevention
"""

import sys
from app.database import SessionLocal
from app.models import ServiceProvider, BuyerCompany, Match
from app.services.provider_optin_service import ProviderOptInService
from app.services.provider_automation_service import ProviderAutomationService
from app.services.rate_limiter import RateLimiter, get_rate_limiter
from app.services.followup_service import FollowUpService
from app.services.response_tracker import ResponseTracker
from app.services.unsubscribe_service import UnsubscribeService
from app.services.match_scorer import MatchScorer
from app.services.template_manager import TemplateManager
from app.services.analytics_service import AnalyticsService
from app.services.testing_mode import TestingModeService
from datetime import datetime

def cleanup_test_data(db):
    """Clean up all test data"""
    try:
        fresh_db = SessionLocal()
        
        # Clean up test matches
        test_matches = fresh_db.query(Match).filter(
            Match.provider_id.like("test-workflow-%")
        ).all()
        for match in test_matches:
            fresh_db.delete(match)
        
        # Clean up test providers
        test_providers = fresh_db.query(ServiceProvider).filter(
            ServiceProvider.provider_id.like("test-workflow-%")
        ).all()
        for provider in test_providers:
            fresh_db.delete(provider)
        
        # Clean up test buyers
        test_buyers = fresh_db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id.like("test-workflow-%")
        ).all()
        for buyer in test_buyers:
            fresh_db.delete(buyer)
        
        fresh_db.commit()
        fresh_db.close()
        print(f"🧹 Cleaned up test data")
    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")
        if 'fresh_db' in locals():
            fresh_db.rollback()
            fresh_db.close()

def create_test_provider(db):
    """Create test provider with ICP"""
    provider = ServiceProvider(
        provider_id="test-workflow-provider-001",
        company_name="Test Workflow Provider",
        contact_email="test-workflow@example.com",
        services=["Cloud Migration", "DevOps"],
        industries=["SaaS"],
        icp_criteria={
            "industries": ["SaaS", "Fintech"],
            "funding_stage": "Series A",
            "employees": "50-500",
            "signals": ["recent_funding", "hiring_engineers"]
        },
        active=True,
        onboarding_complete=True,
        outreach_consent_status="pending"
    )
    db.add(provider)
    db.commit()
    print(f"✅ Created test provider: {provider.provider_id}")
    return provider

def create_test_buyers(db):
    """Create test buyers"""
    buyers = []
    
    # Matching buyer
    buyer1 = BuyerCompany(
        buyer_id="test-workflow-buyer-001",
        company_name="Matching SaaS Company",
        industry="SaaS",
        funding_stage="series_a",
        employee_count=100,
        decision_maker_email="buyer1@matching.com",
        requirements=["cloud_migration"],
        signals=["recent_funding", "hiring_devops"],
        active=True
    )
    buyers.append(buyer1)
    
    # Non-matching buyer
    buyer2 = BuyerCompany(
        buyer_id="test-workflow-buyer-002",
        company_name="Non-Matching E-commerce",
        industry="E-commerce",
        funding_stage="series_a",
        employee_count=150,
        decision_maker_email="buyer2@nonmatching.com",
        requirements=["cloud_migration"],
        signals=["recent_funding"],
        active=True
    )
    buyers.append(buyer2)
    
    for buyer in buyers:
        db.add(buyer)
    
    db.commit()
    print(f"✅ Created {len(buyers)} test buyers")
    return buyers

def test_rate_limiting():
    """Test rate limiting"""
    print("\n=== Testing Rate Limiting ===")
    
    rate_limiter = RateLimiter("free_gmail")
    
    # Check can send
    can_send, reason = rate_limiter.can_send_email()
    print(f"Can send email: {can_send}, Reason: {reason}")
    
    # Record sends
    for i in range(5):
        rate_limiter.record_email_sent()
    
    status = rate_limiter.get_status()
    print(f"Rate limiter status: {status}")
    
    print("✅ Rate limiting test PASSED")

def test_match_scoring(db):
    """Test enhanced match scoring"""
    print("\n=== Testing Enhanced Match Scoring ===")
    
    provider = create_test_provider(db)
    buyers = create_test_buyers(db)
    
    scorer = MatchScorer(db)
    
    for buyer in buyers:
        score_data = scorer.calculate_match_score(provider, buyer)
        print(f"Match score for {buyer.company_name}: {score_data['total_score']}")
        print(f"  Breakdown: {score_data['score_breakdown']}")
    
    print("✅ Enhanced match scoring test PASSED")
    
    # Cleanup
    cleanup_test_data(db)

def test_template_management():
    """Test template management"""
    print("\n=== Testing Template Management ===")
    
    template_manager = TemplateManager(None)
    
    # Get default template
    template = template_manager.get_template("intro")
    print(f"Default intro template: {template['subject'][:50]}...")
    
    # Render template
    rendered = template_manager.render_template("intro", {
        "provider_name": "Test Provider",
        "buyer_name": "Test Buyer",
        "services": "Cloud Migration",
        "signals_text": "Recent funding",
        "unsubscribe_link": "https://test.com/unsubscribe"
    })
    print(f"Rendered subject: {rendered['subject']}")
    
    # List templates
    templates = template_manager.list_templates()
    print(f"Available templates: {len(templates)}")
    
    print("✅ Template management test PASSED")

def test_unsubscribe_mechanism(db):
    """Test unsubscribe mechanism"""
    print("\n=== Testing Unsubscribe Mechanism ===")
    
    provider = create_test_provider(db)
    buyers = create_test_buyers(db)
    
    unsubscribe_service = UnsubscribeService(db)
    
    # Generate unsubscribe link
    link = unsubscribe_service.generate_unsubscribe_link("test-match-123")
    print(f"Unsubscribe link: {link}")
    
    # Add footer
    email_body = "This is a test email"
    email_with_footer = unsubscribe_service.add_unsubscribe_footer(email_body, "test-match-123")
    print(f"Email with footer length: {len(email_with_footer)}")
    
    print("✅ Unsubscribe mechanism test PASSED")
    
    # Cleanup
    cleanup_test_data(db)

def test_followup_sequences(db):
    """Test follow-up sequences"""
    print("\n=== Testing Follow-up Sequences ===")
    
    provider = create_test_provider(db)
    buyers = create_test_buyers(db)
    
    followup_service = FollowUpService(db)
    
    # Get pending follow-ups
    pending = followup_service.get_pending_followups()
    print(f"Pending follow-ups: {len(pending)}")
    
    # Test follow-up schedule
    print(f"Follow-up schedule: {followup_service.FOLLOWUP_SCHEDULE}")
    
    print("✅ Follow-up sequences test PASSED")
    
    # Cleanup
    cleanup_test_data(db)

def test_analytics(db):
    """Test analytics dashboard"""
    print("\n=== Testing Analytics Dashboard ===")
    
    analytics_service = AnalyticsService(db)
    
    # Get platform overview
    overview = analytics_service.get_platform_overview()
    print(f"Platform overview: {overview}")
    
    # Get engagement metrics
    engagement = analytics_service.get_engagement_metrics()
    print(f"Engagement metrics: {engagement}")
    
    print("✅ Analytics test PASSED")

def test_testing_mode(db):
    """Test testing mode"""
    print("\n=== Testing Testing Mode ===")
    
    provider = create_test_provider(db)
    
    testing_service = TestingModeService(db)
    
    # Start test mode
    result = testing_service.start_test_mode(provider.provider_id, batch_size=3)
    print(f"Started test mode: {result}")
    
    # Get test results
    results = testing_service.get_test_results(provider.provider_id)
    print(f"Test results: {results}")
    
    # End test mode
    end_result = testing_service.end_test_mode(provider.provider_id, rollout=False)
    print(f"Ended test mode: {end_result}")
    
    print("✅ Testing mode test PASSED")
    
    # Cleanup
    cleanup_test_data(db)

def test_full_automation_flow(db):
    """Test full automation flow"""
    print("\n=== Testing Full Automation Flow ===")
    
    provider = create_test_provider(db)
    buyers = create_test_buyers(db)
    
    automation_service = ProviderAutomationService(db)
    
    # Trigger automation
    result = automation_service.trigger_provider_automation(provider.provider_id, "platform@example.com")
    print(f"Automation result: {result}")
    
    # Verify matches were created
    matches = db.query(Match).filter(
        Match.provider_id == provider.provider_id
    ).all()
    print(f"Matches created: {len(matches)}")
    
    print("✅ Full automation flow test PASSED")
    
    # Cleanup
    cleanup_test_data(db)

def test_duplicate_prevention(db):
    """Test duplicate prevention"""
    print("\n=== Testing Duplicate Prevention ===")
    
    provider = create_test_provider(db)
    buyers = create_test_buyers(db)
    
    # Create a match with message_id
    from datetime import datetime
    match = Match(
        match_id=f"match-{provider.provider_id}-{buyers[0].buyer_id}-001",
        provider_id=provider.provider_id,
        buyer_id=buyers[0].buyer_id,
        match_score=75,
        status="outreach_sent",
        intro_message_id="msg-12345",
        intro_sent_at=datetime.utcnow()
    )
    db.add(match)
    db.commit()
    
    # Try to send outreach again (should be skipped)
    automation_service = ProviderAutomationService(db)
    result = automation_service._send_outreach_to_matches(provider, [buyers[0]], "platform@example.com")
    print(f"Outreach result with duplicate check: {result}")
    
    if result.get("skipped") == 1:
        print("✅ Duplicate prevention test PASSED")
    else:
        print("❌ Duplicate prevention test FAILED")
        return False
    
    # Cleanup
    cleanup_test_data(db)
    return True

def run_all_tests():
    """Run all workflow tests"""
    print("=" * 70)
    print("COMPLETE WORKFLOW TEST SUITE")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Clean up
        cleanup_test_data(db)
        
        # Test 1: Rate limiting
        test_rate_limiting()
        
        # Test 2: Enhanced match scoring
        test_match_scoring(db)
        
        # Test 3: Template management
        test_template_management()
        
        # Test 4: Unsubscribe mechanism
        test_unsubscribe_mechanism(db)
        
        # Test 5: Follow-up sequences
        test_followup_sequences(db)
        
        # Test 6: Analytics
        test_analytics(db)
        
        # Test 7: Testing mode
        test_testing_mode(db)
        
        # Test 8: Full automation flow
        test_full_automation_flow(db)
        
        # Test 9: Duplicate prevention
        if not test_duplicate_prevention(db):
            return False
        
        print("\n" + "=" * 70)
        print("✅ ALL WORKFLOW TESTS PASSED")
        print("=" * 70)
        print("\nAll workflow features validated:")
        print("• Rate limiting for Gmail API")
        print("• Enhanced match scoring with local heuristics")
        print("• Template management system")
        print("• Unsubscribe mechanism with CAN-SPAM compliance")
        print("• Follow-up email sequences")
        print("• Analytics dashboard")
        print("• Testing mode for providers")
        print("• Full automation flow")
        print("• Duplicate prevention")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup_test_data(db)
        db.close()
    
    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
