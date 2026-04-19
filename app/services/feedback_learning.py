import logging
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models import OutboundMessage, Reply, OfferStrategy, Lead
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class FeedbackLearningLoop:
    """Track performance metrics and optimize based on outcomes"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_outcome(self, message_id: str, replied: bool, converted: bool = False):
        """Record outcome for a message and update metrics"""
        message = self.db.query(OutboundMessage).filter(
            OutboundMessage.message_id == message_id
        ).first()
        
        if not message:
            return
        
        # Update subject performance
        self._update_subject_metrics(message.subject, replied)
        
        # Update offer strategy performance
        lead = self.db.query(Lead).filter(Lead.lead_id == message.lead_id).first()
        if lead:
            self._update_company_type_metrics(lead.company, replied)
        
        # Update angle performance (from offer matching)
        self._update_angle_performance(message, replied)
        
        logger.info(f"Recorded outcome for message {message_id}: replied={replied}, converted={converted}")
    
    def _update_subject_metrics(self, subject: str, replied: bool):
        """Update performance metrics for a subject"""
        from app.models import PerformanceMetric
        
        metric = self.db.query(PerformanceMetric).filter(
            PerformanceMetric.dimension_type == "subject",
            PerformanceMetric.dimension_value == subject[:100]
        ).first()
        
        if not metric:
            metric = PerformanceMetric(
                metric_id=f"metric-{str(uuid.uuid4())[:8]}",
                dimension_type="subject",
                dimension_value=subject[:100],
                total_sent=1,
                total_replies=1 if replied else 0,
                total_converted=0
            )
            self.db.add(metric)
        else:
            metric.total_sent += 1
            if replied:
                metric.total_replies += 1
        
        # Recalculate rates
        if metric.total_sent > 0:
            metric.reply_rate = (metric.total_replies / metric.total_sent) * 100
            metric.conversion_rate = (metric.total_converted / metric.total_sent) * 100
        
        metric.calculated_at = datetime.utcnow()
        self.db.commit()
    
    def _update_company_type_metrics(self, company: str, replied: bool):
        """Update performance metrics for company type"""
        from app.models import PerformanceMetric
        
        # Infer company type from name (simplified)
        company_type = self._infer_company_type(company)
        
        metric = self.db.query(PerformanceMetric).filter(
            PerformanceMetric.dimension_type == "company_type",
            PerformanceMetric.dimension_value == company_type
        ).first()
        
        if not metric:
            metric = PerformanceMetric(
                metric_id=f"metric-{str(uuid.uuid4())[:8]}",
                dimension_type="company_type",
                dimension_value=company_type,
                total_sent=1,
                total_replies=1 if replied else 0,
                total_converted=0
            )
            self.db.add(metric)
        else:
            metric.total_sent += 1
            if replied:
                metric.total_replies += 1
        
        if metric.total_sent > 0:
            metric.reply_rate = (metric.total_replies / metric.total_sent) * 100
        
        metric.calculated_at = datetime.utcnow()
        self.db.commit()
    
    def _update_angle_performance(self, message: OutboundMessage, replied: bool):
        """Update performance for offer angle"""
        # This would be linked to the offer strategy used
        # For now, we'll use subject as a proxy
        self._update_subject_metrics(message.subject, replied)
    
    def _infer_company_type(self, company: str) -> str:
        """Infer company type from company name"""
        company_lower = company.lower()
        
        if any(word in company_lower for word in ["inc", "corp", "llc", "ltd"]):
            return "established"
        elif any(word in company_lower for word in ["lab", "labs", "ai", "tech"]):
            return "startup"
        else:
            return "unknown"
    
    def get_best_performing_subjects(self, limit: int = 10) -> List[Dict]:
        """Get best performing subjects by reply rate"""
        from app.models import PerformanceMetric
        
        metrics = self.db.query(PerformanceMetric).filter(
            PerformanceMetric.dimension_type == "subject",
            PerformanceMetric.total_sent >= 5  # Minimum sample size
        ).order_by(PerformanceMetric.reply_rate.desc()).limit(limit).all()
        
        return [
            {
                "subject": metric.dimension_value,
                "total_sent": metric.total_sent,
                "total_replies": metric.total_replies,
                "reply_rate": metric.reply_rate,
                "trend": metric.trend_direction
            }
            for metric in metrics
        ]
    
    def get_best_company_types(self, limit: int = 10) -> List[Dict]:
        """Get best performing company types"""
        from app.models import PerformanceMetric
        
        metrics = self.db.query(PerformanceMetric).filter(
            PerformanceMetric.dimension_type == "company_type",
            PerformanceMetric.total_sent >= 10
        ).order_by(PerformanceMetric.reply_rate.desc()).limit(limit).all()
        
        return [
            {
                "company_type": metric.dimension_value,
                "total_sent": metric.total_sent,
                "total_replies": metric.total_replies,
                "reply_rate": metric.reply_rate
            }
            for metric in metrics
        ]
    
    def get_worst_performing_subjects(self, limit: int = 10) -> List[Dict]:
        """Get worst performing subjects"""
        from app.models import PerformanceMetric
        
        metrics = self.db.query(PerformanceMetric).filter(
            PerformanceMetric.dimension_type == "subject",
            PerformanceMetric.total_sent >= 5
        ).order_by(PerformanceMetric.reply_rate.asc()).limit(limit).all()
        
        return [
            {
                "subject": metric.dimension_value,
                "total_sent": metric.total_sent,
                "total_replies": metric.total_replies,
                "reply_rate": metric.reply_rate
            }
            for metric in metrics
        ]
    
    def generate_optimization_recommendations(self) -> Dict:
        """Generate recommendations based on performance data"""
        best_subjects = self.get_best_performing_subjects(5)
        worst_subjects = self.get_worst_performing_subjects(5)
        best_company_types = self.get_best_company_types(5)
        
        recommendations = {
            "subject_optimization": [],
            "targeting_optimization": [],
            "overall_health": "good"
        }
        
        # Subject recommendations
        if best_subjects:
            top_subject = best_subjects[0]
            recommendations["subject_optimization"].append(
                f"Use subject pattern similar to: '{top_subject['subject']}' (reply rate: {top_subject['reply_rate']}%)"
            )
        
        if worst_subjects:
            worst_subject = worst_subjects[0]
            recommendations["subject_optimization"].append(
                f"Avoid subject pattern: '{worst_subject['subject']}' (reply rate: {worst_subject['reply_rate']}%)"
            )
        
        # Targeting recommendations
        if best_company_types:
            best_type = best_company_types[0]
            recommendations["targeting_optimization"].append(
                f"Focus more on {best_type['company_type']} companies (reply rate: {best_type['reply_rate']}%)"
            )
        
        # Overall health assessment
        overall_reply_rate = self._calculate_overall_reply_rate()
        if overall_reply_rate < 10:
            recommendations["overall_health"] = "critical"
            recommendations["subject_optimization"].insert(0, "URGENT: Reply rate below 10% - review entire strategy")
        elif overall_reply_rate < 20:
            recommendations["overall_health"] = "needs_improvement"
            recommendations["subject_optimization"].insert(0, "Reply rate below 20% - consider A/B testing")
        
        return recommendations
    
    def _calculate_overall_reply_rate(self) -> float:
        """Calculate overall system reply rate"""
        total_sent = self.db.query(OutboundMessage).filter(
            OutboundMessage.status == 'sent'
        ).count()
        
        total_replied = self.db.query(Reply).count()
        
        if total_sent == 0:
            return 0
        
        return (total_replied / total_sent) * 100
    
    def calculate_trends(self, days: int = 7):
        """Calculate performance trends over time"""
        from app.models import PerformanceMetric
        
        # This would compare current period to previous period
        # For now, simplified implementation
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        metrics = self.db.query(PerformanceMetric).filter(
            PerformanceMetric.calculated_at >= start_date
        ).all()
        
        for metric in metrics:
            if metric.reply_rate > 30:
                metric.trend_direction = "improving"
            elif metric.reply_rate < 10:
                metric.trend_direction = "declining"
            else:
                metric.trend_direction = "stable"
        
        self.db.commit()
    
    def get_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        overall_reply_rate = self._calculate_overall_reply_rate()
        best_subjects = self.get_best_performing_subjects(5)
        best_company_types = self.get_best_company_types(5)
        recommendations = self.generate_optimization_recommendations()
        
        return {
            "overall_reply_rate": round(overall_reply_rate, 2),
            "total_sent": self.db.query(OutboundMessage).filter(
                OutboundMessage.status == 'sent'
            ).count(),
            "total_replied": self.db.query(Reply).count(),
            "best_performing_subjects": best_subjects,
            "best_company_types": best_company_types,
            "recommendations": recommendations,
            "generated_at": datetime.utcnow().isoformat()
        }
