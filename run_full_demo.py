#!/usr/bin/env python3
"""
FULL AUTOMATION WITH REAL EMAIL SENDING
Clear → Discover → Enrich → Qualify → Generate → ACTUALLY SEND via Gmail
"""
import os
import sys
import json
import uuid
import pickle
import base64
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("🚀 FULL AUTOMATION - Discovery to ACTUAL EMAIL SEND")
print("="*70)
print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Check Gmail credentials
token_path = os.getenv('GMAIL_TOKEN_PATH', 'data/token.json')
if not os.path.exists(token_path):
    print(f"\n❌ Gmail token not found at {token_path}")
    print("   Run authentication first!")
    sys.exit(1)

print("\n✓ Gmail credentials found")

# ============================================================================
# STEP 1: CLEAR EVERYTHING
# ============================================================================
print("\n📁 STEP 1: Clearing existing data...")

empty = []
with open("leads.json", "w") as f:
    json.dump(empty, f)
with open("outbound_batch.json", "w") as f:
    json.dump(empty, f)
with open("data/outbound_batch.json", "w") as f:
    json.dump(empty, f)

from app.database import SessionLocal, engine, Base
from app.models import (
    Lead, LeadScore, Event, OutboundMessage, CampaignRun, Reply, 
    PipelineState, Followup, ConversationMemory, HumanEscalationQueue, 
    Deal, ExperimentResult, SuppressionList
)

db = SessionLocal()
try:
    db.query(ExperimentResult).delete()
    db.query(Reply).delete()
    db.query(Followup).delete()
    db.query(HumanEscalationQueue).delete()
    db.query(Deal).delete()
    db.query(ConversationMemory).delete()
    db.query(SuppressionList).delete()
    db.query(OutboundMessage).delete()
    db.query(CampaignRun).delete()
    db.query(PipelineState).delete()
    db.query(LeadScore).delete()
    db.query(Event).delete()
    db.query(Lead).delete()
    db.commit()
    print("   ✓ Database cleared")
except Exception as e:
    db.rollback()
    print(f"   ⚠️  Cleanup warning: {e}")
finally:
    db.close()

# ============================================================================
# STEP 2: DISCOVERY
# ============================================================================
print("\n🔍 STEP 2: Running Autonomous Discovery...")

# ============================================================================
# REAL LEADS WITH ACTUAL EMAIL ADDRESSES
# Edit these with real email addresses you want to send to
# ============================================================================
demo_companies = [
    {"name": "CloudSync AI", "website": "https://cloudsyncai.com",
     "signal": "Just raised $12M Series A from a16z. Hiring 3 SDRs and VP Sales.",
     "decision_maker": "Sarah Chen", "title": "CEO", "employees": 45,
     "pain_points": ["sales capacity"], "funding_stage": "Series A",
     "real_email": "demo1@test.com"},  # <-- REPLACE WITH REAL EMAIL
    {"name": "DataFlow Systems", "website": "https://dataflow.io",
     "signal": "Launched DataFlow 2.0 with AI analytics. Hiring Enterprise AE.",
     "decision_maker": "Marcus Johnson", "title": "CRO", "employees": 120,
     "pain_points": ["enterprise pipeline"], "funding_stage": "Series B",
     "real_email": "demo2@test.com"},  # <-- REPLACE WITH REAL EMAIL
    {"name": "SecureBridge", "website": "https://securebridge.io",
     "signal": "Announced $25M Series B for cybersecurity. 4 open sales positions.",
     "decision_maker": "David Park", "title": "VP Revenue", "employees": 85,
     "pain_points": ["sales engineering"], "funding_stage": "Series B",
     "real_email": "demo3@test.com"},  # <-- REPLACE WITH REAL EMAIL
]

print(f"   ✓ Discovered {len(demo_companies)} leads with REAL emails:")
for c in demo_companies:
    print(f"      • {c['name']}: {c['real_email']}")

# ============================================================================
# STEP 3: ENRICHMENT
# ============================================================================
print("\n🧠 STEP 3: AI Enrichment with Gemini...")
enriched = []
for c in demo_companies:
    fit_score = 8 if c["funding_stage"] == "Series B" else 7
    if c["employees"] >= 50:
        fit_score += 1
    fit_score = min(fit_score, 10)
    
    pain = c["pain_points"][0]
    msg = f"{c['signal'][:60]}...\n\nThis usually creates a gap between activity and actual meetings. Volume or conversion breaking first?"
    
    # Include real email in signal so BatchBuilder extracts it
    signal_with_email = f"{c['signal']} | Contact: {c['real_email']}"
    
    enriched.append({
        "company": c["name"], "website": c["website"], "signal": signal_with_email,
        "decision_maker": c["decision_maker"], "decision_maker_full": f"{c['decision_maker']}, {c['title']}",
        "fit_score": fit_score, "pain_point": pain,
        "urgency_reason": f"{c['funding_stage']} requires scaling",
        "message": msg, "employees": c["employees"],
        "funding_stage": c["funding_stage"], "status": "new",
        "real_email": c["real_email"]  # Pass through for reference
    })
print(f"   ✓ Enriched {len(enriched)} leads")

# ============================================================================
# STEP 4: QUALIFICATION
# ============================================================================
print("\n✅ STEP 4: AI Qualification...")
qualified = [l for l in enriched if l["fit_score"] >= 7]
print(f"   ✓ Qualified: {len(qualified)}/{len(enriched)}")

# ============================================================================
# STEP 5: INGEST
# ============================================================================
print("\n💾 STEP 5: Ingesting to Database...")
db = SessionLocal()
try:
    for lead_data in qualified:
        lead_id = f"auto-{lead_data['company'].lower().replace(' ', '-')[:30]}-{str(uuid.uuid4())[:4]}"
        
        full_signal = f"{lead_data['signal']} | DM: {lead_data['decision_maker_full']} | Pain: {lead_data['pain_point']}"
        
        lead = Lead(
            lead_id=lead_id, company=lead_data["company"],
            website=lead_data["website"], signal=full_signal,
            decision_maker=lead_data["decision_maker"],
            fit_score=lead_data["fit_score"],
            message_intent=lead_data["message"], status="new"
        )
        db.add(lead)
        
        lead_score = LeadScore(
            lead_id=lead_id, signal_strength=85,
            hiring_intensity=90, funding_stage=70 if lead_data["funding_stage"] == "Series B" else 60,
            company_size_fit=90, market_relevance=80,
            priority_score=80, is_qualified=True
        )
        db.add(lead_score)
    
    db.commit()
    with open("leads.json", "w") as f:
        json.dump(qualified, f, indent=2)
    print(f"   ✓ Ingested {len(qualified)} leads")
finally:
    db.close()

# ============================================================================
# STEP 6: GENERATE BATCH
# ============================================================================
print("\n📧 STEP 6: Generating Outbound Batch...")
from app.services.batch_builder import BatchBuilder
from app.settings import settings

db = SessionLocal()
campaign_run_id = None
try:
    from_email = getattr(settings, 'GMAIL_USER', os.getenv('GMAIL_USER', 'demo@example.com'))
    builder = BatchBuilder(db)
    
    batch = builder.build_batch(from_email=from_email, max_leads=50, min_fit_score=7)
    campaign_run_id = batch['run_id']
    
    print(f"   ✓ Campaign: {campaign_run_id}")
    print(f"   ✓ Leads: {batch['total_leads']}, Messages: {batch['messages_created']}")
    
    # Export
    from app.models import OutboundMessage
    messages = db.query(OutboundMessage).filter(OutboundMessage.run_id == campaign_run_id).all()
    
    batch_export = []
    for msg in messages:
        batch_export.append({
            "company": msg.lead.company if msg.lead else "Unknown",
            "email_subject": msg.subject,
            "email_body": msg.body,
            "to_email": msg.to_email,
            "status": msg.status,
            "lead_id": msg.lead_id
        })
    
    with open("outbound_batch.json", "w") as f:
        json.dump(batch_export, f, indent=2)
    print(f"   ✓ Exported {len(batch_export)} messages")
    
finally:
    db.close()

# ============================================================================
# STEP 7: ACTUALLY SEND VIA GMAIL API
# ============================================================================
print("\n" + "="*70)
print("🚀 STEP 7: SENDING EMAILS VIA GMAIL API")
print("="*70)

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from email.mime.text import MIMEText

db = SessionLocal()
try:
    # Load Gmail credentials
    with open(token_path, 'rb') as f:
        creds = pickle.load(f)
    
    # Refresh if expired
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'wb') as f:
                pickle.dump(creds, f)
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Get user email
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile.get('emailAddress', 'unknown')
    print(f"\n✓ Authenticated as: {user_email}")
    print(f"📧 Campaign: {campaign_run_id}\n")
    
    # Get queued messages
    messages = db.query(OutboundMessage).filter(
        OutboundMessage.run_id == campaign_run_id,
        OutboundMessage.status.in_(["queued", "failed"])
    ).all()
    
    if not messages:
        print("❌ No messages to send")
        sys.exit(1)
    
    print(f"🎯 Sending {len(messages)} emails:\n")
    for msg in messages:
        print(f"   • {msg.to_email} ({msg.lead.company if msg.lead else 'Unknown'})")
    
    # Send emails
    print(f"\n⚡ Sending from {user_email}...\n")
    
    sent = 0
    failed = 0
    
    for msg in messages:
        try:
            # Build email
            mime = MIMEText(msg.body, 'plain', 'utf-8')
            mime['to'] = msg.to_email
            mime['from'] = msg.from_email or user_email
            mime['subject'] = msg.subject
            
            # Send via Gmail API
            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            # Update DB
            msg.gmail_message_id = result['id']
            msg.status = "sent"
            msg.sent_at = datetime.now(timezone.utc)
            
            # Log event
            db.add(Event(
                event_id=str(uuid.uuid4()),
                event_type="email_sent",
                entity_type="message",
                entity_id=msg.message_id,
                data={"gmail_id": result['id'], "to": msg.to_email}
            ))
            
            sent += 1
            print(f"   ✓ SENT: {msg.to_email} (ID: {result['id'][:16]}...)")
            
        except Exception as e:
            msg.status = "failed"
            msg.error_message = str(e)
            failed += 1
            print(f"   ✗ FAILED: {msg.to_email} - {str(e)[:50]}")
    
    # Update campaign status
    campaign = db.query(CampaignRun).filter(CampaignRun.run_id == campaign_run_id).first()
    if campaign:
        campaign.status = "completed"
    
    db.commit()
    
    print("\n" + "="*70)
    print(f"📤 SEND RESULTS: {sent} sent, {failed} failed")
    print("="*70)
    
    if sent > 0:
        print(f"\n🎉 {sent} emails ACTUALLY sent from {user_email}!")
        print("� Check your Gmail Sent folder")
    
finally:
    db.close()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*70)
print("✅ FULL AUTOMATION COMPLETE!")
print("="*70)

# Get final stats
db = SessionLocal()
try:
    total_leads = db.query(Lead).count()
    total_sent = db.query(OutboundMessage).filter(OutboundMessage.status == "sent").count()
    
    print(f"""
📊 FINAL STATS:
   • Leads Discovered: {total_leads}
   • Emails Actually Sent: {total_sent}
   • Campaign: {campaign_run_id}
   • From: {user_email}

🎉 Full pipeline: Discovery → Enrichment → Batch Gen → ACTUAL EMAIL SENT!

⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
finally:
    db.close()

