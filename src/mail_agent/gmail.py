"""
Gmail API integration for Mail Agent.
"""
import base64
import email
import email.utils
from typing import List, Optional, Dict, Any
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GmailMessage:
    """Represents a Gmail message with its metadata and content."""
    
    def __init__(self, message_data: Dict[str, Any], service=None):
        """
        Initialize a GmailMessage from Gmail API message data.
        
        Args:
            message_data: Raw message data from Gmail API
            service: Gmail API service instance for additional operations
        """
        self.service = service
       
        self._headers_cache = None

        # Parse payload for message content
        self._payload = message_data.get('payload', {})

        # Initialize message data
        self._message_data = message_data or {}
        self._payload = message_data.get('payload', {})
        
    @property
    def id(self) -> str | None :
        """Get the message ID."""
        return self._message_data.get('id')
    
    @property
    def thread_id(self) -> str | None:
        """Get the thread ID."""
        return self._message_data.get('threadId')
    
    @property
    def label_ids(self) -> List[str]:
        """Get the list of label IDs."""
        return self._message_data.get('labelIds', [])
    
    @property
    def snippet(self) -> str:
        """Get the message snippet."""
        return self._message_data.get('snippet', '')
        
    @property
    def subject(self) -> str:
        """Get the email subject."""
        return self.headers.get('Subject', '')
    
    @property
    def sender(self) -> str:
        """Get the email sender."""
        return self.headers.get('From', '')
    
    @property
    def recipient(self) -> str:
        """Get the email recipient."""
        return self.headers.get('To', '')
    
    @property
    def date_str(self) -> str:
        """Get the email date as a string."""
        return self.headers.get('Date', '')
    
    @property
    def message_id(self) -> str:
        """Get the email Message-ID."""
        return self.headers.get('Message-ID', '')
        

    @property
    def headers(self):
        """Get message headers as a dictionary."""
        if self._headers_cache is None:
            self._headers_cache = self._parse_headers(self._payload.get('headers', []))
        return self._headers_cache
    
    def _parse_headers(self, headers: List[Dict[str, str]]) -> Dict[str, str]:
        """Parse headers list into a dictionary."""
        return {header['name']: header['value'] for header in headers}
    
    @property
    def date(self) -> Optional[datetime]:
        """Parse email date string into datetime object."""

        try:
            # Parse RFC 2822 date format
            parsed_date = email.utils.parsedate_to_datetime(self.date_str)
            return parsed_date
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse date '{self.date_str}': {e}")
            return None
    

    
    @property
    def body_text(self):
        """Get message body content, extracting it if needed."""
        
        if 'parts' in self._payload:
            for part in self._payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    data = part.get('body', {}).get('data')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        else:
            mime_type = self._payload.get('mimeType', '')
            if mime_type == 'text/plain':
                data = self._payload.get('body', {}).get('data')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    
    
    def has_label(self, label_name: str) -> bool:
        """Check if the message has a specific label."""
        return label_name in self.label_ids
    
    def add_label(self, label_id: str) -> bool:
        """
        Add a label to this message.
        
        Args:
            label_id: The label ID to add
            
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.error("No Gmail service available for adding labels")
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=self.id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            # Update local label list
            if label_id not in self.label_ids:
                self.label_ids.append(label_id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to add label {label_id} to message {self.id}: {e}")
            return False
    
    def remove_label(self, label_id: str) -> bool:
        """
        Remove a label from this message.
        
        Args:
            label_id: The label ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.error("No Gmail service available for removing labels")
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=self.id,
                body={'removeLabelIds': [label_id]}
            ).execute()
            
            # Update local label list
            if label_id in self.label_ids:
                self.label_ids.remove(label_id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to remove label {label_id} from message {self.id}: {e}")
            return False
    

    
    def __repr__(self) -> str:
        return f"<GmailMessage id={self.id} subject='{self.subject[:50]}...'>"


class Gmail:
    """Gmail API client integrated with MailAgentApp."""
    
    def __init__(self, app, user_id: int):
        """
        Initialize Gmail client with MailAgentApp and user.
        
        Args:
            app: MailAgentApp instance
            user_id: User ID from the database
        """
        self.app = app
        self.user_id = user_id
        self.service = None
        self._labels_cache = None
    
    def _get_service(self):
        """
        Get authenticated Gmail service for the user.
        
        Returns:
            Gmail API service instance
        """
        from mail_agent.models import User
        
        with self.app.app_context():
            user = User.query.get(self.user_id)
            if not user or not user.access_token:
                raise ValueError(f"No valid access token found for user {self.user_id}")
            
            # Create credentials from stored tokens
            credentials = Credentials(
                token=user.access_token,
                refresh_token=user.refresh_token,
                token_uri=self.app.config['GOOGLE_CLIENT_SECRETS']['web']['token_uri'],
                client_id=self.app.config['GOOGLE_CLIENT_SECRETS']['web']['client_id'],
                client_secret=self.app.config['GOOGLE_CLIENT_SECRETS']['web']['client_secret']
            )
            
            # Check if token is expired
            if credentials.expired:
                if credentials.refresh_token:
                    logger.info(f"Access token expired for user {self.user_id}, refreshing...")
                    credentials.refresh(Request())
                    
                    # Update stored tokens
                    user.access_token = credentials.token
                    if credentials.refresh_token:
                        user.refresh_token = credentials.refresh_token
                    self.app.db.session.commit()
                    logger.info(f"Successfully refreshed tokens for user {self.user_id}")
                else:
                    logger.warning(f"Access token expired for user {self.user_id} but no refresh token available")
                    # Continue anyway - the token might still work for a short time
            
            # Build and return service
            service = build('gmail', 'v1', credentials=credentials)
            return service
    
    def get_labels(self) -> Dict[str, str]:
        """
        Get all labels for the user, returning a mapping of label names to IDs.
        
        Returns:
            Dictionary mapping label names to label IDs
        """
        service = self._get_service()
        
        try:
            results = service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Create mapping of label names to IDs
            label_map = {}
            for label in labels:
                label_map[label['name']] = label['id']
            
            self._labels_cache = label_map
            return label_map
        
        except Exception as e:
            logger.error(f"Failed to fetch labels for user {self.user_id}: {e}")
            return {}
    
    def get_label_id(self, label_name: str) -> Optional[str]:
        """
        Get the label ID for a given label name.
        
        Args:
            label_name: Name of the label
            
        Returns:
            Label ID if found, None otherwise
        """
        if not self._labels_cache:
            self._labels_cache = self.get_labels()
        
        return self._labels_cache.get(label_name)
    
    def read_inbox_emails(self, max_results: int = 100) -> List[GmailMessage]:
        """
        Read all emails in the inbox.
        
        Args:
            max_results: Maximum number of emails to return
            
        Returns:
            List of GmailMessage objects
        """
        service = self._get_service()
        
        try:
            # Get message IDs from inbox
            results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Fetch full message data for each message
            gmail_messages = []
            for message in messages:
                try:
                    msg_data = service.users().messages().get(
                        userId='me',
                        id=message['id']
                    ).execute()
                    
                    gmail_message = GmailMessage(msg_data, service)
                    gmail_messages.append(gmail_message)
                    
                except Exception as e:
                    logger.error(f"Failed to fetch message {message['id']}: {e}")
                    continue
            
            return gmail_messages
        
        except Exception as e:
            logger.error(f"Failed to read inbox emails for user {self.user_id}: {e}")
            return []
    
    def find_emails_with_label(self, label_name: str, max_results: int = 100) -> List[GmailMessage]:
        """
        Find emails that have a specific label.
        
        Args:
            label_name: Name of the label to search for
            max_results: Maximum number of emails to return
            
        Returns:
            List of GmailMessage objects with the specified label
        """
        label_id = self.get_label_id(label_name)
        if not label_id:
            logger.warning(f"Label '{label_name}' not found for user {self.user_id}")
            return []
        
        service = self._get_service()
        
        try:
            # Get message IDs with the specified label
            results = service.users().messages().list(
                userId='me',
                labelIds=[label_id],
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Fetch full message data for each message
            gmail_messages = []
            for message in messages:
                try:
                    msg_data = service.users().messages().get(
                        userId='me',
                        id=message['id']
                    ).execute()
                    
                    gmail_message = GmailMessage(msg_data, service)
                    gmail_messages.append(gmail_message)
                    
                except Exception as e:
                    logger.error(f"Failed to fetch message {message['id']}: {e}")
                    continue
            
            return gmail_messages
        
        except Exception as e:
            logger.error(f"Failed to find emails with label '{label_name}' for user {self.user_id}: {e}")
            return []
    
    def find_emails_without_label(self, label_name: str, max_results: int = 100) -> List[GmailMessage]:
        """
        Find emails that do NOT have a specific label.
        
        Args:
            label_name: Name of the label to exclude
            max_results: Maximum number of emails to return
            
        Returns:
            List of GmailMessage objects without the specified label
        """
        label_id = self.get_label_id(label_name)
        if not label_id:
            logger.warning(f"Label '{label_name}' not found for user {self.user_id}")
            # If label doesn't exist, all emails don't have it
            return self.fetch_all(max_results)
        
        service = self._get_service()
        
        try:
            # Use search query to exclude the label
            query = f"-label:{label_name}"
            
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Fetch full message data for each message
            gmail_messages = []
            for message in messages:
                try:
                    msg_data = service.users().messages().get(
                        userId='me',
                        id=message['id']
                    ).execute()
                    
                    gmail_message = GmailMessage(msg_data, service)
                    gmail_messages.append(gmail_message)
                    
                except Exception as e:
                    logger.error(f"Failed to fetch message {message['id']}: {e}")
                    continue
            
            return gmail_messages
        
        except Exception as e:
            logger.error(f"Failed to find emails without label '{label_name}' for user {self.user_id}: {e}")
            return []
    
    def fetch_all(self, max_results: int = 100) -> List[GmailMessage]:
        """
        Find all emails in the account.
        
        Args:
            max_results: Maximum number of emails to return (can exceed 500)
            
        Returns:
            List of GmailMessage objects
        """
        service = self._get_service()
        
        try:
            all_messages = []
            next_page_token = None
            
            while len(all_messages) < max_results:
                # Calculate how many to fetch in this batch (max 500 per API call)
                batch_size = min(500, max_results - len(all_messages))
                
                # Get message IDs for this page
                request_params = {
                    'userId': 'me',
                    'maxResults': batch_size
                }
                
                if next_page_token:
                    request_params['pageToken'] = next_page_token
                
                results = service.users().messages().list(**request_params).execute()
                
                messages = results.get('messages', [])
                if not messages:
                    break  # No more messages
                
                # Fetch full message data for each message in this batch
                for message in messages:
                    if len(all_messages) >= max_results:
                        break
                        
                    try:
                        msg_data = service.users().messages().get(
                            userId='me',
                            id=message['id']
                        ).execute()
                        
                        gmail_message = GmailMessage(msg_data, service)
                        all_messages.append(gmail_message)
                        
                    except Exception as e:
                        logger.error(f"Failed to fetch message {message['id']}: {e}")
                        continue
                
                # Check if there are more pages
                next_page_token = results.get('nextPageToken')
                if not next_page_token:
                    break  # No more pages
            
            return all_messages
        
        except Exception as e:
            logger.error(f"Failed to find all emails for user {self.user_id}: {e}")
            return []
    
    def fetch_envelopes(self, max_results: int = 100) -> List[GmailMessage]:
        """
        Find email envelopes (metadata only) without message bodies.
        This is more efficient when you only need sender, recipient, subject, etc.
        Uses batch requests for much better performance.
        
        Args:
            max_results: Maximum number of emails to return (can exceed 500)
            
        Returns:
            List of GmailMessage objects with metadata only (no body content)
        """
        service = self._get_service()
        
        try:
            all_messages = []
            next_page_token = None
            
            while len(all_messages) < max_results:
                # Calculate how many to fetch in this batch (max 500 per API call)
                batch_size = min(500, max_results - len(all_messages))
                
                # Get message IDs for this page
                request_params = {
                    'userId': 'me',
                    'maxResults': batch_size
                }
                
                if next_page_token:
                    request_params['pageToken'] = next_page_token
                
                results = service.users().messages().list(**request_params).execute()
                
                messages = results.get('messages', [])
                if not messages:
                    break  # No more messages
                
                # Use batch requests to fetch message envelopes efficiently
                # Process in batches of 50 (conservative batch size to avoid rate limits)
                message_batch_size = 5
                messages_to_process = messages[:min(len(messages), max_results - len(all_messages))]
                
                for i in range(0, len(messages_to_process), message_batch_size):
                    batch_messages = messages_to_process[i:i + message_batch_size]
                    
                    # Create batch request
                    batch = service.new_batch_http_request()
                    batch_results = {}
                    
                    def create_callback(msg_id):
                        def callback(request_id, response, exception):
                            if exception is not None:
                                # Check if it's an authentication error
                                if hasattr(exception, 'resp') and exception.resp.status == 401:
                                    logger.error(f"Authentication failed for message {msg_id}: {exception}")
                                else:
                                    logger.error(f"Failed to fetch message envelope {msg_id}: {exception}")
                            else:
                                batch_results[msg_id] = response
                        return callback
                    
                    # Add requests to batch
                    for message in batch_messages:
                        msg_id = message['id']
                        request = service.users().messages().get(
                            userId='me',
                            id=msg_id,
                            format='metadata',
                            metadataHeaders=['From', 'To', 'Subject', 'Date', 'Message-ID']
                        )
                        batch.add(request, callback=create_callback(msg_id))
                    
                    # Execute batch request
                    batch.execute()
                    
                    # Process batch results
                    for message in batch_messages:
                        msg_id = message['id']
                        if msg_id in batch_results:
                            try:
                                gmail_message = GmailMessage(batch_results[msg_id], service)
                                all_messages.append(gmail_message)
                            except Exception as e:
                                logger.error(f"Failed to process message envelope {msg_id}: {e}")
                        
                        if len(all_messages) >= max_results:
                            break
                    
                    if len(all_messages) >= max_results:
                        break
                
                # Check if there are more pages
                next_page_token = results.get('nextPageToken')
                if not next_page_token or len(all_messages) >= max_results:
                    break  # No more pages or reached limit
            
            return all_messages
        
        except Exception as e:
            logger.error(f"Failed to find email envelopes for user {self.user_id}: {e}")
            return []
