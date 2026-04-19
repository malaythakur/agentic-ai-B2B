#!/usr/bin/env python3
"""Debug batch generation"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.services.batch_builder import BatchBuilder
from app.models import Lead

db = SessionLocal()
builder = BatchBuilder(db)

# Get eligible leads first
leads = db.query(Lead).filter(Lead.fit_score >= 7).limit(1).all()
print(f'Found {len(leads)} leads to test')

for lead in leads:
    print(f'\nTesting lead: {lead.company}')
    print(f'  Website: {lead.website}')
    print(f'  Decision Maker: {lead.decision_maker}')
    
    email = builder._extract_email(lead)
    print(f'  Email: {email}')
    
    # Try to match offer
    try:
        offer = builder.offer_engine.match_offer(lead)
        print(f'  Offer: {offer}')
    except Exception as e:
        print(f'  Offer Error: {e}')
    
    # Try template personalization
    try:
        from app.services.template_service import match_and_personalize
        message_data = match_and_personalize(db, lead)
        print(f'  Template matched: {message_data.get("template_id")}')
        print(f'  Subject: {message_data.get("subject", "N/A")[:50]}')
    except Exception as e:
        print(f'  Template Error: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()

db.close()
