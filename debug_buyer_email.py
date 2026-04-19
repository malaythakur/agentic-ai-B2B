from app.database import SessionLocal
from app.models import BuyerCompany, Match

db = SessionLocal()

# Check buyer
buyer = db.query(BuyerCompany).filter(BuyerCompany.buyer_id == "real-optin-buyer-001").first()
if buyer:
    print(f"Buyer ID: {buyer.buyer_id}")
    print(f"Company: {buyer.company_name}")
    print(f"Decision Maker Email: {buyer.decision_maker_email}")
    print(f"Industry: {buyer.industry}")
    print(f"Funding Stage: {buyer.funding_stage}")
    print(f"Employee Count: {buyer.employee_count}")
    print(f"Active: {buyer.active}")
else:
    print("Buyer not found")

# Check match
match = db.query(Match).filter(
    Match.provider_id == "real-optin-provider-001",
    Match.buyer_id == "real-optin-buyer-001"
).first()

if match:
    print(f"\nMatch ID: {match.match_id}")
    print(f"Status: {match.status}")
    print(f"Intro sent at: {match.intro_sent_at}")
    print(f"Intro message ID: {match.intro_message_id}")
else:
    print("\nMatch not found")

db.close()
