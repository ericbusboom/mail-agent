from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mail_agent.gmail import GmailMessage

# Initialize SQLAlchemy without app (will be initialized in app.py)
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id: int = db.Column(db.Integer, primary_key=True)
    name: Optional[str] = db.Column(db.String(120))
    email: str  = db.Column(db.String(120), unique=True, nullable=False)
    google_id: str = db.Column(db.String(120), unique=True, nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at: datetime = db.Column(db.DateTime, default=datetime.now(timezone.utc), 
                           onupdate=datetime.now(timezone.utc))
    # Keeping this field for backward compatibility but will be deprecated
    processing_instructions = db.Column(db.Text, default="")
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expiry = db.Column(db.DateTime)
    
    # Relationships
    instructions = db.relationship('Instruction', backref='user', lazy=True, cascade='all, delete-orphan')
    logs = db.relationship('ProcessingLog', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'

class Instruction(db.Model):
    __tablename__ = 'instruction'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    instruction_type = db.Column(db.String(20), nullable=False)  # 'system' or 'user'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), 
                           onupdate=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Instruction {self.name}>'

class ProcessingLog(db.Model):
    __tablename__ = 'processing_log'
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.String(255), nullable=False)  # Google's email ID
    email_subject = db.Column(db.String(255))  # Email subject for easier reference
    processing_time = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    description = db.Column(db.Text)  # Description of the processing from the AI
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<ProcessingLog {self.email_id}>'

class Email(db.Model):
    __tablename__ = 'email'
    
    # Primary key and identifiers
    id = db.Column(db.String(255), primary_key=True)  # Gmail message ID
    thread_id = db.Column(db.String(255))  # Gmail thread ID
    message_id = db.Column(db.String(255))  # Email Message-ID header
    
    # Email metadata
    send_time = db.Column(db.DateTime(timezone=True))  # When the email was sent (with timezone)
    from_address = db.Column(db.String(500))  # Sender email address
    to_address = db.Column(db.Text)  # Recipient email addresses
    subject = db.Column(db.Text)  # Email subject
    body = db.Column(db.Text)  # Email body content
    snippet = db.Column(db.String(500))  # Gmail snippet
    
    # Labels and status flags
    labels = db.Column(db.Text)  # Comma-separated list of labels
    is_in_inbox = db.Column(db.Boolean, default=False)
    is_spam = db.Column(db.Boolean, default=False)
    is_starred = db.Column(db.Boolean, default=False)
    is_trash = db.Column(db.Boolean, default=False)
    is_unread = db.Column(db.Boolean, default=True)
    is_sent = db.Column(db.Boolean, default=False)
    is_important = db.Column(db.Boolean, default=False)
    
    # Timestamps and relationships
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), 
                          onupdate=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('emails', lazy=True))
    
    @classmethod
    def from_gmail(cls, gmail_message: 'GmailMessage', user_id: int) -> 'Email':
        """
        Create an Email model instance from a GmailMessage object.
        
        Args:
            gmail_message: GmailMessage instance
            user_id: User ID to associate with this email
            
        Returns:
            Email model instance
        """
        # Parse labels and determine status flags
        label_ids = gmail_message.label_ids
        labels_str = ','.join(label_ids) if label_ids else ''
        
        email = cls()
        email.id = gmail_message.id
        email.thread_id = gmail_message.thread_id
        email.message_id = gmail_message.message_id
        
        # Ensure send_time is timezone-aware
        if gmail_message.date:
            # If date is already timezone-aware, use it directly
            email.send_time = gmail_message.date
        else:
            # If date is missing, use the current time with UTC timezone
            email.send_time = datetime.now(timezone.utc)
            
        email.from_address = gmail_message.sender
        email.to_address = gmail_message.recipient
        email.subject = gmail_message.subject
        email.body = gmail_message.body_text
        email.snippet = gmail_message.snippet
        email.labels = labels_str
        email.is_in_inbox = 'INBOX' in label_ids
        email.is_spam = 'SPAM' in label_ids
        email.is_starred = 'STARRED' in label_ids
        email.is_trash = 'TRASH' in label_ids
        email.is_unread = 'UNREAD' in label_ids
        email.is_sent = 'SENT' in label_ids
        email.is_important = 'IMPORTANT' in label_ids
        email.user_id = user_id
        return email
    
    @classmethod
    def create_or_update_from_gmail(cls, gmail_message: 'GmailMessage', user_id: int) -> 'Email':
        """
        Create a new Email or update existing one from GmailMessage.
        
        Args:
            gmail_message: GmailMessage instance
            user_id: User ID to associate with this email
            
        Returns:
            Email model instance (new or updated)
        """
        existing_email = cls.query.filter_by(id=gmail_message.id, user_id=user_id).first()
        
        if existing_email:
            # Update existing email
            existing_email.thread_id = gmail_message.thread_id
            existing_email.message_id = gmail_message.message_id
            
            # Ensure send_time is timezone-aware
            if gmail_message.date:
                # If date is already timezone-aware, use it directly
                existing_email.send_time = gmail_message.date
            else:
                # If date is missing, use the current time with UTC timezone
                existing_email.send_time = datetime.now(timezone.utc)
                
            existing_email.from_address = gmail_message.sender
            existing_email.to_address = gmail_message.recipient
            existing_email.subject = gmail_message.subject
            existing_email.body = gmail_message.body_text
            existing_email.snippet = gmail_message.snippet
            
            # Update labels and flags
            label_ids = gmail_message.label_ids
            existing_email.labels = ','.join(label_ids) if label_ids else ''
            existing_email.is_in_inbox = 'INBOX' in label_ids
            existing_email.is_spam = 'SPAM' in label_ids
            existing_email.is_starred = 'STARRED' in label_ids
            existing_email.is_trash = 'TRASH' in label_ids
            existing_email.is_unread = 'UNREAD' in label_ids
            existing_email.is_sent = 'SENT' in label_ids
            existing_email.is_important = 'IMPORTANT' in label_ids
            existing_email.updated_at = datetime.now(timezone.utc)
            
            return existing_email
        else:
            # Create new email
            return cls.from_gmail(gmail_message, user_id)
    
    def get_label_list(self) -> list[str]:
        """
        Get labels as a list instead of comma-separated string.
        
        Returns:
            List of label IDs
        """
        if not self.labels:
            return []
        return [label.strip() for label in self.labels.split(',') if label.strip()]
    
    def has_label(self, label_id: str) -> bool:
        """
        Check if this email has a specific label.
        
        Args:
            label_id: Label ID to check for
            
        Returns:
            True if email has the label, False otherwise
        """
        return label_id in self.get_label_list()
    
    def __repr__(self):
        return f'<Email {self.id} from="{self.from_address}" subject="{self.subject[:50]}...">'
