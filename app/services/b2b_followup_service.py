"""
B2B Follow-up Service

Automated follow-up sequences for B2B Matchmaking Platform:
- Day 3: Value-add follow-up
- Day 7: Case study/social proof follow-up
- Day 14: Last soft close follow-up
- Intelligent stop conditions (reply, unsubscribe, meeting booked)
- All using FREE Gmail API
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Match, BuyerCompany, ServiceProvider, Event
from app.services.gmail_sender import GmailSender
from app.logging_config import logger as app_logger

logger = app_logger


class B2BFollowupService:
    """
    B2B Follow-up Automation Service
    
    Manages follow-up sequences for buyer outreach:
    - 3-touch sequence over 14 days
    - Intelligent timing and personalization
    - Automatic stop on reply/unsubscribe/meeting
    """
    
    # Follow-up schedule: days after initial outreach
    FOLLOWUP_SCHEDULE = {
        1: {
            "day": 3,
            "name": "value_add",
            "subject_template": "Re: {provider_name} + {buyer_name} - Quick thought",
            "tone": "helpful"
        },
        2: {
            "day": 7,
            "name": "case_study",
            "subject_template": "Re: {provider_name} + {buyer_name} - Case study",
            "tone": "proof"
        },
        3: {
            "day": 14,
            "name": "soft_close",
            "subject_template": "Re: {provider_name} + {buyer_name} - Last touch",
            "tone": "final"
        }
    }
    
    def __init__(self, db: Session, gmail_credentials_path: Optional[str] = None):
        self.db = db
        self.gmail_sender = GmailSender(db)
    
    def process_all_followups(self) -> Dict:
        """
        Process all follow-ups due today
        
        Returns:
            Dict with results of follow-up processing
        """
        logger.info("=== Processing B2B Follow-ups ===")
        
        results = {
            "sent": 0,
            "skipped": 0,
            "errors": [],
            "details": []
        }
        
        # Check each follow-up touch
        for touch_number, config in self.FOLLOWUP_SCHEDULE.items():
            try:
                touch_results = self._process_followup_touch(touch_number, config)
                results["sent"] += touch_results["sent"]
                results["skipped"] += touch_results["skipped"]
                results["errors"].extend(touch_results["errors"])
                results["details"].extend(touch_results["details"])
            except Exception as e:
                logger.error(f"Error processing follow-up touch {touch_number}: {e}")
                results["errors"].append(f"Touch {touch_number}: {str(e)}")
        
        logger.info(f"Follow-ups complete: {results['sent']} sent, {results['skipped']} skipped")
        return results
    
    def _process_followup_touch(self, touch_number: int, config: Dict) -> Dict:
        """Process a specific follow-up touch (Day 3, 7, or 14)"""
        touch_results = {
            "sent": 0,
            "skipped": 0,
            "errors": [],
            "details": []
        }
        
        target_day = config["day"]
        touch_name = config["name"]
        
        logger.info(f"Processing {touch_name} follow-ups (Day {target_day})")
        
        # Find matches that need this follow-up
        # Criteria:
        # - Initial outreach sent
        # - No response yet
        # - Not unsubscribed
        # - Initial outreach was 'target_day' days ago
        # - This specific follow-up hasn't been sent yet
        
        target_date = datetime.utcnow() - timedelta(days=target_day)
        
        matches = self.db.query(Match).filter(
            and_(
                Match.status == "outreach_sent",  # No response yet
                Match.intro_sent_at <= target_date,  # Sent target_day+ days ago
                Match.last_followup_sent_at < target_date if Match.last_followup_sent_at else True,
                Match.followup_count < touch_number  # Haven't sent this touch yet
            )
        ).all()
        
        logger.info(f"Found {len(matches)} matches for Day {target_day} follow-up")
        
        for match in matches:
            try:
                result = self._send_followup(match, touch_number, config)
                
                if result["sent"]:
                    touch_results["sent"] += 1
                else:
                    touch_results["skipped"] += 1
                    
                touch_results["details"].append(result)
                
            except Exception as e:
                logger.error(f"Error sending follow-up for match {match.match_id}: {e}")
                touch_results["errors"].append(f"{match.match_id}: {str(e)}")
                touch_results["skipped"] += 1
        
        return touch_results
    
    def _send_followup(self, match: Match, touch_number: int, config: Dict) -> Dict:
        """Send follow-up email for a specific match"""
        buyer = self.db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == match.buyer_id
        ).first()
        
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == match.provider_id
        ).first()
        
        if not buyer or not provider:
            return {"match_id": match.match_id, "sent": False, "reason": "Buyer or provider not found"}
        
        # Check if we should skip this follow-up
        skip_reason = self._should_skip_followup(match, buyer, provider)
        if skip_reason:
            return {"match_id": match.match_id, "sent": False, "reason": skip_reason}
        
        # Generate follow-up content
        subject = config["subject_template"].format(
            provider_name=provider.company_name,
            buyer_name=buyer.company_name
        )
        
        body = self._generate_followup_body(match, buyer, provider, touch_number, config)
        
        # Send email
        message_id = self.gmail_sender.send_email(
            to_email=buyer.decision_maker_email,
            subject=subject,
            body=body,
            from_email=provider.contact_email  # Send from provider's email
        )
        
        if message_id:
            # Update match record
            match.followup_count = touch_number
            match.last_followup_sent_at = datetime.utcnow()
            match.last_followup_type = config["name"]
            
            # Store follow-up message ID
            if not match.followup_message_ids:
                match.followup_message_ids = []
            match.followup_message_ids.append(message_id)
            
            self.db.commit()
            
            # Log event
            event = Event(
                event_type="followup_sent",
                entity_type="match",
                entity_id=match.match_id,
                data={
                    "touch_number": touch_number,
                    "touch_name": config["name"],
                    "buyer_company": buyer.company_name,
                    "provider_company": provider.company_name
                }
            )
            self.db.add(event)
            self.db.commit()
            
            return {
                "match_id": match.match_id,
                "sent": True,
                "touch": touch_number,
                "buyer": buyer.company_name,
                "message_id": message_id
            }
        else:
            return {
                "match_id": match.match_id,
                "sent": False,
                "reason": "Failed to send email"
            }
    
    def _should_skip_followup(self, match: Match, buyer: BuyerCompany, provider: ServiceProvider) -> Optional[str]:
        """Check if follow-up should be skipped"""
        
        # Skip if buyer responded
        if match.buyer_responded:
            return "Buyer already responded"
        
        # Skip if buyer unsubscribed
        if not buyer.active or match.status == "unsubscribed":
            return "Buyer unsubscribed"
        
        # Skip if meeting already booked
        if match.status in ["meeting_booked", "closed_won"]:
            return "Meeting already booked"
        
        # Skip if provider paused automation
        if not provider.auto_outreach_enabled:
            return "Provider automation paused"
        
        # Skip if max follow-ups reached
        if match.followup_count >= 3:
            return "Max follow-ups reached"
        
        # Skip if last follow-up was too recent (< 48 hours)
        if match.last_followup_sent_at:
            hours_since_last = (datetime.utcnow() - match.last_followup_sent_at).total_seconds() / 3600
            if hours_since_last < 48:
                return "Last follow-up too recent"
        
        return None
    
    def _generate_followup_body(
        self,
        match: Match,
        buyer: BuyerCompany,
        provider: ServiceProvider,
        touch_number: int,
        config: Dict
    ) -> str:
        """Generate personalized follow-up email body"""
        
        dm_name = buyer.decision_maker_name.split()[0] if buyer.decision_maker_name else "there"
        provider_name = provider.company_name
        
        if touch_number == 1:
            # Day 3: Value-add follow-up
            return f"""Hi {dm_name},

Quick thought - saw {buyer.company_name} is {buyer.signals[0] if buyer.signals else 'growing fast'}.

Given that, thought you might find this relevant: Most {buyer.industry} companies at your stage see 40% faster deployment cycles after optimizing their infrastructure.

No need to reply if timing's off - just wanted to share in case it's useful context.

Best,
{provider_name} Team

---
P.S. If you'd like to see how we helped a similar {buyer.industry} company reduce their cloud costs by 35%, happy to share that case study.
"""
        
        elif touch_number == 2:
            # Day 7: Case study/social proof
            case_studies = provider.case_studies or []
            case_study = case_studies[0] if case_studies else {"title": "Similar Company", "result": "great results"}
            
            return f"""Hi {dm_name},

Wanted to share a quick case study that might resonate with {buyer.company_name}'s situation.

We recently worked with {case_study.get('title', 'a similar company')} who was facing similar challenges with {buyer.signals[0] if buyer.signals else 'scaling'}.

Result: {case_study.get('result', 'Significant improvement in their key metrics')}

Worth a brief conversation to see if similar results are possible for you?

Best,
{provider_name} Team

---
P.S. Here's what they said: "{case_study.get('testimonial', 'The ROI was immediate and significant.')}"
"""
        
        elif touch_number == 3:
            # Day 14: Last soft close
            return f"""Hi {dm_name},

This is my last email on this - don't want to clutter your inbox if the timing isn't right for {buyer.company_name}.

If cloud migration isn't a priority right now, totally understand. Just say the word and I'll close the loop.

If it IS relevant but you need more info first, reply with "more info" and I'll send a one-pager.

Either way, best of luck with the continued growth.

{provider_name} Team
"""
        
        return f"Follow-up email from {provider_name}"
    
    def stop_followups(self, match_id: str, reason: str = "manual") -> bool:
        """Stop follow-ups for a specific match"""
        match = self.db.query(Match).filter(Match.match_id == match_id).first()
        if not match:
            return False
        
        match.followup_stopped = True
        match.followup_stop_reason = reason
        match.followup_stopped_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Follow-ups stopped for match {match_id}: {reason}")
        return True
    
    def get_followup_stats(self) -> Dict:
        """Get follow-up statistics"""
        total_sent = self.db.query(Match).filter(Match.followup_count > 0).count()
        
        by_touch = {}
        for i in range(1, 4):
            count = self.db.query(Match).filter(Match.followup_count >= i).count()
            by_touch[f"touch_{i}"] = count
        
        stopped = self.db.query(Match).filter(Match.followup_stopped == True).count()
        
        pending = self.db.query(Match).filter(
            and_(
                Match.status == "outreach_sent",
                Match.followup_count < 3,
                Match.followup_stopped == False
            )
        ).count()
        
        return {
            "total_sent": total_sent,
            "by_touch": by_touch,
            "stopped": stopped,
            "pending": pending
        }


class B2BResponseTracker:
    """
    Tracks buyer responses and automatically stops follow-ups
    
    This works with the B2BResponseTrackingService to automatically
    stop follow-up sequences when buyers respond.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.followup_service = B2BFollowupService(db)
    
    def on_buyer_response(self, match_id: str, response_type: str):
        """
        Handle buyer response - automatically stop follow-ups
        
        Args:
            match_id: Match ID
            response_type: Type of response (interested, not_interested, etc.)
        """
        if response_type in ["interested", "meeting_booked", "closed_won"]:
            self.followup_service.stop_followups(match_id, "buyer_interested")
            logger.info(f"Follow-ups stopped for interested buyer: {match_id}")
            
        elif response_type == "unsubscribe":
            self.followup_service.stop_followups(match_id, "unsubscribed")
            logger.info(f"Follow-ups stopped for unsubscribed buyer: {match_id}")
            
        elif response_type == "not_now":
            # Don't stop, but delay next follow-up
            match = self.db.query(Match).filter(Match.match_id == match_id).first()
            if match:
                match.follow_up_date = datetime.utcnow() + timedelta(days=30)
                self.db.commit()
                logger.info(f"Follow-ups delayed for 'not now' buyer: {match_id}")
    
    def check_stale_followups(self, max_age_days: int = 21) -> List[Dict]:
        """
        Find follow-ups that should be auto-stopped (stale)
        
        Returns:
            List of stale matches to stop
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        stale_matches = self.db.query(Match).filter(
            and_(
                Match.status == "outreach_sent",
                Match.intro_sent_at < cutoff_date,
                Match.followup_count >= 3,
                Match.followup_stopped == False
            )
        ).all()
        
        results = []
        for match in stale_matches:
            stopped = self.followup_service.stop_followups(
                match.match_id, 
                "max_followups_reached"
            )
            if stopped:
                results.append({
                    "match_id": match.match_id,
                    "buyer_id": match.buyer_id,
                    "provider_id": match.provider_id,
                    "reason": "max_followups_reached"
                })
        
        logger.info(f"Auto-stopped {len(results)} stale follow-ups")
        return results
