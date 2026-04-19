#!/usr/bin/env python3
"""
FORCE SEND - Bypass deliverability checks for demonstration
Updates message status to "sent" without actual email delivery
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("⚠️  FORCE SEND MODE - Simulating email delivery")
print("="*70)

from app.database import SessionLocal
from app.models import OutboundMessage, CampaignRun, Event
from datetime import datetime, timezone
import uuid

db = SessionLocal()

try:
    # Get the most recent campaign
    campaign = db.query(CampaignRun).order_by(CampaignRun.generated_at.desc()).first()
    
    if not campaign:
        print("❌ No campaign found! Run auto_pipeline.py first")
        sys.exit(1)
    
    run_id = campaign.run_id
    print(f"\n📧 Campaign: {run_id}")
    
    # Get queued messages
    messages = db.query(OutboundMessage).filter(
        OutboundMessage.run_id == run_id,
        OutboundMessage.status.in_(["queued", "failed"])
    ).all()
    
    if not messages:
        print("❌ No queued messages found!")
        sys.exit(1)
    
    print(f"🎯 Found {len(messages)} messages to send")
    print("\n📧 Emails to mark as SENT:")
    for msg in messages:
        print(f"   • {msg.to_email} ({msg.lead.company if msg.lead else 'Unknown'})")
        print(f"     Subject: {msg.subject[:50]}...")
    
    print("\n⚡ Marking as sent (bypassing deliverability)...")
    
    sent = 0
    for msg in messages:
        # Mark as sent
        msg.gmail_message_id = f"force_sent_{msg.message_id}"
        msg.status = "sent"
        msg.sent_at = datetime.now(timezone.utc)
        
        # Log send event
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type="message_force_sent",
            entity_type="message",
            entity_id=msg.message_id,
            data={
                "run_id": run_id,
                "lead_id": msg.lead_id,
                "to_email": msg.to_email,
                "subject": msg.subject
            }
        )
        db.add(event)
        
        sent += 1
        print(f"   ✓ {msg.to_email} - MARKED AS SENT")
    
    # Update campaign status
    campaign.status = "completed"
    
    db.commit()
    
    print("\n" + "="*70)
    print("📤 SEND RESULTS:")
    print(f"   Total Messages: {len(messages)}")
    print(f"   Marked as Sent: {sent}")
    print("="*70)
    
    # Show summary
    print("\n🎉 All emails marked as SENT in the system!")
    print("\n� You can now demonstrate:")
    print("   • GET /api/metrics (shows sent messages)")
    print("   • GET /api/runs/{run_id} (campaign details)")
    print("   • Reply classification will process responses")
    print("\n💡 For real email delivery, configure Gmail API properly")
    
finally:
    db.close()
