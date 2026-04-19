"""
Test Duplicate Email Prevention

This script tests that duplicate emails are not sent:
- Provider opt-in email duplicate prevention
- Buyer outreach email duplicate prevention
"""

import sys
from app.database import SessionLocal
from app.models import ServiceProvider, BuyerCompany, Match
from app.services.provider_optin_service import ProviderOptInService
from app.services.provider_automation_service import ProviderAutomationService

def cleanup_test_data(db):
    """Clean up test data"""
    try:
        fresh_db = SessionLocal()
        
        # Clean up test matches
        test_matches = fresh_db.query(Match).filter(
            Match.provider_id.like("test-duplicate-provider-%")
        ).all()
        for match in test_matches:
            fresh_db.delete(match)
        
        # Clean up test providers
        test_providers = fresh_db.query(ServiceProvider).filter(
            ServiceProvider.provider_id.like("test-duplicate-provider-%")
        ).all()
        for provider in test_providers:
            fresh_db.delete(provider)
        
        # Clean up test buyers
        test_buyers = fresh_db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id.like("test-duplicate-buyer-%")
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

def test_provider_optin_duplicate_prevention(db):
    """Test that provider opt-in email is not sent twice"""
    print("\n=== Testing Provider Opt-In Duplicate Prevention ===\n")
    
    # Create test provider
    provider = ServiceProvider(
        provider_id="test-duplicate-provider-001",
        company_name="Test Duplicate Provider",
        contact_email="test-duplicate@example.com",
        services=["Test Service"],
        industries=["SaaS"],
        active=True,
        onboarding_complete=True,
        outreach_consent_status="pending"
    )
    db.add(provider)
    db.commit()
    print(f"✅ Created test provider: {provider.provider_id}")
    
    service = ProviderOptInService(db=db)
    
    # First send should succeed (no Gmail, so it will fail due to Gmail not initialized, but should check the logic)
    result1 = service.send_optin_email(provider.provider_id, "platform@example.com")
    print(f"First send attempt: {result1}")
    
    # Manually set opt_in_email_sent_at to simulate email being sent
    provider.opt_in_email_sent_at = None  # Will be set by the method if Gmail works
    db.commit()
    
    # Second send should be prevented (even if we manually set the timestamp)
    provider.opt_in_email_sent_at = None  # Reset for testing
    db.commit()
    
    # Simulate email was sent by setting the timestamp
    from datetime import datetime
    provider.opt_in_email_sent_at = datetime.utcnow()
    db.commit()
    
    result2 = service.send_optin_email(provider.provider_id, "platform@example.com")
    print(f"Second send attempt (should be prevented): {result2}")
    
    # Verify second attempt was prevented
    if result2.get("error") == "Opt-in email already sent":
        print("✅ Duplicate opt-in email prevention works")
    else:
        print("❌ Duplicate opt-in email prevention FAILED")
        return False
    
    # Cleanup
    db.delete(provider)
    db.commit()
    return True

def test_buyer_outreach_duplicate_prevention(db):
    """Test that buyer outreach email is not sent twice to same buyer-provider pair"""
    print("\n=== Testing Buyer Outreach Duplicate Prevention ===\n")
    
    # Create test provider
    provider = ServiceProvider(
        provider_id="test-duplicate-provider-002",
        company_name="Test Duplicate Provider 2",
        contact_email="test-duplicate2@example.com",
        services=["Test Service"],
        industries=["SaaS"],
        icp_criteria={"industries": ["SaaS"]},
        active=True,
        onboarding_complete=True,
        auto_outreach_enabled=True,
        outreach_consent_status="consented",
        automation_settings={}
    )
    db.add(provider)
    db.commit()
    
    # Create test buyer
    buyer = BuyerCompany(
        buyer_id="test-duplicate-buyer-001",
        company_name="Test Duplicate Buyer",
        industry="SaaS",
        decision_maker_email="buyer@example.com",
        signals=["recent_funding"],
        active=True
    )
    db.add(buyer)
    db.commit()
    
    # Create a match with intro_message_id (simulating email already sent)
    from datetime import datetime
    match = Match(
        match_id=f"match-{provider.provider_id}-{buyer.buyer_id}-001",
        provider_id=provider.provider_id,
        buyer_id=buyer.buyer_id,
        match_score=75,
        status="outreach_sent",
        intro_message_id="msg-12345",
        intro_sent_at=datetime.utcnow()
    )
    db.add(match)
    db.commit()
    print(f"✅ Created match with existing email (intro_message_id)")
    
    service = ProviderAutomationService(db=db)
    
    # Try to send outreach to the same buyer
    result = service._send_outreach_to_matches(provider, [buyer], "platform@example.com")
    print(f"Outreach result: {result}")
    
    # Verify the email was skipped
    if result.get("skipped") == 1:
        print("✅ Duplicate buyer outreach prevention works")
        return True
    else:
        print("❌ Duplicate buyer outreach prevention FAILED")
        return False
    
    # Cleanup
    db.delete(match)
    db.delete(provider)
    db.delete(buyer)
    db.commit()
    return True

def run_all_tests():
    """Run all duplicate prevention tests"""
    print("=" * 60)
    print("DUPLICATE EMAIL PREVENTION TEST SUITE")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Clean up
        cleanup_test_data(db)
        
        # Test 1: Provider opt-in duplicate prevention
        if not test_provider_optin_duplicate_prevention(db):
            return False
        
        # Test 2: Buyer outreach duplicate prevention
        if not test_buyer_outreach_duplicate_prevention(db):
            return False
        
        print("\n" + "=" * 60)
        print("✅ ALL DUPLICATE PREVENTION TESTS PASSED")
        print("=" * 60)
        print("\nDuplicate email prevention is working:")
        print("• Provider opt-in emails are not sent twice")
        print("• Buyer outreach emails are not sent twice to same buyer-provider pair")
        
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
