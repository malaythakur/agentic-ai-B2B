"""
Provider Opt-In Service

Handles provider opt-in flow for automated outreach:
- Send opt-in email to provider
- Monitor provider response via Gmail
- Analyze sentiment of provider response
- Enable automation based on consent
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import ServiceProvider
from app.integrations.gmail_thread_fetcher import GmailThreadFetcher
from app.services.gmail_sender import GmailSender
from app.integrations.gemini_analysis import GeminiAnalysisService

logger = logging.getLogger(__name__)


class ProviderOptInService:
    """Service for managing provider opt-in flow"""
    
    def __init__(
        self,
        db: Session,
        gmail_credentials_path: Optional[str] = None,
        gmail_token_path: Optional[str] = None,
        gemini_api_key: Optional[str] = None
    ):
        self.db = db
        self.gmail_fetcher = None
        self.gmail_sender = None
        self.gemini = GeminiAnalysisService(gemini_api_key)
        
        if gmail_credentials_path and gmail_token_path:
            try:
                self.gmail_fetcher = GmailThreadFetcher()
                self.gmail_sender = GmailSender(db)
                logger.info("Gmail integration initialized for opt-in service")
            except Exception as e:
                logger.error(f"Failed to initialize Gmail integration: {e}")
    
    def send_optin_email(
        self,
        provider_id: str,
        from_email: str
    ) -> Dict:
        """
        Send opt-in email to provider
        
        Args:
            provider_id: Provider ID
            from_email: Platform email to send from
            
        Returns:
            Result dict with status and details
        """
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            return {"success": False, "error": "Provider not found"}
        
        if provider.outreach_consent_status != "pending":
            return {"success": False, "error": f"Provider already has consent status: {provider.outreach_consent_status}"}
        
        # Check if opt-in email was already sent (duplicate prevention)
        if provider.opt_in_email_sent_at:
            return {
                "success": False,
                "error": "Opt-in email already sent",
                "sent_at": provider.opt_in_email_sent_at.isoformat()
            }
        
        # Generate opt-in email
        optin_email = self._generate_optin_email(provider)
        
        # Send email
        if not self.gmail_sender:
            return {"success": False, "error": "Gmail sender not initialized"}
        
        try:
            message_id = self.gmail_sender.send_email(
                to_email=provider.contact_email,
                subject=optin_email["subject"],
                body=optin_email["body"],
                from_email=from_email
            )
            
            if message_id:
                # Update provider record
                provider.opt_in_email_sent_at = datetime.utcnow()
                self.db.commit()
                
                return {
                    "success": True,
                    "message_id": message_id,
                    "provider_id": provider_id,
                    "sent_to": provider.contact_email
                }
            else:
                return {"success": False, "error": "Failed to send email"}
                
        except Exception as e:
            logger.error(f"Failed to send opt-in email: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_optin_email(self, provider: ServiceProvider) -> Dict:
        """Generate opt-in email for provider"""
        subject = f"Enable Automated Outreach for {provider.company_name}"
        
        body = f"""Hi {provider.company_name} Team,

We've identified high-quality buyer matches for your services ({', '.join(provider.services[:3])}).

To help you connect with these prospects, we can send personalized outreach emails on your behalf. This would include:

• AI-generated personalized emails based on buyer signals
• Automated follow-up sequences
• Response tracking and analytics
• Full control over which matches to contact

**To enable this service, please reply to this email with your consent.**

You can say something like:
- "Yes, please proceed"
- "I consent to automated outreach"
- "Go ahead and start sending"
- Or any other positive response

If you have questions or want to discuss further, just reply and we'll be happy to help.

Best regards,
B2B Matchmaking Platform
"""
        
        return {"subject": subject, "body": body}
    
    def check_provider_response(
        self,
        provider_id: str,
        platform_email: str
    ) -> Dict:
        """
        Check if provider has responded to opt-in email
        
        Args:
            provider_id: Provider ID
            platform_email: Platform email to check responses to
            
        Returns:
            Result dict with response status and sentiment
        """
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            return {"success": False, "error": "Provider not found"}
        
        if not self.gmail_fetcher:
            return {"success": False, "error": "Gmail fetcher not initialized"}
        
        if not provider.opt_in_email_sent_at:
            return {"success": False, "error": "Opt-in email not sent yet"}
        
        try:
            # Fetch threads from provider - search for emails from provider to platform
            threads = self.gmail_fetcher.list_threads(
                query=f"from:{provider.contact_email}",
                max_results=10
            )
            
            if not threads or not threads.get('threads'):
                return {
                    "success": True,
                    "response_received": False,
                    "message": "No response received yet"
                }
            
            # Get the most recent thread
            thread_list = threads.get('threads', [])
            if not thread_list:
                return {
                    "success": True,
                    "response_received": False,
                    "message": "No threads found"
                }
            
            latest_thread = thread_list[0]
            thread_result = self.gmail_fetcher.get_thread(latest_thread['id'])
            
            if not thread_result or not thread_result.get('success'):
                return {
                    "success": True,
                    "response_received": False,
                    "message": "Failed to fetch thread"
                }
            
            messages = thread_result.get('messages', [])
            
            if not messages:
                return {
                    "success": True,
                    "response_received": False,
                    "message": "No messages in thread"
                }
            
            # Get provider's response (most recent message from provider)
            provider_response = None
            for msg in reversed(messages):
                if provider.contact_email in msg.get('from', ''):
                    provider_response = msg
                    break
            
            if not provider_response:
                return {
                    "success": True,
                    "response_received": False,
                    "message": "No response from provider found"
                }
            
            response_text = provider_response.get('body', '')
            
            # Analyze sentiment
            sentiment_result = self._analyze_consent_sentiment(response_text)
            
            # Update provider record
            provider.provider_response_received_at = datetime.utcnow()
            provider.provider_response_text = response_text
            provider.sentiment_analysis_result = sentiment_result
            self.db.commit()
            
            return {
                "success": True,
                "response_received": True,
                "response_text": response_text,
                "sentiment_result": sentiment_result,
                "should_enable_automation": sentiment_result.get("consent", False)
            }
            
        except Exception as e:
            logger.error(f"Failed to check provider response: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_consent_sentiment(self, response_text: str) -> Dict:
        """
        Analyze sentiment of provider response to determine consent
        
        Args:
            response_text: Provider's response text
            
        Returns:
            Dict with sentiment analysis and consent determination
        """
        prompt = f"""Analyze the following email response and determine if the provider is giving consent for automated outreach.

Provider Response:
"{response_text}"

Determine:
1. Is this a positive consent response? (yes/no)
2. What is the sentiment? (positive/neutral/negative)
3. What is the confidence level? (high/medium/low)
4. Key phrases that indicate consent or refusal

Return JSON format:
{{
    "consent": true/false,
    "sentiment": "positive/neutral/negative",
    "confidence": "high/medium/low",
    "key_phrases": ["phrase1", "phrase2"],
    "reasoning": "brief explanation"
}}
"""
        
        try:
            result = self.gemini._make_request(prompt, temperature=0.3)
            
            if result:
                # Try to parse as JSON
                import json
                try:
                    analysis = json.loads(result)
                    return analysis
                except:
                    # Fallback: simple keyword analysis
                    return self._fallback_sentiment_analysis(response_text)
            else:
                return self._fallback_sentiment_analysis(response_text)
                
        except Exception as e:
            logger.error(f"Failed to analyze sentiment: {e}")
            return self._fallback_sentiment_analysis(response_text)
    
    def _fallback_sentiment_analysis(self, response_text: str) -> Dict:
        """
        Fallback sentiment analysis using keywords
        
        Args:
            response_text: Provider's response text
            
        Returns:
            Dict with sentiment analysis
        """
        positive_keywords = ["yes", "sure", "proceed", "consent", "agree", "go ahead", "start", "ok", "approved", "please"]
        negative_keywords = ["no", "don't", "not", "decline", "refuse", "stop", "never", "cancel"]
        
        text_lower = response_text.lower()
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
        
        if positive_count > negative_count:
            return {
                "consent": True,
                "sentiment": "positive",
                "confidence": "medium",
                "key_phrases": [],
                "reasoning": "Keyword-based analysis found positive indicators"
            }
        elif negative_count > positive_count:
            return {
                "consent": False,
                "sentiment": "negative",
                "confidence": "medium",
                "key_phrases": [],
                "reasoning": "Keyword-based analysis found negative indicators"
            }
        else:
            return {
                "consent": False,
                "sentiment": "neutral",
                "confidence": "low",
                "key_phrases": [],
                "reasoning": "Unable to determine consent from keywords"
            }
    
    def process_consent(
        self,
        provider_id: str,
        from_email: str
    ) -> Dict:
        """
        Process provider consent and enable/disable automation
        
        Args:
            provider_id: Provider ID
            from_email: Platform email for acknowledgment
            
        Returns:
            Result dict with action taken
        """
        # Check provider response
        response_check = self.check_provider_response(provider_id, from_email)
        
        if not response_check.get("success"):
            return response_check
        
        if not response_check.get("response_received"):
            return {"success": False, "error": "No response received yet"}
        
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == provider_id
        ).first()
        
        if not provider:
            return {"success": False, "error": "Provider not found"}
        
        sentiment_result = response_check.get("sentiment_result", {})
        consent = sentiment_result.get("consent", False)
        
        if consent:
            # Enable automation
            provider.auto_outreach_enabled = True
            provider.outreach_consent_status = "consented"
            provider.outreach_consent_date = datetime.utcnow()
            provider.automation_settings = {
                "max_emails_per_day": 30,
                "min_match_score": 70,
                "auto_approve_matches": True,
                "template_type": "intro"
            }
            self.db.commit()
            
            # Send acknowledgment email (only if not already sent)
            if not provider.automation_settings.get("acknowledgment_sent"):
                self._send_acknowledgment_email(provider, from_email)
                provider.automation_settings["acknowledgment_sent"] = True
                provider.automation_settings["acknowledgment_sent_at"] = datetime.utcnow().isoformat()
                self.db.commit()
            
            # Trigger automated buyer outreach
            from app.services.provider_automation_service import ProviderAutomationService
            automation_service = ProviderAutomationService(
                db=self.db,
                gmail_credentials_path=None,  # Will use existing Gmail integration
                gmail_token_path=None,
                gemini_api_key=None
            )
            automation_result = automation_service.trigger_provider_automation(provider_id, from_email)
            
            return {
                "success": True,
                "action": "automation_enabled",
                "provider_id": provider_id,
                "message": "Provider consent received and automation enabled",
                "automation_result": automation_result
            }
        else:
            # Mark as declined
            provider.outreach_consent_status = "declined"
            self.db.commit()
            
            return {
                "success": True,
                "action": "consent_declined",
                "provider_id": provider_id,
                "message": "Provider declined consent"
            }
    
    def _send_acknowledgment_email(
        self,
        provider: ServiceProvider,
        from_email: str
    ) -> None:
        """Send acknowledgment email to provider"""
        if not self.gmail_sender:
            logger.warning("Gmail sender not initialized, skipping acknowledgment")
            return
        
        subject = f"Automated Outreach Enabled for {provider.company_name}"
        
        body = f"""Hi {provider.company_name} Team,

Thank you for your consent! We've now enabled automated outreach for your account.

**What happens next:**
• We'll identify high-quality buyer matches based on your ICP
• You'll be notified of new matches for review
• Personalized emails will be sent to approved matches
• You can track all responses and analytics in your dashboard

**Your current settings:**
• Max emails per day: {provider.automation_settings.get('max_emails_per_day', 30)}
• Minimum match score: {provider.automation_settings.get('min_match_score', 70)}
• Auto-approve matches: {provider.automation_settings.get('auto_approve_matches', True)}

You can adjust these settings anytime by replying to this email or contacting support.

Best regards,
B2B Matchmaking Platform
"""
        
        try:
            self.gmail_sender.send_email(
                to_email=provider.contact_email,
                subject=subject,
                body=body,
                from_email=from_email
            )
            logger.info(f"Acknowledgment email sent to {provider.contact_email}")
        except Exception as e:
            logger.error(f"Failed to send acknowledgment email: {e}")
