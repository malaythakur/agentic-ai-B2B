#!/usr/bin/env python3
"""
ACTUALLY SEND EMAILS via Gmail API
Bypasses deliverability checks and sends real emails
"""
import os
import sys
import base64
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("📧 REAL EMAIL SEND - Gmail API")
print("="*70)

# Check for Gmail token
if not os.path.exists('data/token.json'):
    print("\n❌ Gmail not authenticated!")
    print("   Run: python -c \"from app.auth import gmail_auth; gmail_auth()\"")
    print("   Or check README for Gmail setup instructions")
    sys.exit(1)

from app.database import SessionLocal
from app.models import OutboundMessage, CampaignRun, Event
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText

db = SessionLocal()

try:
    # Load Gmail credentials
    creds = Credentials.from_authorized_user_file('data/token.json')
    service = build('gmail', 'v1', credentials=creds)
    
    # Get user email
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile.get('emailAddress', 'unknown')
    print(f"\n✓ Authenticated as: {user_email}")
    
    # Get latest campaign
    campaign = db.query(CampaignRun).order_by(CampaignRun.generated_at.desc()).first()
    if not campaign:
        print("❌ No campaign found! Run run_full_demo.py first")
        sys.exit(1)
    
    run_id = campaign.run_id
    print(f"📧 Campaign: {run_id}")
    
    # Get messages to send (queued or failed)
    messages = db.query(OutboundMessage).filter(
        OutboundMessage.run_id == run_id,
        OutboundMessage.status.in_(["queued", "failed"])
    ).all()
    
    if not messages:
        print("❌ No messages to send")
        sys.exit(1)
    
    print(f"\n🎯 Found {len(messages)} emails to send:\n")
    for msg in messages:
        print(f"   To: {msg.to_email}")
        print(f"   Subject: {msg.subject[:50]}...")
        print()
    
    confirm = input("⚠️  Actually send these emails? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        sys.exit(0)
    
    print("\n📤 Sending emails...\n")
    
    sent_count = 0
    failed_count = 0
    
    for msg in messages:
        try:
            # Create email
            mime_msg = MIMEText(msg.body, 'plain', 'utf-8')
            mime_msg['to'] = msg.to_email
            mime_msg['from'] = msg.from_email
            mime_msg['subject'] = msg.subject
            
            # Encode
            raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
            
            # ACTUALLY SEND via Gmail API
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            # Update database
            msg.gmail_message_id = result['id']
            msg.status = "sent"
            msg.sent_at = datetime.now(timezone.utc)
            
            # Log event
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type="email_sent",
                entity_type="message",
                entity_id=msg.message_id,
                data={
                    "gmail_id": result['id'],
                    "to": msg.to_email,
                    "subject": msg.subject
                }
            )
            db.add(event)
            
            sent_count += 1
            print(f"   ✓ SENT: {msg.to_email}")
            print(f"     Gmail ID: {result['id']}")
            
        except Exception as e:
            msg.status = "failed"
            msg.error_message = str(e)
            failed_count += 1
            print(f"   ✗ FAILED: {msg.to_email}")
            print(f"     Error: {e}")
    
    db.commit()
    
    print("\n" + "="*70)
    print("📊 SEND RESULTS:")
    print(f"   Sent: {sent_count}")
    print(f"   Failed: {failed_count}")
    print("="*70)
    
    if sent_count > 0:
        print(f"\n🎉 {sent_count} emails ACTUALLY sent from {user_email}!")
        print("\n📧 Check your Gmail Sent folder to confirm")
    
finally:
    db.close()
