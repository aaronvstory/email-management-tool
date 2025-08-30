# Create the database models
models_content = '''"""
Database models for the Email Moderation System
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import json

db = SQLAlchemy()

class EmailMessage(db.Model):
    """Model for storing email messages in the moderation queue"""
    __tablename__ = 'email_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(255), unique=True, nullable=False)
    sender = db.Column(db.String(255), nullable=False)
    recipients = db.Column(db.Text, nullable=False)  # JSON array
    subject = db.Column(db.Text)
    raw_content = db.Column(db.LargeBinary, nullable=False)  # Original RFC822
    processed_content = db.Column(db.LargeBinary)  # Modified content
    status = db.Column(db.String(50), default='PENDING')  # PENDING, APPROVED, REJECTED, SENT
    direction = db.Column(db.String(10), default='OUTGOING')  # OUTGOING, INCOMING
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.String(255))
    review_notes = db.Column(db.Text)
    keywords_matched = db.Column(db.Text)  # JSON array
    hold_until = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<EmailMessage {self.message_id}>'
    
    def get_recipients_list(self):
        return json.loads(self.recipients) if self.recipients else []
    
    def set_recipients_list(self, recipients_list):
        self.recipients = json.dumps(recipients_list)
    
    def get_keywords_matched_list(self):
        return json.loads(self.keywords_matched) if self.keywords_matched else []
    
    def set_keywords_matched_list(self, keywords_list):
        self.keywords_matched = json.dumps(keywords_list)

class EmailAccount(db.Model):
    """Model for storing email account configurations"""
    __tablename__ = 'email_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    imap_server = db.Column(db.String(255))
    imap_port = db.Column(db.Integer, default=993)
    imap_username = db.Column(db.String(255))
    imap_password = db.Column(db.String(255))  # Should be encrypted in production
    smtp_server = db.Column(db.String(255))
    smtp_port = db.Column(db.Integer, default=587)
    smtp_username = db.Column(db.String(255))
    smtp_password = db.Column(db.String(255))  # Should be encrypted in production
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_tested = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<EmailAccount {self.email}>'

class ModerationRule(db.Model):
    """Model for storing email moderation rules"""
    __tablename__ = 'moderation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    rule_type = db.Column(db.String(50), nullable=False)  # KEYWORD, SENDER_RECIPIENT, ATTACHMENT
    pattern = db.Column(db.Text, nullable=False)
    action = db.Column(db.String(50), default='HOLD')  # HOLD, BLOCK, APPROVE
    priority = db.Column(db.Integer, default=100)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<ModerationRule {self.name}>'

class AuditLog(db.Model):
    """Model for storing audit logs"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(255), db.ForeignKey('email_messages.message_id'))
    action = db.Column(db.String(100), nullable=False)
    user = db.Column(db.String(255))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(45))
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user}>'
'''

with open("email_moderation_system/app/models.py", "w") as f:
    f.write(models_content)

print("Created database models (models.py)")
print("✓ EmailMessage model for queue management")
print("✓ EmailAccount model for IMAP/SMTP configurations") 
print("✓ ModerationRule model for filtering rules")
print("✓ AuditLog model for compliance tracking")