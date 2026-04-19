from sqlalchemy.orm import Session
from app.models import Lead, CampaignRun, OutboundMessage, Reply, SuppressionList, Event
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for tracking and reporting system metrics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_daily_metrics(self, days: int = 7) -> Dict:
        """Get metrics for the last N days"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        metrics = {
            "period": f"{start_date.date()} to {end_date.date()}",
            "days": days,
            "emails": self._get_email_metrics(start_date, end_date),
            "replies": self._get_reply_metrics(start_date, end_date),
            "leads": self._get_lead_metrics(),
            "campaigns": self._get_campaign_metrics(start_date, end_date)
        }
        
        return metrics
    
    def _get_email_metrics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get email-related metrics"""
        total_sent = self.db.query(OutboundMessage).filter(
            OutboundMessage.sent_at >= start_date,
            OutboundMessage.sent_at <= end_date,
            OutboundMessage.status == 'sent'
        ).count()
        
        total_failed = self.db.query(OutboundMessage).filter(
            OutboundMessage.failed_at >= start_date,
            OutboundMessage.failed_at <= end_date,
            OutboundMessage.status == 'failed'
        ).count()
        
        total_queued = self.db.query(OutboundMessage).filter(
            OutboundMessage.status == 'queued'
        ).count()
        
        return {
            "generated": total_sent + total_failed,
            "sent": total_sent,
            "failed": total_failed,
            "queued": total_queued,
            "success_rate": round((total_sent / (total_sent + total_failed) * 100) if (total_sent + total_failed) > 0 else 0, 2)
        }
    
    def _get_reply_metrics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get reply-related metrics"""
        total_replies = self.db.query(Reply).filter(
            Reply.received_at >= start_date,
            Reply.received_at <= end_date
        ).count()
        
        positive_replies = self.db.query(Reply).filter(
            Reply.received_at >= start_date,
            Reply.received_at <= end_date,
            Reply.classification == 'interested'
        ).count()
        
        # Get total sent emails in the period for reply rate calculation
        total_sent = self.db.query(OutboundMessage).filter(
            OutboundMessage.sent_at >= start_date,
            OutboundMessage.sent_at <= end_date,
            OutboundMessage.status == 'sent'
        ).count()
        
        return {
            "total": total_replies,
            "positive": positive_replies,
            "reply_rate": round((total_replies / total_sent * 100) if total_sent > 0 else 0, 2),
            "positive_rate": round((positive_replies / total_replies * 100) if total_replies > 0 else 0, 2)
        }
    
    def _get_lead_metrics(self) -> Dict:
        """Get lead-related metrics"""
        total_leads = self.db.query(Lead).count()
        
        status_breakdown = {}
        for status in ['new', 'queued', 'sent', 'replied', 'positive', 'not_now', 'not_interested', 'unsubscribe', 'bounced']:
            count = self.db.query(Lead).filter(Lead.status == status).count()
            status_breakdown[status] = count
        
        return {
            "total": total_leads,
            "by_status": status_breakdown
        }
    
    def _get_campaign_metrics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get campaign-related metrics"""
        total_runs = self.db.query(CampaignRun).filter(
            CampaignRun.generated_at >= start_date,
            CampaignRun.generated_at <= end_date
        ).count()
        
        completed_runs = self.db.query(CampaignRun).filter(
            CampaignRun.completed_at >= start_date,
            CampaignRun.completed_at <= end_date,
            CampaignRun.status == 'completed'
        ).count()
        
        return {
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "completion_rate": round((completed_runs / total_runs * 100) if total_runs > 0 else 0, 2)
        }
    
    def get_real_time_metrics(self) -> Dict:
        """Get real-time system metrics"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "queue_size": self.db.query(OutboundMessage).filter(
                OutboundMessage.status == 'queued'
            ).count(),
            "pending_followups": self.db.query(OutboundMessage).filter(
                OutboundMessage.status == 'sent'
            ).count(),
            "suppressed_emails": self.db.query(SuppressionList).count(),
            "recent_errors": self._get_recent_errors()
        }
    
    def _get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """Get recent error events"""
        errors = self.db.query(Event).filter(
            Event.event_type == 'email_failed'
        ).order_by(Event.created_at.desc()).limit(limit).all()
        
        return [
            {
                "event_id": error.event_id,
                "entity_id": error.entity_id,
                "data": error.data,
                "created_at": error.created_at.isoformat()
            }
            for error in errors
        ]
    
    def log_metric(self, metric_name: str, value: float, tags: Dict = None):
        """Log a custom metric"""
        logger.info(f"METRIC: {metric_name}={value} tags={tags}")
        
        # Store as event for audit trail
        event = Event(
            event_id=f"metric-{metric_name}-{str(datetime.utcnow().timestamp())}",
            event_type="metric",
            entity_type="metric",
            entity_id=metric_name,
            data={
                "value": value,
                "tags": tags or {}
            }
        )
        self.db.add(event)
        self.db.commit()
