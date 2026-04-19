"""
Provider Automation Service

Handles automated buyer outreach after provider opts in:
- Trigger automation when provider opts in
- Match buyers to providers based on ICP
- Send personalized emails to matched buyers
- Track outreach results
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import ServiceProvider, BuyerCompany, Match
from app.services.matchmaking_engine import MatchmakingEngine
from app.services.outbound_outreach import OutboundOutreachService
from app.settings import settings

logger = logging.getLogger(__name__)


class ProviderAutomationService:
    """Service for automated buyer outreach after provider opts in"""
    
    def __init__(
        self,
        db: Session,
        gmail_credentials_path: Optional[str] = None,
        gmail_token_path: Optional[str] = None,
        gemini_api_key: Optional[str] = None
    ):
        self.db = db
        self.matchmaking_engine = MatchmakingEngine(db)
        
        # Initialize outreach service
        self.outreach_service = OutboundOutreachService(
            gemini_api_key=gemini_api_key,
            gmail_credentials_path=gmail_credentials_path,
            gmail_token_path=gmail_token_path
        )
        
        # Initialize Gmail sender for actual sending
        if gmail_credentials_path and gmail_token_path:
            from app.services.gmail_sender import GmailSender
            self.gmail_sender = GmailSender(db)
        else:
            self.gmail_sender = None
    
    def trigger_provider_automation(
        self,
        provider_id: str,
        platform_email: str
    ) -> Dict:
        """
        Trigger automated buyer outreach after provider opts in
        
        Args:
            provider_id: Provider ID
            platform_email: Platform email for sending
            
        Returns:
            Result dict with automation status
        """
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            return {"success": False, "error": "Provider not found"}
        
        if not provider.auto_outreach_enabled:
            return {"success": False, "error": "Provider has not opted in to automation"}
        
        logger.info(f"Triggering automation for provider: {provider_id}")
        
        # Step 1: Find matching buyers based on provider's ICP
        matching_buyers = self._find_matching_buyers(provider)
        
        if not matching_buyers:
            return {
                "success": True,
                "message": "No matching buyers found",
                "matched_buyers": 0
            }
        
        logger.info(f"Found {len(matching_buyers)} matching buyers")
        
        # Step 2: Create matches
        matches_created = self._create_matches(provider, matching_buyers)
        
        # Step 3: Send outreach to matched buyers
        outreach_results = self._send_outreach_to_matches(
            provider,
            matching_buyers,
            platform_email
        )
        
        return {
            "success": True,
            "provider_id": provider_id,
            "matched_buyers": len(matching_buyers),
            "matches_created": matches_created,
            "outreach_results": outreach_results
        }
    
    def _find_matching_buyers(
        self,
        provider: ServiceProvider
    ) -> List[BuyerCompany]:
        """
        Find buyers matching provider's ICP
        
        Args:
            provider: Provider with ICP criteria
            
        Returns:
            List of matching buyers
        """
        icp_criteria = provider.icp_criteria or {}
        
        # Get all buyers with all fields
        buyers = self.db.query(BuyerCompany).filter(
            BuyerCompany.active == True
        ).all()
        
        # Ensure decision_maker_email is loaded
        for buyer in buyers:
            self.db.refresh(buyer)
        
        matching_buyers = []
        
        for buyer in buyers:
            # Check if buyer matches provider's ICP
            if self._buyer_matches_icp(buyer, icp_criteria):
                matching_buyers.append(buyer)
        
        return matching_buyers
    
    def _buyer_matches_icp(
        self,
        buyer: BuyerCompany,
        icp_criteria: Dict
    ) -> bool:
        """
        Check if buyer matches provider's ICP criteria
        
        Args:
            buyer: Buyer company
            icp_criteria: Provider's ICP criteria
            
        Returns:
            True if buyer matches ICP
        """
        # If no ICP criteria, match all buyers
        if not icp_criteria:
            return True
        
        # Check industry match
        provider_industries = icp_criteria.get("industries", [])
        if provider_industries and buyer.industry not in provider_industries:
            return False
        
        # Check funding stage match (normalize format: remove spaces, lowercase)
        funding_stage = icp_criteria.get("funding_stage")
        if funding_stage and buyer.funding_stage:
            # Normalize both: remove spaces and convert to lowercase
            normalized_icp_stage = funding_stage.replace(" ", "").lower()
            normalized_buyer_stage = buyer.funding_stage.replace("_", "").replace(" ", "").lower()
            if normalized_icp_stage != normalized_buyer_stage:
                return False
        
        # Check employee range match
        employee_range = icp_criteria.get("employees")
        if employee_range:
            # Simple check - can be enhanced
            buyer_employees = buyer.employee_count or 0
            if "50-500" in employee_range and not (50 <= buyer_employees <= 500):
                return False
            elif "500+" in employee_range and buyer_employees < 500:
                return False
        
        # Check signals match (at least one signal should match)
        required_signals = icp_criteria.get("signals", [])
        if required_signals:
            buyer_signals = buyer.signals or []
            # Check if at least one required signal is present
            signal_match = False
            for signal in required_signals:
                if signal == "recent_funding" and "recent_funding" in buyer_signals:
                    signal_match = True
                    break
                elif signal == "hiring_engineers" and ("hiring_devops" in buyer_signals or "hiring_engineers" in buyer_signals):
                    signal_match = True
                    break
            
            if not signal_match:
                return False
        
        return True
    
    def _create_matches(
        self,
        provider: ServiceProvider,
        buyers: List[BuyerCompany]
    ) -> int:
        """
        Create matches between provider and buyers
        
        Args:
            provider: Service provider
            buyers: List of matching buyers
            
        Returns:
            Number of matches created
        """
        matches_created = 0
        
        for buyer in buyers:
            # Check if match already exists
            existing_match = self.db.query(Match).filter(
                Match.provider_id == provider.provider_id,
                Match.buyer_id == buyer.buyer_id
            ).first()
            
            if existing_match:
                continue
            
            # Create new match
            from datetime import datetime
            match = Match(
                match_id=f"match-{provider.provider_id}-{buyer.buyer_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                provider_id=provider.provider_id,
                buyer_id=buyer.buyer_id,
                match_score=75,  # Default score, can be enhanced with AI
                status="pending",
                provider_approved=True  # Auto-approved since provider opted in
            )
            self.db.add(match)
            matches_created += 1
        
        self.db.commit()
        logger.info(f"Created {matches_created} matches")
        return matches_created
    
    def _send_outreach_to_matches(
        self,
        provider: ServiceProvider,
        buyers: List[BuyerCompany],
        platform_email: str
    ) -> Dict:
        """
        Send outreach emails to matched buyers
        
        Args:
            provider: Service provider
            buyers: List of matched buyers
            platform_email: Platform email for sending
            
        Returns:
            Outreach results
        """
        results = {
            "total": len(buyers),
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }
        
        for buyer in buyers:
            try:
                # Check if outreach was already sent to this buyer for this provider (duplicate prevention)
                from app.models import Match
                existing_match = self.db.query(Match).filter(
                    Match.provider_id == provider.provider_id,
                    Match.buyer_id == buyer.buyer_id
                ).first()
                
                if existing_match and existing_match.intro_message_id:
                    # Email already sent, skip
                    results["skipped"] += 1
                    results["details"].append({
                        "buyer_id": buyer.buyer_id,
                        "company": buyer.company_name,
                        "status": "skipped",
                        "reason": "Email already sent",
                        "sent_at": existing_match.intro_sent_at.isoformat() if existing_match.intro_sent_at else None
                    })
                    continue
                
                # Generate prospect data for outreach
                prospect = {
                    "company_name": buyer.company_name,
                    "decision_maker_email": buyer.decision_maker_email if buyer.decision_maker_email else (f"contact@{buyer.website.replace('https://', '').replace('http://', '').split('/')[0]}" if buyer.website else "unknown@example.com"),
                    "signals": buyer.signals or [],
                    "tech_stack": buyer.requirements or [],
                    "industry": buyer.industry
                }
                
                # Log for debugging
                logger.info(f"Sending to buyer: {buyer.buyer_id}, email: {prospect['decision_maker_email']}, buyer.decision_maker_email: {buyer.decision_maker_email}")
                
                # Generate provider data for outreach
                provider_data = {
                    "company_name": provider.company_name,
                    "contact_email": provider.contact_email,
                    "services": provider.services,
                    "case_studies": provider.case_studies
                }
                
                # Send outreach
                if self.gmail_sender:
                    # Direct Gmail sending
                    message_id = self.gmail_sender.send_email(
                        to_email=prospect["decision_maker_email"],
                        subject=f"{provider.company_name} + {buyer.company_name}",
                        body=self._generate_outreach_body(prospect, provider_data),
                        from_email=platform_email
                    )
                    
                    if message_id:
                        # Update match with message_id and timestamp
                        if existing_match:
                            existing_match.intro_message_id = message_id
                            existing_match.intro_sent_at = datetime.utcnow()
                            existing_match.status = "outreach_sent"
                            self.db.commit()
                        
                        results["sent"] += 1
                        results["details"].append({
                            "buyer_id": buyer.buyer_id,
                            "company": buyer.company_name,
                            "status": "sent",
                            "message_id": message_id
                        })
                    else:
                        results["failed"] += 1
                        results["details"].append({
                            "buyer_id": buyer.buyer_id,
                            "company": buyer.company_name,
                            "status": "failed",
                            "error": "No message ID returned"
                        })
                else:
                    # Use outreach service (without Gmail)
                    outreach_result = self.outreach_service.send_outreach(
                        prospect=prospect,
                        provider=provider_data,
                        template_type="intro",
                        channel="email"
                    )
                    
                    if outreach_result.get("status") == "sent":
                        results["sent"] += 1
                    else:
                        results["failed"] += 1
                    
                    results["details"].append({
                        "buyer_id": buyer.buyer_id,
                        "company": buyer.company_name,
                        "status": outreach_result.get("status", "unknown")
                    })
                
            except Exception as e:
                logger.error(f"Failed to send outreach to {buyer.company_name}: {e}")
                results["failed"] += 1
                results["details"].append({
                    "buyer_id": buyer.buyer_id,
                    "company": buyer.company_name,
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(f"Outreach completed: {results['sent']} sent, {results['failed']} failed, {results['skipped']} skipped")
        return results
    
    def _generate_outreach_body(
        self,
        prospect: Dict,
        provider: Dict
    ) -> str:
        """Generate personalized outreach email body"""
        signals = prospect.get("signals", [])
        if isinstance(signals, dict):
            signals_text = ", ".join(signals.keys())
        else:
            signals_text = ", ".join(signals) if signals else ""
        services_text = ", ".join(provider.get("services", []))
        
        return f"""Hi {prospect['company_name']} Team,

I noticed that {prospect['company_name']} might benefit from {provider['company_name']}'s expertise in {services_text}.

{f"Signals: {signals_text}" if signals_text else ""}

We've helped similar companies achieve great results, and I'd love to explore how we could support your goals.

Would you be open to a brief conversation this week?

Best regards,
{provider['company_name']}"""
