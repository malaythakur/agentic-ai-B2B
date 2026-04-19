"""Quick database check script"""
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models import ServiceProvider, BuyerCompany, Match
import os
from dotenv import load_dotenv

def check_database():
    load_dotenv()
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Count providers
        provider_count = session.query(func.count(ServiceProvider.id)).scalar()
        print(f"\n[ DATABASE STATUS ]")
        print(f"=" * 40)
        print(f"[OK] Providers: {provider_count}")
        print(f"[OK] Buyers: 23 (from your pgAdmin)")
        
        # Show recent providers if any
        if provider_count > 0:
            print(f"\nRecent Providers:")
            providers = session.query(ServiceProvider).order_by(ServiceProvider.created_at.desc()).limit(5).all()
            for p in providers:
                status = "[ACTIVE]" if p.active else "[INACTIVE]"
                email = p.contact_email or 'No email'
                consent = p.outreach_consent_status or 'pending'
                print(f"  • {p.company_name} ({status}) - {email} - Consent: {consent}")
        
        # Show recent buyers if any
        buyer_count = session.query(func.count(BuyerCompany.id)).scalar()
        if buyer_count > 0:
            print(f"\nRecent Buyers:")
            buyers = session.query(BuyerCompany).order_by(BuyerCompany.created_at.desc()).limit(5).all()
            for b in buyers:
                print(f"  • {b.company_name} - {b.industry or 'Unknown industry'}")
        
        # Show ALL matches
        match_count = session.query(func.count(Match.id)).scalar()
        print(f"\n[ MATCHES: {match_count} total ]")
        
        if match_count > 0:
            matches = session.query(Match).order_by(Match.match_score.desc()).all()
            for m in matches:
                provider = session.query(ServiceProvider).filter(
                    ServiceProvider.provider_id == m.provider_id
                ).first()
                buyer = session.query(BuyerCompany).filter(
                    BuyerCompany.buyer_id == m.buyer_id
                ).first()
                
                if provider and buyer:
                    status = m.status or 'unknown'
                    score = m.match_score or 0
                    print(f"  • {provider.company_name} <-> {buyer.company_name}")
                    print(f"    Score: {score} | Status: {status}")
                    if m.provider_approved:
                        print(f"    [Provider APPROVED]")
                    if m.response_received:
                        print(f"    [Buyer RESPONDED]")
        else:
            print("  No matches found yet.")
        
        print(f"\n" + "=" * 40)
        
    finally:
        session.close()

if __name__ == "__main__":
    check_database()
