from sqlalchemy.orm import Session
from app.models import OutboundMessage, Lead, Followup, Event
from app.services.subject_generator import SubjectGenerator
from app.services.email_renderer import EmailRenderer
from datetime import datetime, timedelta
import uuid


class FollowupScheduler:
    """Service for scheduling follow-up messages"""
    
    # Follow-up sequence: Day 2, Day 5, Day 9
    FOLLOWUP_DAYS = [2, 5, 9]
    
    def __init__(self, db: Session):
        self.db = db
        self.subject_generator = SubjectGenerator()
        self.email_renderer = EmailRenderer()
    
    def schedule_followups(self) -> dict:
        """Schedule follow-ups for leads that need them"""
        results = {
            "scheduled": 0,
            "skipped": 0,
            "errors": []
        }
        
        # Get sent messages without replies that need follow-ups
        messages = self.db.query(OutboundMessage).filter(
            OutboundMessage.status == 'sent',
            OutboundMessage.sent_at.isnot(None)
        ).all()
        
        for message in messages:
            try:
                # Check if lead has any replies
                from app.models import Reply
                has_reply = self.db.query(Reply).filter(
                    Reply.message_id == message.message_id
                ).first()
                
                if has_reply:
                    results["skipped"] += 1
                    continue
                
                # Check if lead is in a status that allows follow-ups
                lead = self.db.query(Lead).filter(Lead.lead_id == message.lead_id).first()
                if not lead or lead.status in ["replied", "positive", "unsubscribe", "not_interested"]:
                    results["skipped"] += 1
                    continue
                
                # Check existing follow-ups
                existing_followups = self.db.query(Followup).filter(
                    Followup.message_id == message.message_id,
                    Followup.status.in_(["scheduled", "sent"])
                ).count()
                
                # Schedule next follow-up if we haven't reached the limit
                if existing_followups < len(self.FOLLOWUP_DAYS):
                    self._schedule_next_followup(message, lead, existing_followups)
                    results["scheduled"] += 1
                else:
                    results["skipped"] += 1
                    
            except Exception as e:
                results["errors"].append({
                    "message_id": message.message_id,
                    "error": str(e)
                })
        
        # Log event
        self._log_event(
            event_type="followups_scheduled",
            entity_type="system",
            entity_id="scheduler",
            data=results
        )
        
        self.db.commit()
        return results
    
    def _schedule_next_followup(self, message: OutboundMessage, lead: Lead, sequence_number: int):
        """Schedule the next follow-up in the sequence"""
        days_to_wait = self.FOLLOWUP_DAYS[sequence_number]
        scheduled_date = datetime.utcnow() + timedelta(days=days_to_wait)
        
        # Generate follow-up subject and body
        subject = self.subject_generator.generate(lead)
        body = self._generate_followup_body(lead, sequence_number)
        
        # Create follow-up record
        followup = Followup(
            followup_id=f"followup-{str(uuid.uuid4())[:8]}",
            message_id=message.message_id,
            lead_id=lead.lead_id,
            sequence_number=sequence_number + 1,
            scheduled_for=scheduled_date,
            status="scheduled",
            subject=subject,
            body=body
        )
        
        self.db.add(followup)
    
    def _generate_followup_body(self, lead: Lead, sequence_number: int) -> str:
        """Generate follow-up body based on sequence number"""
        followup_templates = {
            0: "Hi {decision_maker},\n\nJust wanted to bump this to the top of your inbox. Any thoughts on the previous message?\n\nBest,",
            1: "Hi {decision_maker},\n\nQuick reminder about this - still interested in exploring how we can help with {company}?\n\nBest,",
            2: "Hi {decision_maker},\n\nLast check-in on this. If it's not a priority right now, no worries. Just wanted to make sure this didn't get lost.\n\nBest,"
        }
        
        template = followup_templates.get(sequence_number, followup_templates[2])
        
        return template.format(
            decision_maker=lead.decision_maker or "there",
            company=lead.company
        )
    
    def send_due_followups(self) -> dict:
        """Send follow-ups that are due"""
        results = {
            "sent": 0,
            "skipped": 0,
            "errors": []
        }
        
        now = datetime.utcnow()
        
        # Get due follow-ups
        due_followups = self.db.query(Followup).filter(
            Followup.status == 'scheduled',
            Followup.scheduled_for <= now
        ).all()
        
        for followup in due_followups:
            try:
                # Get original message for from/to emails
                original_message = self.db.query(OutboundMessage).filter(
                    OutboundMessage.message_id == followup.message_id
                ).first()
                
                if not original_message:
                    results["skipped"] += 1
                    continue
                
                # Send the follow-up
                from app.services.gmail_sender import GmailSender
                sender = GmailSender(self.db)
                
                # Create a temporary outbound message for sending
                temp_message_id = f"followup-msg-{str(uuid.uuid4())[:8]}"
                temp_message = OutboundMessage(
                    message_id=temp_message_id,
                    run_id=original_message.run_id,
                    lead_id=followup.lead_id,
                    subject=followup.subject,
                    body=followup.body,
                    to_email=original_message.to_email,
                    from_email=original_message.from_email,
                    status="queued"
                )
                self.db.add(temp_message)
                self.db.commit()
                
                result = sender.send_message(temp_message_id)
                
                if result["success"]:
                    followup.status = "sent"
                    followup.sent_at = now
                    results["sent"] += 1
                else:
                    results["errors"].append({
                        "followup_id": followup.followup_id,
                        "error": result.get("error")
                    })
                    
            except Exception as e:
                results["errors"].append({
                    "followup_id": followup.followup_id,
                    "error": str(e)
                })
        
        # Log event
        self._log_event(
            event_type="followups_sent",
            entity_type="system",
            entity_id="scheduler",
            data=results
        )
        
        self.db.commit()
        return results
    
    def _log_event(self, event_type: str, entity_type: str, entity_id: str, data: dict):
        """Log an event to the events table"""
        event = Event(
            event_id=f"{event_type}-{entity_id}-{str(uuid.uuid4())[:8]}",
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            data=data
        )
        self.db.add(event)
