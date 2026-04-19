"""
Rate Limiter for Gmail API

Implements rate limiting to respect Gmail API quotas:
- Free Gmail account: 500 emails/day
- Google Workspace (free tier): 2,000 emails/day
- Uses in-memory tracking with daily reset
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for Gmail API to respect daily quotas"""
    
    # Gmail API daily quotas
    QUOTAS = {
        "free_gmail": 500,  # Free Gmail account
        "workspace_free": 2000,  # Google Workspace free tier
        "workspace_business": 10000,  # Google Workspace Business
    }
    
    def __init__(self, account_type: str = "free_gmail"):
        """
        Initialize rate limiter
        
        Args:
            account_type: Type of Gmail account (free_gmail, workspace_free, workspace_business)
        """
        self.account_type = account_type
        self.daily_limit = self.QUOTAS.get(account_type, 500)
        
        # Track sent emails: {date: count}
        self.sent_counts = defaultdict(int)
        
        # Track last reset time
        self.last_reset = datetime.utcnow().date()
        
        logger.info(f"Rate limiter initialized with daily limit: {self.daily_limit} (account type: {account_type})")
    
    def _check_and_reset_daily(self):
        """Check if we need to reset daily counters"""
        today = datetime.utcnow().date()
        if today > self.last_reset:
            logger.info(f"Resetting daily rate limit counters (new day: {today})")
            self.sent_counts.clear()
            self.last_reset = today
    
    def can_send_email(self) -> tuple[bool, Optional[str]]:
        """
        Check if we can send another email
        
        Returns:
            Tuple of (can_send, reason_if_not)
        """
        self._check_and_reset_daily()
        
        today = datetime.utcnow().date()
        sent_today = self.sent_counts[today]
        
        if sent_today >= self.daily_limit:
            remaining = self.daily_limit - sent_today
            return False, f"Daily limit reached ({self.daily_limit} emails/day). Wait until tomorrow."
        
        return True, None
    
    def record_email_sent(self):
        """Record that an email was sent"""
        self._check_and_reset_daily()
        
        today = datetime.utcnow().date()
        self.sent_counts[today] += 1
        
        sent_today = self.sent_counts[today]
        remaining = self.daily_limit - sent_today
        
        logger.info(f"Email sent. Total today: {sent_today}/{self.daily_limit}, Remaining: {remaining}")
        
        return remaining
    
    def get_status(self) -> Dict:
        """Get current rate limiter status"""
        self._check_and_reset_daily()
        
        today = datetime.utcnow().date()
        sent_today = self.sent_counts[today]
        remaining = self.daily_limit - sent_today
        
        return {
            "account_type": self.account_type,
            "daily_limit": self.daily_limit,
            "sent_today": sent_today,
            "remaining_today": remaining,
            "reset_date": (self.last_reset + timedelta(days=1)).isoformat()
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(account_type: str = "free_gmail") -> RateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(account_type)
    return _rate_limiter
