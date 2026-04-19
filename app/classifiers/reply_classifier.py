from sqlalchemy.orm import Session
from app.models import Reply, Lead, OutboundMessage, SuppressionList, Event
from app.settings import settings
from app.services.pipeline_state_machine import PipelineStateMachine
from app.services.conversation_memory import ConversationMemoryLayer
from app.services.human_escalation import HumanEscalationLayer
from app.services.template_service import TemplateService
import openai
import uuid
from datetime import datetime
import re

import logging
logger = logging.getLogger(__name__)


class ReplyClassifier:
    """Service for classifying email replies into 4 outcomes"""
    
    CLASSIFICATIONS = ["interested", "not_now", "not_interested", "unsubscribe"]
    
    def __init__(self, db: Session):
        self.db = db
        openai.api_key = settings.OPENAI_API_KEY
        self.pipeline = PipelineStateMachine(db)
        self.conversation_memory = ConversationMemoryLayer(db)
        self.escalation = HumanEscalationLayer(db)
    
    def classify_and_process(self, reply_id: str) -> dict:
        """Classify a reply and take appropriate action"""
        reply = self.db.query(Reply).filter(Reply.reply_id == reply_id).first()
        if not reply:
            return {"success": False, "error": "Reply not found"}
        
        lead_id = reply.lead_id
        
        # Classify the reply
        classification = self._classify(reply.body)
        
        # Update reply record
        reply.classification = classification
        reply.processed_at = datetime.utcnow()
        
        # Record in conversation memory
        self.conversation_memory.record_reply_received(reply_id, lead_id, reply.body)
        
        # Auto-transition pipeline based on classification
        self.pipeline.auto_transition_on_reply(lead_id, classification)
        
        # Update template performance if template was used
        self._update_template_performance(reply, classification)
        
        # Check for human escalation
        escalation_check = self.escalation.evaluate_for_escalation(lead_id, reply_id)
        if escalation_check["escalate"]:
            logger.info(f"Lead {lead_id} escalated to human queue: {escalation_check['reason']}")
        
        # Take action based on classification
        result = self._take_action(reply, classification)
        
        # Log event
        self._log_event(
            event_type="reply_classified",
            entity_type="reply",
            entity_id=reply_id,
            data={
                "classification": classification,
                "action_taken": result["action"]
            }
        )
        
        self.db.commit()
        
        return {
            "success": True,
            "classification": classification,
            "action": result["action"],
            "details": result
        }
    
    def _update_template_performance(self, reply: Reply, classification: str):
        """Update template performance metrics based on reply classification"""
        try:
            # Get the original message to find template_id
            message = self.db.query(OutboundMessage).filter(
                OutboundMessage.message_id == reply.message_id
            ).first()
            
            if not message or not message.template_id:
                return  # No template used for this message
            
            # Update template performance
            template_service = TemplateService(self.db)
            is_positive = classification in ["interested", "positive"]
            
            template_service.update_template_performance(
                template_id=message.template_id,
                reply_received=True,
                positive=is_positive
            )
            
            logger.info(f"Updated template {message.template_id} performance: reply={classification}, positive={is_positive}")
            
        except Exception as e:
            logger.error(f"Error updating template performance: {e}")
    
    def _classify(self, text: str) -> str:
        """Classify reply text using LLM"""
        try:
            prompt = f"""
Classify this email reply into exactly one of these categories:
1. interested - They want to learn more, schedule a call, or move forward
2. not_now - They're interested but timing is wrong, ask to follow up later
3. not_interested - They're not interested or don't see a fit
4. unsubscribe - They explicitly ask to be removed from emails

Reply text:
{text}

Return only the category name (interested, not_now, not_interested, or unsubscribe), nothing else.
"""
            
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at classifying sales email responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=10
            )
            
            classification = response.choices[0].message.content.strip().lower()
            
            # Validate classification
            if classification not in self.CLASSIFICATIONS:
                classification = self._fallback_classify(text)
            
            return classification
            
        except Exception as e:
            # Fallback to rule-based classification
            return self._fallback_classify(text)
    
    def _fallback_classify(self, text: str) -> str:
        """Fallback rule-based classification"""
        text_lower = text.lower()
        
        # Check for unsubscribe signals
        if any(word in text_lower for word in ["unsubscribe", "remove", "stop emailing", "take me off"]):
            return "unsubscribe"
        
        # Check for interested signals
        if any(word in text_lower for word in ["interested", "let's talk", "schedule", "call", "meeting", "demo", "more info", "tell me more"]):
            return "interested"
        
        # Check for not_now signals
        if any(word in text_lower for word in ["not now", "later", "wrong time", "busy", "follow up later", "next quarter", "next month"]):
            return "not_now"
        
        # Default to not_interested
        return "not_interested"
    
    def _take_action(self, reply: Reply, classification: str) -> dict:
        """Take action based on classification"""
        lead = self.db.query(Lead).filter(Lead.lead_id == reply.lead_id).first()
        
        if classification == "interested":
            return self._handle_interested(reply, lead)
        elif classification == "not_now":
            return self._handle_not_now(reply, lead)
        elif classification == "not_interested":
            return self._handle_not_interested(reply, lead)
        elif classification == "unsubscribe":
            return self._handle_unsubscribe(reply, lead)
        
        return {"action": "none"}
    
    def _handle_interested(self, reply: Reply, lead: Lead) -> dict:
        """Handle interested reply - create meeting task, stop follow-ups"""
        if lead:
            lead.status = "positive"
        
        # Cancel any pending follow-ups
        from app.models import Followup
        self.db.query(Followup).filter(
            Followup.lead_id == reply.lead_id,
            Followup.status == "scheduled"
        ).update({"status": "cancelled"})
        
        return {
            "action": "meeting_task_created",
            "lead_status": "positive",
            "followups_cancelled": True
        }
    
    def _handle_not_now(self, reply: Reply, lead: Lead) -> dict:
        """Handle not_now reply - schedule one follow-up later"""
        if lead:
            lead.status = "not_now"
        
        # Schedule follow-up for 7 days later
        from app.models import Followup
        followup = Followup(
            followup_id=f"followup-{str(uuid.uuid4())[:8]}",
            message_id=reply.message_id,
            lead_id=reply.lead_id,
            sequence_number=1,
            scheduled_for=datetime.utcnow(),
            status="scheduled"
        )
        self.db.add(followup)
        
        return {
            "action": "followup_scheduled",
            "lead_status": "not_now",
            "followup_in_days": 7
        }
    
    def _handle_not_interested(self, reply: Reply, lead: Lead) -> dict:
        """Handle not_interested reply - suppress lead"""
        if lead:
            lead.status = "not_interested"
        
        # Add to suppression list
        message = self.db.query(OutboundMessage).filter(
            OutboundMessage.message_id == reply.message_id
        ).first()
        
        if message:
            suppression = SuppressionList(
                email=message.to_email,
                reason="not_interested",
                lead_id=reply.lead_id
            )
            self.db.add(suppression)
        
        # Cancel pending follow-ups
        from app.models import Followup
        self.db.query(Followup).filter(
            Followup.lead_id == reply.lead_id,
            Followup.status == "scheduled"
        ).update({"status": "cancelled"})
        
        return {
            "action": "lead_suppressed",
            "lead_status": "not_interested",
            "followups_cancelled": True
        }
    
    def _handle_unsubscribe(self, reply: Reply, lead: Lead) -> dict:
        """Handle unsubscribe reply - add to suppression list immediately"""
        if lead:
            lead.status = "unsubscribe"
        
        # Add to suppression list
        message = self.db.query(OutboundMessage).filter(
            OutboundMessage.message_id == reply.message_id
        ).first()
        
        if message:
            suppression = SuppressionList(
                email=message.to_email,
                reason="unsubscribe",
                lead_id=reply.lead_id
            )
            self.db.add(suppression)
        
        # Cancel pending follow-ups
        from app.models import Followup
        self.db.query(Followup).filter(
            Followup.lead_id == reply.lead_id,
            Followup.status == "scheduled"
        ).update({"status": "cancelled"})
        
        return {
            "action": "lead_suppressed",
            "lead_status": "unsubscribe",
            "followups_cancelled": True
        }
    
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
