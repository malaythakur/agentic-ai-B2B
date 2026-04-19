"""AI-Powered Lead Scoring and ICP Matching Service - FREE VERSION
Uses only free signals from existing lead data (no external APIs required)
"""
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from app.models import Lead, LeadScore
from app.logging_config import logger as app_logger
import json
import re
from urllib.parse import urlparse

logger = app_logger


class AILeadScoringService:
    """Service for AI-powered lead scoring and ICP matching"""
    
    def __init__(self, db: Session):
        self.db = db
        self.icp_config = self._load_icp_config()
    
    def _load_icp_config(self) -> Dict:
        """Load ICP configuration - FREE version using only internal signals"""
        return {
            # High-value keywords in signals (FREE - from lead data)
            "high_value_signals": [
                "funding", "raised", "series a", "series b", "series c", "investment",
                "hiring", "growing", "expanding", "scaling", "launch", "announced",
                "released", "new product", "partnership", "acquisition", "merger",
                "revenue growth", "10x", "unicorn", "ipo"
            ],
            # Decision maker titles that indicate buying authority (FREE)
            "high_authority_titles": [
                "ceo", "founder", "cro", "cto", "cmo", "vp", "vice president",
                "head of", "director", "chief"
            ],
            "medium_authority_titles": [
                "manager", "lead", "senior"
            ],
            # High-value company indicators (FREE - from company name/domain)
            "high_value_indicators": [
                "ai", "ml", "data", "cloud", "saas", "api", "platform",
                "automation", "analytics", "intelligence", "get", "try", "use"
            ],
            # Website quality indicators (FREE)
            "high_value_tlds": [".com", ".io", ".ai", ".co"],
            "low_value_tlds": [".blogspot.com", ".wordpress.com", ".github.io"],
            # Urgency indicators (FREE - from signal text)
            "urgency_signals": ["urgent", "immediately", "asap", "critical", "now"],
            "growth_signals": ["growing", "expanding", "scaling", "10x", "growth"],
            # Scoring weights
            "signal_weights": {
                "signal_strength": 0.30,
                "decision_maker_authority": 0.25,
                "company_quality": 0.20,
                "urgency": 0.15,
                "website_quality": 0.10
            }
        }
    
    def score_lead(self, lead: Lead, use_ai: bool = False) -> Dict:
        """Score a lead using FREE signals only (no external APIs)"""
        # FREE version always uses rule-based scoring with enhanced free signals
        return self._rule_based_score_lead(lead)
    
    def _rule_based_score_lead(self, lead: Lead) -> Dict:
        """Rule-based lead scoring using ONLY FREE signals"""
        scores = {
            "signal_strength": self._score_signal_strength(lead),
            "decision_maker_authority": self._score_decision_maker(lead),
            "company_quality": self._score_company_quality(lead),
            "urgency_score": self._score_urgency(lead),
            "website_quality": self._score_website_quality(lead)
        }
        
        # Weighted total score using FREE weights
        weights = self.icp_config["signal_weights"]
        total_score = sum(scores[key] * weights[key.replace("_score", "")] 
                         for key in scores)
        
        # Add bonus for multiple strong signals
        strong_signals = sum(1 for v in scores.values() if v >= 80)
        if strong_signals >= 3:
            total_score = min(100, total_score + 10)
        elif strong_signals >= 2:
            total_score = min(100, total_score + 5)
        
        # Determine tier
        tier = self._determine_tier(total_score)
        
        return {
            "total_score": round(total_score, 2),
            "tier": tier,
            "breakdown": scores,
            "is_qualified": total_score >= 70,
            "qualification_reason": self._get_qualification_reason(scores, total_score),
            "free_signals_used": [
                "signal_text_analysis",
                "decision_maker_title_parsing",
                "company_name_heuristics",
                "website_domain_analysis",
                "urgency_keyword_detection"
            ]
        }
    
    def _score_decision_maker(self, lead: Lead) -> float:
        """Score decision maker authority based on title (FREE signal)"""
        if not lead.decision_maker:
            return 50.0  # Neutral if no decision maker info
        
        title = lead.decision_maker.lower()
        
        # Check for high authority titles
        for auth_title in self.icp_config["high_authority_titles"]:
            if auth_title in title:
                # Bonus for C-level
                if any(c in title for c in ["ceo", "founder", "cro", "cto", "cmo"]):
                    return 100.0
                return 90.0
        
        # Check for medium authority
        for med_title in self.icp_config["medium_authority_titles"]:
            if med_title in title:
                return 70.0
        
        return 50.0
    
    def _score_company_quality(self, lead: Lead) -> float:
        """Score company quality based on name and indicators (FREE signal)"""
        if not lead.company:
            return 50.0
        
        company = lead.company.lower()
        score = 50.0
        
        # Check for high-value indicators in company name
        for indicator in self.icp_config["high_value_indicators"]:
            if indicator in company:
                score += 10
        
        # Bonus for tech-related naming patterns
        if any(suffix in company for suffix in ["ai", "io", "ly", "ify", "box", "hub"]):
            score += 5
        
        return min(100, score)
    
    def _score_urgency(self, lead: Lead) -> float:
        """Score urgency based on signal keywords (FREE signal)"""
        if not lead.signal:
            return 50.0
        
        signal = lead.signal.lower()
        score = 50.0
        
        # Check for urgency signals
        for urgent in self.icp_config["urgency_signals"]:
            if urgent in signal:
                score += 20
                break
        
        # Check for growth signals (indicates timing opportunity)
        for growth in self.icp_config["growth_signals"]:
            if growth in signal:
                score += 15
                break
        
        return min(100, score)
    
    def _score_website_quality(self, lead: Lead) -> float:
        """Score website quality based on domain (FREE signal)"""
        if not lead.website:
            return 50.0
        
        try:
            parsed = urlparse(lead.website)
            domain = parsed.netloc.lower() if parsed.netloc else ""
            
            # Remove www. prefix
            domain = re.sub(r'^www\.', '', domain)
            
            score = 50.0
            
            # Check for high-value TLDs
            for tld in self.icp_config["high_value_tlds"]:
                if domain.endswith(tld):
                    score += 20
                    break
            
            # Penalty for low-value TLDs (indicates hobby/personal projects)
            for bad_tld in self.icp_config["low_value_tlds"]:
                if bad_tld in domain:
                    score -= 20
                    break
            
            # Bonus for professional naming (no numbers, short domain)
            clean_domain = domain.split('.')[0]
            if len(clean_domain) <= 10 and not any(c.isdigit() for c in clean_domain):
                score += 10
            
            return max(0, min(100, score))
        except:
            return 50.0
    
    def _score_signal_strength(self, lead: Lead) -> float:
        """Score signal strength using FREE keyword analysis (0-100)"""
        if not lead.signal:
            return 0.0
        
        signal = lead.signal.lower()
        high_value_signals = self.icp_config["high_value_signals"]
        
        # Count matches
        matches = sum(1 for indicator in high_value_signals if indicator in signal)
        
        # Calculate base score
        if matches >= 4:
            base_score = 100.0
        elif matches == 3:
            base_score = 90.0
        elif matches == 2:
            base_score = 75.0
        elif matches == 1:
            base_score = 60.0
        else:
            base_score = 30.0
        
        # Bonus for signal length (more detailed signals = higher intent)
        word_count = len(signal.split())
        if word_count >= 30:
            base_score += 10
        elif word_count >= 20:
            base_score += 5
        
        return min(100, base_score)
    
    
    def _determine_tier(self, score: float) -> str:
        """Determine lead tier based on score"""
        if score >= 85:
            return "Tier 1"  # Auto-send
        elif score >= 70:
            return "Tier 2"  # Queued for review
        else:
            return "Tier 3"  # Manual approval required
    
    def _get_qualification_reason(self, scores: Dict, total_score: float) -> str:
        """Get reason for qualification status with FREE signal insights"""
        if total_score >= 85:
            strengths = [k for k, v in scores.items() if v >= 80]
            return f"High-fit lead - strong in: {', '.join(strengths)}. Recommended for immediate outreach."
        elif total_score >= 70:
            strengths = [k for k, v in scores.items() if v >= 70]
            return f"Good-fit lead - solid in: {', '.join(strengths)}. Recommended for queued batch."
        else:
            weak_areas = [k for k, v in scores.items() if v < 60]
            return f"Low-fit lead - needs improvement in: {', '.join(weak_areas)}. Consider manual review."
    
    def batch_score_leads(self, lead_ids: List[str], use_ai: bool = False) -> Dict:
        """Score multiple leads in batch"""
        results = {
            "total": len(lead_ids),
            "tier_1": 0,
            "tier_2": 0,
            "tier_3": 0,
            "leads": {}
        }
        
        for lead_id in lead_ids:
            lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
            if lead:
                scoring_result = self.score_lead(lead, use_ai)
                
                # Update counts
                tier = scoring_result["tier"]
                if tier == "Tier 1":
                    results["tier_1"] += 1
                elif tier == "Tier 2":
                    results["tier_2"] += 1
                else:
                    results["tier_3"] += 1
                
                results["leads"][lead_id] = scoring_result
                
                # Update lead in database
                lead.fit_score = int(scoring_result["total_score"])
                
                # Update or create lead score record
                lead_score = self.db.query(LeadScore).filter(
                    LeadScore.lead_id == lead_id
                ).first()
                
                if not lead_score:
                    lead_score = LeadScore(lead_id=lead_id)
                    self.db.add(lead_score)
                
                lead_score.priority_score = int(scoring_result["total_score"])
                lead_score.is_qualified = scoring_result["is_qualified"]
                lead_score.calculated_at = None  # Will be set by DB default
        
        self.db.commit()
        return results
    
    def find_similar_leads(self, lead_id: str, limit: int = 10) -> List[Dict]:
        """Find leads similar to a given lead based on closed-won analysis"""
        target_lead = self.db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not target_lead:
            return []
        
        # Get all leads
        all_leads = self.db.query(Lead).filter(Lead.lead_id != lead_id).all()
        
        similar_leads = []
        for lead in all_leads:
            similarity_score = self._calculate_similarity(target_lead, lead)
            if similarity_score > 0.5:  # 50% similarity threshold
                similar_leads.append({
                    "lead_id": lead.lead_id,
                    "company": lead.company,
                    "similarity_score": similarity_score
                })
        
        # Sort by similarity and return top results
        similar_leads.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar_leads[:limit]
    
    def _calculate_similarity(self, lead1: Lead, lead2: Lead) -> float:
        """Calculate similarity between two leads"""
        score = 0.0
        
        # Signal similarity
        if lead1.signal and lead2.signal:
            signal1_words = set(lead1.signal.lower().split())
            signal2_words = set(lead2.signal.lower().split())
            intersection = signal1_words & signal2_words
            union = signal1_words | signal2_words
            if union:
                score += len(intersection) / len(union) * 0.5
        
        # Company similarity (simplified)
        if lead1.company and lead2.company:
            if lead1.company.split()[0] == lead2.company.split()[0]:
                score += 0.3
        
        # Fit score similarity
        if lead1.fit_score and lead2.fit_score:
            score_diff = abs(lead1.fit_score - lead2.fit_score)
            score += max(0, (100 - score_diff) / 100) * 0.2
        
        return min(score, 1.0)
