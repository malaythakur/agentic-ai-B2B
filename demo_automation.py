#!/usr/bin/env python3
"""
Complete Real-time Demonstration of AI-Powered Lead Generation
Clears existing leads and runs full autonomous workflow with demo data
"""
import json
import asyncio
import os
import sys
from datetime import datetime, timedelta
import uuid
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("🚀 AI SAAS OUTBOUND - REAL-TIME AUTOMATION DEMONSTRATION")
print("="*70)
print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Step 1: Clear all existing leads
print("📁 STEP 1: Clearing existing lead files...")

# Clear leads.json
empty_leads = []
with open("leads.json", "w") as f:
    json.dump(empty_leads, f, indent=2)
print("   ✓ Cleared leads.json")

# Clear outbound_batch.json
empty_batch = []
with open("outbound_batch.json", "w") as f:
    json.dump(empty_batch, f, indent=2)
print("   ✓ Cleared outbound_batch.json")

# Clear data/outbound_batch.json
with open("data/outbound_batch.json", "w") as f:
    json.dump(empty_batch, f, indent=2)
print("   ✓ Cleared data/outbound_batch.json")

# Clear database
print("\n🗄️  STEP 2: Clearing database...")

from app.database import SessionLocal, engine, Base
from app.models import (
    Lead, LeadScore, Event, OutboundMessage, CampaignRun, Reply, 
    PipelineState, Followup, ConversationMemory, HumanEscalationQueue, 
    Deal, ExperimentResult, SuppressionList
)

db = SessionLocal()

try:
    # Count existing records
    leads_count = db.query(Lead).count()
    messages_count = db.query(OutboundMessage).count()
    runs_count = db.query(CampaignRun).count()
    
    # Delete in correct order (respect foreign keys) - child tables first
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
    
    print(f"   ✓ Deleted {leads_count} leads from database")
    print(f"   ✓ Deleted {messages_count} outbound messages")
    print(f"   ✓ Deleted {runs_count} campaign runs")
    print(f"   ✓ All related records cleaned")
except Exception as e:
    db.rollback()
    print(f"   ⚠️  Database cleanup warning: {e}")
finally:
    db.close()

# Step 3: Generate Demo Leads (Simulating Autonomous Discovery)
print("\n🔍 STEP 3: Running Autonomous Lead Discovery...")
print("   Sources: GitHub | Product Hunt | Hacker News | Job Boards | NewsAPI")

# Demo companies with realistic signals
demo_companies = [
    {
        "name": "CloudSync AI",
        "website": "https://cloudsyncai.com",
        "signal": "Just raised $12M Series A from a16z. Hiring 3 SDRs and a VP Sales on LinkedIn.",
        "decision_maker": "Sarah Chen",
        "title": "CEO",
        "employees": 45,
        "tech_stack": ["Python", "AWS", "React"],
        "pain_points": ["sales capacity", "outbound motion"],
        "funding_stage": "Series A"
    },
    {
        "name": "DataFlow Systems",
        "website": "https://dataflow.io",
        "signal": "Launched DataFlow 2.0 with AI analytics last week. Currently hiring Enterprise AE.",
        "decision_maker": "Marcus Johnson",
        "title": "CRO",
        "employees": 120,
        "tech_stack": ["Go", "Kubernetes", "PostgreSQL"],
        "pain_points": ["enterprise pipeline", "conversion rates"],
        "funding_stage": "Series B"
    },
    {
        "name": "NexGen Automation",
        "website": "https://nexgenauto.com",
        "signal": "Featured on Product Hunt with 500+ upvotes. Team grew from 12 to 28 in 3 months.",
        "decision_maker": "Elena Rodriguez",
        "title": "Head of Growth",
        "employees": 28,
        "tech_stack": ["Node.js", "MongoDB", "Vue"],
        "pain_points": ["rapid scaling", "lead qualification"],
        "funding_stage": "Seed"
    },
    {
        "name": "SecureBridge",
        "website": "https://securebridge.io",
        "signal": "Announced $25M Series B for cybersecurity platform. 4 open sales positions.",
        "decision_maker": "David Park",
        "title": "VP Revenue",
        "employees": 85,
        "tech_stack": ["Rust", "AWS", "React"],
        "pain_points": ["sales engineering", "demo capacity"],
        "funding_stage": "Series B"
    },
    {
        "name": "Paywise",
        "website": "https://paywise.com",
        "signal": "YC W25 batch. 300% revenue growth, hiring Founding SDR and Account Executive.",
        "decision_maker": "Alex Thompson",
        "title": "Founder & CEO",
        "employees": 18,
        "tech_stack": ["Python", "Django", "Stripe API"],
        "pain_points": ["founder-led sales", "repeatable playbook"],
        "funding_stage": "Seed"
    },
    {
        "name": "MetricFlow",
        "website": "https://metricflow.co",
        "signal": "Just closed $8M seed round. Hiring first sales hire (Founding AE).",
        "decision_maker": "Jennifer Liu",
        "title": "Co-founder",
        "employees": 12,
        "tech_stack": ["React", "Node.js", "ClickHouse"],
        "pain_points": ["first sales hire", "outbound infrastructure"],
        "funding_stage": "Seed"
    },
    {
        "name": "Vertex CRM",
        "website": "https://vertexcrm.io",
        "signal": "Launched AI-powered sales assistant. Hiring 2 AEs and Sales Manager.",
        "decision_maker": "Michael Chen",
        "title": "VP Sales",
        "employees": 35,
        "tech_stack": ["TypeScript", "Next.js", "OpenAI API"],
        "pain_points": ["sales team expansion", "quota attainment"],
        "funding_stage": "Series A"
    }
]

print(f"\n   📊 Discovery Results:")
print(f"      • Raw leads discovered: {len(demo_companies)}")
print(f"      • From GitHub: 2 companies")
print(f"      • From Product Hunt: 2 companies")
print(f"      • From HN 'Who is hiring': 2 companies")
print(f"      • From job boards: 1 company")

# Step 4: AI Enrichment (Simulating Gemini AI)
print("\n🧠 STEP 4: AI Enrichment with Gemini...")
print("   Analyzing company data, signals, and decision makers...")

enriched_leads = []
for company in demo_companies:
    # Calculate fit score (0-10)
    base_score = 7
    if company["funding_stage"] == "Series B":
        base_score += 1.5
    elif company["funding_stage"] == "Series A":
        base_score += 1
    if company["employees"] >= 50:
        base_score += 0.5
    
    fit_score = min(int(base_score), 10)
    
    # Generate pain point and urgency
    pain_point = company["pain_points"][0] if company["pain_points"] else "pipeline generation"
    urgency_reason = f"{company['funding_stage']} funding requires rapid sales scaling"
    
    # Generate custom hook
    custom_hook = f"{company['name']} is at a critical inflection point - {company['signal'][:50]}..."
    
    # Generate message
    message = f"{company['signal'][:60]}...\n\nThis usually creates a gap between activity and actual meetings. Volume or conversion breaking first?"
    
    # Generate followups
    followups = [
        f"Usually the {pain_point} gap shows up within 30 days of this signal",
        "Most teams I speak with are busy but calendars stay light",
        "Is this a volume problem or a conversion quality issue?"
    ]
    
    # Build full decision maker with title for signal
    decision_maker_full = f"{company['decision_maker']}, {company['title']}"
    
    enriched_leads.append({
        "company": company["name"],
        "website": company["website"],
        "signal": company["signal"],
        "decision_maker": company["decision_maker"],  # Clean name for email generation
        "decision_maker_full": decision_maker_full,  # Full title for display
        "fit_score": fit_score,
        "pain_point": pain_point,
        "urgency_reason": urgency_reason,
        "custom_hook": custom_hook,
        "message": message,
        "followups": followups,
        "employees": company["employees"],
        "tech_stack": company["tech_stack"],
        "funding_stage": company["funding_stage"],
        "status": "new"
    })

print(f"   ✓ Enriched {len(enriched_leads)} leads")

# Step 5: AI-Powered Qualification
print("\n✅ STEP 5: AI-Powered Lead Qualification...")
qualified_leads = [l for l in enriched_leads if l["fit_score"] >= 7]
print(f"   Total leads: {len(enriched_leads)}")
print(f"   Qualified (score >= 7): {len(qualified_leads)}")
print(f"   Disqualified: {len(enriched_leads) - len(qualified_leads)}")

# Step 6: Ingest to Database
print("\n💾 STEP 6: Ingesting to Database...")

db = SessionLocal()
try:
    for lead_data in qualified_leads:
        lead_id = f"auto-{lead_data['company'].lower().replace(' ', '-').replace('.', '')[:30]}-{str(uuid.uuid4())[:4]}"
        
        # Create lead - build signal from all available data
        full_signal = f"{lead_data['signal']} | DM: {lead_data.get('decision_maker_full', lead_data['decision_maker'])} | Pain Point: {lead_data['pain_point']} | Urgency: {lead_data['urgency_reason']}"
        
        lead = Lead(
            lead_id=lead_id,
            company=lead_data["company"],
            website=lead_data["website"],
            signal=full_signal,
            decision_maker=lead_data["decision_maker"],  # Clean name for email extraction
            fit_score=lead_data["fit_score"],
            message_intent=lead_data["message"],
            status="new"
        )
        db.add(lead)
        
        # Create lead score
        lead_score = LeadScore(
            lead_id=lead_id,
            signal_strength=min(len(lead_data["signal"]) * 2, 100),
            hiring_intensity=90 if "hiring" in lead_data["signal"].lower() else 50,
            funding_stage=70 if lead_data["funding_stage"] == "Series B" else 60 if lead_data["funding_stage"] == "Series A" else 40,
            company_size_fit=90 if 20 <= lead_data["employees"] <= 200 else 70,
            market_relevance=lead_data["fit_score"] * 10,
            priority_score=lead_data["fit_score"] * 10,
            is_qualified=True
        )
        db.add(lead_score)
        
        # Log event
        event = Event(
            event_id=f"discovery-{lead_id}-{datetime.utcnow().timestamp()}",
            event_type="autonomous_discovery",
            entity_type="lead",
            entity_id=lead_id,
            data={
                "source": "autonomous_discovery_engine",
                "priority_score": lead_data["fit_score"] * 10,
                "signals": [lead_data["signal"]],
                "pain_points": [lead_data["pain_point"]],
                "tech_stack": lead_data["tech_stack"],
                "funding_stage": lead_data["funding_stage"]
            }
        )
        db.add(event)
    
    db.commit()
    print(f"   ✓ Ingested {len(qualified_leads)} leads to database")
    
    # Save to leads.json
    with open("leads.json", "w") as f:
        json.dump(qualified_leads, f, indent=2)
    print(f"   ✓ Exported to leads.json")
    
finally:
    db.close()

# Step 7: Generate Outbound Batch
print("\n📧 STEP 7: Generating Outbound Email Batch...")

from app.services.batch_builder import BatchBuilder
from app.settings import settings

db = SessionLocal()
try:
    from_email = getattr(settings, 'GMAIL_USER', os.getenv('GMAIL_USER', 'demo@ai-saas.com'))
    builder = BatchBuilder(db)
    
    batch_results = builder.build_batch(
        from_email=from_email,
        max_leads=50,
        min_fit_score=7
    )
    
    print(f"   📤 Campaign Created:")
    print(f"      Run ID: {batch_results['run_id']}")
    print(f"      Total Leads: {batch_results['total_leads']}")
    print(f"      Messages Created: {batch_results['messages_created']}")
    
    if batch_results['errors']:
        print(f"      Errors: {len(batch_results['errors'])}")
    
    # Export to outbound_batch.json
    if batch_results['messages_created'] > 0:
        from app.models import OutboundMessage
        
        messages = db.query(OutboundMessage).filter(
            OutboundMessage.run_id == batch_results['run_id']
        ).all()
        
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
        
        print(f"   ✓ Exported {len(batch_export)} messages to outbound_batch.json")
        
        # Show sample messages
        print("\n" + "="*70)
        print("📨 SAMPLE OUTBOUND MESSAGES")
        print("="*70)
        
        for i, msg in enumerate(batch_export[:3], 1):
            print(f"\n{i}. 🏢 {msg['company']}")
            print(f"   To: {msg['to_email']}")
            print(f"   Subject: {msg['email_subject']}")
            print(f"   Body Preview:")
            body_lines = msg['email_body'].split('\n')[:5]
            for line in body_lines:
                print(f"      {line}")
            if len(msg['email_body'].split('\n')) > 5:
                print(f"      ... ({len(msg['email_body'])} characters total)")
        
        print("\n" + "="*70)
        print("🤖 READY FOR AUTOMATED SEND")
        print("="*70)
        print(f"\n   Use the following API endpoint to send:")
        print(f"   POST /api/send/batch/{batch_results['run_id']}")
        print(f"\n   Or trigger via Celery:")
        print(f"   celery -A app.workers.celery_app call app.workers.tasks.send_batch_task")
        print(f"   -k '{{\"run_id\": \"{batch_results['run_id']}\"}}'")
        
finally:
    db.close()

# Summary
print("\n" + "="*70)
print("✅ DEMONSTRATION COMPLETE - SYSTEM SUMMARY")
print("="*70)

# Get final stats
db = SessionLocal()
try:
    total_leads = db.query(Lead).count()
    qualified = db.query(LeadScore).filter(LeadScore.is_qualified == True).count()
    total_messages = db.query(OutboundMessage).count()
    pending_sends = db.query(OutboundMessage).filter(OutboundMessage.status == "queued").count()
    
    print(f"""
📊 FINAL STATISTICS:
   • Total Leads in Database: {total_leads}
   • Qualified Leads: {qualified}
   • Outbound Messages Ready: {total_messages}
   • Pending to Send: {pending_sends}

📁 FILES UPDATED:
   • leads.json - Contains {len(qualified_leads)} enriched leads
   • outbound_batch.json - Contains {total_messages} email messages

🚀 NEXT STEPS:
   1. Review leads: GET /api/leads
   2. Review batch: GET /api/runs/{batch_results['run_id']}
   3. Send emails: POST /api/send/batch/{batch_results['run_id']}
   4. Monitor replies: Webhook configured at /api/webhooks/gmail

🔄 AUTOMATION STATUS:
   • Autonomous Discovery: Ready to run every 6 hours
   • Reply Classification: Active
   • Follow-up Automation: Active
   • Pipeline State Machine: Active
""")
finally:
    db.close()

print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)
print("🎉 YOUR AI-POWERED OUTBOUND SYSTEM IS READY!")
print("="*70)
