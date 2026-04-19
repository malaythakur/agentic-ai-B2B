"""Check if we have matching buyers for each provider's services"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models import ServiceProvider, BuyerCompany, Match
from dotenv import load_dotenv

load_dotenv()

def analyze_buyer_provider_fit():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("=" * 70)
        print("BUYER-PROVIDER FIT ANALYSIS")
        print("=" * 70)
        
        providers = session.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).all()
        
        buyers = session.query(BuyerCompany).filter(
            BuyerCompany.active == True
        ).all()
        
        print(f"\nTotal Providers: {len(providers)}")
        print(f"Total Buyers: {len(buyers)}")
        
        # Analyze each provider
        print("\n" + "=" * 70)
        print("PROVIDER -> MATCHING BUYERS ANALYSIS")
        print("=" * 70)
        
        for provider in providers:
            print(f"\n[ {provider.company_name} ]")
            print(f"  Services: {', '.join(provider.services[:3]) if provider.services else 'N/A'}")
            print(f"  Industries: {', '.join(provider.industries[:3]) if provider.industries else 'N/A'}")
            print(f"  Status: {provider.outreach_consent_status or 'unknown'}")
            
            # Find potential buyer matches
            matching_buyers = []
            for buyer in buyers:
                # Simple matching logic
                score = 0
                reasons = []
                
                # Check if buyer industry matches provider industries
                if buyer.industry and provider.industries:
                    if any(buyer.industry.lower() in ind.lower() or ind.lower() in buyer.industry.lower() 
                           for ind in provider.industries):
                        score += 30
                        reasons.append(f"Industry fit: {buyer.industry}")
                
                # Check buyer signals for service needs
                if buyer.signals:
                    signals = buyer.signals if isinstance(buyer.signals, list) else []
                    for signal in signals:
                        if any(service.lower() in signal.lower() for service in (provider.services or [])):
                            score += 40
                            reasons.append(f"Signal match: {signal}")
                            break
                
                # Check requirements
                if buyer.requirements:
                    reqs = buyer.requirements if isinstance(buyer.requirements, list) else []
                    for req in reqs:
                        if any(service.lower() in req.lower() for service in (provider.services or [])):
                            score += 30
                            reasons.append(f"Requirement: {req}")
                            break
                
                if score >= 30:
                    matching_buyers.append({
                        'buyer': buyer,
                        'score': score,
                        'reasons': reasons
                    })
            
            # Sort by score
            matching_buyers.sort(key=lambda x: x['score'], reverse=True)
            
            if matching_buyers:
                print(f"  POTENTIAL BUYERS: {len(matching_buyers)}")
                for match in matching_buyers[:3]:  # Show top 3
                    b = match['buyer']
                    print(f"    -> {b.company_name} (Score: {match['score']})")
                    print(f"      Reasons: {', '.join(match['reasons'][:2])}")
            else:
                print(f"  [WARNING] NO MATCHING BUYERS FOUND")
            
            # Check if already matched
            existing_matches = session.query(Match).filter(
                Match.provider_id == provider.provider_id
            ).all()
            
            if existing_matches:
                print(f"  ACTIVE MATCHES: {len(existing_matches)}")
                for m in existing_matches:
                    buyer = session.query(BuyerCompany).filter(
                        BuyerCompany.buyer_id == m.buyer_id
                    ).first()
                    if buyer:
                        print(f"    -> {buyer.company_name} (Status: {m.status}, Score: {m.match_score})")
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        pending_providers = [p for p in providers if p.outreach_consent_status == 'pending']
        consented_providers = [p for p in providers if p.outreach_consent_status == 'consented']
        
        print(f"\nProviders waiting for consent: {len(pending_providers)}")
        for p in pending_providers:
            print(f"  • {p.company_name} - {p.contact_email}")
        
        print(f"\nReady to match (consented): {len(consented_providers)}")
        for p in consented_providers:
            print(f"  • {p.company_name}")
        
        print("\n" + "=" * 70)
        print("When providers consent, they will be automatically matched")
        print("with compatible buyers from your database!")
        print("=" * 70)
        
    finally:
        session.close()

if __name__ == "__main__":
    analyze_buyer_provider_fit()
