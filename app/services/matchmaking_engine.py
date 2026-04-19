"""
Matchmaking Engine for B2B Platform

AI-powered matching between service providers and buyer companies.
Calculates fit scores based on service fit, company size, timing, budget, and signals.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid
import json

from app.models import ServiceProvider, BuyerCompany, Match, ProviderSubscription


class MatchmakingEngine:
    """AI-powered matching engine for B2B platform"""
    
    # Scoring weights for different fit dimensions
    WEIGHTS = {
        "service_fit": 0.35,
        "size_fit": 0.20,
        "timing_fit": 0.15,
        "budget_fit": 0.15,
        "signal_fit": 0.15
    }
    
    # Minimum score to consider a match viable
    MIN_MATCH_SCORE = 70
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_match_score(
        self, 
        provider: ServiceProvider, 
        buyer: BuyerCompany
    ) -> Tuple[int, Dict[str, int], str]:
        """
        Calculate match score between provider and buyer
        
        Returns:
            (total_score, score_breakdown, match_reason)
        """
        scores = {}
        reasons = []
        
        # 1. Service Fit (35% weight)
        scores["service_fit"] = self._score_service_fit(provider, buyer, reasons)
        
        # 2. Company Size Fit (20% weight)
        scores["size_fit"] = self._score_size_fit(provider, buyer, reasons)
        
        # 3. Timing Fit (15% weight)
        scores["timing_fit"] = self._score_timing_fit(provider, buyer, reasons)
        
        # 4. Budget Fit (15% weight)
        scores["budget_fit"] = self._score_budget_fit(provider, buyer, reasons)
        
        # 5. Signal Fit (15% weight)
        scores["signal_fit"] = self._score_signal_fit(provider, buyer, reasons)
        
        # Calculate weighted total
        total_score = sum(
            scores[key] * self.WEIGHTS[key] 
            for key in scores
        )
        
        # Generate match reason
        match_reason = self._generate_match_reason(provider, buyer, scores, reasons)
        
        return round(total_score), scores, match_reason
    
    def _score_service_fit(
        self, 
        provider: ServiceProvider, 
        buyer: BuyerCompany,
        reasons: List[str]
    ) -> int:
        """Score how well provider's services match buyer's needs"""
        provider_services = set(s.lower() for s in (provider.services or []))
        buyer_requirements = set(r.lower() for r in (buyer.requirements or []))
        
        if not buyer_requirements:
            return 50  # Neutral if no requirements specified
        
        if not provider_services:
            return 30  # Low if provider has no services listed
        
        # Service keyword mappings
        service_mappings = {
            "cloud_migration": ["aws migration", "azure migration", "gcp migration", "cloud strategy"],
            "devops": ["devops", "ci/cd", "infrastructure", "sre"],
            "security": ["security", "penetration testing", "compliance", "soc2", "hipaa"],
            "data": ["data engineering", "etl", "data pipeline", "analytics"],
            "marketing": ["performance marketing", "seo", "content", "pr"],
            "sales": ["sales automation", "crm", "outbound", "sdr"],
            "hr": ["recruiting", "talent acquisition", "hr consulting"]
        }
        
        matches = 0
        matched_services = []
        
        for req in buyer_requirements:
            req_lower = req.lower()
            mapped_services = service_mappings.get(req_lower, [req_lower])
            
            for service in provider_services:
                if any(mapped in service or service in mapped for mapped in mapped_services):
                    matches += 1
                    matched_services.append(service)
                    break
        
        score = min(100, int((matches / len(buyer_requirements)) * 100))
        
        if score >= 80:
            reasons.append(f"Strong service alignment: {', '.join(set(matched_services))}")
        elif score >= 50:
            reasons.append(f"Partial service match: {', '.join(set(matched_services))}")
        
        return score
    
    def _score_size_fit(
        self, 
        provider: ServiceProvider, 
        buyer: BuyerCompany,
        reasons: List[str]
    ) -> int:
        """Score company size alignment with provider's ICP"""
        icp = provider.icp_criteria or {}
        target_size = icp.get("employees", "")
        buyer_size = buyer.employee_count
        
        if not target_size or not buyer_size:
            return 70  # Default if unknown
        
        # Parse size ranges
        size_ranges = {
            "1-10": (1, 10),
            "11-50": (11, 50),
            "51-200": (51, 200),
            "201-500": (201, 500),
            "501-1000": (501, 1000),
            "1000+": (1000, 100000)
        }
        
        # Get target range
        target_min, target_max = size_ranges.get(target_size, (0, 100000))
        
        if target_min <= buyer_size <= target_max:
            reasons.append(f"Company size ({buyer_size}) fits ICP ({target_size})")
            return 95
        
        # Check adjacent ranges
        size_order = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
        if target_size in size_order:
            target_idx = size_order.index(target_size)
            for i, size_key in enumerate(size_order):
                if size_key in str(buyer_size) or (size_ranges[size_key][0] <= buyer_size <= size_ranges[size_key][1]):
                    if abs(i - target_idx) == 1:
                        reasons.append(f"Company size ({buyer_size}) is close to ICP ({target_size})")
                        return 75
        
        return 40
    
    def _score_timing_fit(
        self, 
        provider: ServiceProvider, 
        buyer: BuyerCompany,
        reasons: List[str]
    ) -> int:
        """Score urgency/timing alignment"""
        timeline = buyer.timeline or "exploring"
        
        # Urgency scoring
        urgency_scores = {
            "immediate": 100,
            "3_months": 80,
            "6_months": 60,
            "exploring": 40
        }
        
        score = urgency_scores.get(timeline, 50)
        
        if timeline in ["immediate", "3_months"]:
            reasons.append(f"High urgency: {timeline} timeline")
        
        return score
    
    def _score_budget_fit(
        self, 
        provider: ServiceProvider, 
        buyer: BuyerCompany,
        reasons: List[str]
    ) -> int:
        """Score budget alignment"""
        budget = buyer.budget_range or ""
        
        if not budget:
            return 70  # Neutral if unknown
        
        # Check if budget indicates capacity to pay
        if any(indicator in budget.lower() for indicator in ["$50k", "$100k", "$500k", "$1m", "million"]):
            reasons.append(f"Strong budget indicator: {budget}")
            return 90
        elif any(indicator in budget.lower() for indicator in ["$10k", "$25k", "$30k"]):
            reasons.append(f"Moderate budget: {budget}")
            return 75
        elif "unknown" in budget.lower() or "tbd" in budget.lower():
            return 50
        
        return 60
    
    def _score_signal_fit(
        self, 
        provider: ServiceProvider, 
        buyer: BuyerCompany,
        reasons: List[str]
    ) -> int:
        """Score how well buyer's signals match provider's ICP signals"""
        icp = provider.icp_criteria or {}
        target_signals = set(s.lower() for s in icp.get("signals", []))
        buyer_signals = set(s.lower() for s in (buyer.signals or []))
        
        if not target_signals:
            return 70  # Neutral if provider has no target signals
        
        if not buyer_signals:
            return 50  # Lower if no signals
        
        # Signal keyword mappings
        signal_mappings = {
            "recent_funding": ["funding", "raised", "series", "seed", "investment"],
            "hiring_engineers": ["hiring", "devops", "sre", "engineer", "developer"],
            "hiring_sales": ["hiring", "sdr", "ae", "sales", "account executive"],
            "expansion": ["expansion", "new market", "growing", "scaling"],
            "product_launch": ["launch", "product", "release", "new feature"],
            "tech_debt": ["legacy", "migration", "modernization", "upgrade"]
        }
        
        matches = 0
        matched_signals = []
        
        for target in target_signals:
            mapped_keywords = signal_mappings.get(target, [target])
            
            for buyer_signal in buyer_signals:
                if any(keyword in buyer_signal for keyword in mapped_keywords):
                    matches += 1
                    matched_signals.append(buyer_signal)
                    break
        
        score = min(100, int((matches / max(len(target_signals), 1)) * 100))
        
        if score >= 70:
            reasons.append(f"Strong signal match: {', '.join(set(matched_signals))}")
        
        return score
    
    def _generate_match_reason(
        self,
        provider: ServiceProvider,
        buyer: BuyerCompany,
        scores: Dict[str, int],
        reasons: List[str]
    ) -> str:
        """Generate human-readable explanation of the match"""
        parts = [
            f"Match between {provider.company_name} and {buyer.company_name}:",
            f"",
            f"Overall fit score: {sum(scores.values()) / len(scores):.0f}/100",
            f"",
            f"Score breakdown:",
            f"- Service fit: {scores['service_fit']}% (provider offers {', '.join(provider.services or [])})",
            f"- Size fit: {scores['size_fit']}% (buyer: {buyer.employee_count or 'unknown'} employees)",
            f"- Timing: {scores['timing_fit']}% (timeline: {buyer.timeline or 'exploring'})",
            f"- Budget: {scores['budget_fit']}% (range: {buyer.budget_range or 'unknown'})",
            f"- Signals: {scores['signal_fit']}%",
            f""
        ]
        
        if reasons:
            parts.append("Key matching factors:")
            for reason in reasons[:5]:  # Limit to top 5
                parts.append(f"- {reason}")
        
        return "\n".join(parts)
    
    def find_matches_for_buyer(
        self, 
        buyer: BuyerCompany, 
        min_score: int = None,
        limit: int = 10
    ) -> List[Dict]:
        """Find best matching providers for a buyer"""
        min_score = min_score or self.MIN_MATCH_SCORE
        
        # Get active providers
        providers = self.db.query(ServiceProvider).filter(
            ServiceProvider.active == True
        ).all()
        
        matches = []
        
        for provider in providers:
            score, breakdown, reason = self.calculate_match_score(provider, buyer)
            
            if score >= min_score:
                matches.append({
                    "provider": provider,
                    "score": score,
                    "breakdown": breakdown,
                    "reason": reason
                })
        
        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        return matches[:limit]
    
    def find_matches_for_provider(
        self, 
        provider: ServiceProvider, 
        min_score: int = None,
        limit: int = 10
    ) -> List[Dict]:
        """Find best matching buyers for a provider"""
        min_score = min_score or self.MIN_MATCH_SCORE
        
        # Get active, verified buyers
        buyers = self.db.query(BuyerCompany).filter(
            and_(
                BuyerCompany.active == True,
                BuyerCompany.verified == True
            )
        ).all()
        
        matches = []
        
        for buyer in buyers:
            score, breakdown, reason = self.calculate_match_score(provider, buyer)
            
            if score >= min_score:
                matches.append({
                    "buyer": buyer,
                    "score": score,
                    "breakdown": breakdown,
                    "reason": reason
                })
        
        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        return matches[:limit]
    
    def create_match(
        self,
        provider_id: str,
        buyer_id: str,
        auto_approve: bool = False
    ) -> Optional[Match]:
        """Create a match record after calculating score"""
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        buyer = self.db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == buyer_id
        ).first()
        
        if not provider or not buyer:
            return None
        
        # Check if match already exists
        existing = self.db.query(Match).filter(
            and_(
                Match.provider_id == provider_id,
                Match.buyer_id == buyer_id
            )
        ).first()
        
        if existing:
            return existing
        
        # Calculate score
        score, breakdown, reason = self.calculate_match_score(provider, buyer)
        
        # Create match
        match = Match(
            match_id=f"match-{str(uuid.uuid4())[:8]}",
            provider_id=provider_id,
            buyer_id=buyer_id,
            match_score=score,
            score_breakdown=breakdown,
            match_reason=reason,
            status="approved" if auto_approve else "pending",
            provider_approved=auto_approve
        )
        
        self.db.add(match)
        self.db.commit()
        self.db.refresh(match)
        
        return match
    
    def auto_match_all(
        self,
        min_score: int = None,
        limit_per_buyer: int = 3
    ) -> Dict:
        """Automatically create matches for all active buyers"""
        min_score = min_score or self.MIN_MATCH_SCORE
        
        buyers = self.db.query(BuyerCompany).filter(
            and_(
                BuyerCompany.active == True,
                BuyerCompany.verified == True
            )
        ).all()
        
        results = {
            "total_buyers": len(buyers),
            "matches_created": 0,
            "matches_skipped": 0,
            "errors": []
        }
        
        for buyer in buyers:
            try:
                top_matches = self.find_matches_for_buyer(buyer, min_score, limit_per_buyer)
                
                for match_data in top_matches:
                    provider = match_data["provider"]
                    
                    # Check for existing match
                    existing = self.db.query(Match).filter(
                        and_(
                            Match.provider_id == provider.provider_id,
                            Match.buyer_id == buyer.buyer_id
                        )
                    ).first()
                    
                    if existing:
                        results["matches_skipped"] += 1
                        continue
                    
                    # Create new match (auto-approve high scores)
                    match = Match(
                        match_id=f"match-{str(uuid.uuid4())[:8]}",
                        provider_id=provider.provider_id,
                        buyer_id=buyer.buyer_id,
                        match_score=match_data["score"],
                        score_breakdown=match_data["breakdown"],
                        match_reason=match_data["reason"],
                        status="approved" if match_data["score"] >= 85 else "pending",
                        provider_approved=match_data["score"] >= 85
                    )
                    
                    self.db.add(match)
                    results["matches_created"] += 1
                
            except Exception as e:
                results["errors"].append(f"Error matching buyer {buyer.buyer_id}: {str(e)}")
        
        self.db.commit()
        
        return results
    
    def get_match_details(self, match_id: str) -> Optional[Dict]:
        """Get full match details with provider and buyer info"""
        match = self.db.query(Match).filter(Match.match_id == match_id).first()
        
        if not match:
            return None
        
        return {
            "match_id": match.match_id,
            "score": match.match_score,
            "status": match.status,
            "score_breakdown": match.score_breakdown,
            "match_reason": match.match_reason,
            "created_at": match.created_at.isoformat() if match.created_at else None,
            "provider": {
                "provider_id": match.provider.provider_id,
                "company_name": match.provider.company_name,
                "services": match.provider.services,
                "contact_email": match.provider.contact_email
            },
            "buyer": {
                "buyer_id": match.buyer.buyer_id,
                "company_name": match.buyer.company_name,
                "requirements": match.buyer.requirements,
                "signals": match.buyer.signals,
                "decision_maker": {
                    "name": match.buyer.decision_maker_name,
                    "title": match.buyer.decision_maker_title,
                    "email": match.buyer.decision_maker_email
                }
            },
            "meeting": {
                "booked_at": match.meeting_booked_at.isoformat() if match.meeting_booked_at else None,
                "date": match.meeting_date.isoformat() if match.meeting_date else None,
                "status": match.meeting_status
            } if match.meeting_booked_at else None
        }
    
    def approve_match(self, match_id: str) -> Optional[Match]:
        """Provider approves a pending match"""
        match = self.db.query(Match).filter(Match.match_id == match_id).first()
        
        if not match:
            return None
        
        match.status = "approved"
        match.provider_approved = True
        
        self.db.commit()
        self.db.refresh(match)
        
        return match
    
    def reject_match(self, match_id: str, reason: str = None) -> Optional[Match]:
        """Provider rejects a match"""
        match = self.db.query(Match).filter(Match.match_id == match_id).first()
        
        if not match:
            return None
        
        match.status = "rejected"
        
        # Add rejection reason to match_reason
        if reason:
            match.match_reason += f"\n\nREJECTED: {reason}"
        
        self.db.commit()
        self.db.refresh(match)
        
        return match
    
    def get_provider_match_stats(self, provider_id: str) -> Dict:
        """Get match statistics for a provider"""
        matches = self.db.query(Match).filter(
            Match.provider_id == provider_id
        ).all()
        
        total = len(matches)
        pending = sum(1 for m in matches if m.status == "pending")
        approved = sum(1 for m in matches if m.status == "approved")
        intro_sent = sum(1 for m in matches if m.status == "intro_sent")
        meeting_booked = sum(1 for m in matches if m.status == "meeting_booked")
        closed_won = sum(1 for m in matches if m.status == "closed_won")
        closed_lost = sum(1 for m in matches if m.status == "closed_lost")
        
        avg_score = sum(m.match_score for m in matches) / total if total > 0 else 0
        
        return {
            "total_matches": total,
            "by_status": {
                "pending": pending,
                "approved": approved,
                "intro_sent": intro_sent,
                "meeting_booked": meeting_booked,
                "closed_won": closed_won,
                "closed_lost": closed_lost
            },
            "average_match_score": round(avg_score, 1),
            "conversion_rate": round((meeting_booked / intro_sent * 100), 1) if intro_sent > 0 else 0
        }
