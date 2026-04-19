from app.database import SessionLocal
from app.models import Match

db = SessionLocal()
match = db.query(Match).filter(
    Match.provider_id == "real-optin-provider-001",
    Match.buyer_id == "real-optin-buyer-001"
).first()

if match:
    print(f"Match found: {match.match_id}")
    print(f"Clearing intro_message_id to allow fresh send...")
    match.intro_message_id = None
    match.intro_sent_at = None
    match.status = "pending"
    db.commit()
    print("✅ Cleared duplicate check")
else:
    print("No match found")

db.close()
