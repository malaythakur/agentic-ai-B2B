"""Tiered Batch Automation Service"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models import Lead, OutboundMessage, CampaignRun, PipelineState
from app.logging_config import logger as app_logger
from app.services.ai_lead_scoring import AILeadScoringService

logger = app_logger


class TieredAutomationService:
    """Service for tiered batch automation based on lead scoring"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_scorer = AILeadScoringService(db)
    
    def classify_leads_by_tier(self, lead_ids: List[str]) -> Dict:
        """Classify leads into tiers based on scoring"""
        results = {
            "tier_1": {"auto_send": [], "count": 0},
            "tier_2": {"queued": [], "count": 0},
            "tier_3": {"manual_approval": [], "count": 0}
        }
        
        for lead_id in lead_ids:
            lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
            if not lead:
                continue
            
            # Score the lead
            scoring_result = self.ai_scorer.score_lead(lead)
            tier = scoring_result["tier"]
            
            # Update lead status based on tier
            if tier == "Tier 1":
                lead.status = "auto_send_ready"
                results["tier_1"]["auto_send"].append({
                    "lead_id": lead_id,
                    "company": lead.company,
                    "score": scoring_result["total_score"],
                    "reason": scoring_result["qualification_reason"]
                })
                results["tier_1"]["count"] += 1
                
            elif tier == "Tier 2":
                lead.status = "queued_for_review"
                results["tier_2"]["queued"].append({
                    "lead_id": lead_id,
                    "company": lead.company,
                    "score": scoring_result["total_score"],
                    "reason": scoring_result["qualification_reason"]
                })
                results["tier_2"]["count"] += 1
                
            else:  # Tier 3
                lead.status = "manual_approval_required"
                results["tier_3"]["manual_approval"].append({
                    "lead_id": lead_id,
                    "company": lead.company,
                    "score": scoring_result["total_score"],
                    "reason": scoring_result["qualification_reason"]
                })
                results["tier_3"]["count"] += 1
        
        self.db.commit()
        return results
    
    def process_tier_1_batch(
        self,
        from_email: str,
        max_leads: int = 50
    ) -> Dict:
        """Auto-send Tier 1 leads immediately"""
        # Get Tier 1 leads
        tier_1_leads = self.db.query(Lead).filter(
            Lead.status == "auto_send_ready",
            Lead.fit_score >= 85
        ).limit(max_leads).all()
        
        if not tier_1_leads:
            return {"status": "no_leads", "message": "No Tier 1 leads ready for auto-send"}
        
        # Create campaign run
        run_id = f"auto-tier1-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        campaign_run = CampaignRun(
            run_id=run_id,
            name=f"Auto Tier 1 Batch - {datetime.utcnow().strftime('%Y-%m-%d')}",
            status="in_progress",
            total_leads=len(tier_1_leads)
        )
        self.db.add(campaign_run)
        
        # Generate and queue messages for sending
        messages_created = 0
        for lead in tier_1_leads:
            # This would call the message generation service
            # For now, create placeholder outbound messages
            message = OutboundMessage(
                message_id=f"msg-{lead.lead_id}-{run_id}",
                run_id=run_id,
                lead_id=lead.lead_id,
                subject="[Auto] Outreach regarding your recent activity",
                body="Personalized message would go here",
                to_email=f"contact@{lead.website.replace('https://', '')}" if lead.website else "unknown@example.com",
                from_email=from_email,
                status="queued",
                personalization_method="auto_tier1"
            )
            self.db.add(message)
            messages_created += 1
            
            # Update lead status
            lead.status = "outbound_queued"
        
        self.db.commit()
        
        logger.info(f"Tier 1 auto-send batch created: {messages_created} messages")
        
        return {
            "status": "success",
            "run_id": run_id,
            "messages_created": messages_created,
            "leads_processed": len(tier_1_leads),
            "next_action": "send_batch"
        }
    
    def process_tier_2_review_queue(self, limit: int = 100) -> Dict:
        """Process Tier 2 queued leads for review"""
        tier_2_leads = self.db.query(Lead).filter(
            Lead.status == "queued_for_review",
            Lead.fit_score >= 70
        ).limit(limit).all()
        
        review_items = []
        for lead in tier_2_leads:
            scoring_result = self.ai_scorer.score_lead(lead)
            review_items.append({
                "lead_id": lead.lead_id,
                "company": lead.company,
                "score": scoring_result["total_score"],
                "tier": scoring_result["tier"],
                "qualification_reason": scoring_result["qualification_reason"],
                "signal": lead.signal,
                "decision_maker": lead.decision_maker,
                "website": lead.website,
                "recommended_action": "approve" if scoring_result["total_score"] >= 75 else "review"
            })
        
        return {
            "total_queued": len(tier_2_leads),
            "review_items": review_items,
            "auto_approve_count": len([i for i in review_items if i["recommended_action"] == "approve"]),
            "manual_review_count": len([i for i in review_items if i["recommended_action"] == "review"])
        }
    
    def approve_tier_2_leads(
        self,
        lead_ids: List[str],
        from_email: str
    ) -> Dict:
        """Approve and send Tier 2 leads"""
        run_id = f"tier2-approved-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Create campaign run
        campaign_run = CampaignRun(
            run_id=run_id,
            name=f"Tier 2 Approved Batch - {datetime.utcnow().strftime('%Y-%m-%d')}",
            status="in_progress",
            total_leads=len(lead_ids)
        )
        self.db.add(campaign_run)
        
        messages_created = 0
        for lead_id in lead_ids:
            lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
            if not lead:
                continue
            
            # Create outbound message
            message = OutboundMessage(
                message_id=f"msg-{lead_id}-{run_id}",
                run_id=run_id,
                lead_id=lead_id,
                subject="[Approved] Outreach",
                body="Personalized message",
                to_email=f"contact@{lead.website.replace('https://', '')}" if lead.website else "unknown@example.com",
                from_email=from_email,
                status="queued",
                personalization_method="tier2_approved"
            )
            self.db.add(message)
            messages_created += 1
            
            lead.status = "outbound_queued"
        
        self.db.commit()
        
        return {
            "status": "success",
            "run_id": run_id,
            "messages_created": messages_created
        }
    
    def get_tier_3_manual_review_list(self, limit: int = 50) -> Dict:
        """Get Tier 3 leads requiring manual approval"""
        tier_3_leads = self.db.query(Lead).filter(
            Lead.status == "manual_approval_required"
        ).limit(limit).all()
        
        review_list = []
        for lead in tier_3_leads:
            scoring_result = self.ai_scorer.score_lead(lead)
            review_list.append({
                "lead_id": lead.lead_id,
                "company": lead.company,
                "score": scoring_result["total_score"],
                "weak_areas": [k for k, v in scoring_result["breakdown"].items() if v < 60],
                "signal": lead.signal,
                "recommendation": "reject" if scoring_result["total_score"] < 50 else "consider"
            })
        
        return {
            "total": len(tier_3_leads),
            "review_list": review_list
        }
    
    def auto_promote_tier_2_to_tier_1(self) -> Dict:
        """Automatically promote Tier 2 leads that have improved to Tier 1"""
        # Find Tier 2 leads with updated signals that now score as Tier 1
        tier_2_leads = self.db.query(Lead).filter(
            Lead.status == "queued_for_review"
        ).all()
        
        promoted = []
        for lead in tier_2_leads:
            scoring_result = self.ai_scorer.score_lead(lead)
            if scoring_result["tier"] == "Tier 1":
                lead.status = "auto_send_ready"
                lead.fit_score = int(scoring_result["total_score"])
                promoted.append({
                    "lead_id": lead.lead_id,
                    "company": lead.company,
                    "new_score": scoring_result["total_score"]
                })
        
        if promoted:
            self.db.commit()
            logger.info(f"Promoted {len(promoted)} leads from Tier 2 to Tier 1")
        
        return {
            "promoted_count": len(promoted),
            "promoted_leads": promoted
        }
    
    def get_automation_stats(self) -> Dict:
        """Get statistics on tiered automation"""
        stats = {
            "tier_1": self.db.query(Lead).filter(Lead.status == "auto_send_ready").count(),
            "tier_2": self.db.query(Lead).filter(Lead.status == "queued_for_review").count(),
            "tier_3": self.db.query(Lead).filter(Lead.status == "manual_approval_required").count(),
            "outbound_queued": self.db.query(Lead).filter(Lead.status == "outbound_queued").count(),
            "total_leads": self.db.query(Lead).count()
        }
        
        # Calculate percentages
        if stats["total_leads"] > 0:
            stats["tier_1_percent"] = round(stats["tier_1"] / stats["total_leads"] * 100, 2)
            stats["tier_2_percent"] = round(stats["tier_2"] / stats["total_leads"] * 100, 2)
            stats["tier_3_percent"] = round(stats["tier_3"] / stats["total_leads"] * 100, 2)
        else:
            stats["tier_1_percent"] = 0
            stats["tier_2_percent"] = 0
            stats["tier_3_percent"] = 0
        
        return stats
    
    def run_daily_automation_cycle(self, from_email: str, auto_approve_tier2: bool = True) -> Dict:
        """Run the complete daily automation cycle"""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "steps": []
        }
        
        # Step 1: Auto-promote Tier 2 to Tier 1
        promotion_result = self.auto_promote_tier_2_to_tier_1()
        results["steps"].append({
            "step": "promote_tier2_to_tier1",
            "result": promotion_result
        })
        
        # Step 2: Process Tier 1 auto-send
        tier1_result = self.process_tier_1_batch(from_email)
        results["steps"].append({
            "step": "process_tier1_batch",
            "result": tier1_result
        })
        
        # Step 3: Get Tier 2 review queue and auto-approve if enabled
        tier2_review = self.process_tier_2_review_queue()
        results["steps"].append({
            "step": "tier2_review_queue",
            "result": tier2_review
        })
        
        # Auto-approve Tier 2 leads
        if auto_approve_tier2 and tier2_review["total_queued"] > 0:
            auto_approve_lead_ids = [item["lead_id"] for item in tier2_review["review_items"]]
            if auto_approve_lead_ids:
                approval_result = self.approve_tier_2_leads(auto_approve_lead_ids, from_email)
                results["steps"].append({
                    "step": "auto_approve_tier2",
                    "result": approval_result
                })
        
        # Step 4: Get stats
        stats = self.get_automation_stats()
        results["steps"].append({
            "step": "automation_stats",
            "result": stats
        })
        
        logger.info("Daily automation cycle completed")
        return results
