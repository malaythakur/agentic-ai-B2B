"""
Unsubscribe Service

Handles unsubscribe mechanism with CAN-SPAM compliance:
- Generates unsubscribe links
- Processes unsubscribe requests
- Maintains suppression list
- Ensures compliance with CAN-SPAM Act
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import BuyerCompany, Match

logger = logging.getLogger(__name__)


class UnsubscribeService:
    """Service for managing email unsubscribes with CAN-SPAM compliance"""
    
    def __init__(self, db: Session):
        """
        Initialize unsubscribe service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def generate_unsubscribe_link(self, match_id: str) -> str:
        """
        Generate unsubscribe link for a match
        
        Args:
            match_id: Match ID
            
        Returns:
            Unsubscribe URL
        """
        # In production, this would be a real URL
        # For now, return a placeholder
        return f"https://your-platform.com/unsubscribe?match_id={match_id}"
    
    def process_unsubscribe(self, match_id: str) -> Dict:
        """
        Process unsubscribe request
        
        Args:
            match_id: Match ID to unsubscribe
            
        Returns:
            Result of unsubscribe processing
        """
        try:
            match = self.db.query(Match).filter(
                Match.match_id == match_id
            ).first()
            
            if not match:
                return {"success": False, "error": "Match not found"}
            
            # Mark buyer as unsubscribed from this provider
            buyer = self.db.query(BuyerCompany).filter(
                BuyerCompany.buyer_id == match.buyer_id
            ).first()
            
            if not buyer:
                return {"success": False, "error": "Buyer not found"}
            
            # Add buyer to suppression list for this provider
            # This would be stored in a separate suppression table
            # For now, we'll update the match status
            match.status = "unsubscribed"
            self.db.commit()
            
            logger.info(f"Buyer {buyer.buyer_id} unsubscribed from provider {match.provider_id}")
            
            return {
                "success": True,
                "message": "Successfully unsubscribed",
                "match_id": match_id
            }
            
        except Exception as e:
            logger.error(f"Failed to process unsubscribe: {e}")
            return {"success": False, "error": str(e)}
    
    def is_unsubscribed(self, provider_id: str, buyer_id: str) -> bool:
        """
        Check if buyer has unsubscribed from provider
        
        Args:
            provider_id: Provider ID
            buyer_id: Buyer ID
            
        Returns:
            True if unsubscribed
        """
        match = self.db.query(Match).filter(
            Match.provider_id == provider_id,
            Match.buyer_id == buyer_id,
            Match.status == "unsubscribed"
        ).first()
        
        return match is not None
    
    def add_unsubscribe_footer(self, email_body: str, match_id: str) -> str:
        """
        Add CAN-SPAM compliant unsubscribe footer to email
        
        Args:
            email_body: Original email body
            match_id: Match ID for unsubscribe link
            
        Returns:
            Email body with unsubscribe footer
        """
        unsubscribe_link = self.generate_unsubscribe_link(match_id)
        
        footer = """

---
To unsubscribe from future emails: {unsubscribe_link}

This email was sent by [Platform Name]. 
Our address is [Physical Address]. 
See our Privacy Policy: https://your-platform.com/privacy
""".format(unsubscribe_link=unsubscribe_link)
        
        return email_body + footer
    
    def get_suppressed_buyers(self, provider_id: str) -> list:
        """
        Get list of buyers who have unsubscribed from a provider
        
        Args:
            provider_id: Provider ID
            
        Returns:
            List of buyer IDs
        """
        matches = self.db.query(Match).filter(
            Match.provider_id == provider_id,
            Match.status == "unsubscribed"
        ).all()
        
        return [match.buyer_id for match in matches]
