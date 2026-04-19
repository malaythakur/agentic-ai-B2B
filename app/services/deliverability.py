import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
from app.models import DeliverabilityRule

logger = logging.getLogger(__name__)


class DeliverabilitySystem:
    """Domain warming, inbox rotation, send throttling, bounce handling, spam signals"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def can_send(self, from_email: str) -> Dict:
        """Check if we can send from this email (throttling, health checks)"""
        domain = from_email.split('@')[1]
        
        rule = self.db.query(DeliverabilityRule).filter(
            DeliverabilityRule.domain == domain
        ).first()
        
        if not rule:
            # Create default rule
            rule = self._create_default_rule(domain)
        
        # Check health score
        if rule.health_score < 50:
            return {
                "can_send": False,
                "reason": "Domain health score too low",
                "health_score": rule.health_score,
                "recommended_action": "Pause sending and investigate"
            }
        
        # Check hourly limit
        if rule.current_hourly_count >= rule.max_sends_per_hour:
            return {
                "can_send": False,
                "reason": "Hourly send limit reached",
                "current_count": rule.current_hourly_count,
                "limit": rule.max_sends_per_hour,
                "recommended_action": f"Wait until next hour"
            }
        
        # Check daily limit
        if rule.current_daily_count >= rule.max_sends_per_day:
            return {
                "can_send": False,
                "reason": "Daily send limit reached",
                "current_count": rule.current_daily_count,
                "limit": rule.max_sends_per_day,
                "recommended_action": "Wait until tomorrow"
            }
        
        # Check if domain is warmed
        if not rule.domain_warmed:
            warmup_days = (datetime.utcnow() - rule.warmup_start_date).days if rule.warmup_start_date else 0
            if warmup_days < 14:  # 14 day warmup period
                return {
                    "can_send": False,
                    "reason": "Domain not fully warmed",
                    "warmup_days": warmup_days,
                    "recommended_action": "Continue warmup at reduced rate"
                }
        
        return {
            "can_send": True,
            "domain": domain,
            "health_score": rule.health_score,
            "hourly_remaining": rule.max_sends_per_hour - rule.current_hourly_count,
            "daily_remaining": rule.max_sends_per_day - rule.current_daily_count
        }
    
    def record_send(self, from_email: str):
        """Record a send for throttling"""
        domain = from_email.split('@')[1]
        
        rule = self.db.query(DeliverabilityRule).filter(
            DeliverabilityRule.domain == domain
        ).first()
        
        if rule:
            rule.current_hourly_count += 1
            rule.current_daily_count += 1
            self.db.commit()
    
    def record_bounce(self, from_email: str, bounce_type: str = "hard"):
        """Record a bounce and update health metrics"""
        domain = from_email.split('@')[1]
        
        rule = self.db.query(DeliverabilityRule).filter(
            DeliverabilityRule.domain == domain
        ).first()
        
        if rule:
            # Update bounce rate
            total_sent = rule.current_daily_count
            if total_sent > 0:
                # Simplified bounce rate calculation
                rule.bounce_rate = min(rule.bounce_rate + (5 if bounce_type == "hard" else 2), 100)
            
            # Reduce health score
            health_penalty = 15 if bounce_type == "hard" else 5
            rule.health_score = max(rule.health_score - health_penalty, 0)
            
            self.db.commit()
            
            logger.warning(f"Bounce recorded for {domain}, health score now {rule.health_score}")
    
    def record_spam_complaint(self, from_email: str):
        """Record a spam complaint - severe penalty"""
        domain = from_email.split('@')[1]
        
        rule = self.db.query(DeliverabilityRule).filter(
            DeliverabilityRule.domain == domain
        ).first()
        
        if rule:
            rule.spam_rate = min(rule.spam_rate + 10, 100)
            rule.health_score = max(rule.health_score - 30, 0)
            
            self.db.commit()
            
            logger.error(f"Spam complaint for {domain}, health score now {rule.health_score}")
    
    def get_best_inbox(self, domain: str) -> str:
        """Get the best inbox for sending (rotation logic)"""
        rule = self.db.query(DeliverabilityRule).filter(
            DeliverabilityRule.domain == domain
        ).first()
        
        if not rule:
            return f"info@{domain}"
        
        if rule.backup_inboxes:
            # Simple rotation: cycle through inboxes
            current_hour = datetime.utcnow().hour
            inbox_index = current_hour % len(rule.backup_inboxes)
            return rule.backup_inboxes[inbox_index]
        
        return rule.primary_inbox or f"info@{domain}"
    
    def reset_hourly_counts(self):
        """Reset hourly send counts (called by Celery beat hourly)"""
        rules = self.db.query(DeliverabilityRule).all()
        
        for rule in rules:
            rule.current_hourly_count = 0
            self.db.commit()
        
        logger.info(f"Reset hourly counts for {len(rules)} domains")
    
    def reset_daily_counts(self):
        """Reset daily send counts (called by Celery beat daily)"""
        rules = self.db.query(DeliverabilityRule).all()
        
        for rule in rules:
            rule.current_daily_count = 0
            self.db.commit()
        
        logger.info(f"Reset daily counts for {len(rules)} domains")
    
    def start_warmup(self, domain: str):
        """Start domain warmup process"""
        rule = self.db.query(DeliverabilityRule).filter(
            DeliverabilityRule.domain == domain
        ).first()
        
        if not rule:
            rule = self._create_default_rule(domain)
        
        rule.warmup_start_date = datetime.utcnow()
        rule.domain_warmed = False
        
        # Set conservative limits during warmup
        rule.max_sends_per_hour = 5
        rule.max_sends_per_day = 20
        
        self.db.commit()
        
        logger.info(f"Started warmup for {domain}")
    
    def check_warmup_progress(self, domain: str) -> Dict:
        """Check warmup progress and adjust limits"""
        rule = self.db.query(DeliverabilityRule).filter(
            DeliverabilityRule.domain == domain
        ).first()
        
        if not rule or not rule.warmup_start_date:
            return {"status": "not_started"}
        
        days_warming = (datetime.utcnow() - rule.warmup_start_date).days
        
        # Progressive warmup schedule
        warmup_schedule = {
            0: (5, 20),    # Day 0-1: 5/hour, 20/day
            2: (10, 50),   # Day 2-3: 10/hour, 50/day
            5: (15, 100),  # Day 4-6: 15/hour, 100/day
            8: (20, 150),  # Day 7-10: 20/hour, 150/day
            11: (25, 200), # Day 11-13: 25/hour, 200/day
            14: (30, 250)  # Day 14+: 30/hour, 250/day
        }
        
        for day_threshold, (hourly, daily) in sorted(warmup_schedule.items()):
            if days_warming >= day_threshold:
                rule.max_sends_per_hour = hourly
                rule.max_sends_per_day = daily
        
        if days_warming >= 14:
            rule.domain_warmed = True
            rule.warmup_end_date = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "status": "in_progress" if not rule.domain_warmed else "complete",
            "days_warming": days_warming,
            "current_limits": {
                "hourly": rule.max_sends_per_hour,
                "daily": rule.max_sends_per_day
            }
        }
    
    def get_domain_health(self, domain: str) -> Dict:
        """Get comprehensive domain health report"""
        rule = self.db.query(DeliverabilityRule).filter(
            DeliverabilityRule.domain == domain
        ).first()
        
        if not rule:
            return {"domain": domain, "status": "not_configured"}
        
        return {
            "domain": domain,
            "health_score": rule.health_score,
            "bounce_rate": rule.bounce_rate,
            "spam_rate": rule.spam_rate,
            "domain_warmed": rule.domain_warmed,
            "warmup_progress": self.check_warmup_progress(domain),
            "current_usage": {
                "hourly": f"{rule.current_hourly_count}/{rule.max_sends_per_hour}",
                "daily": f"{rule.current_daily_count}/{rule.max_sends_per_day}"
            },
            "recommendations": self._get_health_recommendations(rule)
        }
    
    def _get_health_recommendations(self, rule) -> list:
        """Get health improvement recommendations"""
        recommendations = []
        
        if rule.health_score < 50:
            recommendations.append("Reduce send volume immediately")
            recommendations.append("Review email content for spam triggers")
        
        if rule.bounce_rate > 5:
            recommendations.append("Clean email list - remove invalid addresses")
        
        if rule.spam_rate > 1:
            recommendations.append("Urgent: investigate spam complaints")
            recommendations.append("Review sending practices")
        
        if not rule.domain_warmed:
            recommendations.append("Continue warmup process")
        
        if rule.health_score >= 80 and rule.domain_warmed:
            recommendations.append("Domain healthy - can increase send volume")
        
        return recommendations if recommendations else ["Domain healthy - continue normal operations"]
    
    def _create_default_rule(self, domain: str):
        """Create default deliverability rule for domain"""
        rule = DeliverabilityRule(
            rule_id=f"rule-{str(uuid.uuid4())[:8]}",
            domain=domain,
            domain_warmed=False,
            max_sends_per_hour=30,
            max_sends_per_day=200,
            current_hourly_count=0,
            current_daily_count=0,
            primary_inbox=f"info@{domain}",
            backup_inboxes=[],
            health_score=100,
            bounce_rate=0,
            spam_rate=0
        )
        self.db.add(rule)
        self.db.commit()
        return rule
