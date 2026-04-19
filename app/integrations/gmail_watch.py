from app.settings import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import os


class GmailWatch:
    """Service for setting up Gmail push notifications"""
    
    def __init__(self):
        self.scopes = settings.GMAIL_SCOPES.split(',')
        self.credentials = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        token_path = settings.GMAIL_TOKEN_PATH
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.GMAIL_CREDENTIALS_PATH,
                    self.scopes
                )
                creds = flow.run_local_server(port=0)
            
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.credentials = creds
        self.service = build('gmail', 'v1', credentials=self.credentials)
    
    def watch_mailbox(self, webhook_url: str, topic_name: str):
        """Set up Gmail push notifications for mailbox changes"""
        try:
            request_body = {
                'topicName': topic_name,
                'labelIds': ['INBOX']
            }
            
            response = self.service.users().watch(
                userId='me',
                body=request_body
            ).execute()
            
            return {
                'success': True,
                'historyId': response.get('historyId'),
                'expiration': response.get('expiration')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def stop_watch(self):
        """Stop Gmail push notifications"""
        try:
            self.service.users().stop(userId='me').execute()
            return {'success': True}
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
