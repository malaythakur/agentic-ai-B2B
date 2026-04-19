import re
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models import Lead
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class LeadQualificationEngine:
    """Multi-dimensional lead scoring and qualification engine"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def score_lead(self, lead: Lead) -> Dict:
        """Score a lead across multiple dimensions"""
        scores = {
            "signal_strength": self._score_signal_strength(lead),
            "hiring_intensity": self._score_hiring_intensity(lead),
            "funding_stage": self._score_funding_stage(lead),
            "company_size_fit": self._score_company_size_fit(lead),
            "market_relevance": self._score_market_relevance(lead)
        }
        
        # Compute weighted priority score
        weights = {
            "signal_strength": 0.25,
            "hiring_intensity": 0.20,
            "funding_stage": 0.20,
            "company_size_fit": 0.15,
            "market_relevance": 0.20
        }
        
        priority_score = sum(scores[dim] * weights[dim] for dim in scores)
        
        # Determine qualification
        is_qualified = priority_score >= 50
        disqualification_reason = None
        
        if not is_qualified:
            disqualification_reason = self._get_disqualification_reason(scores)
        
        return {
            "lead_id": lead.lead_id,
            "dimension_scores": scores,
            "priority_score": round(priority_score, 2),
            "is_qualified": is_qualified,
            "disqualification_reason": disqualification_reason,
            "recommended_action": self._get_recommended_action(priority_score),
            "timing_preference": self._get_timing_preference(scores)
        }
    
    def _score_signal_strength(self, lead: Lead) -> int:
        """Score signal strength (0-100)"""
        if not lead.signal:
            return 0
        
        score = 0
        signal_lower = lead.signal.lower()
        
        # High-value signal keywords
        high_value_signals = [
            "launched", "product launch", "new product", "released",
            "hiring", "recruiting", "open role", "job opening",
            "funding", "raised", "series", "investment", "venture",
            "acquired", "merger", "ipo"
        ]
        
        for signal in high_value_signals:
            if signal in signal_lower:
                score += 20
        
        # Signal specificity
        if len(lead.signal) > 200:
            score += 10
        
        # Recency indicators
        if any(word in signal_lower for word in ["recent", "just", "announced", "today"]):
            score += 15
        
        # Multiple signals
        signal_count = len(re.findall(r'[,.]', lead.signal))
        score += min(signal_count * 5, 15)
        
        return min(score, 100)
    
    def _score_hiring_intensity(self, lead: Lead) -> int:
        """Score hiring intensity (0-100)"""
        if not lead.signal:
            return 0
        
        score = 0
        signal_lower = lead.signal.lower()
        
        # Hiring role indicators
        sales_roles = ["sdr", "sales", "account executive", "business development", "bdr"]
        leadership_roles = ["manager", "director", "vp", "head of", "chief"]
        
        for role in sales_roles:
            if role in signal_lower:
                score += 25
        
        for role in leadership_roles:
            if role in signal_lower:
                score += 20
        
        # Multiple hiring signals
        hiring_count = signal_lower.count("hiring") + signal_lower.count("role")
        score += min(hiring_count * 10, 20)
        
        # Urgency indicators
        if any(word in signal_lower for word in ["urgently", "immediately", "asap"]):
            score += 15
        
        return min(score, 100)
    
    def _score_funding_stage(self, lead: Lead) -> int:
        """Score funding stage (0-100)"""
        if not lead.signal:
            return 0
        
        score = 0
        signal_lower = lead.signal.lower()
        
        # Funding stages with weights
        funding_stages = {
            "series a": 90,
            "series b": 85,
            "series c": 80,
            "series d": 75,
            "seed": 70,
            "angel": 60,
            "pre-seed": 50,
            "series a+": 88,
            "series b+": 83
        }
        
        for stage, points in funding_stages.items():
            if stage in signal_lower:
                score = max(score, points)
                break
        
        # Funding amount indicators
        if re.search(r'\$\d+[mM]', signal_lower):
            score += 10
        
        return min(score, 100)
    
    def _score_company_size_fit(self, lead: Lead) -> int:
        """Score company size fit (0-100)"""
        score = 50  # Default mid-score
        
        # If we have explicit company size data
        if hasattr(lead, 'company_size') and lead.company_size:
            size_mapping = {
                "1-10": 40,
                "11-50": 60,
                "51-200": 80,
                "201-500": 90,
                "500+": 70
            }
            score = size_mapping.get(lead.company_size, 50)
        
        # Infer from signal
        if lead.signal:
            signal_lower = lead.signal.lower()
            
            # Startup indicators
            if any(word in signal_lower for word in ["startup", "founded", "early stage"]):
                score = 70
            
            # Enterprise indicators
            if any(word in signal_lower for word in ["enterprise", "fortune", "public company"]):
                score = 85
        
        return score
    
    def _score_market_relevance(self, lead: int) -> int:
        """Score market relevance (0-100)"""
        # This would integrate with external market data
        # For now, return a default score
        return 60
    
    def _get_disqualification_reason(self, scores: Dict) -> Optional[str]:
        """Determine why a lead is disqualified"""
        if scores["signal_strength"] < 20:
            return "Weak signal - insufficient company activity"
        if scores["hiring_intensity"] < 20:
            return "Low hiring intensity - not in growth mode"
        if scores["funding_stage"] < 30:
            return "Early funding stage - limited budget"
        if scores["company_size_fit"] < 40:
            return "Company size mismatch - not ideal fit"
        if scores["market_relevance"] < 40:
            return "Low market relevance - not in target segment"
        return "Overall score below threshold"
    
    def _get_recommended_action(self, priority_score: float) -> str:
        """Get recommended action based on priority score"""
        if priority_score >= 80:
            return "Send immediately - high priority"
        elif priority_score >= 60:
            return "Send within 24 hours"
        elif priority_score >= 40:
            return "Queue for next batch"
        else:
            return "Do not contact - low priority"
    
    def _get_timing_preference(self, scores: Dict) -> str:
        """Get timing preference based on scores"""
        if scores["hiring_intensity"] >= 70:
            return "Urgent - hiring now"
        elif scores["funding_stage"] >= 70:
            return "Within 1-2 weeks - post-funding window"
        else:
            return "Standard timing"
    
    def batch_score_leads(self, lead_ids: list = None) -> Dict:
        """Score multiple leads in batch"""
        if lead_ids is None:
            leads = self.db.query(Lead).all()
        else:
            leads = self.db.query(Lead).filter(Lead.lead_id.in_(lead_ids)).all()
        
        results = {
            "total": len(leads),
            "qualified": 0,
            "disqualified": 0,
            "scores": []
        }
        
        for lead in leads:
            score_result = self.score_lead(lead)
            results["scores"].append(score_result)
            
            if score_result["is_qualified"]:
                results["qualified"] += 1
            else:
                results["disqualified"] += 1
        
        # Save scores to database
        self._save_scores_to_db(results["scores"])
        
        return results
    
    def _save_scores_to_db(self, scores: list):
        """Save lead scores to database"""
        from app.models import LeadScore
        
        for score_data in scores:
            existing = self.db.query(LeadScore).filter(
                LeadScore.lead_id == score_data["lead_id"]
            ).first()
            
            score_record = {
                "lead_id": score_data["lead_id"],
                "signal_strength": score_data["dimension_scores"]["signal_strength"],
                "hiring_intensity": score_data["dimension_scores"]["hiring_intensity"],
                "funding_stage": score_data["dimension_scores"]["funding_stage"],
                "company_size_fit": score_data["dimension_scores"]["company_size_fit"],
                "market_relevance": score_data["dimension_scores"]["market_relevance"],
                "priority_score": score_data["priority_score"],
                "is_qualified": score_data["is_qualified"],
                "disqualification_reason": score_data["disqualification_reason"],
                "qualified_at": datetime.utcnow() if score_data["is_qualified"] else None
            }
            
            if existing:
                for key, value in score_record.items():
                    setattr(existing, key, value)
            else:
                score_record["score_id"] = f"score-{str(uuid.uuid4())[:8]}"
                new_score = LeadScore(**score_record)
                self.db.add(new_score)
        
        self.db.commit()
    
    def get_qualified_leads(self, min_priority_score: int = 50, limit: int = 100) -> list:
        """Get qualified leads for outreach"""
        from app.models import LeadScore
        
        qualified = self.db.query(LeadScore).filter(
            LeadScore.is_qualified == True,
            LeadScore.priority_score >= min_priority_score
        ).order_by(LeadScore.priority_score.desc()).limit(limit).all()
        
        return qualified
