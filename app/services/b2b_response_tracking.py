"""
B2B Buyer Response Tracking Service

Handles monitoring and classification of buyer replies:
- Gmail watch for buyer responses 24/7
- AI classification of buyer responses (interested/not interested/etc.)
- Automated follow-up triggering
- Provider notifications on buyer interest
- All using FREE APIs (Gmail API free tier, GPT-4 via existing integration)
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Match, BuyerCompany, ServiceProvider, Event
from app.integrations.gmail_thread_fetcher import GmailThreadFetcher
from app.integrations.gemini_analysis import GeminiAnalysisService
from app.services.gmail_sender import GmailSender
from app.logging_config import logger as app_logger

logger = app_logger


class B2BResponseClassifier:
    """
    AI-powered buyer response classifier
    
    Classifies buyer replies into categories:
    - interested: Wants to learn more/book meeting
    - not_interested: Explicitly not interested
    - not_now: Interested but not right now
    - more_info: Asking for more information
    - unsubscribe: Wants to unsubscribe
    """
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        self.gemini = GeminiAnalysisService(gemini_api_key) if gemini_api_key else None
    
    def classify_response(self, response_text: str) -> Dict:
        """
        Classify buyer response using AI + keyword fallback
        
        Returns:
            Dict with classification, confidence, and reasoning
        """
        # Try AI classification first
        if self.gemini:
            try:
                ai_result = self._ai_classify(response_text)
                if ai_result.get("confidence", 0) >= 0.7:
                    return ai_result
            except Exception as e:
                logger.warning(f"AI classification failed: {e}, using fallback")
        
        # Fallback to keyword-based classification
        return self._keyword_classify(response_text)
    
    def _ai_classify(self, response_text: str) -> Dict:
        """Use Gemini AI to classify response"""
        try:
            # Use Gemini to analyze sentiment and intent
            result = self.gemini._make_request(
                prompt=f"""
                Analyze this email response and classify it into one category:
                - interested: Positive response, wants to meet/learn more
                - not_interested: Negative response, not interested
                - not_now: Interested but timing is wrong
                - more_info: Asking questions, needs more information
                - unsubscribe: Wants to stop receiving emails
                
                Email: "{response_text}"
                
                Return only the classification and confidence score (0-1).
                Format: category|confidence
                """
            )
            
            if result and "|" in result:
                parts = result.split("|")
                classification = parts[0].strip().lower()
                confidence = float(parts[1].strip()) if len(parts) > 1 else 0.5
                
                valid_categories = ["interested", "not_interested", "not_now", "more_info", "unsubscribe"]
                if classification in valid_categories:
                    return {
                        "classification": classification,
                        "confidence": confidence,
                        "method": "ai",
                        "reasoning": "AI-based analysis"
                    }
            
            return {"classification": "unknown", "confidence": 0.3, "method": "ai"}
            
        except Exception as e:
            logger.error(f"AI classification error: {e}")
            return {"classification": "unknown", "confidence": 0.3, "method": "ai"}
    
    def _keyword_classify(self, response_text: str) -> Dict:
        """Keyword-based classification as fallback"""
        text_lower = response_text.lower()
        
        # Keywords for each category
        interested_keywords = [
            "interested", "yes", "let's talk", "schedule", "meeting", "book",
            "call", "chat", "discuss", "learn more", "tell me more",
            "sounds good", "worth exploring", "open to it", "let's do it"
        ]
        
        not_interested_keywords = [
            "not interested", "not looking", "no thanks", "not now",
            "don't need", "not a fit", "wrong time", "pass", "not relevant"
        ]
        
        not_now_keywords = [
            "not now", "later", "next quarter", "next year", "timing is off",
            "busy now", "come back", "in a few months", "not at the moment"
        ]
        
        more_info_keywords = [
            "more information", "tell me more", "details", "pricing",
            "how does it work", "what is", "explain", "clarify", "questions"
        ]
        
        unsubscribe_keywords = [
            "unsubscribe", "stop emailing", "remove me", "don't email",
            "opt out", "take me off", "no more emails"
        ]
        
        # Count matches for each category
        scores = {
            "interested": sum(1 for kw in interested_keywords if kw in text_lower),
            "not_interested": sum(1 for kw in not_interested_keywords if kw in text_lower),
            "not_now": sum(1 for kw in not_now_keywords if kw in text_lower),
            "more_info": sum(1 for kw in more_info_keywords if kw in text_lower),
            "unsubscribe": sum(1 for kw in unsubscribe_keywords if kw in text_lower)
        }
        
        # Get highest score
        if max(scores.values()) > 0:
            classification = max(scores, key=scores.get)
            confidence = min(0.5 + (scores[classification] * 0.1), 0.8)
            
            return {
                "classification": classification,
                "confidence": confidence,
                "method": "keyword",
                "reasoning": f"Keyword matching: {scores}"
            }
        
        return {
            "classification": "unknown",
            "confidence": 0.3,
            "method": "keyword",
            "reasoning": "No clear keywords found"
        }


class B2BResponseTrackingService:
    """
    B2B Buyer Response Tracking Service
    
    Monitors Gmail for buyer replies and processes them:
    - Watches for responses to sent intros
    - Classifies responses using AI
    - Updates match status
    - Triggers follow-ups
    - Notifies providers
    """
    
    def __init__(
        self,
        db: Session,
        gmail_credentials_path: Optional[str] = None,
        gmail_token_path: Optional[str] = None,
        gemini_api_key: Optional[str] = None
    ):
        self.db = db
        self.gmail_fetcher = GmailThreadFetcher()
        self.gmail_sender = GmailSender(db)
        self.classifier = B2BResponseClassifier(gemini_api_key)
    
    def check_all_pending_responses(self) -> Dict:
        """
        Check for responses from all buyers who received intros
        
        Returns:
            Dict with results of response checking
        """
        logger.info("=== Checking Buyer Responses ===")
        
        results = {
            "checked": 0,
            "responses_found": 0,
            "processed": [],
            "errors": []
        }
        
        # Get all matches with outreach sent but no response yet
        pending_matches = self.db.query(Match).filter(
            and_(
                Match.status == "outreach_sent",
                Match.intro_sent_at != None
            )
        ).all()
        
        logger.info(f"Checking {len(pending_matches)} pending matches")
        
        for match in pending_matches:
            try:
                result = self._check_match_response(match)
                results["checked"] += 1
                
                if result.get("response_found"):
                    results["responses_found"] += 1
                    results["processed"].append(result)
                    
            except Exception as e:
                logger.error(f"Error checking match {match.match_id}: {e}")
                results["errors"].append({
                    "match_id": match.match_id,
                    "error": str(e)
                })
        
        logger.info(f"Response check complete: {results['responses_found']} responses found")
        return results
    
    def _check_match_response(self, match: Match) -> Dict:
        """Check for response from a specific match"""
        buyer = self.db.query(BuyerCompany).filter(
            BuyerCompany.buyer_id == match.buyer_id
        ).first()
        
        if not buyer:
            return {"match_id": match.match_id, "response_found": False, "error": "Buyer not found"}
        
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.provider_id == match.provider_id
        ).first()
        
        if not provider:
            return {"match_id": match.match_id, "response_found": False, "error": "Provider not found"}
        
        # Search for replies from buyer
        try:
            # Query Gmail for messages from buyer
            query = f"from:{buyer.decision_maker_email} newer_than:7d"
            
            # Get threads matching query
            threads = self.gmail_fetcher.search_threads(query)
            
            if not threads:
                return {
                    "match_id": match.match_id,
                    "response_found": False,
                    "buyer": buyer.company_name
                }
            
            # Check each thread for responses to our intro
            for thread in threads:
                messages = self.gmail_fetcher.get_thread_messages(thread["id"])
                
                for message in messages:
                    # Check if this is a reply (not our original message)
                    if message.get("is_inbound", False):
                        # Found a response!
                        response_text = message.get("body", "")
                        
                        # Classify response
                        classification = self.classifier.classify_response(response_text)
                        
                        # Process classified response
                        self._process_buyer_response(match, buyer, provider, classification, message)
                        
                        return {
                            "match_id": match.match_id,
                            "response_found": True,
                            "buyer": buyer.company_name,
                            "classification": classification["classification"],
                            "confidence": classification["confidence"],
                            "message_id": message.get("id")
                        }
            
            return {
                "match_id": match.match_id,
                "response_found": False,
                "buyer": buyer.company_name
            }
            
        except Exception as e:
            logger.error(f"Error checking Gmail for {buyer.decision_maker_email}: {e}")
            return {
                "match_id": match.match_id,
                "response_found": False,
                "error": str(e)
            }
    
    def _process_buyer_response(
        self,
        match: Match,
        buyer: BuyerCompany,
        provider: ServiceProvider,
        classification: Dict,
        message: Dict
    ):
        """Process classified buyer response"""
        category = classification["classification"]
        
        logger.info(f"Processing buyer response: {buyer.company_name} -> {category}")
        
        # Update match based on classification
        if category == "interested":
            match.status = "buyer_interested"
            match.buyer_responded = True
            match.buyer_response_date = datetime.utcnow()
            
            # Notify provider
            self._notify_provider_interested(provider, buyer, match)
            
        elif category == "not_interested":
            match.status = "buyer_declined"
            match.buyer_responded = True
            match.buyer_response_date = datetime.utcnow()
            
        elif category == "not_now":
            match.status = "buyer_not_now"
            match.buyer_responded = True
            match.buyer_response_date = datetime.utcnow()
            
            # Schedule follow-up for later
            match.follow_up_date = datetime.utcnow() + timedelta(days=30)
            
        elif category == "more_info":
            match.status = "buyer_more_info"
            match.buyer_responded = True
            match.buyer_response_date = datetime.utcnow()
            
            # Could trigger auto-response with more info
            # For now, mark for human review
            
        elif category == "unsubscribe":
            match.status = "unsubscribed"
            match.buyer_responded = True
            match.buyer_response_date = datetime.utcnow()
            
            # Mark buyer as unsubscribed
            buyer.active = False
        
        # Store response text
        match.buyer_response_text = message.get("body", "")[:1000]  # Limit length
        match.last_response_classification = category
        
        self.db.commit()
        
        # Log event
        event = Event(
            event_type="buyer_response",
            entity_type="match",
            entity_id=match.match_id,
            data={
                "classification": category,
                "confidence": classification["confidence"],
                "buyer_company": buyer.company_name,
                "provider_company": provider.company_name
            }
        )
        self.db.add(event)
        self.db.commit()
        
        logger.info(f"Response processed: {match.match_id} -> {category}")
    
    def _notify_provider_interested(
        self,
        provider: ServiceProvider,
        buyer: BuyerCompany,
        match: Match
    ):
        """Notify provider that buyer is interested"""
        try:
            subject = f"🎯 Buyer Interested: {buyer.company_name}"
            
            body = f"""
Hi {provider.company_name} Team,

Great news! {buyer.company_name} is interested in your services.

Buyer Details:
- Company: {buyer.company_name}
- Industry: {buyer.industry}
- Size: {buyer.employee_count} employees
- Funding: {buyer.funding_stage}

Match Score: {match.match_score}/100

Next Steps:
1. Review buyer details in your dashboard
2. Reach out directly to schedule a meeting
3. Contact: {buyer.decision_maker_name} ({buyer.decision_maker_title})
   Email: {buyer.decision_maker_email}

Good luck with the conversation!

Best,
Your B2B Matchmaking Platform
"""
            
            # Send notification email to provider
            self.gmail_sender.send_email(
                to_email=provider.contact_email,
                subject=subject,
                body=body,
                from_email="noreply@your-platform.com"
            )
            
            logger.info(f"Provider notified: {provider.company_name} about {buyer.company_name}")
            
        except Exception as e:
            logger.error(f"Failed to notify provider: {e}")
    
    def get_response_stats(self) -> Dict:
        """Get statistics on buyer responses"""
        total_matches = self.db.query(Match).count()
        responded = self.db.query(Match).filter(Match.buyer_responded == True).count()
        interested = self.db.query(Match).filter(Match.status == "buyer_interested").count()
        declined = self.db.query(Match).filter(Match.status == "buyer_declined").count()
        not_now = self.db.query(Match).filter(Match.status == "buyer_not_now").count()
        
        response_rate = (responded / total_matches * 100) if total_matches > 0 else 0
        interested_rate = (interested / responded * 100) if responded > 0 else 0
        
        return {
            "total_matches": total_matches,
            "responded": responded,
            "response_rate": round(response_rate, 2),
            "interested": interested,
            "interested_rate": round(interested_rate, 2),
            "declined": declined,
            "not_now": not_now,
            "pending": total_matches - responded
        }


# Celery task for scheduled response checking
from celery import shared_task

@shared_task
def check_buyer_responses_task():
    """
    Celery task to check buyer responses
    
    Runs every hour via Celery Beat schedule
    """
    from app.database import SessionLocal
    from app.settings import settings
    
    db = SessionLocal()
    try:
        service = B2BResponseTrackingService(
            db=db,
            gemini_api_key=settings.GEMINI_API_KEY
        )
        
        results = service.check_all_pending_responses()
        
        return {
            "status": "success",
            "checked": results["checked"],
            "responses_found": results["responses_found"],
            "processed": len(results["processed"])
        }
        
    except Exception as e:
        logger.error(f"Response checking task failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@shared_task
def run_b2b_followups_task():
    """
    Celery task to run B2B follow-up sequences
    
    Runs daily via Celery Beat schedule
    """
    from app.database import SessionLocal
    from app.services.b2b_followup_service import B2BFollowupService
    
    db = SessionLocal()
    try:
        service = B2BFollowupService(db)
        results = service.process_all_followups()
        
        return {
            "status": "success",
            "followups_sent": results["sent"],
            "skipped": results["skipped"],
            "errors": len(results["errors"])
        }
        
    except Exception as e:
        logger.error(f"Follow-up task failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
