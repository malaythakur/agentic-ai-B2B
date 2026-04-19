"""
Email Warm-up Service

Implements gradual warm-up for new Gmail accounts to avoid spam flags:
- Starts with 5-10 emails per day
- Gradually increases over 14 days
- Maintains consistent sending pattern
- Tracks warm-up progress
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EmailWarmupService:
    """Service for managing email warm-up for new Gmail accounts"""
    
    # Warm-up schedule: day -> max emails per day
    WARMUP_SCHEDULE = {
        1: 5,
        2: 8,
        3: 10,
        4: 15,
        5: 20,
        6: 25,
        7: 30,
        8: 40,
        9: 50,
        10: 60,
        11: 75,
        12: 85,
        13: 95,
        14: 100
    }
    
    def __init__(self, db: Session):
        """
        Initialize warm-up service
        
        Args:
            db: Database session
        """
        self.db = db
        self._load_warmup_state()
    
    def _load_warmup_state(self):
        """Load warm-up state from database or file"""
        # For now, use in-memory state
        # In production, store in database
        self.warmup_start_date = None
        self.emails_sent_today = 0
        self.total_emails_sent = 0
    
    def get_daily_limit(self) -> int:
        """
        Get current daily limit based on warm-up progress
        
        Returns:
            Maximum emails that can be sent today
        """
        if not self.warmup_start_date:
            # First day of warm-up
            return self.WARMUP_SCHEDULE[1]
        
        days_since_start = (datetime.utcnow().date() - self.warmup_start_date).days + 1
        
        if days_since_start >= 14:
            # Warm-up complete, use standard limit
            from app.services.rate_limiter import get_rate_limiter
            rate_limiter = get_rate_limiter()
            return rate_limiter.daily_limit
        
        # Use warm-up schedule
        return self.WARMUP_SCHEDULE.get(days_since_start, 100)
    
    def start_warmup(self):
        """Start the warm-up period"""
        if self.warmup_start_date is None:
            self.warmup_start_date = datetime.utcnow().date()
            logger.info(f"Email warm-up started on {self.warmup_start_date}")
            return True
        return False
    
    def get_warmup_status(self) -> Dict:
        """
        Get current warm-up status
        
        Returns:
            Dict with warm-up progress and limits
        """
        if not self.warmup_start_date:
            return {
                "status": "not_started",
                "message": "Warm-up not started",
                "daily_limit": 0
            }
        
        days_since_start = (datetime.utcnow().date() - self.warmup_start_date).days + 1
        is_complete = days_since_start >= 14
        
        return {
            "status": "complete" if is_complete else "in_progress",
            "start_date": self.warmup_start_date.isoformat(),
            "days_elapsed": days_since_start,
            "days_remaining": max(0, 14 - days_since_start),
            "daily_limit": self.get_daily_limit(),
            "emails_sent_today": self.emails_sent_today,
            "total_emails_sent": self.total_emails_sent
        }
    
    def record_email_sent(self):
        """Record that an email was sent during warm-up"""
        self.emails_sent_today += 1
        self.total_emails_sent += 1
        
        # Reset daily counter at midnight (check in actual implementation)
        today = datetime.utcnow().date()
        if not hasattr(self, 'last_reset_date') or self.last_reset_date != today:
            self.emails_sent_today = 0
            self.last_reset_date = today
    
    def can_send_email(self) -> tuple[bool, str]:
        """
        Check if an email can be sent during warm-up
        
        Returns:
            Tuple of (can_send, reason_if_not)
        """
        daily_limit = self.get_daily_limit()
        
        if self.emails_sent_today >= daily_limit:
            return False, f"Daily warm-up limit reached ({daily_limit} emails/day)"
        
        return True, ""
