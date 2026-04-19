#!/usr/bin/env python3
"""
ACTUALLY SEND EMAILS - Bypass deliverability and send for real
"""
import os
import sys
import pickle
import base64
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("📧 ACTUALLY SEND EMAILS - Real Gmail API")
print("="*70)

# Check token (it's a pickle file, not JSON)
token_path = os.getenv('GMAIL_TOKEN_PATH', 'data/token.json')
if not os.path.exists(token_path):
    print("\n❌ Gmail not authenticated!")
    print("\n📋 To authenticate:")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create OAuth 2.0 credentials (Desktop app)")
    print("3. Download JSON and save as data/credentials.json")
    print("4. Run: python -c \"from app.services.gmail_sender import GmailSender; from app.database import SessionLocal; GmailSender(SessionLocal())\"")
    print("\nOr manually create this quick auth script:\n")
    print("""   from google_auth_oauthlib.flow import InstalledAppFlow
   scopes = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']
   flow = InstalledAppFlow.from_client_secrets_file('data/credentials.json', scopes)
   creds = flow.run_local_server(port=0)
   import pickle
   with open('data/token.json', 'wb') as f:
       pickle.dump(creds, f)
   print('Authenticated!')""")
    sys.exit(1)

print(f"✓ Token found: {token_path}\n")

from app.database import SessionLocal
from app.models import OutboundMessage, CampaignRun, Event
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText

db = SessionLocal()

try:
    # Load credentials (pickle format)
    with open(token_path, 'rb') as f:
        creds = pickle.load(f)
    
    # Refresh if needed
    if not creds.valid:
        from google.auth.transport.requests import Request
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'wb') as f:
                pickle.dump(creds, f)
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Get user email
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile.get('emailAddress', 'unknown')
    print(f"✓ Authenticated as: {user_email}\n")
    
    # Get campaign
    campaign = db.query(CampaignRun).order_by(CampaignRun.generated_at.desc()).first()
    if not campaign:
        print("❌ No campaign! Run: python demo_automation.py")
        sys.exit(1)
    
    print(f"📧 Campaign: {campaign.run_id}")
    
    # Get messages
    messages = db.query(OutboundMessage).filter(
        OutboundMessage.run_id == campaign.run_id,
        OutboundMessage.status.in_(["queued", "failed"])
    ).all()
    
    if not messages:
        # Check if already sent
        sent_msgs = db.query(OutboundMessage).filter(
            OutboundMessage.run_id == campaign.run_id,
            OutboundMessage.status == "sent"
        ).all()
        if sent_msgs:
            print(f"\n✓ {len(sent_msgs)} messages already sent!")
            for m in sent_msgs[:3]:
                print(f"   - {m.to_email}: {m.subject[:40]}...")
        else:
            print("\n❌ No messages to send")
        sys.exit(0)
    
    print(f"\n🎯 {len(messages)} emails to send:\n")
    for i, msg in enumerate(messages, 1):
        print(f"{i}. {msg.to_email} ({msg.lead.company if msg.lead else 'Unknown'})")
        print(f"   Subject: {msg.subject[:55]}...")
    
    # Ask for confirmation
    print(f"\n⚠️  Send {len(messages)} emails from {user_email}?")
    confirm = input("Type 'yes' to send: ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        sys.exit(0)
    
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
            
            # Send
            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            # Update DB
            msg.gmail_message_id = result['id']
            msg.status = "sent"
            msg.sent_at = datetime.now(timezone.utc)
            
            db.add(Event(
                event_id=str(uuid.uuid4()),
                event_type="email_sent",
                entity_type="message",
                entity_id=msg.message_id,
                data={"gmail_id": result['id'], "to": msg.to_email}
            ))
            
            sent += 1
            print(f"✓ SENT: {msg.to_email}")
            
        except Exception as e:
            msg.status = "failed"
            msg.error_message = str(e)
            failed += 1
            print(f"✗ FAILED: {msg.to_email} - {str(e)[:50]}")
    
    db.commit()
    
    print("\n" + "="*70)
    print(f"📊 RESULTS: {sent} sent, {failed} failed")
    print("="*70)
    
    if sent > 0:
        print(f"\n🎉 {sent} emails ACTUALLY sent!")
        print(f"📧 Check your Gmail Sent folder: https://mail.google.com/mail/u/0/#sent")
    
finally:
    db.close()
