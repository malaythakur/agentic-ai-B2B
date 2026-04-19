"""Automated Follow-Up Sequence Engine"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models import Lead, OutboundMessage, Reply, Event
from app.logging_config import logger as app_logger
from datetime import datetime, timedelta
from app.services.ai_email_generator import AIEmailGenerator
from app.services.gmail_sender import GmailSender

logger = app_logger


class FollowUpAutomation:
    """Automated follow-up sequences based on reply status"""
    
    # Follow-up schedule (days after initial outreach)
    SEQUENCE = {
        0: {"type": "initial", "subject": "initial_outreach", "template": "day_0"},
        3: {"type": "bump", "subject": "quick_bump", "template": "day_3"},
        7: {"type": "value", "subject": "value_add", "template": "day_7"},
        14: {"type": "breakup", "subject": "breakup", "template": "day_14"},
        21: {"type": "suppress", "action": "auto_suppress"}
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_generator = AIEmailGenerator(db)
        self.gmail_sender = GmailSender(db)
    
    def run_followup_check(self) -> Dict:
        """Check all leads and send appropriate follow-ups"""
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "followups_sent": 0,
            "suppressed": 0,
            "sequences_completed": 0,
            "details": []
        }
        
        # Get leads that need follow-ups
        leads_needing_followup = self._get_leads_needing_followup()
        
        for lead_data in leads_needing_followup:
            try:
                lead_id = lead_data["lead_id"]
                days_since_last = lead_data["days_since_last_contact"]
                has_replied = lead_data["has_replied"]
                
                # Skip if already replied
                if has_replied:
                    continue
                
                # Check if it's time for next follow-up
                next_followup_day = self._get_next_followup_day(lead_id)
                
                if next_followup_day and days_since_last >= next_followup_day:
                    if next_followup_day == 21:
                        # Auto-suppress after 21 days of no reply
                        self._suppress_lead(lead_id, "No engagement after 21 days")
                        results["suppressed"] += 1
                    else:
                        # Send follow-up
                        followup_config = self.SEQUENCE[next_followup_day]
                        result = self._send_followup(lead_id, followup_config)
                        
                        if result["success"]:
                            results["followups_sent"] += 1
                            results["details"].append({
                                "lead_id": lead_id,
                                "day": next_followup_day,
                                "type": followup_config["type"]
                            })
                
            except Exception as e:
                logger.error(f"Error processing follow-up for {lead_id}: {e}")
        
        logger.info(f"Follow-up check complete: {results['followups_sent']} sent, {results['suppressed']} suppressed")
        return results
    
    def _get_leads_needing_followup(self) -> List[Dict]:
        """Find all leads that need follow-up attention"""
        
        # Get leads that are in "sent" status (initial outreach sent)
        sent_leads = self.db.query(Lead).filter(
            Lead.status.in_(["sent", "contacted"])
        ).all()
        
        leads_data = []
        
        for lead in sent_leads:
            # Get last contact date
            last_message = self.db.query(OutboundMessage).filter(
                OutboundMessage.lead_id == lead.lead_id,
                OutboundMessage.status == "sent"
            ).order_by(OutboundMessage.sent_at.desc()).first()
            
            if not last_message or not last_message.sent_at:
                continue
            
            days_since_last = (datetime.utcnow() - last_message.sent_at).days
            
            # Check if lead has replied
            has_replied = self.db.query(Reply).filter(
                Reply.lead_id == lead.lead_id
            ).first() is not None
            
            leads_data.append({
                "lead_id": lead.lead_id,
                "days_since_last_contact": days_since_last,
                "has_replied": has_replied,
                "last_message_id": last_message.message_id
            })
        
        return leads_data
    
    def _get_next_followup_day(self, lead_id: str) -> Optional[int]:
        """Determine which follow-up day is next for this lead"""
        
        # Count how many follow-ups have been sent
        followup_count = self.db.query(OutboundMessage).filter(
            OutboundMessage.lead_id == lead_id,
            OutboundMessage.personalization_method.in_(["followup_day3", "followup_day7", "followup_day14"])
        ).count()
        
        # Map count to next follow-up day
        followup_days = [0, 3, 7, 14, 21]
        
        if followup_count < len(followup_days) - 1:
            return followup_days[followup_count + 1]
        
        return None
    
    def _send_followup(self, lead_id: str, config: Dict) -> Dict:
        """Send a follow-up email"""
        
        lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return {"success": False, "error": "Lead not found"}
        
        # Get previous message for thread reference
        previous_message = self.db.query(OutboundMessage).filter(
            OutboundMessage.lead_id == lead_id,
            OutboundMessage.status == "sent"
        ).order_by(OutboundMessage.sent_at.desc()).first()
        
        if not previous_message:
            return {"success": False, "error": "No previous message found"}
        
        # Generate follow-up content
        subject, body = self._generate_followup_content(lead, config, previous_message)
        
        # Create follow-up message
        followup_message = OutboundMessage(
            message_id=f"followup-{lead_id}-{config['template']}-{datetime.utcnow().strftime('%Y%m%d')}",
            lead_id=lead_id,
            subject=subject,
            body=body,
            to_email=previous_message.to_email,
            from_email=previous_message.from_email,
            status="queued",
            personalization_method=f"followup_{config['template']}",
            thread_id=previous_message.thread_id
        )
        
        self.db.add(followup_message)
        self.db.commit()
        
        # Auto-send the follow-up (bypass deliverability for follow-ups)
        result = self.gmail_sender.send_message(followup_message.message_id)
        
        if result["success"]:
            logger.info(f"Follow-up sent to {lead.company} ({config['type']})")
            return {"success": True, "message_id": followup_message.message_id}
        else:
            logger.error(f"Failed to send follow-up to {lead.company}: {result.get('error')}")
            return {"success": False, "error": result.get("error")}
    
    def _generate_followup_content(self, lead: Lead, config: Dict, previous_message: OutboundMessage) -> tuple:
        """Generate subject and body for follow-up"""
        
        followup_type = config["type"]
        
        if followup_type == "bump":
            subject = f"Re: {previous_message.subject}"
            body = f"""Hi {lead.decision_maker or 'there'},

Quick bump on my note below - know you're probably swamped.

{previous_message.body[:200]}...

Worth a brief conversation?

Best,
Malay

---

On {previous_message.sent_at.strftime('%b %d')}:
{previous_message.body[:100]}...
"""
        
        elif followup_type == "value":
            subject = f"Thought this might help, {lead.decision_maker or 'there'}"
            body = f"""Hi {lead.decision_maker or 'there'},

Saw this case study of a {lead.signal.split('|')[0] if lead.signal else 'similar company'} using AI outreach to 10x their pipeline.

Link: [value_content_url]

Worth exploring for {lead.company}?

Best,
Malay
"""
        
        elif followup_type == "breakup":
            subject = "Should I close the loop?"
            body = f"""Hi {lead.decision_maker or 'there'},

Totally get it if {lead.company} isn't exploring outbound automation right now.

Wanted to close the loop rather than keep bothering you.

If things change, feel free to ping me.

Best,
Malay
"""
        else:
            # Default to AI-generated
            email = self.ai_generator.generate_personalized_email(lead)
            subject = f"Re: {previous_message.subject}"
            body = email["body"]
        
        return subject, body
    
    def _suppress_lead(self, lead_id: str, reason: str):
        """Suppress lead after no engagement"""
        
        lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if lead:
            lead.status = "unsubscribe"
            
            # Add to suppression list
            from app.models import SuppressionList
            suppression = SuppressionList(
                lead_id=lead_id,
                email=None,  # Would extract from lead data
                reason=reason
            )
            self.db.add(suppression)
            
            # Log event
            event = Event(
                event_id=f"auto-suppress-{lead_id}-{datetime.utcnow().strftime('%Y%m%d')}",
                event_type="lead_auto_suppressed",
                entity_type="lead",
                entity_id=lead_id,
                data={"reason": reason, "days_without_reply": 21}
            )
            self.db.add(event)
            
            self.db.commit()
            
            logger.info(f"Lead {lead_id} auto-suppressed: {reason}")
    
    def get_followup_stats(self) -> Dict:
        """Get statistics on follow-up performance"""
        
        # Count by follow-up day
        stats = {}
        for day, config in self.SEQUENCE.items():
            if day == 21:
                continue
            
            count = self.db.query(OutboundMessage).filter(
                OutboundMessage.personalization_method == f"followup_{config['template']}"
            ).count()
            
            stats[f"day_{day}"] = {
                "sent": count,
                "reply_rate": self._calculate_reply_rate(day)
            }
        
        return stats
    
    def _calculate_reply_rate(self, followup_day: int) -> float:
        """Calculate reply rate for a specific follow-up day"""
        
        # Get all messages for this follow-up day
        messages = self.db.query(OutboundMessage).filter(
            OutboundMessage.personalization_method == f"followup_day{followup_day}"
        ).all()
        
        if not messages:
            return 0.0
        
        # Count replies
        replies = 0
        for msg in messages:
            has_reply = self.db.query(Reply).filter(
                Reply.message_id == msg.message_id
            ).first() is not None
            if has_reply:
                replies += 1
        
        return round(replies / len(messages) * 100, 2)


class ReplyAutoResponder:
    """Auto-classify replies and trigger next actions"""
    
    RESPONSE_PATTERNS = {
        "interested": {
            "keywords": [
                "interested", "tell me more", "pricing", "demo", 
                "book a call", "schedule", "learn more", "sounds good",
                "let's talk", "send info", "proposal", "quote"
            ],
            "action": "send_meeting_link",
            "priority": "high",
            "escalate": True
        },
        "meeting_booked": {
            "keywords": [
                "booked", "scheduled", "calendly", "calendar invite",
                "see you", "looking forward", "confirmed"
            ],
            "action": "mark_meeting_scheduled",
            "priority": "urgent",
            "escalate": True,
            "notify": "sales_team"
        },
        "not_interested": {
            "keywords": [
                "not interested", "pass", "no budget", "not now",
                "wrong time", "no need", "already have", "competitor",
                "not a fit", "decline"
            ],
            "action": "suppress_and_stop",
            "priority": "low",
            "escalate": False
        },
        "wrong_person": {
            "keywords": [
                "wrong person", "not my area", "forward", "someone else",
                "different team", "not responsible", "pass along"
            ],
            "action": "request_intro",
            "priority": "medium",
            "escalate": False
        },
        "unsubscribe": {
            "keywords": [
                "unsubscribe", "remove me", "stop emailing", "opt out",
                "don't contact", "cease", "desist"
            ],
            "action": "immediate_suppress",
            "priority": "high",
            "escalate": False
        },
        "question": {
            "keywords": [
                "what is", "how does", "question", "clarify",
                "explain", "details", "more info"
            ],
            "action": "auto_answer",
            "priority": "medium",
            "escalate": False
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_generator = AIEmailGenerator(db)
        self.gmail_sender = GmailSender(db)
    
    def process_new_reply(self, reply_id: str) -> Dict:
        """Process a new reply and take automated action"""
        
        reply = self.db.query(Reply).filter(Reply.reply_id == reply_id).first()
        if not reply:
            return {"success": False, "error": "Reply not found"}
        
        # Classify the reply
        classification = self._classify_reply(reply.body)
        
        # Update reply with classification
        reply.classification = classification["category"]
        reply.intent = classification["action"]
        
        self.db.commit()
        
        # Take automated action
        action_result = self._take_action(reply, classification)
        
        return {
            "success": True,
            "classification": classification,
            "action_taken": action_result
        }
    
    def _classify_reply(self, reply_body: str) -> Dict:
        """Classify reply using keyword matching + AI"""
        
        reply_lower = reply_body.lower()
        
        # Score each category
        scores = {}
        for category, config in self.RESPONSE_PATTERNS.items():
            score = sum(1 for keyword in config["keywords"] if keyword in reply_lower)
            scores[category] = score
        
        # Find best match
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        
        # If no clear match, default to "question"
        if best_score == 0:
            best_category = "question"
        
        config = self.RESPONSE_PATTERNS[best_category]
        
        return {
            "category": best_category,
            "action": config["action"],
            "priority": config["priority"],
            "escalate": config["escalate"],
            "confidence": min(best_score / 2, 1.0)  # Normalize confidence
        }
    
    def _take_action(self, reply: Reply, classification: Dict) -> Dict:
        """Take automated action based on classification"""
        
        action = classification["action"]
        lead = self.db.query(Lead).filter(Lead.lead_id == reply.lead_id).first()
        
        if action == "send_meeting_link":
            return self._send_meeting_link(lead, reply)
        
        elif action == "mark_meeting_scheduled":
            return self._mark_meeting_scheduled(lead, reply)
        
        elif action == "suppress_and_stop":
            return self._suppress_lead(lead, reply, classification["category"])
        
        elif action == "immediate_suppress":
            return self._suppress_lead(lead, reply, "unsubscribe_request", urgent=True)
        
        elif action == "request_intro":
            return self._request_intro(lead, reply)
        
        elif action == "auto_answer":
            return self._auto_answer_question(lead, reply)
        
        else:
            return {"action": "none", "reason": "No automated action defined"}
    
    def _send_meeting_link(self, lead: Lead, reply: Reply) -> Dict:
        """Auto-send Calendly link to interested lead"""
        
        # Generate meeting booking email
        calendly_url = "https://calendly.com/malaythakur/30min"  # From settings
        
        response_body = f"""Hi {lead.decision_maker or 'there'},

Thanks for the interest! Would love to show you what we're building.

Book a time that works for you: {calendly_url}

Looking forward to connecting,
Malay
"""
        
        # Create and send response
        response_message = OutboundMessage(
            message_id=f"auto-response-{reply.reply_id}",
            lead_id=lead.lead_id,
            subject=f"Re: {reply.subject}",
            body=response_body,
            to_email=reply.from_email,
            from_email=reply.to_email,  # Original sender
            status="queued",
            personalization_method="auto_meeting_link",
            thread_id=reply.thread_id
        )
        
        self.db.add(response_message)
        self.db.commit()
        
        # Send immediately
        result = self.gmail_sender.send_message(response_message.message_id)
        
        # Update lead status
        lead.status = "meeting_link_sent"
        
        # Escalate to sales team
        if result["success"]:
            self._notify_sales_team(lead, "Interested lead - meeting link sent")
        
        return {
            "action": "send_meeting_link",
            "success": result["success"],
            "message_id": response_message.message_id
        }
    
    def _mark_meeting_scheduled(self, lead: Lead, reply: Reply) -> Dict:
        """Mark lead as meeting scheduled and notify team"""
        
        lead.status = "meeting_scheduled"
        
        # Create CRM opportunity
        self._create_crm_opportunity(lead, reply)
        
        # Notify sales team
        self._notify_sales_team(lead, "🔥 MEETING BOOKED - Immediate follow-up required", urgent=True)
        
        return {
            "action": "mark_meeting_scheduled",
            "lead_status": lead.status
        }
    
    def _suppress_lead(self, lead: Lead, reply: Reply, reason: str, urgent: bool = False) -> Dict:
        """Suppress lead from further outreach"""
        
        from app.models import SuppressionList
        
        suppression = SuppressionList(
            lead_id=lead.lead_id,
            email=reply.from_email,
            reason=f"Auto-suppressed: {reason}"
        )
        self.db.add(suppression)
        
        lead.status = "unsubscribe"
        self.db.commit()
        
        return {
            "action": "suppress",
            "reason": reason,
            "email": reply.from_email
        }
    
    def _request_intro(self, lead: Lead, reply: Reply) -> Dict:
        """Auto-request intro to right person"""
        
        response_body = f"""Hi {lead.decision_maker or 'there'},

Thanks for letting me know! Would you mind connecting me with the right person on your team?

Happy to make the intro easy - just need an email.

Best,
Malay
"""
        
        response_message = OutboundMessage(
            message_id=f"auto-intro-request-{reply.reply_id}",
            lead_id=lead.lead_id,
            subject=f"Re: {reply.subject}",
            body=response_body,
            to_email=reply.from_email,
            from_email=reply.to_email,
            status="queued",
            personalization_method="auto_intro_request",
            thread_id=reply.thread_id
        )
        
        self.db.add(response_message)
        self.db.commit()
        
        result = self.gmail_sender.send_message(response_message.message_id)
        
        return {
            "action": "request_intro",
            "success": result["success"]
        }
    
    def _auto_answer_question(self, lead: Lead, reply: Reply) -> Dict:
        """Auto-answer common questions using AI"""
        
        # Use AI to generate answer
        answer_prompt = f"""
        Lead question: {reply.body}
        
        Generate a helpful, concise answer about AI-powered outbound automation.
        Keep it under 100 words.
        """
        
        # For now, use template answer
        response_body = f"""Hi {lead.decision_maker or 'there'},

Great question! We use GPT-4 to generate personalized outreach based on company signals (funding, hiring, tech stack, etc.).

It finds leads from Crunchbase/Apollo, scores them with AI, and automates the entire sequence including follow-ups.

Want to see a quick demo?

Best,
Malay
"""
        
        response_message = OutboundMessage(
            message_id=f"auto-answer-{reply.reply_id}",
            lead_id=lead.lead_id,
            subject=f"Re: {reply.subject}",
            body=response_body,
            to_email=reply.from_email,
            from_email=reply.to_email,
            status="queued",
            personalization_method="auto_answer",
            thread_id=reply.thread_id
        )
        
        self.db.add(response_message)
        self.db.commit()
        
        result = self.gmail_sender.send_message(response_message.message_id)
        
        return {
            "action": "auto_answer",
            "success": result["success"]
        }
    
    def _notify_sales_team(self, lead: Lead, message: str, urgent: bool = False):
        """Notify sales team via email/Slack"""
        
        # Log event (would integrate with Slack/Teams in production)
        event = Event(
            event_id=f"escalation-{lead.lead_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            event_type="lead_escalated",
            entity_type="lead",
            entity_id=lead.lead_id,
            data={
                "message": message,
                "urgent": urgent,
                "lead_company": lead.company,
                "lead_score": lead.fit_score
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Sales team notified: {message} ({lead.company})")
    
    def _create_crm_opportunity(self, lead: Lead, reply: Reply):
        """Create opportunity in CRM (Salesforce/HubSpot)"""
        
        # Placeholder for CRM integration
        # Would call Salesforce API to create Opportunity
        
        event = Event(
            event_id=f"crm-opportunity-{lead.lead_id}",
            event_type="crm_opportunity_created",
            entity_type="lead",
            entity_id=lead.lead_id,
            data={
                "company": lead.company,
                "contact": reply.from_email,
                "stage": "Meeting Scheduled",
                "source": "AI Outbound",
                "meeting_date": "pending"
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"CRM opportunity created for {lead.company}")
