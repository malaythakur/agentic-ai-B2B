"""
Follow-up Email Service

Handles automated follow-up email sequences:
- Day 3: First follow-up
- Day 7: Second follow-up  
- Day 14: Third follow-up
- Stops if buyer responds or unsubscribes
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import Match, BuyerCompany, ServiceProvider

logger = logging.getLogger(__name__)


class FollowUpService:
    """Service for managing follow-up email sequences"""
    
    # Follow-up schedule in days
    FOLLOWUP_SCHEDULE = [3, 7, 14]
    
    def __init__(self, db: Session, gmail_sender=None):
        """
        Initialize follow-up service
        
        Args:
            db: Database session
            gmail_sender: GmailSender instance for sending emails
        """
        self.db = db
        self.gmail_sender = gmail_sender
    
    def get_pending_followups(self, days_ahead: int = 1) -> List[Match]:
        """
        Get matches that need follow-up emails sent today
        
        Args:
            days_ahead: How many days ahead to look (default 1 for today)
            
        Returns:
            List of matches needing follow-up
        """
        today = datetime.utcnow().date()
        target_date = today + timedelta(days=days_ahead)
        
        # Get matches where initial email was sent but no response
        matches = self.db.query(Match).filter(
            Match.status == "outreach_sent",
            Match.intro_sent_at.isnot(None),
            Match.intro_message_id.isnot(None),
            Match.response_received == False
        ).all()
        
        pending_followups = []
        
        for match in matches:
            if self._should_send_followup(match, target_date):
                pending_followups.append(match)
        
        logger.info(f"Found {len(pending_followups)} pending follow-ups for {target_date}")
        return pending_followups
    
    def _should_send_followup(self, match: Match, target_date: datetime.date) -> bool:
        """
        Check if a follow-up should be sent for this match
        
        Args:
            match: Match record
            target_date: Date to check if follow-up is due
            
        Returns:
            True if follow-up should be sent
        """
        if not match.intro_sent_at:
            return False
        
        # Calculate days since initial email
        days_since_initial = (target_date - match.intro_sent_at.date()).days
        
        # Check if this day is in the follow-up schedule
        if days_since_initial not in self.FOLLOWUP_SCHEDULE:
            return False
        
        # Check if this follow-up was already sent
        followup_count = match.followup_count or 0
        expected_followup_index = self.FOLLOWUP_SCHEDULE.index(days_since_initial)
        
        if followup_count > expected_followup_index:
            return False
        
        return True
    
    def send_followup_email(
        self,
        match: Match,
        platform_email: str,
        followup_number: int
    ) -> Dict:
        """
        Send follow-up email for a match
        
        Args:
            match: Match record
            platform_email: Platform email to send from
            followup_number: Which follow-up in sequence (1, 2, or 3)
            
        Returns:
            Result dict with status
        """
        if not self.gmail_sender:
            return {"success": False, "error": "Gmail sender not initialized"}
        
        # Get provider and buyer details
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == match.provider_id
        ).first()
        
        buyer = self.db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == match.buyer_id
        ).first()
        
        if not provider or not buyer:
            return {"success": False, "error": "Provider or buyer not found"}
        
        # Generate follow-up email
        followup_email = self._generate_followup_email(
            provider,
            buyer,
            followup_number
        )
        
        try:
            message_id = self.gmail_sender.send_email(
                to_email=buyer.decision_maker_email,
                subject=followup_email["subject"],
                body=followup_email["body"],
                from_email=platform_email
            )
            
            if message_id:
                # Update match with follow-up info
                match.followup_count = (match.followup_count or 0) + 1
                match.last_followup_sent_at = datetime.utcnow()
                match.status = f"followup_{followup_number}_sent"
                self.db.commit()
                
                return {
                    "success": True,
                    "message_id": message_id,
                    "followup_number": followup_number
                }
            else:
                return {"success": False, "error": "Failed to send follow-up email"}
                
        except Exception as e:
            logger.error(f"Failed to send follow-up email: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_followup_email(
        self,
        provider: ServiceProvider,
        buyer: BuyerCompany,
        followup_number: int
    ) -> Dict:
        """
        Generate follow-up email based on follow-up number
        
        Args:
            provider: Service provider
            buyer: Buyer company
            followup_number: Which follow-up (1, 2, or 3)
            
        Returns:
            Dict with subject and body
        """
        company_name = buyer.company_name
        provider_name = provider.company_name
        services = ", ".join(provider.services[:2])
        
        if followup_number == 1:
            # Day 3 follow-up - gentle reminder
            subject = f"Quick follow-up: {provider_name} + {company_name}"
            body = f"""Hi {company_name} Team,

I wanted to follow up on my previous email about how {provider_name} could help with {services}.

I understand you're likely busy, but I thought this might be relevant given your recent activities.

Would you be open to a brief 15-minute call to explore if there's a fit?

Best regards,
{provider_name}

---
To unsubscribe: https://your-platform.com/unsubscribe?match_id={match_id}
"""
        
        elif followup_number == 2:
            # Day 7 follow-up - add value
            subject = f"Another thought on {company_name}'s growth"
            body = f"""Hi {company_name} Team,

I've been thinking about your company's trajectory and how {provider_name} could support your growth.

Here's a quick case study: We recently helped a similar company achieve [specific result] with {services}.

I'd love to share more details about how we could do the same for you.

Open to a quick chat?

Best,
{provider_name}

---
To unsubscribe: https://your-platform.com/unsubscribe?match_id={match_id}
"""
        
        else:  # followup_number == 3
            # Day 14 follow-up - last attempt
            subject = f"Last message regarding {company_name}"
            body = f"""Hi {company_name} Team,

This is my last follow-up regarding potential collaboration between our companies.

I believe {provider_name} could add significant value to {company_name}, especially with {services}.

If you're interested in exploring this further, great! If not, I'll respect your inbox and won't follow up again.

Either way, I'd appreciate a quick reply so I know where we stand.

Best,
{provider_name}

---
To unsubscribe: https://your-platform.com/unsubscribe?match_id={match_id}
"""
        
        return {"subject": subject, "body": body}
    
    def process_daily_followups(self, platform_email: str) -> Dict:
        """
        Process all follow-ups due today
        
        Args:
            platform_email: Platform email to send from
            
        Returns:
            Summary of follow-up processing
        """
        pending_followups = self.get_pending_followups(days_ahead=0)
        
        results = {
            "total_pending": len(pending_followups),
            "sent": 0,
            "failed": 0,
            "details": []
        }
        
        for match in pending_followups:
            # Determine which follow-up number this is
            followup_number = (match.followup_count or 0) + 1
            
            result = self.send_followup_email(match, platform_email, followup_number)
            
            if result.get("success"):
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "match_id": match.match_id,
                "buyer_id": match.buyer_id,
                "followup_number": followup_number,
                "status": result
            })
        
        logger.info(f"Follow-up processing completed: {results['sent']} sent, {results['failed']} failed")
        return results
