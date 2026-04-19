"""Alerting system for production monitoring"""
import logging
import json
from typing import Optional, Dict, List
from datetime import datetime
import requests
from app.settings import settings

logger = logging.getLogger(__name__)


class AlertManager:
    """Manage and send alerts"""
    
    def __init__(self):
        self.webhook_url = getattr(settings, 'ALERT_WEBHOOK_URL', None)
        self.slack_webhook = getattr(settings, 'SLACK_WEBHOOK_URL', None)
        self.email_alerts = getattr(settings, 'ALERT_EMAILS', [])
        self.severity_threshold = getattr(settings, 'ALERT_SEVERITY_THRESHOLD', 'warning')
    
    def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "warning",
        metadata: Optional[Dict] = None
    ):
        """Send alert through configured channels"""
        alert_data = {
            "title": title,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Log alert
        log_method = getattr(logger, severity, logger.warning)
        log_method(f"ALERT: {title} - {message}")
        
        # Send to webhook if configured
        if self.webhook_url:
            self._send_webhook(alert_data)
        
        # Send to Slack if configured
        if self.slack_webhook:
            self._send_slack(alert_data)
    
    def _send_webhook(self, alert_data: Dict):
        """Send alert to generic webhook"""
        try:
            response = requests.post(
                self.webhook_url,
                json=alert_data,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def _send_slack(self, alert_data: Dict):
        """Send alert to Slack"""
        try:
            # Color based on severity
            color_map = {
                "critical": "danger",
                "error": "danger",
                "warning": "warning",
                "info": "good"
            }
            
            payload = {
                "attachments": [
                    {
                        "color": color_map.get(alert_data["severity"], "warning"),
                        "title": alert_data["title"],
                        "text": alert_data["message"],
                        "footer": "AI SaaS GTM Agent",
                        "ts": int(datetime.utcnow().timestamp()),
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert_data["severity"],
                                "short": True
                            },
                            {
                                "title": "Timestamp",
                                "value": alert_data["timestamp"],
                                "short": True
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def alert_error(self, error: Exception, context: str = ""):
        """Alert on error"""
        self.send_alert(
            title=f"Error: {type(error).__name__}",
            message=f"{str(error)} | Context: {context}",
            severity="error",
            metadata={"error_type": type(error).__name__, "context": context}
        )
    
    def alert_critical(self, message: str, metadata: Optional[Dict] = None):
        """Alert on critical issue"""
        self.send_alert(
            title="CRITICAL ISSUE",
            message=message,
            severity="critical",
            metadata=metadata
        )
    
    def alert_high_reply_rate(self, reply_rate: float, threshold: float = 30.0):
        """Alert when reply rate exceeds threshold (good news!)"""
        if reply_rate > threshold:
            self.send_alert(
                title="High Reply Rate Detected",
                message=f"Reply rate is {reply_rate:.1f}%, exceeding threshold of {threshold}%",
                severity="info",
                metadata={"reply_rate": reply_rate, "threshold": threshold}
            )
    
    def alert_low_reply_rate(self, reply_rate: float, threshold: float = 5.0):
        """Alert when reply rate drops below threshold"""
        if reply_rate < threshold:
            self.send_alert(
                title="Low Reply Rate Warning",
                message=f"Reply rate is {reply_rate:.1f}%, below threshold of {threshold}%",
                severity="warning",
                metadata={"reply_rate": reply_rate, "threshold": threshold}
            )
    
    def alert_gmail_rate_limit(self):
        """Alert when Gmail rate limit is approached"""
        self.send_alert(
            title="Gmail Rate Limit Warning",
            message="Approaching Gmail API rate limit",
            severity="warning"
        )
    
    def alert_deliverability_issue(self, domain: str, health_score: int):
        """Alert on deliverability issues"""
        self.send_alert(
            title=f"Deliverability Issue: {domain}",
            message=f"Domain health score dropped to {health_score}",
            severity="error",
            metadata={"domain": domain, "health_score": health_score}
        )
    
    def alert_pipeline_stuck_leads(self, count: int, threshold: int = 10):
        """Alert when leads are stuck in pipeline"""
        if count >= threshold:
            self.send_alert(
                title="Stuck Leads Detected",
                message=f"{count} leads are stuck in pipeline for more than 7 days",
                severity="warning",
                metadata={"stuck_count": count}
            )
    
    def alert_circuit_breaker_open(self, service: str):
        """Alert when circuit breaker opens"""
        self.send_alert(
            title=f"Circuit Breaker Open: {service}",
            message=f"Circuit breaker for {service} has opened due to failures",
            severity="critical",
            metadata={"service": service}
        )
    
    def alert_escalation_queue_full(self, count: int, threshold: int = 20):
        """Alert when escalation queue is filling up"""
        if count >= threshold:
            self.send_alert(
                title="Escalation Queue Backlog",
                message=f"{count} items in escalation queue",
                severity="warning",
                metadata={"queue_size": count}
            )
    
    def alert_high_bounce_rate(self, bounce_rate: float, threshold: float = 5.0):
        """Alert on high bounce rate"""
        if bounce_rate > threshold:
            self.send_alert(
                title="High Bounce Rate",
                message=f"Bounce rate is {bounce_rate:.1f}%, above threshold of {threshold}%",
                severity="error",
                metadata={"bounce_rate": bounce_rate}
            )


# Global alert manager
alert_manager = AlertManager()


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    return alert_manager
