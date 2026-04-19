import asyncio
from app.database import SessionLocal
from app.services.b2b_provider_discovery import B2BProviderDiscoveryService
from app.settings import settings

db = SessionLocal()

print('=== TESTING PROVIDER DISCOVERY ===')
print(f"PLATFORM_EMAIL: {settings.PLATFORM_EMAIL}")
print(f"GEMINI_API_KEY exists: {bool(settings.GEMINI_API_KEY)}")

try:
    provider_service = B2BProviderDiscoveryService(
        db=db,
        gemini_api_key=settings.GEMINI_API_KEY,
        platform_email=settings.PLATFORM_EMAIL or 'platform@example.com',
        dry_run=True  # Won't send actual emails
    )
    print('Provider service initialized successfully')
    
    results = asyncio.run(provider_service.run_provider_discovery())
    print('\n=== RESULTS ===')
    print(f"Discovered: {results['discovered']}")
    print(f"Created: {results['created']}")
    print(f"Opt-in emails sent: {results['optin_sent']}")
    print(f"Sources: {results.get('sources', {})}")
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

db.close()
