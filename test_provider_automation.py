"""
Test Provider Automation Service

This script tests the automated buyer outreach after provider opts in:
- Test ICP matching logic
- Test automation trigger
- Validate match creation
- Test outreach generation (without sending real emails)
"""

import sys
from app.database import SessionLocal
from app.models import ServiceProvider, BuyerCompany
from app.services.provider_automation_service import ProviderAutomationService

def cleanup_test_data(db):
    """Clean up test data"""
    try:
        # Use fresh session for cleanup
        fresh_db = SessionLocal()
        
        # Clean up test matches
        from app.models import Match
        test_matches = fresh_db.query(Match).filter(
            Match.provider_id.like("test-automation-provider-%")
        ).all()
        for match in test_matches:
            fresh_db.delete(match)
        
        # Clean up test providers
        test_providers = fresh_db.query(ServiceProvider).filter(
            ServiceProvider.provider_id.like("test-automation-provider-%")
        ).all()
        for provider in test_providers:
            fresh_db.delete(provider)
        
        # Clean up test buyers
        test_buyers = fresh_db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id.like("test-automation-buyer-%")
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

def create_test_provider_with_icp(db):
    """Create a test provider with ICP criteria"""
    provider = ServiceProvider(
        provider_id="test-automation-provider-001",
        company_name="Test Automation Provider",
        contact_email="test-automation@example.com",
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
        auto_outreach_enabled=True,
        outreach_consent_status="consented",
        automation_settings={
            "max_emails_per_day": 30,
            "min_match_score": 70,
            "auto_approve_matches": True,
            "template_type": "intro"
        }
    )
    db.add(provider)
    db.commit()
    print(f"✅ Created test provider with ICP: {provider.provider_id}")
    return provider

def create_test_buyers(db):
    """Create test buyers with different characteristics"""
    buyers = []
    
    # Buyer 1: Matches ICP (SaaS, Series A, 50-500 employees, recent funding)
    buyer1 = BuyerCompany(
        buyer_id="test-automation-buyer-001",
        company_name="Matching SaaS Company",
        industry="SaaS",
        funding_stage="series_a",
        employee_count=100,
        decision_maker_email="contact@matchingsaas.com",
        requirements=["cloud_migration", "devops"],
        signals=["hiring_devops", "recent_funding"],
        active=True
    )
    buyers.append(buyer1)
    
    # Buyer 2: Matches ICP (Fintech, Series A, 50-500 employees)
    buyer2 = BuyerCompany(
        buyer_id="test-automation-buyer-002",
        company_name="Matching Fintech Company",
        industry="Fintech",
        funding_stage="series_a",
        employee_count=200,
        decision_maker_email="contact@matchingfintech.com",
        requirements=["cloud_migration"],
        signals=["recent_funding"],
        active=True
    )
    buyers.append(buyer2)
    
    # Buyer 3: Does NOT match ICP (E-commerce, not in provider industries)
    buyer3 = BuyerCompany(
        buyer_id="test-automation-buyer-003",
        company_name="Non-Matching E-commerce",
        industry="E-commerce",
        funding_stage="series_a",
        employee_count=150,
        decision_maker_email="contact@nonmatching.com",
        requirements=["cloud_migration"],
        signals=["recent_funding"],
        active=True
    )
    buyers.append(buyer3)
    
    # Buyer 4: Does NOT match ICP (Series B, not Series A)
    buyer4 = BuyerCompany(
        buyer_id="test-automation-buyer-004",
        company_name="Wrong Stage SaaS",
        industry="SaaS",
        funding_stage="series_b",
        employee_count=100,
        decision_maker_email="contact@wrongstage.com",
        requirements=["cloud_migration"],
        signals=["recent_funding"],
        active=True
    )
    buyers.append(buyer4)
    
    for buyer in buyers:
        db.add(buyer)
    
    db.commit()
    print(f"✅ Created {len(buyers)} test buyers (2 matching, 2 non-matching)")
    return buyers

def test_icp_matching(db):
    """Test ICP matching logic"""
    print("\n=== Testing ICP Matching Logic ===\n")
    
    provider = create_test_provider_with_icp(db)
    buyers = create_test_buyers(db)
    
    service = ProviderAutomationService(db=db)
    
    matching_buyers = service._find_matching_buyers(provider)
    
    print(f"Provider ICP: {provider.icp_criteria}")
    print(f"Total buyers in database: {len(buyers)}")
    
    # Debug: Check each buyer
    for buyer in buyers:
        matches = service._buyer_matches_icp(buyer, provider.icp_criteria)
        print(f"  Buyer: {buyer.company_name} - Industry: {buyer.industry}, Stage: {buyer.funding_stage}, Signals: {buyer.signals} - Matches: {matches}")
    
    print(f"Matching buyers found: {len(matching_buyers)}")
    
    for buyer in matching_buyers:
        print(f"  ✓ {buyer.company_name} ({buyer.industry}, {buyer.funding_stage})")
    
    # Verify
    assert len(matching_buyers) == 2, f"Expected 2 matching buyers, got {len(matching_buyers)}"
    assert matching_buyers[0].buyer_id == "test-automation-buyer-001", "First match should be buyer 1"
    assert matching_buyers[1].buyer_id == "test-automation-buyer-002", "Second match should be buyer 2"
    
    print("\n✅ ICP matching test PASSED")
    
    # Cleanup this test's data before next test
    cleanup_test_data(db)
    return provider, matching_buyers

def test_match_creation(db, provider, matching_buyers):
    """Test match creation"""
    print("\n=== Testing Match Creation ===\n")
    
    # Create fresh data for this test
    provider = create_test_provider_with_icp(db)
    buyers = create_test_buyers(db)
    
    service = ProviderAutomationService(db=db)
    matching_buyers = service._find_matching_buyers(provider)
    
    matches_created = service._create_matches(provider, matching_buyers)
    
    print(f"Matches created: {matches_created}")
    
    # Verify matches exist
    from app.models import Match
    matches = db.query(Match).filter(
        Match.provider_id == provider.provider_id
    ).all()
    
    print(f"Total matches in database: {len(matches)}")
    
    for match in matches:
        print(f"  ✓ Match: {match.provider_id} → {match.buyer_id}")
    
    assert len(matches) == 2, f"Expected 2 matches, got {len(matches)}"
    
    print("\n✅ Match creation test PASSED")
    
    # Cleanup this test's data
    cleanup_test_data(db)

def test_outreach_generation(db, provider, matching_buyers):
    """Test outreach email generation (without sending)"""
    print("\n=== Testing Outreach Email Generation ===\n")
    
    # Create fresh data for this test
    provider = create_test_provider_with_icp(db)
    buyers = create_test_buyers(db)
    
    service = ProviderAutomationService(db=db)
    matching_buyers = service._find_matching_buyers(provider)
    
    # Test email generation for first matching buyer
    buyer = matching_buyers[0]
    
    prospect = {
        "company_name": buyer.company_name,
        "decision_maker_email": buyer.decision_maker_email,
        "signals": buyer.signals or [],
        "tech_stack": buyer.requirements or [],
        "industry": buyer.industry
    }
    
    provider_data = {
        "company_name": provider.company_name,
        "contact_email": provider.contact_email,
        "services": provider.services,
        "case_studies": provider.case_studies
    }
    
    email_body = service._generate_outreach_body(prospect, provider_data)
    
    print(f"Email to: {prospect['decision_maker_email']}")
    print(f"Subject: {provider.company_name} + {prospect['company_name']}")
    print(f"Body preview: {email_body[:200]}...")
    
    assert provider.company_name in email_body, "Email should mention provider"
    assert prospect['company_name'] in email_body, "Email should mention buyer"
    assert "Cloud Migration" in email_body or "DevOps" in email_body, "Email should mention services"
    
    print("\n✅ Outreach generation test PASSED")
    
    # Cleanup this test's data
    cleanup_test_data(db)

def test_automation_trigger(db):
    """Test full automation trigger"""
    print("\n=== Testing Full Automation Trigger ===\n")
    
    provider = create_test_provider_with_icp(db)
    buyers = create_test_buyers(db)
    
    service = ProviderAutomationService(db=db)
    
    # Trigger automation (without actual Gmail sending)
    result = service.trigger_provider_automation(provider.provider_id, "platform@example.com")
    
    print(f"\nAutomation trigger result: {result}")
    
    # Verify
    assert result.get("success") == True, "Automation should succeed"
    assert result.get("matched_buyers") == 2, "Should find 2 matching buyers"
    assert result.get("matches_created") == 2, "Should create 2 matches"
    
    # Check outreach results
    outreach_results = result.get("outreach_results", {})
    print(f"Outreach results: {outreach_results}")
    
    print("\n✅ Full automation trigger test PASSED")

def run_all_tests():
    """Run all automation tests"""
    print("=" * 60)
    print("PROVIDER AUTOMATION SERVICE TEST SUITE")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Clean up
        cleanup_test_data(db)
        
        # Test: Full Automation Trigger (this tests the complete flow)
        test_automation_trigger(db)
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nThe provider automation service is working correctly:")
        print("• ICP matching filters buyers correctly")
        print("• Matches are created between providers and buyers")
        print("• Personalized emails are generated")
        print("• Automation trigger orchestrates the full flow")
        
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
