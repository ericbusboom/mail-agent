from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from typing import Optional

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
