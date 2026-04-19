"""
Outbound Outreach Service

Handles personalized outreach to prospects including:
- Email generation with signals
- Multi-channel outreach (email, LinkedIn, Twitter)
- Response tracking
- Meeting scheduling
"""

import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import openai

from app.integrations.gemini_analysis import GeminiAnalysisService
from app.integrations.gmail_thread_fetcher import GmailThreadFetcher
from app.services.gmail_sender import GmailSender

logger = logging.getLogger(__name__)


class OutboundOutreachService:
    """Service for outbound outreach to prospects"""
    
    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        gmail_credentials_path: Optional[str] = None,
        gmail_token_path: Optional[str] = None
    ):
        """
        Initialize outbound outreach service
        
        Args:
            gemini_api_key: Gemini API key for AI content generation
            openai_api_key: OpenAI API key for email generation
            gmail_credentials_path: Path to Gmail credentials
            gmail_token_path: Path to Gmail token
        """
        self.gemini = GeminiAnalysisService(gemini_api_key)
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        # Gmail integration
        self.gmail_sender = None
        self.gmail_fetcher = None
        
        if gmail_credentials_path and gmail_token_path:
            try:
                self.gmail_sender = GmailSender(gmail_credentials_path, gmail_token_path)
                self.gmail_fetcher = GmailThreadFetcher()
                logger.info("Gmail integration initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gmail integration: {e}")
    
    def generate_personalized_email(
        self,
        prospect: Dict,
        provider: Dict,
        template_type: str = "intro"
    ) -> Dict:
        """
        Generate personalized email for prospect
        
        Args:
            prospect: Prospect data with enrichment
            provider: Provider data
            template_type: Type of email (intro, followup, meeting_request)
            
        Returns:
            Email dict with subject and body
        """
        logger.info(f"Generating {template_type} email for {prospect.get('company_name')}")
        
        # Extract key signals
        signals = prospect.get("signals", [])
        hiring_signals = prospect.get("hiring_signals", [])
        funding_signals = prospect.get("funding_signals", {})
        
        # Build signal context
        signal_context = []
        
        # Funding signals
        if funding_signals.get("latest_round"):
            round_info = funding_signals["latest_round"]
            signal_context.append(f"raised {round_info.get('type')} of ${round_info.get('amount', 0):,}")
        
        # Hiring signals
        if hiring_signals:
            signal_context.append("is actively hiring")
        
        # Growth signals
        growth_signals = [s for s in signals if s.get("type") in ["growth", "expansion"]]
        if growth_signals:
            signal_context.append("is expanding")
        
        # Tech signals
        tech_stack = prospect.get("tech_stack", [])
        if tech_stack:
            signal_context.append(f"uses {', '.join(tech_stack[:3])}")
        
        # Generate email using OpenAI
        buyer_signals = signal_context if signal_context else ["is growing"]

        if template_type == "intro":
            email_body = self._generate_openai_email(
                buyer_company=prospect.get("company_name", ""),
                buyer_signals=buyer_signals,
                provider_company=provider.get("company_name", ""),
                provider_services=provider.get("services", []),
                provider_case_study=provider.get("case_studies", [{}])[0].get("title", "") if provider.get("case_studies") else None
            )
            
            # Generate subject line
            subject = f"{provider.get('company_name')} + {prospect.get('company_name')}"
            if funding_signals.get("latest_round"):
                round_amount = funding_signals["latest_round"].get("amount", 0)
                if round_amount > 0:
                    subject += f" (${round_amount/1000000:.0f}M)"
            
        elif template_type == "followup":
            email_body = self._generate_followup_email(prospect, provider)
            subject = f"Following up: {provider.get('company_name')} for {prospect.get('company_name')}"
        
        elif template_type == "meeting_request":
            email_body = self._generate_meeting_request_email(prospect, provider)
            subject = f"Quick chat: {provider.get('company_name')} + {prospect.get('company_name')}"
        
        else:
            email_body = self._generate_openai_email(
                buyer_company=prospect.get("company_name", ""),
                buyer_signals=buyer_signals,
                provider_company=provider.get("company_name", ""),
                provider_services=provider.get("services", [])
            )
            subject = f"{provider.get('company_name')} for {prospect.get('company_name')}"
        
        return {
            "subject": subject,
            "body": email_body,
            "to_email": prospect.get("decision_maker_email") or prospect.get("contact_email"),
            "from_email": provider.get("contact_email"),
            "template_type": template_type,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _generate_followup_email(self, prospect: Dict, provider: Dict) -> str:
        """Generate follow-up email"""
        prompt = f"""Write a brief follow-up email to {prospect.get('company_name')}.

Context: We previously introduced {provider.get('company_name')} who offers {', '.join(provider.get('services', []))}.

Requirements:
- Keep it under 100 words
- Be polite but persistent
- Ask if they're still interested
- Include clear next step

Return ONLY the email body."""
        
        return self.gemini._make_request(prompt, temperature=0.7) or ""
    
    def _generate_meeting_request_email(self, prospect: Dict, provider: Dict) -> str:
        """Generate meeting request email"""
        return f"Hi {prospect.get('decision_maker_name', 'there')},\n\nWould you be available for a quick 15-minute call to discuss how {provider.get('company_name')} can help with {prospect.get('company_name')}'s needs?\n\nBest regards,\n{provider.get('company_name')}"

    def _generate_openai_email(
        self,
        buyer_company: str,
        buyer_signals: List[str],
        provider_company: str,
        provider_services: List[str],
        provider_case_study: Optional[str] = None
    ) -> str:
        """Generate personalized email using OpenAI"""
        if not self.openai_api_key:
            logger.warning("OpenAI API key not available, using fallback")
            return self._generate_fallback_email(buyer_company, provider_company, provider_services)

        try:
            signals_text = ", ".join(buyer_signals)
            services_text = ", ".join(provider_services)

            prompt = f"""Write a personalized introduction email from {provider_company} to {buyer_company}.

About {buyer_company}: {signals_text}

About {provider_company}: They offer {services_text}
{f"Case study: {provider_case_study}" if provider_case_study else ""}

Requirements:
- Keep it under 200 words
- Mention the specific signals about the buyer
- Be professional but conversational
- Include a clear call to action
- Don't sound like a generic sales email

Return ONLY the email body, no subject line or other text."""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional B2B sales email writer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )

            email_body = response.choices[0].message.content.strip()
            return email_body

        except Exception as e:
            logger.error(f"OpenAI email generation failed: {e}")
            return self._generate_fallback_email(buyer_company, provider_company, provider_services)

    def _generate_fallback_email(
        self,
        buyer_company: str,
        provider_company: str,
        provider_services: List[str]
    ) -> str:
        """Generate fallback email when AI fails"""
        services_text = ", ".join(provider_services[:3])
        return f"""Hi there,

I noticed that {buyer_company} might benefit from {provider_company}'s expertise in {services_text}.

We've helped similar companies achieve great results, and I'd love to explore how we could support your goals.

Would you be open to a brief conversation this week?

Best regards,
{provider_company}"""
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None
    ) -> Optional[str]:
        """
        Send email via Gmail
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            from_email: Sender email (optional)
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.gmail_sender:
            logger.error("Gmail sender not initialized")
            return None
        
        try:
            message_id = self.gmail_sender.send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                from_email=from_email
            )
            logger.info(f"Email sent successfully: {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return None
    
    def send_outreach(
        self,
        prospect: Dict,
        provider: Dict,
        template_type: str = "intro",
        channel: str = "email"
    ) -> Dict:
        """
        Send outreach to prospect
        
        Args:
            prospect: Prospect data
            provider: Provider data
            template_type: Type of message
            channel: Channel to use (email, linkedin, twitter)
            
        Returns:
            Outreach result dict
        """
        logger.info(f"Sending {channel} outreach to {prospect.get('company_name')}")
        
        if channel == "email":
            email = self.generate_personalized_email(prospect, provider, template_type)
            message_id = self.send_email(
                to_email=email["to_email"],
                subject=email["subject"],
                body=email["body"]
            )
            
            return {
                "channel": "email",
                "template_type": template_type,
                "message_id": message_id,
                "sent_at": datetime.utcnow().isoformat(),
                "status": "sent" if message_id else "failed",
                "email": email
            }
        
        elif channel in ["linkedin", "twitter"]:
            # Placeholder for social outreach
            return {
                "channel": channel,
                "template_type": template_type,
                "message_id": None,
                "sent_at": datetime.utcnow().isoformat(),
                "status": "not_implemented",
                "message": f"{channel} outreach not yet implemented"
            }
        
        else:
            logger.error(f"Unknown channel: {channel}")
            return {
                "channel": channel,
                "status": "failed",
                "error": f"Unknown channel: {channel}"
            }
    
    def track_response(self, message_id: str) -> Optional[Dict]:
        """
        Track response to sent message
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Response data dict
        """
        if not self.gmail_fetcher:
            logger.error("Gmail fetcher not initialized")
            return None
        
        try:
            # Fetch thread for this message
            thread = self.gmail_fetcher.get_thread_by_message_id(message_id)
            
            if thread:
                messages = thread.get("messages", [])
                if len(messages) > 1:
                    # Has replies
                    latest_reply = messages[-1]
                    return {
                        "message_id": message_id,
                        "has_reply": True,
                        "reply_count": len(messages) - 1,
                        "latest_reply_at": latest_reply.get("internalDate"),
                        "status": "replied"
                    }
                else:
                    return {
                        "message_id": message_id,
                        "has_reply": False,
                        "reply_count": 0,
                        "status": "sent"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to track response: {e}")
            return None
    
    def create_outreach_sequence(
        self,
        prospect: Dict,
        provider: Dict,
        sequence_config: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Create outreach sequence with multiple touches
        
        Args:
            prospect: Prospect data
            provider: Provider data
            sequence_config: Sequence configuration
            
        Returns:
            List of scheduled outreach steps
        """
        if not sequence_config:
            sequence_config = {
                "touches": [
                    {"day": 0, "template": "intro", "channel": "email"},
                    {"day": 3, "template": "followup", "channel": "email"},
                    {"day": 7, "template": "meeting_request", "channel": "email"}
                ]
            }
        
        sequence = []
        for touch in sequence_config["touches"]:
            scheduled_at = datetime.utcnow() + timedelta(days=touch["day"])
            sequence.append({
                "prospect_id": prospect.get("prospect_id") or prospect.get("company_name"),
                "provider_id": provider.get("provider_id") or provider.get("company_name"),
                "template_type": touch["template"],
                "channel": touch["channel"],
                "scheduled_at": scheduled_at.isoformat(),
                "status": "scheduled"
            })
        
        return sequence
    
    def schedule_outreach(
        self,
        prospect: Dict,
        provider: Dict,
        sequence_config: Optional[Dict] = None
    ) -> Dict:
        """
        Schedule outreach sequence for prospect
        
        Args:
            prospect: Prospect data
            provider: Provider data
            sequence_config: Sequence configuration
            
        Returns:
            Scheduled sequence dict
        """
        logger.info(f"Scheduling outreach sequence for {prospect.get('company_name')}")
        
        sequence = self.create_outreach_sequence(prospect, provider, sequence_config)
        
        return {
            "prospect": prospect.get("company_name"),
            "provider": provider.get("company_name"),
            "sequence": sequence,
            "created_at": datetime.utcnow().isoformat(),
            "total_touches": len(sequence)
        }


# Example usage
if __name__ == "__main__":
    service = OutboundOutreachService()
    
    # Example prospect and provider
    prospect = {
        "company_name": "TechCo",
        "decision_maker_email": "cto@techco.com",
        "signals": [{"type": "growth", "value": "expanding"}],
        "hiring_signals": [{"type": "hiring", "confidence": 0.8}],
        "funding_signals": {
            "latest_round": {"type": "series_b", "amount": 15000000}
        },
        "tech_stack": ["react", "python"]
    }
    
    provider = {
        "company_name": "CloudServices Pro",
        "contact_email": "sales@cloudservices.com",
        "services": ["Cloud Migration", "DevOps", "Infrastructure"],
        "case_studies": [{"title": "Helped 50+ companies migrate to AWS"}]
    }
    
    # Generate email
    email = service.generate_personalized_email(prospect, provider, "intro")
    print(f"Subject: {email['subject']}")
    print(f"Body: {email['body'][:200]}...")
