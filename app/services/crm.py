import logging
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from app.models import Lead, PipelineState, Deal
from datetime import datetime, date
import uuid

logger = logging.getLogger(__name__)


class CRMLayer:
    """Internal CRM logic for deal tracking, ROI measurement, multi-client scaling"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_deal(self, lead_id: str, deal_name: str, deal_value: float, deal_stage: str = "prospecting") -> Dict:
        """Create a new deal for a lead"""
        deal = Deal(
            deal_id=f"deal-{str(uuid.uuid4())[:8]}",
            lead_id=lead_id,
            deal_name=deal_name,
            deal_value=deal_value,
            deal_stage=deal_stage,
            win_probability=self._calculate_initial_probability(deal_stage),
            owner_type="system",
            status="open"
        )
        
        self.db.add(deal)
        self.db.commit()
        
        logger.info(f"Created deal {deal.deal_id} for lead {lead_id}")
        
        return {
            "deal_id": deal.deal_id,
            "lead_id": lead_id,
            "deal_name": deal_name,
            "deal_value": deal_value,
            "deal_stage": deal_stage
        }
    
    def _calculate_initial_probability(self, deal_stage: str) -> int:
        """Calculate initial win probability based on stage"""
        stage_probabilities = {
            "prospecting": 10,
            "qualification": 20,
            "needs_analysis": 30,
            "value_proposition": 40,
            "proposal": 50,
            "negotiation": 70,
            "closing": 85
        }
        return stage_probabilities.get(deal_stage, 10)
    
    def update_deal_stage(self, deal_id: str, new_stage: str, probability: int = None) -> Dict:
        """Update deal stage and probability"""
        deal = self.db.query(Deal).filter(Deal.deal_id == deal_id).first()
        
        if not deal:
            return {"error": "Deal not found"}
        
        deal.deal_stage = new_stage
        if probability:
            deal.win_probability = probability
        else:
            deal.win_probability = self._calculate_initial_probability(new_stage)
        
        self.db.commit()
        
        logger.info(f"Updated deal {deal_id} to stage {new_stage}")
        
        return {
            "deal_id": deal_id,
            "new_stage": new_stage,
            "win_probability": deal.win_probability
        }
    
    def close_deal(self, deal_id: str, won: bool, deal_value: float = None, lost_reason: str = None) -> Dict:
        """Close a deal as won or lost"""
        deal = self.db.query(Deal).filter(Deal.deal_id == deal_id).first()
        
        if not deal:
            return {"error": "Deal not found"}
        
        deal.status = "won" if won else "lost"
        deal.actual_close_date = date.today()
        
        if won and deal_value:
            deal.deal_value = deal_value
        
        if not won and lost_reason:
            deal.lost_reason = lost_reason
        
        # Update pipeline state
        if won:
            from app.services.pipeline_state_machine import PipelineStateMachine
            pipeline = PipelineStateMachine(self.db)
            pipeline.transition(deal.lead_id, "CLOSED", {"reason": "deal_won"})
        else:
            from app.services.pipeline_state_machine import PipelineStateMachine
            pipeline = PipelineStateMachine(self.db)
            pipeline.transition(deal.lead_id, "LOST", {"reason": f"deal_lost: {lost_reason}"})
        
        self.db.commit()
        
        logger.info(f"Closed deal {deal_id} as {'won' if won else 'lost'}")
        
        return {
            "deal_id": deal_id,
            "status": deal.status,
            "actual_close_date": deal.actual_close_date.isoformat()
        }
    
    def get_deal(self, deal_id: str) -> Dict:
        """Get deal details"""
        deal = self.db.query(Deal).filter(Deal.deal_id == deal_id).first()
        
        if not deal:
            return {"error": "Deal not found"}
        
        return {
            "deal_id": deal.deal_id,
            "lead_id": deal.lead_id,
            "deal_name": deal.deal_name,
            "deal_value": float(deal.deal_value) if deal.deal_value else 0,
            "deal_stage": deal.deal_stage,
            "win_probability": deal.win_probability,
            "expected_close_date": deal.expected_close_date.isoformat() if deal.expected_close_date else None,
            "actual_close_date": deal.actual_close_date.isoformat() if deal.actual_close_date else None,
            "owner_type": deal.owner_type,
            "owner_id": deal.owner_id,
            "status": deal.status,
            "lost_reason": deal.lost_reason
        }
    
    def get_deals_by_lead(self, lead_id: str) -> List[Dict]:
        """Get all deals for a lead"""
        deals = self.db.query(Deal).filter(Deal.lead_id == lead_id).all()
        
        return [self.get_deal(deal.deal_id) for deal in deals]
    
    def get_pipeline_value(self) -> Dict:
        """Calculate total pipeline value"""
        open_deals = self.db.query(Deal).filter(Deal.status == "open").all()
        
        total_value = sum(float(deal.deal_value) if deal.deal_value else 0 for deal in open_deals)
        
        # Weighted value by probability
        weighted_value = sum(
            (float(deal.deal_value) if deal.deal_value else 0) * (deal.win_probability / 100)
            for deal in open_deals
        )
        
        # By stage
        by_stage = {}
        for deal in open_deals:
            stage = deal.deal_stage
            if stage not in by_stage:
                by_stage[stage] = {"count": 0, "value": 0}
            by_stage[stage]["count"] += 1
            by_stage[stage]["value"] += float(deal.deal_value) if deal.deal_value else 0
        
        return {
            "total_deals": len(open_deals),
            "total_value": round(total_value, 2),
            "weighted_value": round(weighted_value, 2),
            "by_stage": by_stage
        }
    
    def get_roi_metrics(self, days: int = 90) -> Dict:
        """Calculate ROI metrics"""
        from datetime import timedelta
        from app.models import LeadScore, OutboundMessage
        
        cutoff_date = date.today() - timedelta(days=days)
        
        # Total leads contacted
        leads_contacted = self.db.query(OutboundMessage).filter(
            OutboundMessage.sent_at >= cutoff_date
        ).distinct(OutboundMessage.lead_id).count()
        
        # Deals won in period
        deals_won = self.db.query(Deal).filter(
            Deal.status == "won",
            Deal.actual_close_date >= cutoff_date
        ).all()
        
        total_revenue = sum(float(deal.deal_value) if deal.deal_value else 0 for deal in deals_won)
        
        # Deals lost
        deals_lost = self.db.query(Deal).filter(
            Deal.status == "lost",
            Deal.actual_close_date >= cutoff_date
        ).count()
        
        # Conversion rates
        conversion_rate = (len(deals_won) / leads_contacted * 100) if leads_contacted > 0 else 0
        win_rate = (len(deals_won) / (len(deals_won) + deals_lost) * 100) if (len(deals_won) + deals_lost) > 0 else 0
        
        return {
            "period_days": days,
            "leads_contacted": leads_contacted,
            "deals_won": len(deals_won),
            "deals_lost": deals_lost,
            "total_revenue": round(total_revenue, 2),
            "conversion_rate": round(conversion_rate, 2),
            "win_rate": round(win_rate, 2)
        }
    
    def get_deal_velocity(self, days: int = 30) -> Dict:
        """Calculate deal velocity metrics"""
        from datetime import timedelta
        
        cutoff_date = date.today() - timedelta(days=days)
        
        deals_closed = self.db.query(Deal).filter(
            Deal.actual_close_date >= cutoff_date,
            Deal.status.in_(["won", "lost"])
        ).all()
        
        if not deals_closed:
            return {"average_days_to_close": 0, "total_closed": 0}
        
        total_days = 0
        for deal in deals_closed:
            if deal.source_message_id:
                from app.models import OutboundMessage
                message = self.db.query(OutboundMessage).filter(
                    OutboundMessage.message_id == deal.source_message_id
                ).first()
                if message and message.sent_at:
                    days_to_close = (deal.actual_close_date - message.sent_at.date()).days
                    total_days += days_to_close
        
        average_days = total_days / len(deals_closed) if deals_closed else 0
        
        return {
            "period_days": days,
            "total_closed": len(deals_closed),
            "average_days_to_close": round(average_days, 1)
        }
    
    def assign_to_human(self, deal_id: str, human_id: str):
        """Assign deal to human owner"""
        deal = self.db.query(Deal).filter(Deal.deal_id == deal_id).first()
        
        if deal:
            deal.owner_id = human_id
            deal.owner_type = "human"
            self.db.commit()
            
            logger.info(f"Assigned deal {deal_id} to human {human_id}")
            
            return {"success": True, "deal_id": deal_id, "owner_id": human_id}
        
        return {"error": "Deal not found"}
    
    def get_deals_by_owner(self, owner_id: str) -> List[Dict]:
        """Get deals by owner (human or system)"""
        deals = self.db.query(Deal).filter(Deal.owner_id == owner_id).all()
        
        return [self.get_deal(deal.deal_id) for deal in deals]
    
    def auto_create_deal_on_interest(self, lead_id: str):
        """Auto-create deal when lead shows interest"""
        # Check if deal already exists
        existing = self.db.query(Deal).filter(
            Deal.lead_id == lead_id,
            Deal.status == "open"
        ).first()
        
        if existing:
            return {"message": "Deal already exists"}
        
        lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return {"error": "Lead not found"}
        
        # Estimate deal value based on company size (simplified)
        from app.models import LeadScore
        lead_score = self.db.query(LeadScore).filter(LeadScore.lead_id == lead_id).first()
        
        estimated_value = 10000  # Default
        if lead_score and lead_score.priority_score >= 80:
            estimated_value = 50000
        elif lead_score and lead_score.priority_score >= 60:
            estimated_value = 25000
        
        return self.create_deal(
            lead_id=lead_id,
            deal_name=f"{lead.company} - Opportunity",
            deal_value=estimated_value,
            deal_stage="qualification"
        )
