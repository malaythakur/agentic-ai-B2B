"""Add more buyers and providers with duplicate prevention"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models import ServiceProvider, BuyerCompany, Match
from app.services.b2b_buyer_discovery import B2BBuyerDiscoveryService
from app.services.b2b_provider_discovery import B2BProviderDiscoveryService
from app.services.provider_management import ProviderManagementService
from dotenv import load_dotenv
import asyncio
import uuid

load_dotenv()

def check_for_duplicates(db, company_name, email, is_provider=True):
    """Check if company already exists"""
    if is_provider:
        # Check by name (case insensitive)
        existing = db.query(ServiceProvider).filter(
            func.lower(ServiceProvider.company_name) == func.lower(company_name)
        ).first()
        if existing:
            return True, f"Provider '{company_name}' already exists"
        
        # Check by email
        if email:
            existing = db.query(ServiceProvider).filter(
                ServiceProvider.contact_email == email
            ).first()
            if existing:
                return True, f"Email '{email}' already registered"
    else:
        # Check buyer by name
        existing = db.query(BuyerCompany).filter(
            func.lower(BuyerCompany.company_name) == func.lower(company_name)
        ).first()
        if existing:
            return True, f"Buyer '{company_name}' already exists"
        
        # Check by email
        if email:
            existing = db.query(BuyerCompany).filter(
                BuyerCompany.decision_maker_email == email
            ).first()
            if existing:
                return True, f"Email '{email}' already registered"
    
    return False, None

async def run_buyer_discovery():
    """Run autonomous buyer discovery (no duplicates)"""
    print("=" * 70)
    print("RUNNING BUYER DISCOVERY (Auto Deduplication)")
    print("=" * 70)
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Get current count
        before_count = db.query(BuyerCompany).count()
        print(f"Buyers before: {before_count}")
        
        # Run discovery
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            print("   [ERROR] GEMINI_API_KEY not found in environment")
            return None
        
        service = B2BBuyerDiscoveryService(db, gemini_api_key=gemini_key)
        results = await service.run_buyer_discovery()
        
        # Get new count
        after_count = db.query(BuyerCompany).count()
        new_buyers = after_count - before_count
        
        print(f"\n[OK] Discovery Complete!")
        print(f"   Discovered: {results.get('discovered', 0)}")
        print(f"   Enriched: {results.get('enriched', 0)}")
        print(f"   Created: {results.get('created', 0)}")
        print(f"   Total buyers now: {after_count} (+{new_buyers} new)")
        
        # Show new buyers
        if new_buyers > 0:
            print(f"\n[NEW BUYERS]:")
            new_buyer_list = db.query(BuyerCompany).order_by(
                BuyerCompany.created_at.desc()
            ).limit(new_buyers).all()
            
            for buyer in new_buyer_list:
                print(f"   -> {buyer.company_name} ({buyer.industry or 'Unknown'})")
                if buyer.signals:
                    print(f"      Signals: {', '.join(buyer.signals[:2])}")
        
        return results
        
    finally:
        db.close()

async def run_provider_discovery():
    """Run provider discovery (no duplicates)"""
    print("\n" + "=" * 70)
    print("RUNNING PROVIDER DISCOVERY (Auto Deduplication)")
    print("=" * 70)
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Get current count
        before_count = db.query(ServiceProvider).count()
        print(f"Providers before: {before_count}")
        
        # Run discovery
        service = B2BProviderDiscoveryService(db, dry_run=False)
        results = await service.run_discovery_cycle()
        
        # Get new count
        after_count = db.query(ServiceProvider).count()
        new_providers = after_count - before_count
        
        print(f"\n[OK] Discovery Complete!")
        print(f"   Discovered: {results.get('discovered', 0)}")
        print(f"   Enriched: {results.get('enriched', 0)}")
        print(f"   Created: {results.get('created', 0)}")
        print(f"   Opt-in emails sent: {results.get('optin_sent', 0)}")
        print(f"   Total providers now: {after_count} (+{new_providers} new)")
        
        # Show new providers
        if new_providers > 0:
            print(f"\n[NEW PROVIDERS]:")
            new_provider_list = db.query(ServiceProvider).order_by(
                ServiceProvider.created_at.desc()
            ).limit(new_providers).all()
            
            for provider in new_provider_list:
                print(f"   -> {provider.company_name}")
                print(f"      Services: {', '.join(provider.services[:2]) if provider.services else 'N/A'}")
                print(f"      Email: {provider.contact_email}")
        
        return results
        
    finally:
        db.close()

def add_manual_provider(company_name, contact_email, services, website=None):
    """Add a single provider manually (checks for duplicates first)"""
    print(f"\n[ Adding Manual Provider: {company_name} ]")
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Check for duplicates
        is_dup, reason = check_for_duplicates(db, company_name, contact_email, is_provider=True)
        if is_dup:
            print(f"   [SKIP] {reason}")
            return None
        
        # Create provider
        provider_mgmt = ProviderManagementService(db)
        provider = provider_mgmt.create_provider(
            company_name=company_name,
            contact_email=contact_email,
            services=services,
            website=website,
            description=f"Manual entry: {', '.join(services)}",
            industries=["Technology"],
        )
        
        provider.outreach_consent_status = "discovered"
        db.commit()
        
        print(f"   [OK] ADDED: {provider.company_name}")
        print(f"      ID: {provider.provider_id}")
        print(f"      Email: {provider.contact_email}")
        
        return provider
        
    except Exception as e:
        print(f"   [ERROR] {e}")
        return None
    finally:
        db.close()

def show_duplicate_check_examples():
    """Show how duplicate checking works"""
    print("\n" + "=" * 70)
    print("DUPLICATE CHECK EXAMPLES")
    print("=" * 70)
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Test cases
        test_cases = [
            ("CloudMigration Co", "sales@cloudmigration.com", True),  # Should be duplicate
            ("cloudmigration co", "new@email.com", True),  # Should be duplicate (case insensitive)
            ("Brand New Company", "new@email.com", True),  # Should be new
            ("TechStartup XYZ", "buyer@test.com", False),  # Should be duplicate buyer
        ]
        
        for name, email, is_provider in test_cases:
            is_dup, reason = check_for_duplicates(db, name, email, is_provider)
            type_str = "Provider" if is_provider else "Buyer"
            
            if is_dup:
                print(f"   [DUP] {type_str} '{name}' -> DUPLICATE: {reason}")
            else:
                print(f"   [OK] {type_str} '{name}' -> NEW (can add)")
        
    finally:
        db.close()

async def main():
    import sys
    
    if len(sys.argv) < 2:
        print("=" * 70)
        print("ADD MORE BUYERS & PROVIDERS - USAGE")
        print("=" * 70)
        print("\nCommands:")
        print("  python add_more_leads.py buyers     - Run buyer discovery")
        print("  python add_more_leads.py providers  - Run provider discovery")
        print("  python add_more_leads.py test       - Test duplicate checking")
        print("  python add_more_leads.py manual     - Add manual provider example")
        print("\nDuplicate Prevention:")
        print("  • Checks company name (case insensitive)")
        print("  • Checks email address")
        print("  • Checks website domain")
        print("  • Automatic during discovery process")
        return
    
    command = sys.argv[1]
    
    if command == "buyers":
        await run_buyer_discovery()
    elif command == "providers":
        await run_provider_discovery()
    elif command == "test":
        show_duplicate_check_examples()
    elif command == "manual":
        # Example: Add a manual provider
        add_manual_provider(
            company_name="Super Dev Agency",
            contact_email="hello@superdev.io",
            services=["React", "Node.js", "Cloud"],
            website="https://superdev.io"
        )
        
        # Try to add duplicate (should be rejected)
        add_manual_provider(
            company_name="super dev agency",  # Same name, different case
            contact_email="different@email.com",
            services=["Python", "Django"],
            website="https://superdev.io"
        )
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    asyncio.run(main())
