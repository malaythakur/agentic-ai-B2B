"""
Email Compliance Service

Handles CAN-SPAM compliance:
- Unsubscribe management
- Physical mailing address
- Opt-out tracking
- Suppression list management
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Lead, SuppressionList

logger = logging.getLogger(__name__)


class ComplianceService:
    """Service for email compliance management"""
    
    def __init__(self):
        """Initialize compliance service"""
        pass
    
    def add_unsubscribe_link(self, message_body: str, match_id: str) -> str:
        """
        Add unsubscribe link to email body
        
        Args:
            message_body: Original email body
            match_id: Match ID for tracking
            
        Returns:
            Email body with unsubscribe link appended
        """
        unsubscribe_url = f"https://api.yourdomain.com/unsubscribe/{match_id}"
        
        footer = f"""
---
To stop receiving these emails, click here to unsubscribe: {unsubscribe_url}

Our mailing address is:
Your Company Name
123 Business Street
San Francisco, CA 94105
"""
        
        return message_body + footer
    
    def process_unsubscribe(self, match_id: str, reason: Optional[str] = None) -> Dict:
        """
        Process unsubscribe request
        
        Args:
            match_id: Match ID
            reason: Optional unsubscribe reason
            
        Returns:
            Unsubscribe result
        """
        db = SessionLocal()
        try:
            # Find match and get buyer email
            from app.models import Match
            match = db.query(Match).filter(Match.match_id == match_id).first()
            
            if not match:
                return {"status": "error", "message": "Match not found"}
            
            # Get buyer email
            from app.models import BuyerCompany
            buyer = db.query(BuyerCompany).filter(
                BuyerCompany.buyer_id == match.buyer_id
            ).first()
            
            if not buyer:
                return {"status": "error", "message": "Buyer not found"}
            
            email = buyer.decision_maker_email
            
            # Add to suppression list
            suppression = SuppressionList(
                email=email,
                reason=reason or "User unsubscribed",
                source="outbound_unsubscribe",
                suppressed_at=datetime.utcnow()
            )
            
            db.add(suppression)
            db.commit()
            
            logger.info(f"Added {email} to suppression list (match: {match_id})")
            return {"status": "success", "email": email, "message": "Successfully unsubscribed"}
        except Exception as e:
            logger.error(f"Failed to process unsubscribe: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    def is_suppressed(self, email: str) -> bool:
        """
        Check if email is on suppression list
        
        Args:
            email: Email address to check
            
        Returns:
            True if suppressed, False otherwise
        """
        db = SessionLocal()
        try:
            suppression = db.query(SuppressionList).filter(
                SuppressionList.email == email
            ).first()
            return suppression is not None
        except Exception as e:
            logger.error(f"Failed to check suppression: {e}")
            return False
        finally:
            db.close()
    
    def add_to_suppression_list(
        self,
        email: str,
        reason: str,
        source: str = "manual"
    ) -> Dict:
        """
        Manually add email to suppression list
        
        Args:
            email: Email address
            reason: Suppression reason
            source: Source of suppression
            
        Returns:
            Result
        """
        db = SessionLocal()
        try:
            # Check if already suppressed
            existing = db.query(SuppressionList).filter(
                SuppressionList.email == email
            ).first()
            
            if existing:
                return {"status": "already_suppressed", "email": email}
            
            suppression = SuppressionList(
                email=email,
                reason=reason,
                source=source,
                suppressed_at=datetime.utcnow()
            )
            
            db.add(suppression)
            db.commit()
            
            logger.info(f"Added {email} to suppression list (source: {source})")
            return {"status": "success", "email": email}
        except Exception as e:
            logger.error(f"Failed to add to suppression list: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    def remove_from_suppression_list(self, email: str) -> Dict:
        """
        Remove email from suppression list (re-opt-in)
        
        Args:
            email: Email address
            
        Returns:
            Result
        """
        db = SessionLocal()
        try:
            suppression = db.query(SuppressionList).filter(
                SuppressionList.email == email
            ).first()
            
            if not suppression:
                return {"status": "not_suppressed", "email": email}
            
            db.delete(suppression)
            db.commit()
            
            logger.info(f"Removed {email} from suppression list")
            return {"status": "success", "email": email}
        except Exception as e:
            logger.error(f"Failed to remove from suppression list: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    def get_suppression_stats(self) -> Dict:
        """
        Get suppression list statistics
        
        Returns:
            Statistics dict
        """
        db = SessionLocal()
        try:
            total = db.query(SuppressionList).count()
            
            # Count by source
            sources = {}
            for s in db.query(SuppressionList.source, SuppressionList.id).all():
                source = s[0]
                sources[source] = sources.get(source, 0) + 1
            
            # Count by reason
            reasons = {}
            for s in db.query(SuppressionList.reason, SuppressionList.id).all():
                reason = s[0]
                reasons[reason] = reasons.get(reason, 0) + 1
            
            # Recent suppressions (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent = db.query(SuppressionList).filter(
                SuppressionList.suppressed_at >= thirty_days_ago
            ).count()
            
            return {
                "total_suppressed": total,
                "recent_suppressed_30d": recent,
                "by_source": sources,
                "by_reason": reasons
            }
        except Exception as e:
            logger.error(f"Failed to get suppression stats: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    def validate_email_compliance(self, to_email: str, subject: str, body: str) -> Dict:
        """
        Validate email for CAN-SPAM compliance
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            
        Returns:
            Validation result
        """
        issues = []
        
        # Check suppression list
        if self.is_suppressed(to_email):
            issues.append("Email is on suppression list")
        
        # Check for unsubscribe link
        if "unsubscribe" not in body.lower():
            issues.append("Missing unsubscribe link")
        
        # Check for physical address
        if "address" not in body.lower() and "street" not in body.lower():
            issues.append("Missing physical mailing address")
        
        # Check subject line
        if not subject or len(subject) > 200:
            issues.append("Subject line too long or missing")
        
        # Check for misleading subject
        misleading_keywords = ["free", "winner", "congratulations", "urgent", "act now"]
        if any(kw in subject.lower() for kw in misleading_keywords):
            issues.append("Subject line may be misleading")
        
        return {
            "compliant": len(issues) == 0,
            "issues": issues
        }


# Example usage
if __name__ == "__main__":
    service = ComplianceService()
    
    # Add unsubscribe link
    body = "Hello, this is a test email."
    body_with_unsubscribe = service.add_unsubscribe_link(body, "match-123")
    print(body_with_unsubscribe)
    
    # Process unsubscribe
    result = service.process_unsubscribe("match-123", "Not interested")
    print(f"Unsubscribe: {result}")
    
    # Validate email
    validation = service.validate_email_compliance("test@example.com", "Test Subject", body_with_unsubscribe)
    print(f"Validation: {validation}")
