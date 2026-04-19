from app.database import SessionLocal
from app.models import ServiceProvider

db = SessionLocal()
provider = db.query(ServiceProvider).filter(
    ServiceProvider.provider_id == "real-optin-provider-001"
).first()

if provider:
    print(f"Provider found: {provider.provider_id}")
    print(f"Current automation_settings: {provider.automation_settings}")
    
    # Mark acknowledgment as sent
    if provider.automation_settings is None:
        provider.automation_settings = {}
    
    provider.automation_settings["acknowledgment_sent"] = True
    provider.automation_settings["acknowledgment_sent_at"] = "2026-04-19T04:35:00"
    
    db.commit()
    print("✅ Marked acknowledgment as sent")
else:
    print("Provider not found")

db.close()
