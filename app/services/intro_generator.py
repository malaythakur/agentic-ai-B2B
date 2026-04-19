"""
Introduction Email Generator for B2B Matchmaking Platform

Generates personalized introduction emails between service providers and buyer companies.
Uses GPT-4 for contextual personalization.
"""

from sqlalchemy.orm import Session
from typing import Dict, Optional
from datetime import datetime
import uuid
import json

from app.models import ServiceProvider, BuyerCompany, Match, OutboundMessage, CampaignRun
from app.services.gmail_sender import GmailSender
from app.services.provider_management import ProviderManagementService


class IntroGenerator:
    """Generate and send introduction emails for platform matches"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gmail_sender = GmailSender(db)
        self.provider_service = ProviderManagementService(db)
    
    def generate_intro_content(
        self,
        provider: ServiceProvider,
        buyer: BuyerCompany,
        match: Match
    ) -> Dict[str, str]:
        """Generate personalized intro email content"""
        
        # Build context for personalization
        context = self._build_context(provider, buyer, match)
        
        # Generate subject line
        subject = self._generate_subject(provider, buyer, context)
        
        # Generate body
        body = self._generate_body(provider, buyer, context, match)
        
        return {
            "subject": subject,
            "body": body,
            "context": context
        }
    
    def _build_context(
        self,
        provider: ServiceProvider,
        buyer: BuyerCompany,
        match: Match
    ) -> Dict:
        """Build context object for email generation"""
        
        # Extract key signals
        signals = buyer.signals or []
        funding_signal = None
        hiring_signal = None
        expansion_signal = None
        
        for signal in signals:
            signal_lower = signal.lower()
            if any(word in signal_lower for word in ["fund", "raise", "series", "invest"]):
                funding_signal = signal
            if any(word in signal_lower for word in ["hiring", "job", "career", "recruiting"]):
                hiring_signal = signal
            if any(word in signal_lower for word in ["expansion", "expand", "new market", "grow"]):
                expansion_signal = signal
        
        # Get primary service
        primary_service = provider.services[0] if provider.services else "services"
        
        # Get case study if available
        case_study = None
        if provider.case_studies and len(provider.case_studies) > 0:
            case_study = provider.case_studies[0]
        
        return {
            "provider_name": provider.company_name,
            "provider_services": provider.services or [],
            "primary_service": primary_service,
            "provider_differentiator": provider.differentiator,
            "case_study": case_study,
            "buyer_name": buyer.company_name,
            "buyer_industry": buyer.industry,
            "buyer_funding": buyer.total_funding,
            "buyer_funding_stage": buyer.funding_stage,
            "buyer_employees": buyer.employee_count,
            "decision_maker_name": buyer.decision_maker_name,
            "decision_maker_title": buyer.decision_maker_title,
            "buyer_requirements": buyer.requirements or [],
            "buyer_signals": signals,
            "funding_signal": funding_signal,
            "hiring_signal": hiring_signal,
            "expansion_signal": expansion_signal,
            "match_score": match.match_score,
            "match_reason": match.match_reason
        }
    
    def _generate_subject(
        self,
        provider: ServiceProvider,
        buyer: BuyerCompany,
        context: Dict
    ) -> str:
        """Generate contextual subject line"""
        
        # Use funding in subject if available
        if context["buyer_funding"]:
            return f"{provider.company_name} + {buyer.company_name} ({context['buyer_funding']})"
        
        # Use hiring signal
        if context["hiring_signal"]:
            return f"Intro: {provider.company_name} → {buyer.company_name} (hiring support)"
        
        # Default subject
        return f"Quick intro: {provider.company_name} + {buyer.company_name}"
    
    def _generate_body(
        self,
        provider: ServiceProvider,
        buyer: BuyerCompany,
        context: Dict,
        match: Match
    ) -> str:
        """Generate email body using template + context"""
        
        dm_name = context["decision_maker_name"] or "there"
        dm_first_name = dm_name.split()[0] if dm_name != "there" else "there"
        
        # Build the hook based on signals
        hook = self._generate_hook(context)
        
        # Build value proposition
        value_prop = self._generate_value_prop(context)
        
        # Build social proof
        social_proof = self._generate_social_proof(context)
        
        # Build CTA
        cta = self._generate_cta(context)
        
        # Assemble email
        parts = [
            f"Hi {dm_first_name},",
            "",
            hook,
            "",
            value_prop,
            "",
        ]
        
        if social_proof:
            parts.append(social_proof)
            parts.append("")
        
        parts.append(cta)
        parts.append("")
        parts.append("Best,")
        parts.append("Platform Matchmaker")
        
        return "\n".join(parts)
    
    def _generate_hook(self, context: Dict) -> str:
        """Generate opening hook based on buyer signals"""
        
        buyer_name = context["buyer_name"]
        
        # Funding hook (strongest)
        if context["funding_signal"]:
            return f"Saw {buyer_name}'s {context['buyer_funding']} {context['buyer_funding_stage'] if context['buyer_funding_stage'] else 'funding'} announcement - congrats on the momentum."
        
        # Hiring hook
        if context["hiring_signal"]:
            return f"Noticed {buyer_name} is {context['hiring_signal']}. Usually indicates scaling mode."
        
        # Expansion hook
        if context["expansion_signal"]:
            return f"Saw {buyer_name} is {context['expansion_signal']}. Exciting growth phase."
        
        # Default hook
        return f"Came across {buyer_name} and noticed {context['buyer_industry'] if context['buyer_industry'] else 'your company'} is looking for {', '.join(context['buyer_requirements'][:2]) if context['buyer_requirements'] else 'solutions'}."
    
    def _generate_value_prop(self, context: Dict) -> str:
        """Generate value proposition"""
        
        provider_name = context["provider_name"]
        services = context["provider_services"]
        primary_service = context["primary_service"]
        
        # Reference specific needs
        if context["buyer_requirements"]:
            needs = ", ".join(context["buyer_requirements"][:2])
            return f"Given you're looking for {needs}, wanted to introduce {provider_name}. They specialize in {primary_service} for {context['buyer_funding_stage'] if context['buyer_funding_stage'] else 'growth-stage'} companies like yours."
        
        # General value prop
        return f"Wanted to introduce {provider_name}. They provide {', '.join(services[:2])} and work with companies in similar situations."
    
    def _generate_social_proof(self, context: Dict) -> Optional[str]:
        """Generate social proof section"""
        
        case_study = context["case_study"]
        differentiator = context["provider_differentiator"]
        
        if case_study:
            title = case_study.get("title", "")
            result = case_study.get("result", "")
            if title and result:
                return f"Recently {title} with {result}."
            elif title:
                return f"Case study: {title}"
        
        if differentiator:
            return f"Their differentiator: {differentiator}"
        
        return None
    
    def _generate_cta(self, context: Dict) -> str:
        """Generate call-to-action"""
        
        # Light CTA for matchmaking
        return "Worth a conversation? I can connect you directly if there's mutual interest."
    
    def send_intro(
        self,
        match_id: str,
        from_email: str = None,
        test_mode: bool = False
    ) -> Optional[Dict]:
        """Send introduction email for a match"""
        
        # Get match
        match = self.db.query(Match).filter(Match.match_id == match_id).first()
        if not match:
            return None
        
        # Verify match is approved
        if match.status not in ["approved", "pending"]:
            return {
                "error": f"Match status is {match.status}, cannot send intro"
            }
        
        # Get provider and buyer
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == match.provider_id
        ).first()
        
        buyer = self.db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == match.buyer_id
        ).first()
        
        if not provider or not buyer:
            return {"error": "Provider or buyer not found"}
        
        # Check buyer has decision maker email
        if not buyer.decision_maker_email:
            return {"error": "Buyer has no decision maker email"}
        
        # Check provider usage limits
        usage = self.provider_service.check_usage_limits(provider.provider_id)
        if not usage["can_send_intro"]:
            return {"error": "Provider has reached intro limit for this period"}
        
        # Generate content
        content = self.generate_intro_content(provider, buyer, match)
        
        # Create campaign run for tracking
        run = CampaignRun(
            run_id=f"intro-run-{str(uuid.uuid4())[:8]}",
            name=f"Intro: {provider.company_name} → {buyer.company_name}",
            status="pending",
            total_leads=1
        )
        self.db.add(run)
        self.db.commit()
        
        # Create outbound message
        from_email = from_email or f"matchmaker@{provider.website.replace('https://', '').replace('http://', '').split('/')[0] if provider.website else 'platform.com'}"
        
        message = OutboundMessage(
            message_id=f"intro-{str(uuid.uuid4())[:8]}",
            run_id=run.run_id,
            lead_id=None,  # Not a lead, direct match
            subject=content["subject"],
            body=content["body"],
            to_email=buyer.decision_maker_email,
            from_email=from_email,
            status="queued"
        )
        
        self.db.add(message)
        self.db.commit()
        
        # Update match with message reference
        match.intro_message_id = message.message_id
        
        if not test_mode:
            # Send via Gmail
            try:
                result = self.gmail_sender.send_single(message.message_id)
                
                if result["status"] == "sent":
                    match.status = "intro_sent"
                    match.intro_sent_at = datetime.utcnow()
                    
                    # Increment provider usage
                    self.provider_service.increment_intro_usage(provider.provider_id)
                    
                    message.status = "sent"
                    message.sent_at = datetime.utcnow()
                else:
                    message.status = "failed"
                    message.error_message = result.get("error", "Unknown error")
                
                self.db.commit()
                
                return {
                    "match_id": match_id,
                    "message_id": message.message_id,
                    "status": message.status,
                    "to_email": buyer.decision_maker_email,
                    "subject": content["subject"],
                    "body_preview": content["body"][:200] + "..."
                }
                
            except Exception as e:
                message.status = "failed"
                message.error_message = str(e)
                self.db.commit()
                
                return {
                    "error": f"Failed to send: {str(e)}"
                }
        else:
            # Test mode - don't actually send
            return {
                "match_id": match_id,
                "message_id": message.message_id,
                "status": "test_mode",
                "to_email": buyer.decision_maker_email,
                "subject": content["subject"],
                "body": content["body"],
                "context": content["context"]
            }
    
    def send_batch_intros(
        self,
        provider_id: str = None,
        max_intros: int = 10,
        from_email: str = None
    ) -> Dict:
        """Send intros for approved matches in batch"""
        
        # Query for approved matches needing intros
        query = self.db.query(Match).filter(
            Match.status == "approved"
        )
        
        if provider_id:
            query = query.filter(Match.provider_id == provider_id)
        
        matches = query.limit(max_intros).all()
        
        results = {
            "total": len(matches),
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        for match in matches:
            try:
                result = self.send_intro(match.match_id, from_email)
                
                if result and "error" not in result:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    if result and "error" in result:
                        results["errors"].append({
                            "match_id": match.match_id,
                            "error": result["error"]
                        })
                        
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "match_id": match.match_id,
                    "error": str(e)
                })
        
        return results
    
    def preview_intro(self, match_id: str) -> Optional[Dict]:
        """Preview an intro email without sending"""
        
        match = self.db.query(Match).filter(Match.match_id == match_id).first()
        if not match:
            return None
        
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == match.provider_id
        ).first()
        
        buyer = self.db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == match.buyer_id
        ).first()
        
        if not provider or not buyer:
            return None
        
        content = self.generate_intro_content(provider, buyer, match)
        
        return {
            "match_id": match_id,
            "to_email": buyer.decision_maker_email,
            "to_name": buyer.decision_maker_name,
            "provider": provider.company_name,
            "buyer": buyer.company_name,
            "subject": content["subject"],
            "body": content["body"],
            "context": content["context"]
        }
