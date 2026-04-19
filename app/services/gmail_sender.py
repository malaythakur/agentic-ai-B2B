import base64
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models import OutboundMessage, Lead, Event
from app.settings import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
import pickle
import os
import logging
from app.services.deliverability import DeliverabilitySystem
from app.services.conversation_memory import ConversationMemoryLayer
from app.services.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

class GmailSender:
    """Gmail API sender with proper authentication and rate limiting"""
    
    def __init__(self, db: Session, account_type: str = "free_gmail"):
        self.db = db
        self.account_type = account_type
        self.scopes = settings.GMAIL_SCOPES.split(',')
        self.credentials = None
        self.service = None
        self.deliverability = DeliverabilitySystem(db)
        self.conversation_memory = ConversationMemoryLayer(db)
        self._authenticate()
        
        # Initialize rate limiter
        self.rate_limiter = get_rate_limiter(account_type)
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        token_path = settings.GMAIL_TOKEN_PATH
        
        if os.path.exists(token_path):
            try:
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"Failed to load token: {e}")
                creds = None
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    creds = None
            else:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        settings.GMAIL_CREDENTIALS_PATH,
                        self.scopes
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Authentication flow failed: {e}")
                    raise
            
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.credentials = creds
        self._build_service()
    
    def _build_service(self):
        """Build Gmail API service"""
        from googleapiclient.discovery import build
        self.service = build('gmail', 'v1', credentials=self.credentials)
    
    def send_email(self, to_email: str, subject: str, body: str, from_email: str = None) -> Optional[str]:
        """
        Send email directly without database persistence
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            from_email: Sender email (optional, defaults to authenticated user)
            
        Returns:
            Message ID if successful, None otherwise
        """
        # Check rate limit before sending
        can_send, reason = self.rate_limiter.can_send_email()
        if not can_send:
            logger.warning(f"Rate limit reached: {reason}")
            return None
        
        try:
            import base64
            from email.mime.text import MIMEText
            import email
            
            # Create message
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = subject
            if from_email:
                message['from'] = from_email
            
            # Log what we're trying to send
            logger.info(f"Attempting to send email TO: {to_email}, FROM: {from_email or 'authenticated account'}")
            print(f"[GmailSender] Sending TO: {to_email}, FROM: {from_email or 'authenticated account'}")
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send via Gmail API
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            # Log the actual result
            logger.info(f"Email sent successfully. Message ID: {sent_message.get('id')}")
            
            message_id = sent_message.get('id')
            if not message_id:
                # Fallback: generate a message ID if Gmail doesn't return one
                import uuid
                message_id = f"msg-{uuid.uuid4().hex[:16]}"
            
            # Record email sent in rate limiter
            self.rate_limiter.record_email_sent()
            
            return message_id
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            return None
    
    def send_message(self, message_id: str) -> Dict:
        """Send a single email message with deliverability check"""
        message = self.db.query(OutboundMessage).filter(
            OutboundMessage.message_id == message_id
        ).first()
        
        if not message:
            return {"success": False, "error": "Message not found"}
        
        # Skip deliverability check for auto-approved messages
        skip_check = message.personalization_method in ["tier2_approved", "auto_tier1"]
        
        if not skip_check:
            # Check deliverability before sending
            can_send = self.deliverability.can_send(message.from_email)
            if not can_send["can_send"]:
                return {
                    "success": False,
                    "error": f"Deliverability check failed: {can_send['reason']}",
                    "details": can_send
                }
        
        try:
            # Create RFC 2822 email
            raw_message = self._create_raw_message(message)
            
            # Send via Gmail API
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            # Update message record
            message.gmail_message_id = sent_message['id']
            message.gmail_thread_id = sent_message.get('threadId')
            message.status = 'sent'
            message.sent_at = datetime.utcnow()
            
            # Update lead status
            lead = self.db.query(Lead).filter(Lead.lead_id == message.lead_id).first()
            if lead:
                lead.status = 'sent'
            
            # Record send in deliverability system
            self.deliverability.record_send(message.from_email)
            
            # Record in conversation memory
            self.conversation_memory.record_email_sent(
                message_id, message.lead_id, message.subject, message.body
            )
            
            # Log event
            self._log_event(
                event_type="email_sent",
                entity_type="outbound_message",
                entity_id=message_id,
                data={
                    "gmail_message_id": sent_message['id'],
                    "gmail_thread_id": sent_message.get('threadId'),
                    "to_email": message.to_email
                }
            )
            
            self.db.commit()
            
            return {
                "success": True,
                "gmail_message_id": sent_message['id'],
                "gmail_thread_id": sent_message.get('threadId')
            }
            
        except Exception as e:
            # Update message with error
            message.status = 'failed'
            message.failed_at = datetime.utcnow()
            message.error_message = str(e)
            message.retry_count += 1
            
            self.db.commit()
            
            # Log event
            self._log_event(
                event_type="email_failed",
                entity_type="outbound_message",
                entity_id=message_id,
                data={"error": str(e), "retry_count": message.retry_count}
            )
            
            return {"success": False, "error": str(e)}
    
    def _create_raw_message(self, message: OutboundMessage) -> str:
        """Create RFC 2822 formatted email"""
        msg = MIMEMultipart()
        msg['To'] = message.to_email
        msg['From'] = message.from_email
        msg['Subject'] = message.subject
        
        # Add body
        msg.attach(MIMEText(message.body, 'plain'))
        
        # Encode to base64url
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        return raw
    
    def send_batch(self, run_id: str, rate_limit: int = 10) -> Dict:
        """Send all messages in a batch with rate limiting"""
        messages = self.db.query(OutboundMessage).filter(
            OutboundMessage.run_id == run_id,
            OutboundMessage.status == 'queued'
        ).all()
        
        results = {
            "total": len(messages),
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        for i, message in enumerate(messages):
            try:
                # Rate limiting
                if i > 0 and i % rate_limit == 0:
                    time.sleep(1)  # Pause every N messages
                
                result = self.send_message(message.message_id)
                
                if result["success"]:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "message_id": message.message_id,
                        "error": result.get("error", "Unknown error")
                    })
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "message_id": message.message_id,
                    "error": str(e)
                })
        
        # Log batch event
        self._log_event(
            event_type="batch_sent",
            entity_type="campaign_run",
            entity_id=run_id,
            data=results
        )
        
        return results
    
    def _log_event(self, event_type: str, entity_type: str, entity_id: str, data: Dict):
        """Log an event to the events table"""
        import uuid
        event = Event(
            event_id=f"{event_type}-{entity_id}-{str(uuid.uuid4())[:8]}",
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            data=data
        )
        self.db.add(event)
