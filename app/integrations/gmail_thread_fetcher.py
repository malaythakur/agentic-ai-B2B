from app.settings import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import os
from typing import Dict, List


class GmailThreadFetcher:
    """Service for fetching Gmail threads and messages"""
    
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
    
    def get_thread(self, thread_id: str) -> Dict:
        """Fetch a Gmail thread with all messages"""
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            
            messages = []
            for msg in thread.get('messages', []):
                payload = msg.get('payload', {})
                headers = {h['name']: h['value'] for h in payload.get('headers', [])}
                
                # Extract body
                body = self._extract_body(payload)
                
                messages.append({
                    'message_id': msg['id'],
                    'thread_id': msg['threadId'],
                    'from': headers.get('From'),
                    'to': headers.get('To'),
                    'subject': headers.get('Subject'),
                    'date': headers.get('Date'),
                    'body': body
                })
            
            return {
                'success': True,
                'thread_id': thread_id,
                'messages': messages
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        import base64
                        return base64.urlsafe_b64decode(data).decode('utf-8')
        elif 'body' in payload:
            data = payload['body'].get('data', '')
            if data:
                import base64
                return base64.urlsafe_b64decode(data).decode('utf-8')
        return ""
    
    def get_message(self, message_id: str) -> Dict:
        """Fetch a single Gmail message"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            payload = message.get('payload', {})
            headers = {h['name']: h['value'] for h in payload.get('headers', [])}
            body = self._extract_body(payload)
            
            return {
                'success': True,
                'message_id': message_id,
                'thread_id': message.get('threadId'),
                'from': headers.get('From'),
                'to': headers.get('To'),
                'subject': headers.get('Subject'),
                'date': headers.get('Date'),
                'body': body
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_threads(self, label_ids: List[str] = None, max_results: int = 10, query: str = None) -> Dict:
        """List threads from Gmail"""
        try:
            result = self.service.users().threads().list(
                userId='me',
                labelIds=label_ids,
                maxResults=max_results,
                q=query
            ).execute()
            
            threads = result.get('threads', [])
            return {
                'success': True,
                'threads': threads,
                'next_page_token': result.get('nextPageToken')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
