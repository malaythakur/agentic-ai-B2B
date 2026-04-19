#!/usr/bin/env python3
"""
QUICK SEND - Bypass all checks and actually send via Gmail
No deliverability checks, just pure sending
"""
import os
import sys
import base64
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# First, check if Gmail is set up
if not os.path.exists('data/token.json'):
    print("="*70)
    print("🔐 GMAIL AUTHENTICATION NEEDED")
    print("="*70)
    print("\n1. Make sure you have data/credentials.json from Google Cloud Console")
    print("2. Run the auth flow:")
    print("\n   python -c \"from app.integrations.gmail_auth import authenticate_gmail; authenticate_gmail()\"\n")
    print("3. Then run this script again")
    print("\n📖 See README.md for Gmail API setup instructions")
    sys.exit(1)

print("="*70)
print("📧 QUICK SEND - Gmail API (No Deliverability Checks)")
print("="*70)

from app.database import SessionLocal
from app.models import OutboundMessage, CampaignRun, Event
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText

db = SessionLocal()

try:
    # Load Gmail
    creds = Credentials.from_authorized_user_file('data/token.json')
    service = build('gmail', 'v1', credentials=creds)
    
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile.get('emailAddress', 'unknown')
    print(f"✓ Gmail: {user_email}\n")
    
    # Get latest campaign with messages
    campaign = db.query(CampaignRun).order_by(CampaignRun.generated_at.desc()).first()
    if not campaign:
        print("❌ No campaign found! Run: python demo_automation.py")
        sys.exit(1)
    
    print(f"📧 Campaign: {campaign.run_id}")
    
    # Get messages
    messages = db.query(OutboundMessage).filter(
        OutboundMessage.run_id == campaign.run_id,
        OutboundMessage.status.in_(["queued", "failed"])
    ).all()
    
    if not messages:
        print("\n⚠️  No queued messages. Checking for any messages...")
        all_msgs = db.query(OutboundMessage).filter(
            OutboundMessage.run_id == campaign.run_id
        ).all()
        if all_msgs:
            print(f"   Found {len(all_msgs)} messages with status: {set(m.status for m in all_msgs)}")
            already_sent = [m for m in all_msgs if m.status == "sent"]
            if already_sent:
                print(f"\n   ✓ {len(already_sent)} messages already sent!")
                for m in already_sent[:3]:
                    print(f"     - {m.to_email}: {m.subject[:40]}...")
        else:
            print("   No messages found at all")
        sys.exit(0)
    
    print(f"\n🎯 {len(messages)} emails ready to send:\n")
    for i, msg in enumerate(messages, 1):
        print(f"{i}. {msg.to_email}")
        print(f"   Subject: {msg.subject[:50]}...")
        print(f"   Preview: {msg.body[:80]}...\n")
    
    # Auto-send without confirmation for demo
    print("⚡ Auto-sending in 3 seconds... (Ctrl+C to cancel)")
    import time
    time.sleep(3)
    
    print("\n📤 Sending...\n")
    
    sent = 0
    failed = 0
    
    for msg in messages:
        try:
            # Build email
            mime = MIMEText(msg.body, 'plain', 'utf-8')
            mime['to'] = msg.to_email
            mime['from'] = msg.from_email or user_email
            mime['subject'] = msg.subject
            
            # Encode and send
            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            # Update DB
            msg.gmail_message_id = result['id']
            msg.status = "sent"
            msg.sent_at = datetime.now(timezone.utc)
            
            # Log
            db.add(Event(
                event_id=str(uuid.uuid4()),
                event_type="email_sent",
                entity_type="message",
                entity_id=msg.message_id,
                data={"gmail_id": result['id'], "to": msg.to_email}
            ))
            
            sent += 1
            print(f"✓ SENT: {msg.to_email} (ID: {result['id'][:15]}...)")
            
        except Exception as e:
            msg.status = "failed"
            msg.error_message = str(e)
            failed += 1
            print(f"✗ FAILED: {msg.to_email} - {e}")
    
    db.commit()
    
    print("\n" + "="*70)
    print(f"📊 RESULTS: Sent: {sent}, Failed: {failed}")
    print("="*70)
    
    if sent > 0:
        print(f"\n🎉 {sent} emails sent from {user_email}!")
        print("📧 Check your Gmail Sent folder")
        
finally:
    db.close()
