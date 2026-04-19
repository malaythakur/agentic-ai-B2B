"""
Match Scorer with Local Heuristics

Enhanced match scoring using local heuristics (no paid AI):
- Industry matching score
- Funding stage alignment
- Employee size fit
- Signal strength scoring
- Tech stack compatibility
- Geographic proximity
- Historical success patterns
"""

import logging
from typing import Dict, List
from sqlalchemy.orm import Session

from app.models import ServiceProvider, BuyerCompany

logger = logging.getLogger(__name__)


class MatchScorer:
    """Match scorer using local heuristics instead of paid AI"""
    
    def __init__(self, db: Session):
        """
        Initialize match scorer
        
        Args:
            db: Database session
        """
        self.db = db
    
    def calculate_match_score(self, provider: ServiceProvider, buyer: BuyerCompany) -> Dict:
        """
        Calculate match score between provider and buyer using local heuristics
        
        Args:
            provider: Service provider
            buyer: Buyer company
            
        Returns:
            Dict with score and breakdown
        """
        scores = {}
        
        # Industry match (0-25 points)
        scores['industry'] = self._score_industry_match(provider, buyer)
        
        # Funding stage alignment (0-20 points)
        scores['funding_stage'] = self._score_funding_stage(provider, buyer)
        
        # Employee size fit (0-15 points)
        scores['employee_size'] = self._score_employee_size(provider, buyer)
        
        # Signal strength (0-20 points)
        scores['signals'] = self._score_signals(provider, buyer)
        
        # Tech stack compatibility (0-10 points)
        scores['tech_stack'] = self._score_tech_stack(provider, buyer)
        
        # Historical pattern (0-10 points) - if available
        scores['historical'] = self._score_historical_pattern(provider, buyer)
        
        # Calculate total score
        total_score = sum(scores.values())
        
        return {
            'total_score': total_score,
            'score_breakdown': scores,
            'max_possible': 100
        }
    
    def _score_industry_match(self, provider: ServiceProvider, buyer: BuyerCompany) -> int:
        """Score industry match (0-25 points)"""
        provider_industries = provider.industries or []
        buyer_industry = buyer.industry
        
        if not provider_industries or not buyer_industry:
            return 5  # Neutral score if no data
        
        if buyer_industry in provider_industries:
            return 25  # Perfect match
        elif any(ind in buyer_industry.lower() for ind in provider_industries):
            return 20  # Partial match
        else:
            return 0  # No match
    
    def _score_funding_stage(self, provider: ServiceProvider, buyer: BuyerCompany) -> int:
        """Score funding stage alignment (0-20 points)"""
        icp_criteria = provider.icp_criteria or {}
        target_stage = icp_criteria.get('funding_stage')
        buyer_stage = buyer.funding_stage
        
        if not target_stage or not buyer_stage:
            return 10  # Neutral score
        
        # Normalize stage comparison
        target_normalized = target_stage.replace(' ', '').replace('_', '').lower()
        buyer_normalized = buyer_stage.replace(' ', '').replace('_', '').lower()
        
        if target_normalized == buyer_normalized:
            return 20  # Perfect match
        elif target_normalized in buyer_normalized or buyer_normalized in target_normalized:
            return 15  # Partial match
        else:
            # Check if close in funding progression
            stages = ['seed', 'seriesa', 'seriesb', 'seriesc', 'seriesd', 'seriese', 'ipo']
            try:
                if target_normalized in stages and buyer_normalized in stages:
                    target_idx = stages.index(target_normalized)
                    buyer_idx = stages.index(buyer_normalized)
                    if abs(target_idx - buyer_idx) <= 1:
                        return 10  # Close stages
            except:
                pass
            
            return 5  # Not aligned
    
    def _score_employee_size(self, provider: ServiceProvider, buyer: BuyerCompany) -> int:
        """Score employee size fit (0-15 points)"""
        icp_criteria = provider.icp_criteria or {}
        target_range = icp_criteria.get('employees')
        buyer_employees = buyer.employee_count or 0
        
        if not target_range or buyer_employees == 0:
            return 7  # Neutral score
        
        if '50-500' in target_range:
            if 50 <= buyer_employees <= 500:
                return 15  # Perfect fit
            elif 25 <= buyer_employees <= 750:
                return 10  # Close fit
            else:
                return 5  # Not ideal
        elif '500+' in target_range:
            if buyer_employees >= 500:
                return 15  # Perfect fit
            elif buyer_employees >= 300:
                return 10  # Close fit
            else:
                return 0  # Too small
        else:
            return 7  # Unknown range
    
    def _score_signals(self, provider: ServiceProvider, buyer: BuyerCompany) -> int:
        """Score signal strength (0-20 points)"""
        icp_criteria = provider.icp_criteria or {}
        required_signals = icp_criteria.get('signals', [])
        buyer_signals = buyer.signals or []
        
        if not required_signals:
            return 10  # Neutral if no requirements
        
        if not buyer_signals:
            return 0  # No signals from buyer
        
        # Count how many required signals are present
        matches = 0
        for signal in required_signals:
            if signal == 'recent_funding' and 'recent_funding' in buyer_signals:
                matches += 1
            elif signal == 'hiring_engineers' and ('hiring_devops' in buyer_signals or 'hiring_engineers' in buyer_signals):
                matches += 1
            elif signal in buyer_signals:
                matches += 1
        
        if matches == len(required_signals):
            return 20  # All signals match
        elif matches >= len(required_signals) / 2:
            return 15  # Half or more match
        elif matches > 0:
            return 10  # Some match
        else:
            return 0  # No match
    
    def _score_tech_stack(self, provider: ServiceProvider, buyer: BuyerCompany) -> int:
        """Score tech stack compatibility (0-10 points)"""
        provider_services = provider.services or []
        buyer_requirements = buyer.requirements or []
        
        if not provider_services or not buyer_requirements:
            return 5  # Neutral score
        
        # Check if provider services match buyer requirements
        matches = 0
        for service in provider_services:
            service_lower = service.lower()
            for req in buyer_requirements:
                if service_lower in req.lower() or req.lower() in service_lower:
                    matches += 1
                    break
        
        if matches >= len(provider_services):
            return 10  # Strong match
        elif matches > 0:
            return 7  # Some match
        else:
            return 0  # No match
    
    def _score_historical_pattern(self, provider: ServiceProvider, buyer: BuyerCompany) -> int:
        """Score based on historical success patterns (0-10 points)"""
        # This would analyze historical matches for this provider
        # For now, return neutral score
        # In production, could analyze:
        # - Which industries have responded well
        # - Which funding stages convert better
        # - Which signals predict success
        return 5
    
    def rank_buyers_for_provider(self, provider_id: str, limit: int = 50) -> List[Dict]:
        """
        Rank buyers for a provider based on match scores
        
        Args:
            provider_id: Provider ID
            limit: Maximum number of buyers to return
            
        Returns:
            List of ranked buyers with scores
        """
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            return []
        
        buyers = self.db.query(BuyerCompany).filter(
            BuyerCompany.active == True
        ).all()
        
        scored_buyers = []
        
        for buyer in buyers:
            score_data = self.calculate_match_score(provider, buyer)
            
            if score_data['total_score'] >= 50:  # Only include decent matches
                scored_buyers.append({
                    'buyer_id': buyer.buyer_id,
                    'company_name': buyer.company_name,
                    'score': score_data['total_score'],
                    'breakdown': score_data['score_breakdown']
                })
        
        # Sort by score descending
        scored_buyers.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_buyers[:limit]
