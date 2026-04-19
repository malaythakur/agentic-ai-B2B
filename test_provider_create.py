"""Quick test to create providers from discovered data"""
import asyncio
import sys
import os

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import ServiceProvider
from app.services.b2b_provider_discovery import B2BProviderDiscoveryService
import uuid

def create_test_providers():
    """Create providers directly to test the flow"""
    
    # Setup DB
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Mock discovered providers
    test_providers = [
        {
            "company_name": "TechFlow Solutions",
            "website": "https://techflow.dev",
            "description": "Full-stack web development agency",
            "services": ["Web Development", "React", "Node.js"],
            "industries": ["SaaS", "Fintech"],
            "contact_email": "hello@techflow.dev",
            "source": "test",
            "category": "web-developers"
        },
        {
            "company_name": "CloudScale Pro",
            "website": "https://cloudscale.io", 
            "description": "AWS cloud migration specialists",
            "services": ["AWS Migration", "Cloud Architecture", "DevOps"],
            "industries": ["Enterprise", "Healthcare"],
            "contact_email": "contact@cloudscale.io",
            "source": "test",
            "category": "cloud-consultants"
        },
        {
            "company_name": "MobileFirst Labs",
            "website": "https://mobilefirst.app",
            "description": "iOS and Android mobile app development",
            "services": ["Mobile Apps", "iOS", "Android", "Flutter"],
            "industries": ["Consumer", "E-commerce"],
            "contact_email": "team@mobilefirst.app",
            "source": "test",
            "category": "mobile-developers"
        }
    ]
    
    print("Creating test providers...")
    created = 0
    
    for provider_data in test_providers:
        try:
            # Check for duplicate
            existing = db.query(ServiceProvider).filter(
                ServiceProvider.company_name == provider_data["company_name"]
            ).first()
            
            if existing:
                print(f"  ⚠️  Skipping (duplicate): {provider_data['company_name']}")
                continue
            
            # Create provider
            provider = ServiceProvider(
                provider_id=str(uuid.uuid4()),
                company_name=provider_data["company_name"],
                website=provider_data["website"],
                description=provider_data["description"],
                services=provider_data["services"],
                industries=provider_data["industries"],
                contact_email=provider_data["contact_email"],
                active=True,
                outreach_consent_status="pending"
            )
            
            db.add(provider)
            created += 1
            print(f"  ✅ Created: {provider_data['company_name']}")
            
        except Exception as e:
            print(f"  ❌ Error creating {provider_data['company_name']}: {e}")
    
    if created > 0:
        db.commit()
        print(f"\n✅ Committed {created} providers to database")
    else:
        print("\n⚠️  No new providers created")
    
    db.close()
    
    # Show updated count
    print("\n📊 Updated Database Status:")
    db2 = Session()
    count = db2.query(ServiceProvider).count()
    print(f"   Total Providers: {count}")
    
    # Show all providers
    providers = db2.query(ServiceProvider).order_by(ServiceProvider.created_at.desc()).all()
    for p in providers:
        print(f"   • {p.company_name} - {p.contact_email}")
    
    db2.close()

if __name__ == "__main__":
    create_test_providers()
