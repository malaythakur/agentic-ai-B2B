"""
Response Tracking Service

Tracks email opens, clicks, and replies using Gmail API (free tier):
- Monitors Gmail for replies to sent emails
- Updates match status when responses received
- Tracks engagement metrics
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import Match, ServiceProvider, BuyerCompany

logger = logging.getLogger(__name__)


class ResponseTracker:
    """Service for tracking email responses using Gmail API"""
    
    def __init__(self, db: Session, gmail_service=None):
        """
        Initialize response tracker
        
        Args:
            db: Database session
            gmail_service: Gmail API service instance
        """
        self.db = db
        self.gmail_service = gmail_service
    
    def check_for_responses(self, platform_email: str) -> Dict:
        """
        Check Gmail for new responses to outreach emails
        
        Args:
            platform_email: Platform email to check
            
        Returns:
            Summary of response checking
        """
        if not self.gmail_service:
            return {"success": False, "error": "Gmail service not initialized"}
        
        try:
            # Get matches where outreach was sent but no response recorded
            matches_needing_check = self.db.query(Match).filter(
                Match.intro_sent_at.isnot(None),
                Match.intro_message_id.isnot(None),
                Match.response_received == False
            ).all()
            
            results = {
                "total_checked": len(matches_needing_check),
                "responses_found": 0,
                "updated_matches": []
            }
            
            for match in matches_needing_check:
                # Check if there's a reply to the sent email
                has_reply = self._check_for_reply(match.intro_message_id)
                
                if has_reply:
                    # Update match with response
                    match.response_received = True
                    match.response_received_at = datetime.utcnow()
                    match.status = "response_received"
                    self.db.commit()
                    
                    results["responses_found"] += 1
                    results["updated_matches"].append({
                        "match_id": match.match_id,
                        "buyer_id": match.buyer_id,
                        "response_at": match.response_received_at.isoformat()
                    })
                    
                    logger.info(f"Response detected for match {match.match_id}")
            
            logger.info(f"Response checking completed: {results['responses_found']} responses found")
            return results
            
        except Exception as e:
            logger.error(f"Failed to check for responses: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_for_reply(self, message_id: str) -> bool:
        """
        Check if there's a reply to a specific message
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if reply exists
        """
        try:
            # Get the message thread
            message = self.gmail_service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata',
                metadataHeaders=['References', 'In-Reply-To']
            ).execute()
            
            thread_id = message.get('threadId')
            
            if not thread_id:
                return False
            
            # Get all messages in the thread
            thread = self.gmail_service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = thread.get('messages', [])
            
            # If there's more than 1 message in thread, there's a reply
            return len(messages) > 1
            
        except Exception as e:
            logger.error(f"Failed to check for reply: {e}")
            return False
    
    def get_response_metrics(self, provider_id: str) -> Dict:
        """
        Get response metrics for a provider
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Response metrics
        """
        matches = self.db.query(Match).filter(
            Match.provider_id == provider_id,
            Match.intro_sent_at.isnot(None)
        ).all()
        
        total_sent = len(matches)
        responses = [m for m in matches if m.response_received]
        
        # Calculate response rate over time
        response_times = []
        for match in responses:
            if match.intro_sent_at and match.response_received_at:
                response_time = (match.response_received_at - match.intro_sent_at).days
                response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_sent": total_sent,
            "total_responses": len(responses),
            "response_rate": round(len(responses) / total_sent * 100, 1) if total_sent > 0 else 0,
            "avg_response_days": round(avg_response_time, 1) if response_times else 0,
            "response_times": response_times
        }
    
    def get_open_tracking_pixel(self, match_id: str) -> str:
        """
        Generate open tracking pixel URL (1x1 transparent image)
        
        Args:
            match_id: Match ID to track
            
        Returns:
            Tracking pixel URL
        """
        # This would be served by a separate endpoint that logs opens
        # For now, return a placeholder
        return f"https://your-platform.com/track/open?match_id={match_id}"
    
    def track_email_open(self, match_id: str) -> Dict:
        """
        Track when an email is opened (via tracking pixel)
        
        Args:
            match_id: Match ID
            
        Returns:
            Tracking result
        """
        try:
            match = self.db.query(Match).filter(
                Match.match_id == match_id
            ).first()
            
            if not match:
                return {"success": False, "error": "Match not found"}
            
            # Add open tracking field to match (need to add to model)
            # For now, we'll log it
            logger.info(f"Email opened for match {match_id}")
            
            return {"success": True, "match_id": match_id}
            
        except Exception as e:
            logger.error(f"Failed to track email open: {e}")
            return {"success": False, "error": str(e)}
