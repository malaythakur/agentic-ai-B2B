"""Safeguards Service - Suppression Lists, Circuit Breakers, Sentiment Detection"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import SuppressionList, OutboundMessage, Reply, DeliverabilityRule
from app.logging_config import logger as app_logger

logger = app_logger


class SafeguardsService:
    """Service for outbound safety mechanisms"""
    
    def __init__(self, db: Session):
        self.db = db
        self.circuit_breaker_state = "closed"  # closed, half_open, open
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 10
        self.circuit_breaker_timeout = timedelta(minutes=30)
        self.circuit_breaker_last_failure_time = None
    
    def check_suppression_list(self, email: str, company: str = None) -> Dict:
        """Check if email or company is on suppression list"""
        # Check email
        suppressed_email = self.db.query(SuppressionList).filter(
            SuppressionList.email == email
        ).first()
        
        if suppressed_email:
            return {
                "blocked": True,
                "reason": "email_suppressed",
                "detail": suppressed_email.reason,
                "added_at": suppressed_email.added_at.isoformat()
            }
        
        # Check company domain if provided
        if company:
            domain = company.lower().replace(" ", "")
            suppressed_domain = self.db.query(SuppressionList).filter(
                SuppressionList.email.like(f"%@{domain}%")
            ).first()
            
            if suppressed_domain:
                return {
                    "blocked": True,
                    "reason": "domain_suppressed",
                    "detail": suppressed_domain.reason,
                    "added_at": suppressed_domain.added_at.isoformat()
                }
        
        return {"blocked": False}
    
    def add_to_suppression_list(
        self,
        email: str,
        reason: str,
        lead_id: str = None
    ) -> bool:
        """Add email to suppression list"""
        # Check if already exists
        existing = self.db.query(SuppressionList).filter(
            SuppressionList.email == email
        ).first()
        
        if existing:
            logger.info(f"Email {email} already on suppression list")
            return False
        
        suppression = SuppressionList(
            email=email,
            reason=reason,
            lead_id=lead_id
        )
        self.db.add(suppression)
        self.db.commit()
        
        logger.info(f"Added {email} to suppression list: {reason}")
        return True
    
    def auto_suppress_bounces(self, bounce_threshold: int = 3) -> Dict:
        """Automatically suppress emails that bounce multiple times"""
        # Find messages with bounce status
        bounced_messages = self.db.query(OutboundMessage).filter(
            OutboundMessage.status == "failed",
            OutboundMessage.error_message.ilike("%bounce%")
        ).all()
        
        # Count bounces per email
        email_bounce_counts = {}
        for msg in bounced_messages:
            email = msg.to_email
            email_bounce_counts[email] = email_bounce_counts.get(email, 0) + 1
        
        # Suppress emails exceeding threshold
        suppressed_count = 0
        for email, count in email_bounce_counts.items():
            if count >= bounce_threshold:
                self.add_to_suppression_list(
                    email=email,
                    reason=f"Auto-suppressed: {count} bounces detected"
                )
                suppressed_count += 1
        
        return {
            "total_bounced": len(bounced_messages),
            "unique_emails": len(email_bounce_counts),
            "suppressed": suppressed_count
        }
    
    def auto_suppress_unsubscribes(self) -> Dict:
        """Automatically suppress emails that unsubscribe"""
        # Find replies with unsubscribe keywords
        unsubscribe_keywords = ["unsubscribe", "remove", "opt-out", "stop"]
        
        replies = self.db.query(Reply).filter(
            Reply.body.ilike("%unsubscribe%") |
            Reply.body.ilike("%remove%") |
            Reply.body.ilike("%opt-out%") |
            Reply.body.ilike("%stop%")
        ).all()
        
        suppressed_count = 0
        for reply in replies:
            # Get the original message to find the to_email
            message = self.db.query(OutboundMessage).filter(
                OutboundMessage.message_id == reply.message_id
            ).first()
            
            if message:
                # Suppress the from_email of the reply (the person who unsubscribed)
                self.add_to_suppression_list(
                    email=reply.from_email,
                    reason="Auto-suppressed: Unsubscribe request detected",
                    lead_id=reply.lead_id
                )
                suppressed_count += 1
        
        return {
            "unsubscribes_detected": len(replies),
            "suppressed": suppressed_count
        }
    
    def check_circuit_breaker(self) -> Dict:
        """Check if circuit breaker should block sends"""
        now = datetime.utcnow()
        
        # If circuit is open, check if timeout has elapsed
        if self.circuit_breaker_state == "open":
            if self.circuit_breaker_last_failure_time:
                time_since_failure = now - self.circuit_breaker_last_failure_time
                if time_since_failure >= self.circuit_breaker_timeout:
                    # Transition to half_open
                    self.circuit_breaker_state = "half_open"
                    logger.info("Circuit breaker transitioning to half_open")
                    return {
                        "blocked": False,
                        "state": "half_open",
                        "message": "Circuit breaker in half_open state - allowing test traffic"
                    }
            return {
                "blocked": True,
                "state": "open",
                "message": "Circuit breaker is open - blocking sends"
            }
        
        # If circuit is half_open, allow limited traffic
        if self.circuit_breaker_state == "half_open":
            return {
                "blocked": False,
                "state": "half_open",
                "message": "Circuit breaker in half_open state - monitoring"
            }
        
        # Circuit is closed - normal operation
        return {
            "blocked": False,
            "state": "closed",
            "message": "Circuit breaker closed - normal operation"
        }
    
    def record_circuit_breaker_failure(self):
        """Record a failure and potentially trip the circuit breaker"""
        self.circuit_breaker_failures += 1
        self.circuit_breaker_last_failure_time = datetime.utcnow()
        
        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            self.circuit_breaker_state = "open"
            logger.warning(f"Circuit breaker tripped after {self.circuit_breaker_failures} failures")
    
    def record_circuit_breaker_success(self):
        """Record a success and potentially close the circuit breaker"""
        if self.circuit_breaker_state == "half_open":
            self.circuit_breaker_failures = 0
            self.circuit_breaker_state = "closed"
            logger.info("Circuit breaker closed after successful test")
        else:
            # Reset failure count on success in closed state
            self.circuit_breaker_failures = 0
    
    def check_reply_rate_threshold(self, min_reply_rate: float = 5.0) -> Dict:
        """Check if reply rate has dropped below threshold"""
        # Get messages sent in last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        sent_messages = self.db.query(OutboundMessage).filter(
            OutboundMessage.sent_at >= seven_days_ago,
            OutboundMessage.status == "sent"
        ).all()
        
        if not sent_messages:
            return {"checked": False, "reason": "no_messages_sent"}
        
        # Count replies
        replied_message_ids = self.db.query(Reply.message_id).distinct().all()
        replied_count = len(replied_message_ids)
        
        reply_rate = (replied_count / len(sent_messages)) * 100
        
        if reply_rate < min_reply_rate:
            logger.warning(f"Reply rate {reply_rate}% below threshold {min_reply_rate}%")
            return {
                "blocked": True,
                "reply_rate": reply_rate,
                "threshold": min_reply_rate,
                "message": f"Reply rate {reply_rate}% below threshold - pausing sends"
            }
        
        return {
            "blocked": False,
            "reply_rate": reply_rate,
            "threshold": min_reply_rate,
            "message": "Reply rate healthy"
        }
    
    def detect_negative_sentiment(self, reply_body: str) -> Dict:
        """Detect negative sentiment in replies"""
        negative_keywords = [
            "angry", "furious", "spam", "harassment", "report",
            "never contact", "stop emailing", "remove immediately",
            "legal action", "cease and desist", "unwanted"
        ]
        
        body_lower = reply_body.lower()
        
        detected_keywords = [kw for kw in negative_keywords if kw in body_lower]
        
        if detected_keywords:
            severity = "high" if len(detected_keywords) >= 2 else "medium"
            
            logger.warning(f"Negative sentiment detected: {detected_keywords}")
            
            return {
                "negative": True,
                "severity": severity,
                "keywords": detected_keywords,
                "action": "suppress_and_escalate" if severity == "high" else "flag_for_review"
            }
        
        return {"negative": False}
    
    def check_deliverability_health(self, domain: str) -> Dict:
        """Check deliverability health for a domain"""
        rule = self.db.query(DeliverabilityRule).filter(
            DeliverabilityRule.domain == domain
        ).first()
        
        if not rule:
            # Create rule if doesn't exist
            rule = DeliverabilityRule(
                domain=domain,
                health_score=100,
                max_sends_per_hour=30,
                max_sends_per_day=200
            )
            self.db.add(rule)
            self.db.commit()
        
        # Check if health score is too low
        if rule.health_score < 50:
            return {
                "blocked": True,
                "health_score": rule.health_score,
                "message": f"Domain health score {rule.health_score} too low - pausing sends"
            }
        
        # Check hourly limit
        if rule.current_hourly_count >= rule.max_sends_per_hour:
            return {
                "blocked": True,
                "reason": "hourly_limit",
                "current": rule.current_hourly_count,
                "limit": rule.max_sends_per_hour,
                "message": "Hourly send limit reached"
            }
        
        # Check daily limit
        if rule.current_daily_count >= rule.max_sends_per_day:
            return {
                "blocked": True,
                "reason": "daily_limit",
                "current": rule.current_daily_count,
                "limit": rule.max_sends_per_day,
                "message": "Daily send limit reached"
            }
        
        return {
            "blocked": False,
            "health_score": rule.health_score,
            "hourly_remaining": rule.max_sends_per_hour - rule.current_hourly_count,
            "daily_remaining": rule.max_sends_per_day - rule.current_daily_count
        }
    
    def run_all_safeguard_checks(
        self,
        email: str,
        domain: str,
        company: str = None
    ) -> Dict:
        """Run all safeguard checks before sending"""
        checks = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": []
        }
        
        # Suppression list check
        suppression_check = self.check_suppression_list(email, company)
        checks["checks"].append({
            "name": "suppression_list",
            "passed": not suppression_check["blocked"],
            "result": suppression_check
        })
        
        # Circuit breaker check
        circuit_check = self.check_circuit_breaker()
        checks["checks"].append({
            "name": "circuit_breaker",
            "passed": not circuit_check["blocked"],
            "result": circuit_check
        })
        
        # Reply rate check
        reply_rate_check = self.check_reply_rate_threshold()
        if reply_rate_check.get("checked", True):
            checks["checks"].append({
                "name": "reply_rate",
                "passed": not reply_rate_check.get("blocked", False),
                "result": reply_rate_check
            })
        
        # Deliverability check
        deliverability_check = self.check_deliverability_health(domain)
        checks["checks"].append({
            "name": "deliverability",
            "passed": not deliverability_check["blocked"],
            "result": deliverability_check
        })
        
        # Overall result
        all_passed = all(check["passed"] for check in checks["checks"])
        checks["all_passed"] = all_passed
        checks["can_send"] = all_passed
        
        return checks
    
    def get_safeguards_summary(self) -> Dict:
        """Get summary of safeguards status"""
        return {
            "circuit_breaker": {
                "state": self.circuit_breaker_state,
                "failures": self.circuit_breaker_failures,
                "threshold": self.circuit_breaker_threshold
            },
            "suppression_list": {
                "total_suppressed": self.db.query(SuppressionList).count()
            },
            "deliverability": {
                "domains_monitored": self.db.query(DeliverabilityRule).count(),
                "healthy_domains": self.db.query(DeliverabilityRule).filter(
                    DeliverabilityRule.health_score >= 70
                ).count()
            }
        }
