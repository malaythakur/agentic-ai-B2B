import json
import uuid
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models import Lead, Event
from datetime import datetime


class LeadLoader:
    """Service for importing leads from JSON into PostgreSQL"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def load_from_json(self, json_path: str) -> Dict:
        """Load leads from JSON file and import into database"""
        with open(json_path, 'r') as f:
            leads_data = json.load(f)
        
        results = {
            "total": len(leads_data),
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "errors": []
        }
        
        for lead_data in leads_data:
            try:
                lead_id = self._generate_lead_id(lead_data["company"])
                
                # Check if lead already exists
                existing_lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
                
                lead_record = {
                    "lead_id": lead_id,
                    "company": lead_data["company"],
                    "website": lead_data.get("website"),
                    "signal": self._build_signal(lead_data),
                    "decision_maker": lead_data.get("decision_maker"),
                    "fit_score": int(lead_data.get("fit_score", 0)),
                    "message_intent": lead_data.get("message"),
                    "status": "new"
                }
                
                if existing_lead:
                    # Update existing lead
                    for key, value in lead_record.items():
                        setattr(existing_lead, key, value)
                    results["updated"] += 1
                else:
                    # Create new lead
                    new_lead = Lead(**lead_record)
                    self.db.add(new_lead)
                    results["imported"] += 1
                
                # Log event
                self._log_event(
                    event_type="lead_imported" if not existing_lead else "lead_updated",
                    entity_type="lead",
                    entity_id=lead_id,
                    data=lead_record
                )
                
            except Exception as e:
                results["errors"].append({
                    "company": lead_data.get("company", "unknown"),
                    "error": str(e)
                })
                results["skipped"] += 1
        
        self.db.commit()
        return results
    
    def _generate_lead_id(self, company: str) -> str:
        """Generate a unique lead_id from company name"""
        return f"{company.lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}"
    
    def _build_signal(self, lead_data: Dict) -> str:
        """Build comprehensive signal from lead data"""
        signal_parts = []
        
        if lead_data.get("signal"):
            signal_parts.append(f"Signal: {lead_data['signal']}")
        
        if lead_data.get("pain_point"):
            signal_parts.append(f"Pain Point: {lead_data['pain_point']}")
        
        if lead_data.get("urgency_reason"):
            signal_parts.append(f"Urgency: {lead_data['urgency_reason']}")
        
        if lead_data.get("custom_hook"):
            signal_parts.append(f"Custom Hook: {lead_data['custom_hook']}")
        
        if lead_data.get("followups"):
            signal_parts.append(f"Followups: {', '.join(lead_data['followups'])}")
        
        return " | ".join(signal_parts)
    
    def _log_event(self, event_type: str, entity_type: str, entity_id: str, data: Dict):
        """Log an event to the events table"""
        event = Event(
            event_id=f"{event_type}-{entity_id}-{str(uuid.uuid4())[:8]}",
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            data=data
        )
        self.db.add(event)
