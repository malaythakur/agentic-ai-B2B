"""
Provider Opt-in Real Email Test

Test the complete provider opt-in flow with real email:
1. Create provider with malaythakur13@gmail.com
2. Send opt-in email to provider
3. Wait for provider response
4. Process consent
5. Trigger automation to send to buyer (thakurujjwal13@gmail.com)
"""

import sys
from app.database import SessionLocal
from app.models import ServiceProvider, BuyerCompany
from app.services.provider_optin_service import ProviderOptInService
from app.services.provider_automation_service import ProviderAutomationService
from app.settings import settings

def cleanup_test_data(db, force=False):
    """Clean up test data"""
    try:
        fresh_db = SessionLocal()
        
        # Only cleanup if force=True, otherwise skip if provider exists
        test_provider = fresh_db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == "real-optin-provider-001"
        ).first()
        
        if force or not test_provider:
            if test_provider:
                fresh_db.delete(test_provider)
            
            # Clean up test buyer
            test_buyer = fresh_db.query(BuyerCompany).filter(
                BuyerCompany.buyer_id == "real-optin-buyer-001"
            ).first()
            if test_buyer:
                fresh_db.delete(test_buyer)
            
            fresh_db.commit()
            print(f"🧹 Cleaned up test data")
        else:
            print(f"⏭️  Skipping cleanup - provider exists (checking for response)")
        
        fresh_db.close()
    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")
        if 'fresh_db' in locals():
            fresh_db.rollback()
            fresh_db.close()

def create_test_provider(db):
    """Create test provider with user's email"""
    # Check if provider already exists
    existing_provider = db.query(ServiceProvider).filter(
        ServiceProvider.provider_id == "real-optin-provider-001"
    ).first()
    
    if existing_provider:
        print(f"✅ Using existing provider: {existing_provider.provider_id}")
        print(f"   Email: {existing_provider.contact_email}")
        print(f"   Consent status: {existing_provider.outreach_consent_status}")
        return existing_provider
    
    provider = ServiceProvider(
        provider_id="real-optin-provider-001",
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
        outreach_consent_status="pending",  # Start with pending
        auto_outreach_enabled=False,
        automation_settings={}
    )
    db.add(provider)
    db.commit()
    print(f"✅ Created test provider: {provider.provider_id}")
    print(f"   Email: {provider.contact_email}")
    print(f"   Consent status: {provider.outreach_consent_status}")
    return provider

def create_test_buyer(db):
    """Create test buyer with user's email"""
    # Check if buyer already exists
    existing_buyer = db.query(BuyerCompany).filter(
        BuyerCompany.buyer_id == "real-optin-buyer-001"
    ).first()
    
    if existing_buyer:
        print(f"✅ Using existing buyer: {existing_buyer.buyer_id}")
        print(f"   Email: {existing_buyer.decision_maker_email}")
        return existing_buyer
    
    buyer = BuyerCompany(
        buyer_id="real-optin-buyer-001",
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

def send_optin_email(db, provider):
    """Send opt-in email to provider"""
    print("\n" + "=" * 70)
    print("STEP 1: Send Opt-in Email to Provider")
    print("=" * 70)
    
    optin_service = ProviderOptInService(
        db=db,
        gmail_credentials_path=settings.GMAIL_CREDENTIALS_PATH,
        gmail_token_path=settings.GMAIL_TOKEN_PATH,
        gemini_api_key=settings.GEMINI_API_KEY
    )
    
    # Use platform email as sender
    from_email = "malaythakur1800@gmail.com"
    
    result = optin_service.send_optin_email(provider.provider_id, from_email)
    
    print(f"\nOpt-in email result:")
    print(f"  Success: {result.get('success')}")
    print(f"  Message ID: {result.get('message_id')}")
    print(f"  Sent to: {result.get('sent_to')}")
    
    if result.get('error'):
        print(f"  Error: {result.get('error')}")
    
    return result

def check_provider_response(db, provider_id):
    """Check if provider has responded to opt-in email"""
    print("\n" + "=" * 70)
    print("STEP 2: Check Provider Response")
    print("=" * 70)
    
    optin_service = ProviderOptInService(
        db=db,
        gmail_credentials_path=settings.GMAIL_CREDENTIALS_PATH,
        gmail_token_path=settings.GMAIL_TOKEN_PATH,
        gemini_api_key=settings.GEMINI_API_KEY
    )
    
    result = optin_service.check_provider_response(provider_id, platform_email="malaythakur13@gmail.com")
    
    print(f"\nResponse check result:")
    print(f"  Success: {result.get('success')}")
    print(f"  Response received: {result.get('response_received')}")
    print(f"  Response text: {result.get('response_text')}")
    print(f"  Sentiment: {result.get('sentiment')}")
    
    if result.get('error'):
        print(f"  Error: {result.get('error')}")
    
    return result

def process_consent(db, provider_id):
    """Process provider consent"""
    print("\n" + "=" * 70)
    print("STEP 3: Process Provider Consent")
    print("=" * 70)
    
    optin_service = ProviderOptInService(
        db=db,
        gmail_credentials_path=settings.GMAIL_CREDENTIALS_PATH,
        gmail_token_path=settings.GMAIL_TOKEN_PATH,
        gemini_api_key=settings.GEMINI_API_KEY
    )
    
    result = optin_service.process_consent(provider_id, from_email="malaythakur13@gmail.com")
    
    print(f"\nConsent processing result:")
    print(f"  Success: {result.get('success')}")
    print(f"  Consent status: {result.get('consent_status')}")
    print(f"  Automation enabled: {result.get('automation_enabled')}")
    print(f"  Message: {result.get('message')}")
    
    if result.get('error'):
        print(f"  Error: {result.get('error')}")
    
    return result

def trigger_automation(db, provider_id):
    """Trigger automation to send to buyer"""
    print("\n" + "=" * 70)
    print("STEP 4: Trigger Automation to Send to Buyer")
    print("=" * 70)
    
    automation_service = ProviderAutomationService(
        db=db,
        gmail_credentials_path=settings.GMAIL_CREDENTIALS_PATH,
        gmail_token_path=settings.GMAIL_TOKEN_PATH,
        gemini_api_key=settings.GEMINI_API_KEY
    )
    
    platform_email = "malaythakur1800@gmail.com"
    print(f"Platform email: {platform_email}")
    
    result = automation_service.trigger_provider_automation(provider_id, platform_email)
    
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
    
    return result

def run_optin_flow_test():
    """Run the complete opt-in flow test"""
    print("=" * 70)
    print("PROVIDER OPT-IN REAL EMAIL TEST")
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
        print("GMAIL CREDENTIALS CHECK")
        print("=" * 70)
        
        if not settings.GMAIL_CREDENTIALS_PATH:
            print("⚠️  GMAIL_CREDENTIALS_PATH not set in settings")
            print("   Emails will be simulated (not actually sent)")
        else:
            print(f"✅ Gmail credentials configured: {settings.GMAIL_CREDENTIALS_PATH}")
        
        # Step 1: Send opt-in email (only if not already sent)
        if provider.opt_in_email_sent_at:
            print("\n" + "=" * 70)
            print("OPT-IN EMAIL ALREADY SENT")
            print("=" * 70)
            print(f"Sent at: {provider.opt_in_email_sent_at}")
            print("Skipping email send, checking for response...")
            optin_result = {"success": True, "already_sent": True}
        else:
            optin_result = send_optin_email(db, provider)
            
            if not optin_result.get('success'):
                print("\n❌ Failed to send opt-in email")
                return False
        
        print("\n" + "=" * 70)
        print("📧 OPT-IN EMAIL SENT")
        print("=" * 70)
        print(f"\nEmail sent to: {provider.contact_email}")
        print("Message ID: " + optin_result.get('message_id', 'N/A'))
        
        # Step 2: Check response
        response_result = check_provider_response(db, provider.provider_id)
        
        if not response_result.get('response_received'):
            print("\n⚠️  No response received yet")
            print("Please reply to the opt-in email with 'yes' or 'I consent'")
            print("Then run this script again to continue")
            return True
        
        # Step 3: Process consent
        consent_result = process_consent(db, provider.provider_id)
        
        if not consent_result.get('success'):
            print("\n❌ Failed to process consent")
            return False
        
        # Step 4: Trigger automation
        automation_result = trigger_automation(db, provider.provider_id)
        
        if automation_result.get('success'):
            print("\n" + "=" * 70)
            print("📧 BUYER EMAIL SENT")
            print("=" * 70)
            print(f"\nCheck your inbox at: {buyer.decision_maker_email}")
            print("You should have received an outreach email")
        
        print("\n" + "=" * 70)
        print("✅ COMPLETE OPT-IN FLOW COMPLETED")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Don't cleanup yet - we need the data for the next steps
        db.close()
    
    return True

if __name__ == "__main__":
    success = run_optin_flow_test()
    sys.exit(0 if success else 1)
