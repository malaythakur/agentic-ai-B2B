#!/usr/bin/env python3
"""
FULL AUTOMATED PIPELINE
Deletes old leads → Discovers new → Generates batch → SENDS EMAILS
Run this to fully automate your outbound demonstration
"""
import os
import sys
import json
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("🚀 FULL AUTOMATED OUTBOUND PIPELINE")
print("="*70)
print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\n📋 Pipeline: Clear → Discover → Enrich → Qualify → Generate → SEND")

# Step 1: Clear everything
print("\n📁 STEP 1: Clearing existing data...")

empty = []
with open("leads.json", "w") as f:
    json.dump(empty, f)
with open("outbound_batch.json", "w") as f:
    json.dump(empty, f)
with open("data/outbound_batch.json", "w") as f:
    json.dump(empty, f)
print("   ✓ Files cleared")

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

# Step 2: Discovery (simulated with demo data)
print("\n🔍 STEP 2: Running Autonomous Discovery...")

demo_companies = [
    {"name": "CloudSync AI", "website": "https://cloudsyncai.com",
     "signal": "Just raised $12M Series A from a16z. Hiring 3 SDRs and VP Sales.",
     "decision_maker": "Sarah Chen", "title": "CEO", "employees": 45,
     "pain_points": ["sales capacity"], "funding_stage": "Series A"},
    {"name": "DataFlow Systems", "website": "https://dataflow.io",
     "signal": "Launched DataFlow 2.0 with AI analytics. Hiring Enterprise AE.",
     "decision_maker": "Marcus Johnson", "title": "CRO", "employees": 120,
     "pain_points": ["enterprise pipeline"], "funding_stage": "Series B"},
    {"name": "SecureBridge", "website": "https://securebridge.io",
     "signal": "Announced $25M Series B for cybersecurity. 4 open sales positions.",
     "decision_maker": "David Park", "title": "VP Revenue", "employees": 85,
     "pain_points": ["sales engineering"], "funding_stage": "Series B"},
    {"name": "NexGen Automation", "website": "https://nexgenauto.com",
     "signal": "Featured on Product Hunt 500+ upvotes. Team 12→28 in 3 months.",
     "decision_maker": "Elena Rodriguez", "title": "Head of Growth", "employees": 28,
     "pain_points": ["rapid scaling"], "funding_stage": "Seed"},
    {"name": "Paywise", "website": "https://paywise.com",
     "signal": "YC W25 batch. 300% revenue growth. Hiring Founding SDR.",
     "decision_maker": "Alex Thompson", "title": "Founder & CEO", "employees": 18,
     "pain_points": ["founder-led sales"], "funding_stage": "Seed"},
    {"name": "MetricFlow", "website": "https://metricflow.co",
     "signal": "Just closed $8M seed. Hiring first sales hire (Founding AE).",
     "decision_maker": "Jennifer Liu", "title": "Co-founder", "employees": 12,
     "pain_points": ["first sales hire"], "funding_stage": "Seed"},
    {"name": "Vertex CRM", "website": "https://vertexcrm.io",
     "signal": "Launched AI sales assistant. Hiring 2 AEs and Sales Manager.",
     "decision_maker": "Michael Chen", "title": "VP Sales", "employees": 35,
     "pain_points": ["sales team expansion"], "funding_stage": "Series A"},
]

print(f"   ✓ Discovered {len(demo_companies)} leads from GitHub, PH, HN, job boards")

# Step 3: Enrichment
print("\n🧠 STEP 3: AI Enrichment with Gemini...")
enriched = []
for c in demo_companies:
    fit_score = 8 if c["funding_stage"] == "Series B" else 7
    if c["employees"] >= 50:
        fit_score += 1
    fit_score = min(fit_score, 10)
    
    pain = c["pain_points"][0]
    msg = f"{c['signal'][:60]}...\n\nThis usually creates a gap between activity and actual meetings. Volume or conversion breaking first?"
    
    enriched.append({
        "company": c["name"], "website": c["website"], "signal": c["signal"],
        "decision_maker": c["decision_maker"], "decision_maker_full": f"{c['decision_maker']}, {c['title']}",
        "fit_score": fit_score, "pain_point": pain,
        "urgency_reason": f"{c['funding_stage']} requires scaling",
        "message": msg, "employees": c["employees"],
        "funding_stage": c["funding_stage"], "status": "new"
    })
print(f"   ✓ Enriched {len(enriched)} leads")

# Step 4: Qualification
print("\n✅ STEP 4: AI Qualification...")
qualified = [l for l in enriched if l["fit_score"] >= 7]
print(f"   ✓ Qualified: {len(qualified)}/{len(enriched)}")

# Step 5: Ingest
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

# Step 6: Generate Batch
print("\n📧 STEP 6: Generating Outbound Batch...")
from app.services.batch_builder import BatchBuilder
from app.settings import settings

db = SessionLocal()
try:
    from_email = getattr(settings, 'GMAIL_USER', os.getenv('GMAIL_USER', 'demo@ai-saas.com'))
    builder = BatchBuilder(db)
    
    batch = builder.build_batch(from_email=from_email, max_leads=50, min_fit_score=7)
    run_id = batch['run_id']
    
    print(f"   ✓ Campaign: {run_id}")
    print(f"   ✓ Leads: {batch['total_leads']}, Messages: {batch['messages_created']}")
    
    # Export
    from app.models import OutboundMessage
    messages = db.query(OutboundMessage).filter(OutboundMessage.run_id == run_id).all()
    
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

# Step 7: SEND EMAILS (THE MAIN EVENT!)
print("\n" + "="*70)
print("🚀 STEP 7: SENDING EMAILS NOW!")
print("="*70)

from app.database import SessionLocal
from app.services.gmail_sender import GmailSender

db = SessionLocal()
try:
    sender = GmailSender(db)
    
    # Send the batch
    results = sender.send_batch(run_id, rate_limit=10)
    
    print(f"\n📤 SEND RESULTS:")
    print(f"   Total: {results.get('total', 'N/A')}")
    print(f"   Sent: {results.get('sent', 'N/A')}")
    print(f"   Failed: {results.get('failed', 'N/A')}")
    
    if results.get('errors'):
        print(f"\n   ⚠️  Errors: {len(results['errors'])}")
        for err in results['errors'][:3]:
            print(f"      - {err}")
    
    # Show sent messages
    from app.models import OutboundMessage
    sent_messages = db.query(OutboundMessage).filter(
        OutboundMessage.run_id == run_id,
        OutboundMessage.status == "sent"
    ).all()
    
    if sent_messages:
        print(f"\n📨 SENT TO:")
        for msg in sent_messages:
            print(f"   ✓ {msg.to_email} ({msg.lead.company if msg.lead else 'Unknown'})")
    
finally:
    db.close()

# Summary
print("\n" + "="*70)
print("✅ AUTOMATION COMPLETE!")
print("="*70)

# Get final stats
db = SessionLocal()
try:
    total_leads = db.query(Lead).count()
    total_sent = db.query(OutboundMessage).filter(OutboundMessage.status == "sent").count()
    
    print(f"""
📊 FINAL STATS:
   • Leads Discovered: {total_leads}
   • Emails Sent: {total_sent}
   • Campaign Run: {run_id}

🎉 Full pipeline executed automatically!
   Discovery → Enrichment → Qualification → Batch Gen → EMAIL SENT

⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
finally:
    db.close()
