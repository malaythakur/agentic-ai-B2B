import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models import Lead, Reply, HumanEscalationQueue
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class HumanEscalationLayer:
    """Route high-value leads, pricing questions, angry replies to human inbox"""
    
    ESCALATION_REASONS = {
        "pricing": "Pricing question - requires human negotiation",
        "negotiation": "Negotiation needed - human intervention required",
        "angry": "Angry reply - requires human damage control",
        "high_value": "High-value lead - human attention recommended",
        "complex": "Complex inquiry - beyond automated handling"
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def evaluate_for_escalation(self, lead_id: str, reply_id: str = None, message_id: str = None) -> Dict:
        """Evaluate if a lead should be escalated to human"""
        escalation_needed = False
        reason = None
        priority = "normal"
        
        lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return {"escalate": False, "reason": "Lead not found"}
        
        # Check lead score
        from app.models import LeadScore
        lead_score = self.db.query(LeadScore).filter(
            LeadScore.lead_id == lead_id
        ).first()
        
        if lead_score and lead_score.priority_score >= 80:
            escalation_needed = True
            reason = "high_value"
            priority = "high"
        
        # Check reply content if provided
        if reply_id:
            reply = self.db.query(Reply).filter(Reply.reply_id == reply_id).first()
            if reply:
                escalation_check = self._check_reply_for_escalation(reply.body)
                if escalation_check["escalate"]:
                    escalation_needed = True
                    reason = escalation_check["reason"]
                    priority = escalation_check.get("priority", "normal")
        
        if escalation_needed:
            self._create_escalation(lead_id, message_id, reply_id, reason, priority)
        
        return {
            "escalate": escalation_needed,
            "reason": reason,
            "priority": priority if escalation_needed else None
        }
    
    def _check_reply_for_escalation(self, reply_body: str) -> Dict:
        """Check if reply content requires human escalation"""
        body_lower = reply_body.lower()
        
        # Pricing/negotiation triggers
        pricing_keywords = ["price", "cost", "pricing", "discount", "negotiate", "budget"]
        if any(keyword in body_lower for keyword in pricing_keywords):
            return {"escalate": True, "reason": "pricing", "priority": "normal"}
        
        # Angry/negative triggers
        angry_keywords = ["angry", "furious", "unhappy", "terrible", "worst", "never again", "spam"]
        if any(keyword in body_lower for keyword in angry_keywords):
            return {"escalate": True, "reason": "angry", "priority": "urgent"}
        
        # Complex inquiry triggers
        complex_keywords = ["custom", "integration", "api", "enterprise", "contract", "legal"]
        if any(keyword in body_lower for keyword in complex_keywords):
            return {"escalate": True, "reason": "complex", "priority": "high"}
        
        return {"escalate": False}
    
    def _create_escalation(self, lead_id: str, message_id: str, reply_id: str, reason: str, priority: str):
        """Create an escalation queue entry"""
        escalation = HumanEscalationQueue(
            escalation_id=f"escalation-{str(uuid.uuid4())[:8]}",
            lead_id=lead_id,
            message_id=message_id,
            reply_id=reply_id,
            escalation_reason=reason,
            priority=priority,
            status="pending"
        )
        
        self.db.add(escalation)
        self.db.commit()
        
        logger.info(f"Created escalation for lead {lead_id}, reason: {reason}, priority: {priority}")
    
    def get_pending_escalations(self, priority: str = None) -> list:
        """Get pending escalations, optionally filtered by priority"""
        query = self.db.query(HumanEscalationQueue).filter(
            HumanEscalationQueue.status == "pending"
        )
        
        if priority:
            query = query.filter(HumanEscalationQueue.priority == priority)
        
        escalations = query.order_by(
            HumanEscalationQueue.priority.desc(),
            HumanEscalationQueue.created_at.asc()
        ).all()
        
        return [
            {
                "escalation_id": esc.escalation_id,
                "lead_id": esc.lead_id,
                "message_id": esc.message_id,
                "reply_id": esc.reply_id,
                "escalation_reason": esc.escalation_reason,
                "priority": esc.priority,
                "context_summary": esc.context_summary,
                "created_at": esc.created_at.isoformat() if esc.created_at else None
            }
            for esc in escalations
        ]
    
    def assign_escalation(self, escalation_id: str, assigned_to: str) -> Dict:
        """Assign an escalation to a human"""
        escalation = self.db.query(HumanEscalationQueue).filter(
            HumanEscalationQueue.escalation_id == escalation_id
        ).first()
        
        if not escalation:
            return {"error": "Escalation not found"}
        
        escalation.assigned_to = assigned_to
        escalation.assigned_at = datetime.utcnow()
        escalation.status = "in_progress"
        
        self.db.commit()
        
        logger.info(f"Assigned escalation {escalation_id} to {assigned_to}")
        
        return {"success": True, "escalation_id": escalation_id, "assigned_to": assigned_to}
    
    def resolve_escalation(self, escalation_id: str, resolution_notes: str) -> Dict:
        """Mark an escalation as resolved"""
        escalation = self.db.query(HumanEscalationQueue).filter(
            HumanEscalationQueue.escalation_id == escalation_id
        ).first()
        
        if not escalation:
            return {"error": "Escalation not found"}
        
        escalation.status = "resolved"
        escalation.resolution_notes = resolution_notes
        escalation.resolved_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Resolved escalation {escalation_id}")
        
        return {"success": True, "escalation_id": escalation_id}
    
    def dismiss_escalation(self, escalation_id: str, reason: str) -> Dict:
        """Dismiss an escalation (not actually requiring human action)"""
        escalation = self.db.query(HumanEscalationQueue).filter(
            HumanEscalationQueue.escalation_id == escalation_id
        ).first()
        
        if not escalation:
            return {"error": "Escalation not found"}
        
        escalation.status = "dismissed"
        escalation.resolution_notes = f"Dismissed: {reason}"
        
        self.db.commit()
        
        logger.info(f"Dismissed escalation {escalation_id}: {reason}")
        
        return {"success": True, "escalation_id": escalation_id}
    
    def get_escalation_stats(self) -> Dict:
        """Get escalation queue statistics"""
        total_pending = self.db.query(HumanEscalationQueue).filter(
            HumanEscalationQueue.status == "pending"
        ).count()
        
        total_in_progress = self.db.query(HumanEscalationQueue).filter(
            HumanEscalationQueue.status == "in_progress"
        ).count()
        
        total_resolved = self.db.query(HumanEscalationQueue).filter(
            HumanEscalationQueue.status == "resolved"
        ).count()
        
        urgent_pending = self.db.query(HumanEscalationQueue).filter(
            HumanEscalationQueue.status == "pending",
            HumanEscalationQueue.priority == "urgent"
        ).count()
        
        # By reason
        by_reason = {}
        for reason in self.ESCALATION_REASONS.keys():
            count = self.db.query(HumanEscalationQueue).filter(
                HumanEscalationQueue.escalation_reason == reason,
                HumanEscalationQueue.status == "pending"
            ).count()
            by_reason[reason] = count
        
        return {
            "total_pending": total_pending,
            "total_in_progress": total_in_progress,
            "total_resolved": total_resolved,
            "urgent_pending": urgent_pending,
            "by_reason": by_reason
        }
    
    def auto_escalate_high_value_leads(self, min_priority_score: int = 85):
        """Auto-escalate high-value leads"""
        from app.models import LeadScore, PipelineState
        
        # Get high-value leads not in terminal states
        high_value_leads = self.db.query(LeadScore).join(PipelineState).filter(
            LeadScore.priority_score >= min_priority_score,
            PipelineState.current_state.notin_(["CLOSED", "LOST", "SUPPRESSED"])
        ).all()
        
        escalated_count = 0
        
        for lead_score in high_value_leads:
            # Check if already escalated
            existing = self.db.query(HumanEscalationQueue).filter(
                HumanEscalationQueue.lead_id == lead_score.lead_id,
                HumanEscalationQueue.status.in_(["pending", "in_progress"])
            ).first()
            
            if not existing:
                self._create_escalation(
                    lead_score.lead_id,
                    None,
                    None,
                    "high_value",
                    "high"
                )
                escalated_count += 1
        
        logger.info(f"Auto-escalated {escalated_count} high-value leads")
        
        return {"escalated_count": escalated_count}
