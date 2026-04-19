"""
Buyer Management Service for B2B Matchmaking Platform

Handles CRUD operations for buyer companies (companies looking for services).
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Optional
from datetime import datetime
import uuid

from app.models import BuyerCompany, Match


class BuyerManagementService:
    """Manage buyer companies on the platform"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_buyer(
        self,
        company_name: str,
        requirements: List[str],
        decision_maker_email: str = None,
        decision_maker_name: str = None,
        decision_maker_title: str = None,
        website: str = None,
        industry: str = None,
        employee_count: int = None,
        funding_stage: str = None,
        total_funding: str = None,
        budget_range: str = None,
        timeline: str = "exploring",
        signals: List[str] = None,
        verified: bool = False
    ) -> BuyerCompany:
        """Create a new buyer company"""
        
        buyer = BuyerCompany(
            buyer_id=f"buyer-{str(uuid.uuid4())[:8]}",
            company_name=company_name,
            website=website,
            industry=industry,
            employee_count=employee_count,
            funding_stage=funding_stage,
            total_funding=total_funding,
            requirements=requirements,
            budget_range=budget_range,
            timeline=timeline,
            signals=signals or [],
            decision_maker_name=decision_maker_name,
            decision_maker_title=decision_maker_title,
            decision_maker_email=decision_maker_email,
            verified=verified,
            active=True
        )
        
        self.db.add(buyer)
        self.db.commit()
        self.db.refresh(buyer)
        
        return buyer
    
    def get_buyer(self, buyer_id: str) -> Optional[BuyerCompany]:
        """Get buyer by ID"""
        return self.db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == buyer_id
        ).first()
    
    def get_buyer_by_company_name(self, company_name: str) -> Optional[BuyerCompany]:
        """Get buyer by company name (case-insensitive)"""
        return self.db.query(BuyerCompany).filter(
            func.lower(BuyerCompany.company_name) == func.lower(company_name)
        ).first()
    
    def list_buyers(
        self,
        active_only: bool = True,
        verified_only: bool = False,
        industry: str = None,
        funding_stage: str = None,
        timeline: str = None,
        has_requirements: bool = None,
        search: str = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict:
        """List buyers with filters"""
        
        query = self.db.query(BuyerCompany)
        
        if active_only:
            query = query.filter(BuyerCompany.active == True)
        
        if verified_only:
            query = query.filter(BuyerCompany.verified == True)
        
        if industry:
            query = query.filter(
                func.lower(BuyerCompany.industry) == func.lower(industry)
            )
        
        if funding_stage:
            query = query.filter(
                func.lower(BuyerCompany.funding_stage) == func.lower(funding_stage)
            )
        
        if timeline:
            query = query.filter(
                func.lower(BuyerCompany.timeline) == func.lower(timeline)
            )
        
        if has_requirements is True:
            # Filter for buyers with non-empty requirements
            query = query.filter(BuyerCompany.requirements.isnot(None))
        
        if search:
            search_lower = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(BuyerCompany.company_name).like(search_lower),
                    func.lower(BuyerCompany.industry).like(search_lower)
                )
            )
        
        total = query.count()
        buyers = query.offset((page - 1) * page_size).limit(page_size).all()
        
        results = []
        for buyer in buyers:
            # Count matches for this buyer
            match_count = self.db.query(Match).filter(
                Match.buyer_id == buyer.buyer_id
            ).count()
            
            results.append({
                "buyer_id": buyer.buyer_id,
                "company_name": buyer.company_name,
                "website": buyer.website,
                "industry": buyer.industry,
                "employee_count": buyer.employee_count,
                "funding_stage": buyer.funding_stage,
                "requirements": buyer.requirements,
                "timeline": buyer.timeline,
                "signals": buyer.signals[:5] if buyer.signals else [],  # Limit signals
                "verified": buyer.verified,
                "active": buyer.active,
                "match_count": match_count,
                "created_at": buyer.created_at.isoformat() if buyer.created_at else None
            })
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "buyers": results
        }
    
    def update_buyer(
        self,
        buyer_id: str,
        **kwargs
    ) -> Optional[BuyerCompany]:
        """Update buyer fields"""
        
        buyer = self.get_buyer(buyer_id)
        if not buyer:
            return None
        
        allowed_fields = [
            "company_name", "website", "industry", "employee_count",
            "funding_stage", "total_funding", "requirements", "budget_range",
            "timeline", "signals", "decision_maker_name", "decision_maker_title",
            "decision_maker_email", "verified", "active"
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(buyer, field):
                setattr(buyer, field, value)
        
        self.db.commit()
        self.db.refresh(buyer)
        
        return buyer
    
    def delete_buyer(self, buyer_id: str) -> bool:
        """Soft delete a buyer (mark inactive)"""
        
        buyer = self.get_buyer(buyer_id)
        if not buyer:
            return False
        
        buyer.active = False
        self.db.commit()
        
        return True
    
    def verify_buyer(self, buyer_id: str) -> Optional[BuyerCompany]:
        """Mark a buyer as verified"""
        
        buyer = self.get_buyer(buyer_id)
        if not buyer:
            return None
        
        buyer.verified = True
        self.db.commit()
        self.db.refresh(buyer)
        
        return buyer
    
    def get_buyer_details(self, buyer_id: str) -> Optional[Dict]:
        """Get full buyer details with matches"""
        
        buyer = self.get_buyer(buyer_id)
        if not buyer:
            return None
        
        # Get matches
        matches = self.db.query(Match).filter(
            Match.buyer_id == buyer_id
        ).all()
        
        return {
            "buyer_id": buyer.buyer_id,
            "company_name": buyer.company_name,
            "website": buyer.website,
            "industry": buyer.industry,
            "employee_count": buyer.employee_count,
            "funding_stage": buyer.funding_stage,
            "total_funding": buyer.total_funding,
            "requirements": buyer.requirements,
            "budget_range": buyer.budget_range,
            "timeline": buyer.timeline,
            "signals": buyer.signals,
            "decision_maker": {
                "name": buyer.decision_maker_name,
                "title": buyer.decision_maker_title,
                "email": buyer.decision_maker_email
            },
            "verified": buyer.verified,
            "active": buyer.active,
            "created_at": buyer.created_at.isoformat() if buyer.created_at else None,
            "matches": [
                {
                    "match_id": m.match_id,
                    "provider_id": m.provider_id,
                    "provider_name": m.provider.company_name if m.provider else None,
                    "score": m.match_score,
                    "status": m.status,
                    "intro_sent_at": m.intro_sent_at.isoformat() if m.intro_sent_at else None,
                    "meeting_booked": m.meeting_booked_at is not None
                }
                for m in matches
            ]
        }
    
    def get_buyer_stats(self, buyer_id: str) -> Optional[Dict]:
        """Get statistics for a buyer"""
        
        buyer = self.get_buyer(buyer_id)
        if not buyer:
            return None
        
        matches = self.db.query(Match).filter(
            Match.buyer_id == buyer_id
        ).all()
        
        total_matches = len(matches)
        intro_sent = sum(1 for m in matches if m.intro_sent_at)
        meeting_booked = sum(1 for m in matches if m.meeting_booked_at)
        closed_won = sum(1 for m in matches if m.status == "closed_won")
        
        return {
            "buyer_id": buyer.buyer_id,
            "company_name": buyer.company_name,
            "total_matches": total_matches,
            "intros_received": intro_sent,
            "meetings_booked": meeting_booked,
            "deals_closed": closed_won,
            "conversion_rate": round((meeting_booked / intro_sent * 100), 1) if intro_sent > 0 else 0,
            "verified": buyer.verified
        }
    
    def find_buyers_by_requirement(
        self,
        requirement: str,
        verified_only: bool = True,
        limit: int = 50
    ) -> List[Dict]:
        """Find buyers by specific requirement keyword"""
        
        query = self.db.query(BuyerCompany).filter(
            BuyerCompany.active == True
        )
        
        if verified_only:
            query = query.filter(BuyerCompany.verified == True)
        
        # Filter for buyers with this requirement
        requirement_lower = requirement.lower()
        all_buyers = query.all()
        
        matching_buyers = []
        for buyer in all_buyers:
            if buyer.requirements:
                if any(requirement_lower in req.lower() for req in buyer.requirements):
                    matching_buyers.append(buyer)
        
        # Return limited results
        results = []
        for buyer in matching_buyers[:limit]:
            results.append({
                "buyer_id": buyer.buyer_id,
                "company_name": buyer.company_name,
                "requirements": buyer.requirements,
                "funding_stage": buyer.funding_stage,
                "timeline": buyer.timeline
            })
        
        return results
    
    def import_from_lead(
        self,
        lead_id: str,
        requirements: List[str] = None,
        budget_range: str = None,
        timeline: str = "exploring"
    ) -> Optional[BuyerCompany]:
        """Convert an existing Lead to a BuyerCompany"""
        
        from app.models import Lead
        
        lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return None
        
        # Check if already exists
        existing = self.get_buyer_by_company_name(lead.company)
        if existing:
            return existing
        
        # Extract signals from lead
        signals = []
        if lead.signal:
            signal_lower = lead.signal.lower()
            if any(word in signal_lower for word in ["fund", "raise", "series", "invest"]):
                signals.append("recent_funding")
            if any(word in signal_lower for word in ["hiring", "job", "career"]):
                signals.append("hiring")
        
        # Parse employee count if available
        employee_count = None
        if lead.signal:
            # Try to extract employee count from signal
            import re
            emp_match = re.search(r'(\d+)\s*(?:employees?|people|staff)', lead.signal.lower())
            if emp_match:
                employee_count = int(emp_match.group(1))
        
        buyer = BuyerCompany(
            buyer_id=f"buyer-{str(uuid.uuid4())[:8]}",
            company_name=lead.company,
            website=lead.website,
            requirements=requirements or ["general_services"],
            budget_range=budget_range,
            timeline=timeline,
            signals=signals,
            decision_maker_name=lead.decision_maker,
            verified=False,  # Requires manual verification
            active=True
        )
        
        self.db.add(buyer)
        self.db.commit()
        self.db.refresh(buyer)
        
        return buyer
    
    def bulk_import_buyers(
        self,
        buyers_data: List[Dict],
        auto_verify: bool = False
    ) -> Dict:
        """Bulk import buyers from list"""
        
        created = []
        skipped = []
        errors = []
        
        for data in buyers_data:
            try:
                # Check for duplicate
                existing = self.get_buyer_by_company_name(data.get("company_name"))
                if existing:
                    skipped.append({
                        "company": data.get("company_name"),
                        "reason": "Duplicate"
                    })
                    continue
                
                buyer = self.create_buyer(
                    company_name=data["company_name"],
                    requirements=data.get("requirements", []),
                    website=data.get("website"),
                    industry=data.get("industry"),
                    employee_count=data.get("employee_count"),
                    funding_stage=data.get("funding_stage"),
                    total_funding=data.get("total_funding"),
                    budget_range=data.get("budget_range"),
                    timeline=data.get("timeline", "exploring"),
                    signals=data.get("signals", []),
                    decision_maker_email=data.get("decision_maker_email"),
                    decision_maker_name=data.get("decision_maker_name"),
                    decision_maker_title=data.get("decision_maker_title"),
                    verified=auto_verify
                )
                
                created.append({
                    "buyer_id": buyer.buyer_id,
                    "company_name": buyer.company_name
                })
                
            except Exception as e:
                errors.append({
                    "company": data.get("company_name"),
                    "error": str(e)
                })
        
        return {
            "total_submitted": len(buyers_data),
            "created": len(created),
            "skipped": len(skipped),
            "errors": len(errors),
            "created_buyers": created,
            "skipped_buyers": skipped[:10],
            "error_details": errors[:10]
        }
    
    def get_buyer_pipeline_summary(self) -> Dict:
        """Get summary of all buyers in pipeline"""
        
        total_buyers = self.db.query(BuyerCompany).filter(
            BuyerCompany.active == True
        ).count()
        
        verified_buyers = self.db.query(BuyerCompany).filter(
            and_(
                BuyerCompany.active == True,
                BuyerCompany.verified == True
            )
        ).count()
        
        # By timeline
        timeline_counts = {}
        for timeline in ["immediate", "3_months", "6_months", "exploring"]:
            count = self.db.query(BuyerCompany).filter(
                and_(
                    BuyerCompany.active == True,
                    BuyerCompany.timeline == timeline
                )
            ).count()
            timeline_counts[timeline] = count
        
        # By funding stage
        funding_counts = {}
        for stage in ["seed", "series_a", "series_b", "series_c", "late_stage", "bootstrapped"]:
            count = self.db.query(BuyerCompany).filter(
                and_(
                    BuyerCompany.active == True,
                    BuyerCompany.funding_stage == stage
                )
            ).count()
            if count > 0:
                funding_counts[stage] = count
        
        return {
            "total_active": total_buyers,
            "verified": verified_buyers,
            "unverified": total_buyers - verified_buyers,
            "by_timeline": timeline_counts,
            "by_funding_stage": funding_counts
        }
