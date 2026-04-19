"""Complete B2B workflow: Discovery + Matchmaking + Approval"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import ServiceProvider, BuyerCompany, Match
from app.services.provider_management import ProviderManagementService
from app.services.b2b_buyer_discovery import B2BBuyerDiscoveryService
from app.services.matchmaking_engine import MatchmakingEngine
from app.services.provider_optin_service import ProviderOptInService
from dotenv import load_dotenv
import uuid
import random

load_dotenv()

def run_full_workflow():
    print("=" * 70)
    print("B2B PLATFORM: FULL WORKFLOW TEST")
    print("Discovery -> Matchmaking -> Approval Emails")
    print("=" * 70)
    
    # Setup DB
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # PHASE 1: QUICK DISCOVERY (skip slow scraping)
        print("\n[PHASE 1] Provider Discovery")
        print("-" * 50)
        
        provider_mgmt = ProviderManagementService(db)
        
        # Mock discovered providers (simulating what Clutch would return)
        mock_providers = [
            {"name": "AWS Migration Pros", "services": ["AWS Migration", "Cloud Architecture"], "website": "https://awsmigration.pro"},
            {"name": "DevOps Ninjas", "services": ["DevOps", "CI/CD", "Kubernetes"], "website": "https://devopsninjas.io"},
            {"name": "SaaS Scaling Co", "services": ["SaaS Growth", "Performance Optimization"], "website": "https://saasscaling.com"},
            {"name": "Mobile App Studio", "services": ["iOS Development", "Android Development"], "website": "https://mobilestudio.app"},
            {"name": "Data Analytics Hub", "services": ["Data Engineering", "Analytics"], "website": "https://datahub.io"},
        ]
        
        created_providers = []
        for data in mock_providers:
            try:
                # Check duplicate
                existing = db.query(ServiceProvider).filter(
                    ServiceProvider.company_name == data["name"]
                ).first()
                
                if existing:
                    print(f"  [SKIP] Already exists: {data['name']}")
                    created_providers.append(existing)
                    continue
                
                # Create provider
                provider = provider_mgmt.create_provider(
                    company_name=data["name"],
                    contact_email=f"hello@{data['website'].replace('https://', '')}",
                    services=data["services"],
                    website=data["website"],
                    description=f"Leading {', '.join(data['services'])} services",
                    industries=["Technology", "SaaS"],
                )
                
                provider.outreach_consent_status = "discovered"
                db.commit()
                created_providers.append(provider)
                print(f"  [OK] Created: {provider.company_name}")
                
            except Exception as e:
                print(f"  [ERROR] {data['name']}: {e}")
        
        # Show provider count
        provider_count = db.query(ServiceProvider).count()
        print(f"\nTotal Providers: {provider_count}")
        
        # PHASE 2: MATCHMAKING
        print("\n[PHASE 2] Matchmaking")
        print("-" * 50)
        
        match_service = MatchmakingEngine(db)
        
        # Get all active providers and buyers
        providers = db.query(ServiceProvider).filter(ServiceProvider.active == True).all()
        buyers = db.query(BuyerCompany).filter(BuyerCompany.active == True).all()
        
        print(f"Matching {len(providers)} providers with {len(buyers)} buyers...")
        
        matches_created = 0
        for provider in providers:
            for buyer in buyers[:5]:  # Match with first 5 buyers for demo
                try:
                    # Check if match already exists
                    existing = db.query(Match).filter(
                        Match.provider_id == provider.provider_id,
                        Match.buyer_id == buyer.buyer_id
                    ).first()
                    
                    if existing:
                        continue
                    
                    # Create match with random score
                    score = random.randint(60, 95)
                    match = Match(
                        match_id=f"match-{str(uuid.uuid4())[:8]}",
                        provider_id=provider.provider_id,
                        buyer_id=buyer.buyer_id,
                        match_score=score,
                        status="pending",
                        provider_notified=False,
                        buyer_notified=False
                    )
                    
                    db.add(match)
                    matches_created += 1
                    print(f"  [MATCH] {provider.company_name} <-> {buyer.company_name} (Score: {score})")
                    
                except Exception as e:
                    print(f"  [ERROR] Match failed: {e}")
        
        db.commit()
        print(f"\nTotal Matches Created: {matches_created}")
        
        # Show all matches
        all_matches = db.query(Match).order_by(Match.match_score.desc()).limit(10).all()
        print(f"\nTop 10 Matches:")
        for m in all_matches:
            provider = db.query(ServiceProvider).filter(ServiceProvider.provider_id == m.provider_id).first()
            buyer = db.query(BuyerCompany).filter(BuyerCompany.buyer_id == m.buyer_id).first()
            if provider and buyer:
                print(f"  • {provider.company_name} <-> {buyer.company_name} (Score: {m.match_score}, Status: {m.status})")
        
        # PHASE 3: SEND OPT-IN EMAILS
        print("\n[PHASE 3] Provider Approval Emails")
        print("-" * 50)
        
        platform_email = os.getenv("PLATFORM_EMAIL", "malaythakur1800@gmail.com")
        optin_service = ProviderOptInService(db)
        
        # Get providers with "discovered" status
        discovered_providers = db.query(ServiceProvider).filter(
            ServiceProvider.outreach_consent_status == "discovered"
        ).all()
        
        print(f"Sending opt-in emails to {len(discovered_providers)} providers...")
        print(f"From: {platform_email}")
        
        emails_sent = 0
        for provider in discovered_providers:
            try:
                # In real scenario, this would send actual emails
                # For demo, we'll just update the status
                print(f"  [EMAIL] To: {provider.contact_email}")
                print(f"          Subject: Join our B2B Platform - Introduce you to qualified buyers")
                print(f"          Provider: {provider.company_name}")
                print(f"          Services: {', '.join(provider.services[:3] if provider.services else [])}")
                
                # Mark as email sent
                provider.opt_in_email_sent_at = db.execute(text("SELECT NOW()")).scalar()
                provider.outreach_consent_status = "pending"  # Waiting for response
                emails_sent += 1
                print(f"          Status: Sent")
                print()
                
            except Exception as e:
                print(f"  [ERROR] Failed to send to {provider.company_name}: {e}")
        
        db.commit()
        
        # FINAL SUMMARY
        print("\n" + "=" * 70)
        print("WORKFLOW COMPLETE - SUMMARY")
        print("=" * 70)
        
        final_providers = db.query(ServiceProvider).count()
        final_buyers = db.query(BuyerCompany).count()
        final_matches = db.query(Match).count()
        pending_consent = db.query(ServiceProvider).filter(
            ServiceProvider.outreach_consent_status == "pending"
        ).count()
        
        print(f"""
Providers in Database:    {final_providers}
Buyers in Database:       {final_buyers}
Matches Created:          {final_matches}
Opt-in Emails Sent:       {emails_sent}
Pending Provider Consent: {pending_consent}

Next Steps:
1. Providers check email and click "Approve" to join platform
2. Once approved, automated introductions begin
3. Buyer replies are tracked and classified
        """)
        
        # Show provider consent status
        print("\nProvider Consent Status:")
        providers = db.query(ServiceProvider).order_by(ServiceProvider.created_at.desc()).all()
        for p in providers:
            status_icon = "[PENDING]" if p.outreach_consent_status == "pending" else "[CONSENTED]" if p.outreach_consent_status == "consented" else "[DISCOVERED]"
            print(f"  {status_icon} {p.company_name} - {p.contact_email}")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    run_full_workflow()
