import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models import Lead
import uuid

logger = logging.getLogger(__name__)


class OfferMatchingEngine:
    """Signal to offer strategy mapping engine"""
    
    def __init__(self, db: Session):
        self.db = db
        self.strategies = self._load_default_strategies()
    
    def _load_default_strategies(self) -> list:
        """Load default offer strategies"""
        return [
            {
                "signal_type": "hiring_sdr",
                "signal_keywords": ["hiring", "sdr", "sales development", "bdr", "business development"],
                "offer_angle": "Pipeline acceleration - help your new SDRs hit quota faster",
                "message_style": "direct_metric",
                "cta_type": "demo_request"
            },
            {
                "signal_type": "funding_series_a",
                "signal_keywords": ["series a", "$10m", "$15m", "$20m", "funded", "raised"],
                "offer_angle": "GTM scaling - scale your go-to-market with the new capital",
                "message_style": "growth_focused",
                "cta_type": "strategy_call"
            },
            {
                "signal_type": "funding_series_b",
                "signal_keywords": ["series b", "$50m", "$40m", "$30m", "growth"],
                "offer_angle": "Enterprise expansion - break into enterprise accounts",
                "message_style": "enterprise_focused",
                "cta_type": "consultation"
            },
            {
                "signal_type": "product_launch",
                "signal_keywords": ["launched", "product launch", "new product", "released"],
                "offer_angle": "Conversion optimization - convert launch traffic into pipeline",
                "message_style": "curiosity_driven",
                "cta_type": "quick_chat"
            },
            {
                "signal_type": "high_growth",
                "signal_keywords": ["10x", "100%", "rapid growth", "scaling fast", "growing"],
                "offer_angle": "Sustainable growth - maintain momentum without breaking",
                "message_style": "problem_awareness",
                "cta_type": "exploration"
            },
            {
                "signal_type": "hiring_leadership",
                "signal_keywords": ["hiring", "manager", "director", "vp", "head of", "chief"],
                "offer_angle": "Team productivity - make your new hires productive faster",
                "message_style": "leadership_focused",
                "cta_type": "best_practices"
            }
        ]
    
    def match_offer(self, lead: Lead) -> Dict:
        """Match lead signal to best offer strategy"""
        signal_text = lead.signal.lower() if lead.signal else ""
        
        best_match = None
        best_match_score = 0
        
        for strategy in self.strategies:
            score = self._calculate_match_score(signal_text, strategy)
            
            if score > best_match_score:
                best_match_score = score
                best_match = strategy
        
        if not best_match:
            # Default strategy
            best_match = {
                "signal_type": "default",
                "signal_keywords": [],
                "offer_angle": "General pipeline improvement - let's discuss your current challenges",
                "message_style": "conversational",
                "cta_type": "intro_call"
            }
        
        result = {
            "lead_id": lead.lead_id,
            "matched_strategy": best_match["signal_type"],
            "offer_angle": best_match["offer_angle"],
            "message_style": best_match["message_style"],
            "cta_type": best_match["cta_type"],
            "match_score": best_match_score,
            "personalization_notes": self._generate_personalization_notes(lead, best_match)
        }
        
        # Save to database
        self._save_offer_match(result)
        
        return result
    
    def _calculate_match_score(self, signal_text: str, strategy: Dict) -> int:
        """Calculate how well signal matches strategy"""
        score = 0
        keywords = strategy["signal_keywords"]
        
        for keyword in keywords:
            if keyword.lower() in signal_text:
                score += 20
        
        # Bonus for multiple keyword matches
        if score >= 40:
            score += 10
        
        return min(score, 100)
    
    def _generate_personalization_notes(self, lead: Lead, strategy: Dict) -> str:
        """Generate notes for message personalization"""
        notes = []
        
        if lead.decision_maker:
            notes.append(f"Address {lead.decision_maker}")
        
        if lead.company:
            notes.append(f"Reference {lead.company}")
        
        signal_type = strategy["signal_type"]
        if signal_type == "hiring_sdr":
            notes.append("Focus on SDR productivity and quota attainment")
        elif signal_type == "funding_series_a":
            notes.append("Focus on post-funding GTM acceleration")
        elif signal_type == "funding_series_b":
            notes.append("Focus on enterprise expansion")
        elif signal_type == "product_launch":
            notes.append("Focus on converting launch traffic")
        elif signal_type == "high_growth":
            notes.append("Focus on sustainable growth systems")
        elif signal_type == "hiring_leadership":
            notes.append("Focus on team ramp-up and productivity")
        
        return " | ".join(notes)
    
    def _save_offer_match(self, result: Dict):
        """Save offer match to database"""
        from app.models import OfferStrategy
        
        # Check if strategy exists
        strategy = self.db.query(OfferStrategy).filter(
            OfferStrategy.signal_type == result["matched_strategy"]
        ).first()
        
        if not strategy:
            # Create new strategy
            strategy_data = {
                "strategy_id": f"strategy-{str(uuid.uuid4())[:8]}",
                "name": result["matched_strategy"].replace("_", " ").title(),
                "signal_type": result["matched_strategy"],
                "signal_keywords": [],
                "offer_angle": result["offer_angle"],
                "message_style": result["message_style"],
                "cta_type": result["cta_type"]
            }
            strategy = OfferStrategy(**strategy_data)
            self.db.add(strategy)
            self.db.commit()
        
        # Update performance tracking
        strategy.total_sent += 1
        self.db.commit()
    
    def get_message_template(self, message_style: str, offer_angle: str) -> str:
        """Get message template based on style and offer angle"""
        templates = {
            "direct_metric": {
                "template": "Hi {decision_maker},\n\n{offer_angle}.\n\nMost companies in your position see {metric} improvement in {timeframe}.\n\n{cta}",
                "metric": "30-50% pipeline",
                "timeframe": "first 30 days",
                "cta": "Open to a quick chat?"
            },
            "growth_focused": {
                "template": "Hi {decision_maker},\n\n{offer_angle}.\n\nWith the recent funding, timing is critical to maximize ROI.\n\n{cta}",
                "metric": "2-3x pipeline",
                "timeframe": "90 days",
                "cta": "Worth a 15-min conversation?"
            },
            "enterprise_focused": {
                "template": "Hi {decision_maker},\n\n{offer_angle}.\n\nSeries B is when enterprise deals become realistic - or they slip away.\n\n{cta}",
                "metric": "enterprise pipeline",
                "timeframe": "next quarter",
                "cta": "Let's discuss your enterprise strategy"
            },
            "curiosity_driven": {
                "template": "Hi {decision_maker},\n\n{offer_angle}.\n\n{hook}\n\n{cta}",
                "metric": "conversion lift",
                "timeframe": "launch window",
                "cta": "Curious what this looks like?"
            },
            "problem_awareness": {
                "template": "Hi {decision_maker},\n\n{offer_angle}.\n\nGrowth is great - until systems break.\n\n{cta}",
                "metric": "sustainable growth",
                "timeframe": "long-term",
                "cta": "Want to avoid the growth traps?"
            },
            "leadership_focused": {
                "template": "Hi {decision_maker},\n\n{offer_angle}.\n\nYour new hires need to ramp fast to justify the headcount.\n\n{cta}",
                "metric": "time-to-productivity",
                "timeframe": "first 90 days",
                "cta": "Open to sharing best practices?"
            },
            "conversational": {
                "template": "Hi {decision_maker},\n\n{offer_angle}.\n\n{context}\n\n{cta}",
                "metric": "pipeline improvement",
                "timeframe": "30-60 days",
                "cta": "Worth a conversation?"
            }
        }
        
        return templates.get(message_style, templates["conversational"])
    
    def update_strategy_performance(self, strategy_id: str, replied: bool):
        """Update strategy performance metrics"""
        from app.models import OfferStrategy
        
        strategy = self.db.query(OfferStrategy).filter(
            OfferStrategy.strategy_id == strategy_id
        ).first()
        
        if strategy:
            if replied:
                strategy.total_replies += 1
            
            # Recalculate reply rate
            if strategy.total_sent > 0:
                strategy.reply_rate = (strategy.total_replies / strategy.total_sent) * 100
            
            self.db.commit()
