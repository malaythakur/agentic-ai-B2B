#!/usr/bin/env python3
"""
Reset all leads and run autonomous discovery for real-time demonstration
"""
import json
import asyncio
import os
from datetime import datetime

# Clear leads.json
empty_leads = []
with open("leads.json", "w") as f:
    json.dump(empty_leads, f, indent=2)
print("✓ Cleared leads.json")

# Clear outbound_batch.json
empty_batch = []
with open("outbound_batch.json", "w") as f:
    json.dump(empty_batch, f, indent=2)
print("✓ Cleared outbound_batch.json")

with open("data/outbound_batch.json", "w") as f:
    json.dump(empty_batch, f, indent=2)
print("✓ Cleared data/outbound_batch.json")

# Now run autonomous discovery
print("\n=== Starting Autonomous Lead Discovery ===\n")

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal, engine, Base
from app.services.autonomous_discovery import AutonomousDiscoveryEngine
from app.settings import settings

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Check for Gemini API key
    gemini_key = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))
    if not gemini_key:
        print("❌ ERROR: GEMINI_API_KEY not configured!")
        print("Set GEMINI_API_KEY in your .env file")
        sys.exit(1)
    
    newsapi_key = getattr(settings, 'NEWSAPI_KEY', os.getenv('NEWSAPI_KEY'))
    
    # Initialize discovery engine
    engine_discovery = AutonomousDiscoveryEngine(
        db=db,
        gemini_api_key=gemini_key,
        newsapi_key=newsapi_key
    )
    
    print("🔍 Phase 1: Discovering raw leads from free sources...")
    print("   - GitHub (tech companies with hiring signals)")
    print("   - Product Hunt (new launches)")
    print("   - Hacker News (hiring posts)")
    print("   - Job boards (sales role openings)")
    if newsapi_key:
        print("   - NewsAPI (funding & hiring announcements)")
    print()
    
    # Run the full discovery cycle
    async def run_discovery():
        results = await engine_discovery.run_discovery_cycle()
        return results
    
    # Run discovery
    results = asyncio.run(run_discovery())
    
    print("\n" + "="*60)
    print("📊 DISCOVERY RESULTS")
    print("="*60)
    print(f"⏰ Start Time: {results['cycle_start']}")
    print(f"🎯 Raw Leads Discovered: {results['discovered']}")
    print(f"🧠 Leads Enriched with AI: {results['enriched']}")
    print(f"✅ Qualified Leads: {results['qualified']}")
    print(f"📥 Ingested to Database: {results['ingested']}")
    
    if results['leads']:
        print(f"\n🏢 Companies Found:")
        for company in results['leads']:
            print(f"   • {company}")
    
    print(f"\n⏰ End Time: {results['cycle_end']}")
    print("="*60)
    
    # Close connections
    asyncio.run(engine_discovery.close())
    
    print("\n✅ Discovery cycle complete!")
    
    # Save discovered leads to leads.json for backup/reference
    if results['ingested'] > 0:
        # Query the leads we just added
        from app.models import Lead
        from sqlalchemy import desc
        
        new_leads = db.query(Lead).order_by(desc(Lead.created_at)).limit(results['ingested']).all()
        
        leads_export = []
        for lead in new_leads:
            leads_export.append({
                "company": lead.company,
                "website": lead.website,
                "signal": lead.signal,
                "decision_maker": lead.decision_maker,
                "fit_score": lead.fit_score,
                "status": lead.status,
                "created_at": lead.created_at.isoformat() if lead.created_at else None
            })
        
        with open("leads.json", "w") as f:
            json.dump(leads_export, f, indent=2)
        
        print(f"\n💾 Exported {len(leads_export)} leads to leads.json")
        
        # Generate outbound batch
        print("\n📧 Generating outbound email batch...")
        from app.services.batch_builder import BatchBuilder
        
        from_email = getattr(settings, 'GMAIL_USER', os.getenv('GMAIL_USER', 'demo@example.com'))
        builder = BatchBuilder(db)
        
        batch_results = builder.build_batch(
            from_email=from_email,
            max_leads=50,
            min_fit_score=7
        )
        
        print(f"\n📤 BATCH GENERATION RESULTS:")
        print(f"   Run ID: {batch_results['run_id']}")
        print(f"   Campaign: {batch_results['campaign_name']}")
        print(f"   Total Messages: {batch_results['messages_created']}")
        print(f"   Errors: {batch_results['errors']}")
        
        if batch_results['messages_created'] > 0:
            # Export batch to outbound_batch.json
            from app.models import OutboundMessage
            
            messages = db.query(OutboundMessage).filter(
                OutboundMessage.run_id == batch_results['run_id']
            ).all()
            
            batch_export = []
            for msg in messages:
                batch_export.append({
                    "company": msg.lead.company if msg.lead else "Unknown",
                    "email_subject": msg.subject,
                    "email_body": msg.body_text,
                    "to_email": msg.to_email,
                    "status": msg.status
                })
            
            with open("outbound_batch.json", "w") as f:
                json.dump(batch_export, f, indent=2)
            
            print(f"\n💾 Exported {len(batch_export)} messages to outbound_batch.json")
            
            print("\n" + "="*60)
            print("📧 SAMPLE OUTBOUND MESSAGES")
            print("="*60)
            for i, msg in enumerate(batch_export[:3], 1):
                print(f"\n{i}. Company: {msg['company']}")
                print(f"   Subject: {msg['email_subject']}")
                print(f"   Body: {msg['email_body'][:150]}...")
    
    print("\n🎉 DEMONSTRATION COMPLETE!")
    print("Your system is now ready with fresh, AI-discovered leads.")
    
except Exception as e:
    print(f"\n❌ Error during discovery: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
    print("\n✓ Database connection closed")
