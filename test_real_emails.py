"""
Real Email Test

Test the complete workflow with user's actual email addresses:
- Provider: malaythakur13@gmail.com
- Buyer: thakurujjwal13@gmail.com
"""

import sys
from app.database import SessionLocal
from app.models import ServiceProvider, BuyerCompany, Match
from app.services.provider_automation_service import ProviderAutomationService
from app.services.provider_optin_service import ProviderOptInService
from app.settings import settings

def cleanup_test_data(db):
    """Clean up test data"""
    try:
        fresh_db = SessionLocal()
        
        # Clean up test matches
        test_matches = fresh_db.query(Match).filter(
            Match.provider_id == "real-test-provider-001"
        ).all()
        for match in test_matches:
            fresh_db.delete(match)
        
        # Clean up test provider
        test_provider = fresh_db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == "real-test-provider-001"
        ).first()
        if test_provider:
            fresh_db.delete(test_provider)
        
        # Clean up test buyer
        test_buyer = fresh_db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == "real-test-buyer-001"
        ).first()
        if test_buyer:
            fresh_db.delete(test_buyer)
        
        fresh_db.commit()
        fresh_db.close()
        print(f"🧹 Cleaned up test data")
    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")
        if 'fresh_db' in locals():
            fresh_db.rollback()
            fresh_db.close()

def create_test_provider(db):
    """Create test provider with user's email"""
    provider = ServiceProvider(
        provider_id="real-test-provider-001",
        company_name="Test Provider (Malay)",
        contact_email="malaythakur13@gmail.com",
        services=["Cloud Migration", "DevOps", "AI Solutions"],
        industries=["SaaS", "Fintech"],
        icp_criteria={
            "industries": ["SaaS", "Fintech"],
            "funding_stage": "Series A",
            "employees": "50-500",
            "signals": ["recent_funding", "hiring_engineers"]
        },
        active=True,
        onboarding_complete=True,
        outreach_consent_status="consented",  # Auto-consent for testing
        outreach_consent_date=None,
        auto_outreach_enabled=True,
        automation_settings={}
    )
    db.add(provider)
    db.commit()
    print(f"✅ Created test provider: {provider.provider_id}")
    print(f"   Email: {provider.contact_email}")
    return provider

def create_test_buyer(db):
    """Create test buyer with user's email"""
    buyer = BuyerCompany(
        buyer_id="real-test-buyer-001",
        company_name="Test Buyer (Ujjwal)",
        industry="SaaS",
        funding_stage="series_a",
        employee_count=100,
        decision_maker_email="thakurujjwal13@gmail.com",
        requirements=["cloud_migration", "devops"],
        signals=["recent_funding", "hiring_engineers"],
        active=True
    )
    db.add(buyer)
    db.commit()
    print(f"✅ Created test buyer: {buyer.buyer_id}")
    print(f"   Email: {buyer.decision_maker_email}")
    return buyer

def run_real_email_test():
    """Run test with real emails"""
    print("=" * 70)
    print("REAL EMAIL TEST")
    print("=" * 70)
    print("\nProvider: malaythakur13@gmail.com")
    print("Buyer: thakurujjwal13@gmail.com")
    print()
    
    db = SessionLocal()
    
    try:
        # Clean up
        cleanup_test_data(db)
        
        # Create provider and buyer
        provider = create_test_provider(db)
        buyer = create_test_buyer(db)
        
        print("\n" + "=" * 70)
        print("STEP 1: Check Gmail Credentials")
        print("=" * 70)
        
        if not settings.GMAIL_CREDENTIALS_PATH:
            print("⚠️  GMAIL_CREDENTIALS_PATH not set in settings")
            print("   Emails will be simulated (not actually sent)")
            print("   To send real emails, set GMAIL_CREDENTIALS_PATH in .env")
        else:
            print(f"✅ Gmail credentials configured: {settings.GMAIL_CREDENTIALS_PATH}")
        
        print("\n" + "=" * 70)
        print("STEP 2: Trigger Automation")
        print("=" * 70)
        
        automation_service = ProviderAutomationService(
            db=db,
            gmail_credentials_path=settings.GMAIL_CREDENTIALS_PATH,
            gmail_token_path=settings.GMAIL_TOKEN_PATH,
            gemini_api_key=settings.GEMINI_API_KEY
        )
        
        # Trigger automation with platform email
        platform_email = "malaythakur13@gmail.com"  # Use provider's email as sender
        print(f"Platform email: {platform_email}")
        
        result = automation_service.trigger_provider_automation(
            provider.provider_id,
            platform_email
        )
        
        print(f"\nAutomation result:")
        print(f"  Success: {result.get('success')}")
        print(f"  Provider ID: {result.get('provider_id')}")
        print(f"  Matched buyers: {result.get('matched_buyers')}")
        print(f"  Matches created: {result.get('matches_created')}")
        
        if 'outreach_results' in result:
            outreach = result['outreach_results']
            print(f"\nOutreach results:")
            print(f"  Total: {outreach.get('total')}")
            print(f"  Sent: {outreach.get('sent')}")
            print(f"  Failed: {outreach.get('failed')}")
            print(f"  Skipped: {outreach.get('skipped')}")
            
            if outreach.get('details'):
                print(f"\nDetails:")
                for detail in outreach.get('details'):
                    print(f"  - Buyer: {detail.get('company')}")
                    print(f"    Status: {detail.get('status')}")
                    if detail.get('error'):
                        print(f"    Error: {detail.get('error')}")
        
        print("\n" + "=" * 70)
        print("STEP 3: Verify Match Created")
        print("=" * 70)
        
        matches = db.query(Match).filter(
            Match.provider_id == provider.provider_id
        ).all()
        
        print(f"Matches in database: {len(matches)}")
        
        for match in matches:
            print(f"\n  Match ID: {match.match_id}")
            print(f"  Provider: {match.provider_id}")
            print(f"  Buyer: {match.buyer_id}")
            print(f"  Status: {match.status}")
            print(f"  Score: {match.match_score}")
            print(f"  Intro sent at: {match.intro_sent_at}")
            print(f"  Intro message ID: {match.intro_message_id}")
            print(f"  Follow-up count: {match.followup_count}")
            print(f"  Response received: {match.response_received}")
        
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        if result.get('success'):
            print("✅ Automation triggered successfully")
            print(f"✅ {result.get('matches_created')} match(es) created")
            
            if result.get('outreach_results', {}).get('sent', 0) > 0:
                print("✅ Email(s) sent successfully")
                print("\n📧 Check your inbox:")
                print(f"   Provider: {provider.contact_email}")
                print(f"   Buyer: {buyer.decision_maker_email}")
            elif result.get('outreach_results', {}).get('failed', 0) > 0:
                print("⚠️  Email sending failed (check Gmail credentials)")
            else:
                print("⚠️  No emails sent (check configuration)")
        else:
            print("❌ Automation failed")
            print(f"Error: {result.get('error')}")
        
        print("\n" + "=" * 70)
        print("✅ REAL EMAIL TEST COMPLETED")
        print("=" * 70)
        
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
    success = run_real_email_test()
    sys.exit(0 if success else 1)
