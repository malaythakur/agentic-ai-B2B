import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models import Lead, OutboundMessage, Reply, ConversationMemory
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ConversationMemoryLayer:
    """Thread memory system for tracking conversation context"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_email_sent(self, message_id: str, lead_id: str, subject: str, body: str):
        """Record an email sent in the conversation"""
        memory = self._get_or_create_memory(lead_id)
        
        memory.emails_sent += 1
        memory.last_topic = self._extract_topic(subject, body)
        memory.key_points = self._extract_key_points(body)
        memory.context_summary = self._update_summary(memory)
        memory.updated_at = datetime.utcnow()
        
        self.db.commit()
        logger.info(f"Recorded email sent for lead {lead_id}")
    
    def record_reply_received(self, reply_id: str, lead_id: str, body: str):
        """Record a reply received in the conversation"""
        memory = self._get_or_create_memory(lead_id)
        
        memory.replies_received += 1
        memory.tone = self._analyze_tone(body)
        memory.objection_raised = self._detect_objection(body)
        memory.relationship_stage = self._update_relationship_stage(memory)
        memory.context_summary = self._update_summary(memory)
        memory.updated_at = datetime.utcnow()
        
        self.db.commit()
        logger.info(f"Recorded reply received for lead {lead_id}")
    
    def get_conversation_context(self, lead_id: str) -> Dict:
        """Get full conversation context for a lead"""
        memory = self.db.query(ConversationMemory).filter(
            ConversationMemory.lead_id == lead_id
        ).first()
        
        if not memory:
            return {
                "lead_id": lead_id,
                "emails_sent": 0,
                "replies_received": 0,
                "tone": None,
                "relationship_stage": "new",
                "key_points": [],
                "objection_raised": None,
                "context_summary": "No conversation history"
            }
        
        return {
            "lead_id": lead_id,
            "thread_id": memory.thread_id,
            "emails_sent": memory.emails_sent,
            "replies_received": memory.replies_received,
            "tone": memory.tone,
            "relationship_stage": memory.relationship_stage,
            "key_points": memory.key_points or [],
            "objection_raised": memory.objection_raised,
            "last_topic": memory.last_topic,
            "context_summary": memory.context_summary
        }
    
    def _get_or_create_memory(self, lead_id: str):
        """Get or create conversation memory for a lead"""
        memory = self.db.query(ConversationMemory).filter(
            ConversationMemory.lead_id == lead_id
        ).first()
        
        if not memory:
            memory = ConversationMemory(
                memory_id=f"memory-{str(uuid.uuid4())[:8]}",
                lead_id=lead_id,
                relationship_stage="new",
                emails_sent=0,
                replies_received=0
            )
            self.db.add(memory)
            self.db.commit()
        
        return memory
    
    def _extract_topic(self, subject: str, body: str) -> str:
        """Extract the main topic from email"""
        text = f"{subject} {body}"
        
        # Simple keyword extraction
        keywords = ["pipeline", "growth", "hiring", "funding", "sales", "revenue", "demo", "meeting"]
        found = [kw for kw in keywords if kw.lower() in text.lower()]
        
        return found[0] if found else "general outreach"
    
    def _extract_key_points(self, body: str) -> list:
        """Extract key points from email body"""
        key_points = []
        
        sentences = body.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 150:
                # Likely a key point
                key_points.append(sentence)
        
        return key_points[:5]  # Top 5 key points
    
    def _analyze_tone(self, body: str) -> str:
        """Analyze the tone of a reply"""
        body_lower = body.lower()
        
        positive_indicators = ["interested", "yes", "sure", "sounds good", "let's", "please", "thanks"]
        negative_indicators = ["no", "not interested", "remove", "unsubscribe", "stop", "don't", "won't"]
        neutral_indicators = ["maybe", "later", "busy", "not now", "timing"]
        urgent_indicators = ["asap", "urgent", "immediately", "quickly"]
        
        positive_count = sum(1 for word in positive_indicators if word in body_lower)
        negative_count = sum(1 for word in negative_indicators if word in body_lower)
        neutral_count = sum(1 for word in neutral_indicators if word in body_lower)
        urgent_count = sum(1 for word in urgent_indicators if word in body_lower)
        
        if urgent_count >= 1:
            return "urgent"
        elif positive_count >= 2:
            return "positive"
        elif negative_count >= 2:
            return "negative"
        elif neutral_count >= 1:
            return "neutral"
        else:
            return "neutral"
    
    def _detect_objection(self, body: str) -> Optional[str]:
        """Detect if an objection was raised"""
        body_lower = body.lower()
        
        objections = {
            "price": ["price", "cost", "expensive", "budget", "too much"],
            "timing": ["not now", "later", "wrong time", "busy", "timing"],
            "authority": ["not my decision", "need to ask", "check with"],
            "interest": ["not interested", "pass", "no need"],
            "competitor": ["already using", "have a solution", "happy with current"]
        }
        
        for objection_type, keywords in objections.items():
            if any(keyword in body_lower for keyword in keywords):
                return objection_type
        
        return None
    
    def _update_relationship_stage(self, memory) -> str:
        """Update relationship stage based on conversation history"""
        if memory.replies_received == 0:
            return "outreach"
        elif memory.replies_received == 1:
            if memory.tone == "positive":
                return "engaged"
            elif memory.tone == "negative":
                return "declined"
            else:
                return "responded"
        elif memory.replies_received >= 2:
            if memory.tone == "positive":
                return "qualified"
            else:
                return "in_progress"
        
        return memory.relationship_stage
    
    def _update_summary(self, memory) -> str:
        """Generate context summary"""
        parts = []
        
        if memory.emails_sent > 0:
            parts.append(f"{memory.emails_sent} emails sent")
        
        if memory.replies_received > 0:
            parts.append(f"{memory.replies_received} replies received")
        
        if memory.tone:
            parts.append(f"tone: {memory.tone}")
        
        if memory.objection_raised:
            parts.append(f"objection: {memory.objection_raised}")
        
        if memory.last_topic:
            parts.append(f"last topic: {memory.last_topic}")
        
        return " | ".join(parts) if parts else "Initial outreach"
    
    def get_followup_context(self, lead_id: str) -> Dict:
        """Get context specifically for follow-up generation"""
        context = self.get_conversation_context(lead_id)
        
        followup_guidance = {
            "should_followup": True,
            "followup_style": None,
            "address_objection": None,
            "reference_previous": False
        }
        
        # Determine followup strategy
        if context["replies_received"] == 0:
            followup_guidance["followup_style"] = "gentle_bump"
            followup_guidance["reference_previous"] = True
        elif context["objection_raised"]:
            followup_guidance["followup_style"] = "objection_handling"
            followup_guidance["address_objection"] = context["objection_raised"]
        elif context["tone"] == "positive":
            followup_guidance["followup_style"] = "accelerate"
            followup_guidance["should_followup"] = False  # Let human take over
        elif context["tone"] == "negative":
            followup_guidance["should_followup"] = False
        else:
            followup_guidance["followup_style"] = "value_add"
        
        return {
            **context,
            "followup_guidance": followup_guidance
        }
