"""
Response Tracking Service

Tracks email engagement metrics:
- Opens (via pixel tracking)
- Clicks (via link tracking)
- Replies (via Gmail API)
- Bounces and spam complaints
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Match

logger = logging.getLogger(__name__)


class ResponseTrackingService:
    """Service for tracking email responses and engagement"""
    
    def __init__(self):
        """Initialize response tracking service"""
        pass
    
    def generate_tracking_pixel(self, match_id: str) -> str:
        """
        Generate tracking pixel URL for open tracking
        
        Args:
            match_id: Match ID
            
        Returns:
            Tracking pixel URL
        """
        # In production, this would be a real tracking pixel
        # For now, return a placeholder URL
        return f"https://api.yourdomain.com/track/open/{match_id}"
    
    def generate_tracking_link(self, match_id: str, destination_url: str) -> str:
        """
        Generate tracked link URL for click tracking
        
        Args:
            match_id: Match ID
            destination_url: Original destination URL
            
        Returns:
            Tracked link URL
        """
        # In production, this would redirect through tracking server
        # For now, return destination with tracking parameter
        return f"{destination_url}?utm_source=outbound&utm_medium=email&utm_campaign=match_{match_id}"
    
    def track_open(self, match_id: str, user_agent: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """
        Track email open event
        
        Args:
            match_id: Match ID
            user_agent: User agent string
            ip: IP address
            
        Returns:
            Tracking result
        """
        db = SessionLocal()
        try:
            match = db.query(Match).filter(Match.match_id == match_id).first()
            if not match:
                return {"status": "error", "message": "Match not found"}
            
            # Update open tracking
            if not match.opens_count:
                match.opens_count = 0
            match.opens_count += 1
            match.first_opened_at = match.first_opened_at or datetime.utcnow()
            match.last_opened_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Tracked open for match {match_id} (total: {match.opens_count})")
            return {"status": "success", "match_id": match_id, "opens_count": match.opens_count}
        except Exception as e:
            logger.error(f"Failed to track open: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    def track_click(self, match_id: str, url: Optional[str] = None, user_agent: Optional[str] = None) -> Dict:
        """
        Track link click event
        
        Args:
            match_id: Match ID
            url: Clicked URL
            user_agent: User agent string
            
        Returns:
            Tracking result
        """
        db = SessionLocal()
        try:
            match = db.query(Match).filter(Match.match_id == match_id).first()
            if not match:
                return {"status": "error", "message": "Match not found"}
            
            # Update click tracking
            if not match.clicks_count:
                match.clicks_count = 0
            match.clicks_count += 1
            match.first_clicked_at = match.first_clicked_at or datetime.utcnow()
            match.last_clicked_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Tracked click for match {match_id} (total: {match.clicks_count})")
            return {"status": "success", "match_id": match_id, "clicks_count": match.clicks_count}
        except Exception as e:
            logger.error(f"Failed to track click: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    def track_reply(self, match_id: str, reply_content: str, sentiment: str = "neutral") -> Dict:
        """
        Track email reply event
        
        Args:
            match_id: Match ID
            reply_content: Reply content
            sentiment: Sentiment classification (positive, negative, neutral)
            
        Returns:
            Tracking result
        """
        db = SessionLocal()
        try:
            match = db.query(Match).filter(Match.match_id == match_id).first()
            if not match:
                return {"status": "error", "message": "Match not found"}
            
            # Update reply tracking
            match.reply_count = (match.reply_count or 0) + 1
            match.last_replied_at = datetime.utcnow()
            
            # Classify reply sentiment
            if "interested" in reply_content.lower() or "yes" in reply_content.lower() or "let's talk" in reply_content.lower():
                match.reply_sentiment = "positive"
                match.status = "interested"
            elif "not interested" in reply_content.lower() or "no thanks" in reply_content.lower() or "remove" in reply_content.lower():
                match.reply_sentiment = "negative"
                match.status = "not_interested"
            else:
                match.reply_sentiment = sentiment
            
            db.commit()
            
            logger.info(f"Tracked reply for match {match_id} (sentiment: {match.reply_sentiment})")
            return {"status": "success", "match_id": match_id, "reply_count": match.reply_count, "sentiment": match.reply_sentiment}
        except Exception as e:
            logger.error(f"Failed to track reply: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    def track_bounce(self, match_id: str, bounce_type: str = "hard") -> Dict:
        """
        Track email bounce event
        
        Args:
            match_id: Match ID
            bounce_type: Bounce type (hard, soft)
            
        Returns:
            Tracking result
        """
        db = SessionLocal()
        try:
            match = db.query(Match).filter(Match.match_id == match_id).first()
            if not match:
                return {"status": "error", "message": "Match not found"}
            
            # Update bounce tracking
            match.bounced = True
            match.bounce_type = bounce_type
            match.bounced_at = datetime.utcnow()
            
            # If hard bounce, mark as not interested
            if bounce_type == "hard":
                match.status = "bounced"
            
            db.commit()
            
            logger.info(f"Tracked bounce for match {match_id} (type: {bounce_type})")
            return {"status": "success", "match_id": match_id, "bounce_type": bounce_type}
        except Exception as e:
            logger.error(f"Failed to track bounce: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    def get_match_engagement(self, match_id: str) -> Dict:
        """
        Get engagement metrics for a match
        
        Args:
            match_id: Match ID
            
        Returns:
            Engagement metrics dict
        """
        db = SessionLocal()
        try:
            match = db.query(Match).filter(Match.match_id == match_id).first()
            if not match:
                return {"status": "error", "message": "Match not found"}
            
            return {
                "match_id": match_id,
                "opens_count": match.opens_count or 0,
                "clicks_count": match.clicks_count or 0,
                "reply_count": match.reply_count or 0,
                "reply_sentiment": match.reply_sentiment,
                "first_opened_at": match.first_opened_at.isoformat() if match.first_opened_at else None,
                "last_opened_at": match.last_opened_at.isoformat() if match.last_opened_at else None,
                "first_clicked_at": match.first_clicked_at.isoformat() if match.first_clicked_at else None,
                "last_clicked_at": match.last_clicked_at.isoformat() if match.last_clicked_at else None,
                "last_replied_at": match.last_replied_at.isoformat() if match.last_replied_at else None,
                "bounced": match.bounced,
                "bounce_type": match.bounce_type,
                "status": match.status
            }
        except Exception as e:
            logger.error(f"Failed to get engagement: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            db.close()
    
    def get_engagement_summary(self, days: int = 30) -> Dict:
        """
        Get engagement summary for all matches in time period
        
        Args:
            days: Number of days to look back
            
        Returns:
            Engagement summary dict
        """
        db = SessionLocal()
        try:
            since = datetime.utcnow() - timedelta(days=days)
            
            matches = db.query(Match).filter(
                Match.intro_sent_at >= since
            ).all()
            
            total_sent = len(matches)
            total_opens = sum(m.opens_count or 0 for m in matches)
            total_clicks = sum(m.clicks_count or 0 for m in matches)
            total_replies = sum(m.reply_count or 0 for m in matches)
            total_bounces = sum(1 for m in matches if m.bounced)
            
            interested = sum(1 for m in matches if m.status == "interested")
            not_interested = sum(1 for m in matches if m.status == "not_interested")
            meeting_booked = sum(1 for m in matches if m.status == "meeting_booked")
            
            return {
                "period_days": days,
                "total_sent": total_sent,
                "total_opens": total_opens,
                "total_clicks": total_clicks,
                "total_replies": total_replies,
                "total_bounces": total_bounces,
                "open_rate": total_opens / total_sent if total_sent > 0 else 0,
                "click_rate": total_clicks / total_opens if total_opens > 0 else 0,
                "reply_rate": total_replies / total_opens if total_opens > 0 else 0,
                "bounce_rate": total_bounces / total_sent if total_sent > 0 else 0,
                "interested_count": interested,
                "not_interested_count": not_interested,
                "meeting_booked_count": meeting_booked
            }
        except Exception as e:
            logger.error(f"Failed to get engagement summary: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            db.close()


# Example usage
if __name__ == "__main__":
    service = ResponseTrackingService()
    
    # Track open
    result = service.track_open("match-123")
    print(f"Open tracked: {result}")
    
    # Get engagement
    engagement = service.get_match_engagement("match-123")
    print(f"Engagement: {engagement}")
    
    # Get summary
    summary = service.get_engagement_summary(days=30)
    print(f"Summary: {summary}")
