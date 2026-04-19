"""
Clean up automation test data from database
"""

from app.database import SessionLocal
from app.models import Match, ServiceProvider, BuyerCompany

db = SessionLocal()

try:
    # Clean up test matches
    test_matches = db.query(Match).filter(
        Match.provider_id.like("test-automation-provider-%")
    ).all()
    print(f"Found {len(test_matches)} test matches")
    for match in test_matches:
        db.delete(match)
    
    # Clean up test providers
    test_providers = db.query(ServiceProvider).filter(
        ServiceProvider.provider_id.like("test-automation-provider-%")
    ).all()
    print(f"Found {len(test_providers)} test providers")
    for provider in test_providers:
        db.delete(provider)
    
    # Clean up test buyers
    test_buyers = db.query(BuyerCompany).filter(
        BuyerCompany.buyer_id.like("test-automation-buyer-%")
    ).all()
    print(f"Found {len(test_buyers)} test buyers")
    for buyer in test_buyers:
        db.delete(buyer)
    
    db.commit()
    print("✅ Cleanup completed")
except Exception as e:
    db.rollback()
    print(f"❌ Cleanup failed: {e}")
finally:
    db.close()
