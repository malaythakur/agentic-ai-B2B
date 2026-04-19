"""
Prospect Scoring Service

Scores and ranks prospects based on multiple factors:
- Fit score (how well they match target criteria)
- Readiness score (how ready they are to engage)
- Value score (potential deal value/revenue)
- Urgency score (time sensitivity)
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProspectScoringService:
    """Service for scoring and ranking prospects"""
    
    def __init__(self):
        """Initialize prospect scoring service"""
        self.weights = {
            "fit_score": 0.3,
            "readiness_score": 0.3,
            "value_score": 0.25,
            "urgency_score": 0.15
        }
    
    def calculate_fit_score(
        self,
        prospect: Dict,
        target_criteria: Dict
    ) -> Dict:
        """
        Calculate how well prospect fits target criteria
        
        Args:
            prospect: Prospect data with enrichment
            target_criteria: Target criteria (tech stack, industry, etc.)
            
        Returns:
            Score dict with breakdown
        """
        score = 0
        reasons = []
        
        # Tech stack match
        target_tech = target_criteria.get("tech_stack", [])
        prospect_tech = prospect.get("tech_stack", [])
        
        if target_tech and prospect_tech:
            matches = len(set(target_tech) & set(prospect_tech))
            tech_score = min(100, (matches / len(target_tech)) * 100)
            score += tech_score * 0.35
            reasons.append(f"Tech stack match: {matches}/{len(target_tech)} technologies")
        
        # Industry match
        target_industries = target_criteria.get("industries", [])
        prospect_industry = prospect.get("industry") or prospect.get("ai_analysis", {}).get("industry")
        
        if target_industries and prospect_industry:
            if prospect_industry.lower() in [i.lower() for i in target_industries]:
                score += 30
                reasons.append(f"Industry match: {prospect_industry}")
        
        # Company size match
        target_size = target_criteria.get("employee_count_range")
        prospect_size = prospect.get("employee_count")
        
        if target_size and prospect_size:
            # Parse range like "50-200"
            try:
                min_size, max_size = map(int, target_size.split("-"))
                if min_size <= prospect_size <= max_size:
                    score += 25
                    reasons.append(f"Company size match: {prospect_size} employees")
            except:
                pass
        
        # AI analysis fit
        ai_analysis = prospect.get("ai_analysis", {})
        if ai_analysis:
            confidence = ai_analysis.get("confidence", 0)
            score += confidence * 10
            reasons.append(f"AI confidence: {confidence}")
        
        return {
            "score": min(100, int(score)),
            "breakdown": {
                "tech_stack_match": reasons[0] if len(reasons) > 0 else "N/A",
                "industry_match": reasons[1] if len(reasons) > 1 else "N/A",
                "size_match": reasons[2] if len(reasons) > 2 else "N/A"
            },
            "reasons": reasons
        }
    
    def calculate_readiness_score(self, prospect: Dict) -> Dict:
        """
        Calculate how ready prospect is to engage
        
        Args:
            prospect: Prospect data with enrichment
            
        Returns:
            Score dict with breakdown
        """
        score = 0
        reasons = []
        
        # Funding signals
        funding_signals = prospect.get("funding_signals", {})
        if funding_signals.get("latest_round"):
            score += 30
            latest_round = funding_signals["latest_round"]
            reasons.append(f"Recent funding: {latest_round.get('type')} ${latest_round.get('amount', 0):,}")
        
        # Hiring signals
        hiring_signals = prospect.get("hiring_signals", [])
        if hiring_signals:
            score += min(30, len(hiring_signals) * 10)
            reasons.append(f"Hiring signals: {len(hiring_signals)} detected")
        
        # GitHub activity
        github_activity = prospect.get("github_activity", {})
        if github_activity.get("commits", 0) > 10:
            score += 20
            reasons.append(f"Active development: {github_activity.get('commits')} commits")
        
        # Growth signals
        signals = prospect.get("signals", [])
        growth_signals = [s for s in signals if s.get("type") in ["growth", "expansion"]]
        if growth_signals:
            score += min(20, len(growth_signals) * 10)
            reasons.append(f"Growth signals: {len(growth_signals)} detected")
        
        # Stage classification
        stage = prospect.get("stage_classification", {})
        if stage.get("stage") in ["series_b", "series_c", "growth"]:
            score += 15
            reasons.append(f"Growth stage: {stage.get('stage')}")
        
        return {
            "score": min(100, int(score)),
            "breakdown": {
                "funding": 30 if funding_signals.get("latest_round") else 0,
                "hiring": min(30, len(hiring_signals) * 10),
                "activity": 20 if github_activity.get("commits", 0) > 10 else 0,
                "growth": min(20, len(growth_signals) * 10),
                "stage": 15 if stage.get("stage") in ["series_b", "series_c", "growth"] else 0
            },
            "reasons": reasons
        }
    
    def calculate_value_score(self, prospect: Dict) -> Dict:
        """
        Calculate potential deal value
        
        Args:
            prospect: Prospect data with enrichment
            
        Returns:
            Score dict with breakdown
        """
        score = 0
        reasons = []
        
        # Revenue range
        value_signals = prospect.get("value_signals", {})
        revenue_range = value_signals.get("estimated_revenue_range", "")
        
        revenue_scores = {
            "pre-revenue": 10,
            "<$1M": 20,
            "$1M-$10M": 40,
            "$10M-$50M": 60,
            "$50M-$100M": 80,
            ">$100M": 100
        }
        
        if revenue_range in revenue_scores:
            score += revenue_scores[revenue_range]
            reasons.append(f"Revenue: {revenue_range}")
        
        # Deal size estimate
        deal_size = value_signals.get("deal_size_estimate", "")
        if "100K" in deal_size or "200K" in deal_size:
            score += 20
            reasons.append(f"High deal size: {deal_size}")
        elif "50K" in deal_size:
            score += 15
            reasons.append(f"Medium deal size: {deal_size}")
        
        # Company size (correlates with deal size)
        employee_count = prospect.get("employee_count", 0)
        if employee_count > 1000:
            score += 30
            reasons.append(f"Enterprise: {employee_count} employees")
        elif employee_count > 200:
            score += 20
            reasons.append(f"Mid-market: {employee_count} employees")
        elif employee_count > 50:
            score += 10
            reasons.append(f"SMB: {employee_count} employees")
        
        # Funding amount
        funding_signals = prospect.get("funding_signals", {})
        total_funding = funding_signals.get("total_funding", 0)
        if total_funding > 50000000:  # >$50M
            score += 25
            reasons.append(f"Well-funded: ${total_funding:,}")
        elif total_funding > 10000000:  # >$10M
            score += 15
            reasons.append(f"Funded: ${total_funding:,}")
        
        return {
            "score": min(100, int(score)),
            "breakdown": {
                "revenue": revenue_scores.get(revenue_range, 0),
                "deal_size": 20 if "100K" in deal_size or "200K" in deal_size else (15 if "50K" in deal_size else 0),
                "company_size": 30 if employee_count > 1000 else (20 if employee_count > 200 else (10 if employee_count > 50 else 0)),
                "funding": 25 if total_funding > 50000000 else (15 if total_funding > 10000000 else 0)
            },
            "reasons": reasons,
            "estimated_deal_size": deal_size
        }
    
    def calculate_urgency_score(self, prospect: Dict) -> Dict:
        """
        Calculate time sensitivity/urgency
        
        Args:
            prospect: Prospect data with enrichment
            
        Returns:
            Score dict with breakdown
        """
        score = 0
        reasons = []
        
        # Recent funding (indicates urgency to spend)
        funding_signals = prospect.get("funding_signals", {})
        latest_round_date = funding_signals.get("latest_round_date")
        
        if latest_round_date:
            try:
                round_date = datetime.fromisoformat(latest_round_date.replace("Z", "+00:00"))
                days_since = (datetime.utcnow() - round_date).days
                
                if days_since < 30:
                    score += 40
                    reasons.append(f"Very recent funding: {days_since} days ago")
                elif days_since < 90:
                    score += 30
                    reasons.append(f"Recent funding: {days_since} days ago")
                elif days_since < 180:
                    score += 20
                    reasons.append(f"Funding: {days_since} days ago")
            except:
                pass
        
        # Hiring signals (indicates growth/urgency)
        hiring_signals = prospect.get("hiring_signals", [])
        if hiring_signals:
            score += 30
            reasons.append(f"Actively hiring: {len(hiring_signals)} signals")
        
        # Budget readiness
        value_signals = prospect.get("value_signals", {})
        budget_readiness = value_signals.get("budget_readiness", 0)
        score += budget_readiness * 0.3
        reasons.append(f"Budget readiness: {budget_readiness}")
        
        # Urgency from AI analysis
        signals = prospect.get("signals", [])
        urgent_signals = [s for s in signals if "urgent" in str(s).lower() or "asap" in str(s).lower()]
        if urgent_signals:
            score += 20
            reasons.append(f"Urgent signals: {len(urgent_signals)}")
        
        return {
            "score": min(100, int(score)),
            "breakdown": {
                "recent_funding": 40 if latest_round_date and days_since < 30 else (30 if latest_round_date and days_since < 90 else 0),
                "hiring": 30 if hiring_signals else 0,
                "budget_readiness": budget_readiness * 0.3,
                "urgent_signals": 20 if urgent_signals else 0
            },
            "reasons": reasons
        }
    
    def calculate_overall_score(
        self,
        prospect: Dict,
        target_criteria: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate overall prospect score
        
        Args:
            prospect: Prospect data with enrichment
            target_criteria: Optional target criteria for fit scoring
            
        Returns:
            Overall score dict with all components
        """
        # Calculate component scores
        fit_score = self.calculate_fit_score(prospect, target_criteria or {})
        readiness_score = self.calculate_readiness_score(prospect)
        value_score = self.calculate_value_score(prospect)
        urgency_score = self.calculate_urgency_score(prospect)
        
        # Calculate weighted overall score
        overall = (
            fit_score["score"] * self.weights["fit_score"] +
            readiness_score["score"] * self.weights["readiness_score"] +
            value_score["score"] * self.weights["value_score"] +
            urgency_score["score"] * self.weights["urgency_score"]
        )
        
        return {
            "overall_score": int(overall),
            "fit_score": fit_score,
            "readiness_score": readiness_score,
            "value_score": value_score,
            "urgency_score": urgency_score,
            "weights": self.weights,
            "scored_at": datetime.utcnow().isoformat()
        }
    
    def rank_prospects(
        self,
        prospects: List[Dict],
        target_criteria: Optional[Dict] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Score and rank prospects
        
        Args:
            prospects: List of prospect dicts
            target_criteria: Optional target criteria
            limit: Maximum results to return
            
        Returns:
            Ranked list of prospects with scores
        """
        logger.info(f"Ranking {len(prospects)} prospects")
        
        scored_prospects = []
        for prospect in prospects:
            try:
                score_data = self.calculate_overall_score(prospect, target_criteria)
                prospect["score_data"] = score_data
                scored_prospects.append(prospect)
            except Exception as e:
                logger.error(f"Error scoring prospect: {e}")
                continue
        
        # Sort by overall score (descending)
        scored_prospects.sort(
            key=lambda x: x["score_data"]["overall_score"],
            reverse=True
        )
        
        logger.info(f"Ranked {len(scored_prospects)} prospects")
        return scored_prospects[:limit]
    
    def get_top_prospects(
        self,
        prospects: List[Dict],
        target_criteria: Optional[Dict] = None,
        min_score: int = 60,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get top prospects above minimum score threshold
        
        Args:
            prospects: List of prospect dicts
            target_criteria: Optional target criteria
            min_score: Minimum overall score
            limit: Maximum results
            
        Returns:
            List of top prospects
        """
        ranked = self.rank_prospects(prospects, target_criteria, limit * 2)
        
        top_prospects = [
            p for p in ranked
            if p["score_data"]["overall_score"] >= min_score
        ]
        
        return top_prospects[:limit]


# Example usage
if __name__ == "__main__":
    service = ProspectScoringService()
    
    # Example prospect
    prospect = {
        "company_name": "TechCo",
        "industry": "SaaS",
        "tech_stack": ["react", "python", "kubernetes"],
        "employee_count": 150,
        "funding_signals": {
            "total_funding": 25000000,
            "latest_round": {"type": "series_b", "amount": 15000000},
            "latest_round_date": "2026-01-15T00:00:00Z"
        },
        "hiring_signals": [
            {"type": "hiring", "confidence": 0.8}
        ],
        "github_activity": {
            "commits": 50,
            "issues_opened": 10
        },
        "value_signals": {
            "estimated_revenue_range": "$10M-$50M",
            "deal_size_estimate": "$50K-$100K",
            "budget_readiness": 70
        },
        "signals": [
            {"type": "growth", "value": "expanding to new markets"}
        ],
        "stage_classification": {
            "stage": "series_b"
        }
    }
    
    target_criteria = {
        "tech_stack": ["react", "kubernetes"],
        "industries": ["SaaS", "Fintech"],
        "employee_count_range": "50-200"
    }
    
    score = service.calculate_overall_score(prospect, target_criteria)
    print(f"Overall score: {score['overall_score']}/100")
    print(f"Fit: {score['fit_score']['score']}")
    print(f"Readiness: {score['readiness_score']['score']}")
    print(f"Value: {score['value_score']['score']}")
    print(f"Urgency: {score['urgency_score']['score']}")
