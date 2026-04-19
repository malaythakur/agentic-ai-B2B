"""
Testing Mode Service

Allows providers to test automation with a small batch before full rollout:
- Test with limited number of buyers (e.g., 5)
- Test different email templates
- Test ICP criteria
- Test response rates
- Roll back if not satisfied
"""

import logging
from typing import Dict, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import ServiceProvider, BuyerCompany, Match

logger = logging.getLogger(__name__)


class TestingModeService:
    """Service for provider testing mode"""
    
    DEFAULT_TEST_BATCH_SIZE = 5  # Number of buyers to test with
    
    def __init__(self, db: Session):
        """
        Initialize testing mode service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def start_test_mode(
        self,
        provider_id: str,
        batch_size: int = None,
        test_template: str = "intro"
    ) -> Dict:
        """
        Start testing mode for a provider
        
        Args:
            provider_id: Provider ID
            batch_size: Number of buyers to test with (default 5)
            test_template: Template to test
            
        Returns:
            Result of starting test mode
        """
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            return {"success": False, "error": "Provider not found"}
        
        batch_size = batch_size or self.DEFAULT_TEST_BATCH_SIZE
        
        # Mark provider as in testing mode
        provider.automation_settings = provider.automation_settings or {}
        provider.automation_settings["testing_mode"] = True
        provider.automation_settings["test_batch_size"] = batch_size
        provider.automation_settings["test_template"] = test_template
        provider.automation_settings["test_started_at"] = datetime.utcnow().isoformat()
        
        self.db.commit()
        
        logger.info(f"Started testing mode for provider {provider_id} with batch size {batch_size}")
        
        return {
            "success": True,
            "provider_id": provider_id,
            "batch_size": batch_size,
            "template": test_template
        }
    
    def end_test_mode(self, provider_id: str, rollout: bool = False) -> Dict:
        """
        End testing mode for a provider
        
        Args:
            provider_id: Provider ID
            rollout: If True, roll out to full automation; if False, pause automation
            
        Returns:
            Result of ending test mode
        """
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            return {"success": False, "error": "Provider not found"}
        
        # Get test results
        test_results = self.get_test_results(provider_id)
        
        if rollout:
            # Roll out to full automation
            provider.automation_settings = provider.automation_settings or {}
            provider.automation_settings["testing_mode"] = False
            provider.automation_settings["test_rolled_out_at"] = datetime.utcnow().isoformat()
            provider.auto_outreach_enabled = True
        else:
            # Pause automation
            provider.auto_outreach_enabled = False
            provider.automation_settings = provider.automation_settings or {}
            provider.automation_settings["testing_mode"] = False
            provider.automation_settings["test_paused_at"] = datetime.utcnow().isoformat()
        
        self.db.commit()
        
        logger.info(f"Ended testing mode for provider {provider_id}, rollout: {rollout}")
        
        return {
            "success": True,
            "provider_id": provider_id,
            "rollout": rollout,
            "test_results": test_results
        }
    
    def get_test_results(self, provider_id: str) -> Dict:
        """
        Get test results for a provider
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Dict with test metrics
        """
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            return {"success": False, "error": "Provider not found"}
        
        # Get matches sent during testing period
        test_started = provider.automation_settings.get("test_started_at")
        if not test_started:
            return {"success": False, "error": "Test not started"}
        
        test_start_date = datetime.fromisoformat(test_started)
        
        # Get matches created after test start
        matches = self.db.query(Match).filter(
            Match.provider_id == provider_id,
            Match.created_at >= test_start_date
        ).all()
        
        # Calculate metrics
        total_sent = len([m for m in matches if m.intro_sent_at])
        responses = len([m for m in matches if m.response_received])
        
        return {
            "success": True,
            "provider_id": provider_id,
            "test_started_at": test_started,
            "batch_size": provider.automation_settings.get("test_batch_size", 0),
            "emails_sent": total_sent,
            "responses": responses,
            "response_rate": round(responses / total_sent * 100, 1) if total_sent > 0 else 0,
            "matches": [
                {
                    "match_id": m.match_id,
                    "buyer_id": m.buyer_id,
                    "status": m.status,
                    "response_received": m.response_received
                }
                for m in matches
            ]
        }
    
    def get_test_candidates(self, provider_id: str, batch_size: int = None) -> List[Dict]:
        """
        Get buyers for testing (small batch based on ICP)
        
        Args:
            provider_id: Provider ID
            batch_size: Number of buyers to return
            
        Returns:
            List of buyer candidates for testing
        """
        from app.services.provider_automation_service import ProviderAutomationService
        from app.services.match_scorer import MatchScorer
        
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            return []
        
        batch_size = batch_size or self.DEFAULT_TEST_BATCH_SIZE
        
        # Use match scorer to find best matches
        scorer = MatchScorer(self.db)
        ranked_buyers = scorer.rank_buyers_for_provider(provider_id, limit=batch_size * 2)
        
        # Return top candidates
        return ranked_buyers[:batch_size]
