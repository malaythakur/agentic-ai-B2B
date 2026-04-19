"""Quick test - skip scraping, test enrichment & creation only"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import ServiceProvider
from app.services.b2b_provider_discovery import B2BProviderDiscoveryService
from app.services.provider_management import ProviderManagementService
from app.services.gemini_enrichment import GeminiEnrichmentService
import uuid

async def test_provider_creation():
    """Test provider creation with mock discovered data"""
    
    # Setup DB - use the same config as check_database
    from dotenv import load_dotenv
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Mock discovered providers (what Clutch scraper would return)
    mock_discovered = [
        {
            "company_name": "TechFlow Solutions",
            "website": "https://techflow.dev",
            "description": "Full-stack web development agency specializing in React",
            "services": ["Web Development", "React"],
            "category": "web-developers"
        },
        {
            "company_name": "CloudScale Pro",
            "website": "https://cloudscale.io", 
            "description": "AWS cloud migration specialists",
            "services": ["AWS Migration", "Cloud Architecture"],
            "category": "cloud-consultants"
        }
    ]
    
    print("=" * 60)
    print("TESTING PROVIDER CREATION FLOW")
    print("=" * 60)
    
    # Test 1: Create without enrichment (like buyers)
    print("\n[TEST 1] Direct Creation (like buyers work)")
    print("-" * 40)
    
    provider_mgmt = ProviderManagementService(db)
    
    for data in mock_discovered:
        try:
            # Check duplicate
            existing = db.query(ServiceProvider).filter(
                ServiceProvider.company_name == data["company_name"]
            ).first()
            
            if existing:
                print(f"  [SKIP] Duplicate: {data['company_name']}")
                continue
            
            # Create directly
            provider = provider_mgmt.create_provider(
                company_name=data["company_name"],
                contact_email=f"hello@{data['website'].replace('https://', '')}",
                services=data["services"],
                website=data["website"],
                description=data["description"],
                industries=["Technology"],
            )
            
            provider.outreach_consent_status = "discovered"
            db.commit()
            
            print(f"  [OK] Created: {provider.company_name}")
            
        except Exception as e:
            print(f"  [ERROR] {e}")
    
    # Show results
    print("\n[RESULTS]")
    print("-" * 40)
    
    count = db.query(ServiceProvider).count()
    print(f"Total Providers in DB: {count}")
    
    providers = db.query(ServiceProvider).order_by(ServiceProvider.created_at.desc()).limit(10).all()
    for p in providers:
        print(f"  • {p.company_name} - {p.contact_email} - {p.outreach_consent_status}")
    
    db.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_provider_creation())
