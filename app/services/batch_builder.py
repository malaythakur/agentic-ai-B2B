import uuid
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Lead, CampaignRun, OutboundMessage, Event, SuppressionList
from datetime import datetime
from app.services.lead_qualification import LeadQualificationEngine
from app.services.offer_matching import OfferMatchingEngine
from app.services.template_service import match_and_personalize, TemplateService

logger = logging.getLogger(__name__)


class BatchBuilder:
    """Service for building outbound batches from leads with template-based personalization"""
    
    def __init__(self, db: Session):
        self.db = db
        self.qualification_engine = LeadQualificationEngine(db)
        self.offer_engine = OfferMatchingEngine(db)
        self.template_service = TemplateService(db)
    
    def build_batch(
        self,
        from_email: str,
        max_leads: int = 50,
        min_fit_score: int = 7,
        exclude_statuses: List[str] = None
    ) -> Dict:
        """Build an outbound batch from eligible leads"""
        if exclude_statuses is None:
            exclude_statuses = ["sent", "replied", "positive", "not_now", "unsubscribe", "bounced"]
        
        # Create campaign run
        run_id = f"run-{str(uuid.uuid4())[:8]}"
        campaign_run = CampaignRun(
            run_id=run_id,
            name=f"Batch {datetime.now().strftime('%Y-%m-%d')}",
            status="pending",
            total_leads=0
        )
        self.db.add(campaign_run)
        
        # Get eligible leads
        eligible_leads = self._get_eligible_leads(min_fit_score, exclude_statuses, max_leads)
        
        results = {
            "run_id": run_id,
            "total_leads": len(eligible_leads),
            "messages_created": 0,
            "errors": []
        }
        
        for lead in eligible_leads:
            try:
                # Check suppression list
                if self._is_suppressed(lead):
                    continue
                
                # Match offer strategy
                offer_match = self.offer_engine.match_offer(lead)
                
                # Match template and personalize message
                message_data = match_and_personalize(
                    self.db, 
                    lead, 
                    offer_angle=offer_match.get("offer_angle")
                )
                
                # Track template usage if template was used
                if message_data.get("template_id"):
                    self.template_service.record_template_usage(
                        message_data["template_id"],
                        f"msg-{str(uuid.uuid4())[:8]}"
                    )
                
                # Create outbound message
                message_id = f"msg-{str(uuid.uuid4())[:8]}"
                to_email = self._extract_email(lead)
                
                if not to_email:
                    results["errors"].append({
                        "lead_id": lead.lead_id,
                        "error": "No email found"
                    })
                    continue
                
                outbound_message = OutboundMessage(
                    message_id=message_id,
                    run_id=run_id,
                    lead_id=lead.lead_id,
                    subject=message_data["subject"],
                    body=message_data["body"],
                    to_email=to_email,
                    from_email=from_email,
                    status="queued",
                    template_id=message_data.get("template_id"),
                    personalization_method=message_data.get("personalization_method", "ai_generated")
                )
                self.db.add(outbound_message)
                
                # Update lead status
                lead.status = "queued"
                
                results["messages_created"] += 1
                
            except Exception as e:
                results["errors"].append({
                    "lead_id": lead.lead_id,
                    "error": str(e)
                })
        
        # Update campaign run
        campaign_run.total_leads = results["messages_created"]
        campaign_run.status = "generated"
        
        # Log event
        self._log_event(
            event_type="batch_generated",
            entity_type="campaign_run",
            entity_id=run_id,
            data=results
        )
        
        self.db.commit()
        
        # Export to outbound_batch.json
        self._export_to_json(run_id, from_email)
        
        return results
    
    def _get_eligible_leads(
        self,
        min_fit_score: int,
        exclude_statuses: List[str],
        limit: int
    ) -> List[Lead]:
        """Get leads eligible for outbound using qualification engine"""
        # First, get raw leads
        query = self.db.query(Lead).filter(
            and_(
                Lead.fit_score >= min_fit_score,
                ~Lead.status.in_(exclude_statuses)
            )
        ).order_by(Lead.fit_score.desc()).limit(limit * 2)  # Get more to filter
        
        leads = query.all()
        
        # Score and filter using qualification engine
        qualified_leads = []
        for lead in leads:
            score_result = self.qualification_engine.score_lead(lead)
            if score_result["is_qualified"] and score_result["priority_score"] >= 50:
                qualified_leads.append(lead)
                if len(qualified_leads) >= limit:
                    break
        
        return qualified_leads
    
    def _is_suppressed(self, lead: Lead) -> bool:
        """Check if lead is in suppression list"""
        # Check by email if available
        email = self._extract_email(lead)
        if email:
            suppressed = self.db.query(SuppressionList).filter(
                SuppressionList.email == email
            ).first()
            if suppressed:
                return True
        
        # Check by lead_id
        suppressed = self.db.query(SuppressionList).filter(
            SuppressionList.lead_id == lead.lead_id
        ).first()
        if suppressed:
            return True
        
        return False
    
    def _extract_email(self, lead: Lead) -> Optional[str]:
        """Extract email from lead data"""
        import re
        
        # Try to extract email from signal field
        if lead.signal:
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            emails = re.findall(email_pattern, lead.signal)
            if emails:
                return emails[0]
        
        # Try to extract from website (construct likely email)
        if lead.website:
            domain = lead.website.replace('https://', '').replace('http://', '').replace('www.', '')
            # Common patterns for decision makers
            if lead.decision_maker:
                name_parts = lead.decision_maker.lower().split()
                if len(name_parts) >= 2:
                    first_initial = name_parts[0][0]
                    last_name = name_parts[-1]
                    return f"{first_initial}.{last_name}@{domain}"
        
        # Fallback: return None - you'll need to add actual email data to your leads
        logger.warning(f"No email found for lead {lead.lead_id}. Please add email data to leads.json")
        return None
    
    def _export_to_json(self, run_id: str, from_email: str):
        """Export batch to outbound_batch.json"""
        import json
        
        messages = self.db.query(OutboundMessage).filter(
            OutboundMessage.run_id == run_id
        ).all()
        
        batch_data = []
        for msg in messages:
            batch_data.append({
                "message_id": msg.message_id,
                "lead_id": msg.lead_id,
                "subject": msg.subject,
                "body": msg.body,
                "to_email": msg.to_email,
                "from_email": msg.from_email
            })
        
        with open("data/outbound_batch.json", "w") as f:
            json.dump(batch_data, f, indent=2)
    
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
