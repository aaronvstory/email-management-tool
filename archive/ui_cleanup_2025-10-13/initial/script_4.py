# Create the SMTP proxy server
smtp_proxy_content = '''"""
SMTP Proxy Server for Email Interception
Handles both outgoing and incoming email moderation
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from email import message_from_bytes, policy
from email.parser import BytesParser
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message
import sqlite3
import json
import re
import threading
import configparser
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailModerationHandler:
    """Handler for processing intercepted emails"""
    
    def __init__(self, config_path="config/config.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.db_path = "data/email_moderation.db"
        self.setup_database()
        self.load_moderation_rules()
    
    def setup_database(self):
        """Initialize SQLite database"""
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                sender TEXT NOT NULL,
                recipients TEXT NOT NULL,
                subject TEXT,
                raw_content BLOB NOT NULL,
                processed_content BLOB,
                status TEXT DEFAULT 'PENDING',
                direction TEXT DEFAULT 'OUTGOING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by TEXT,
                review_notes TEXT,
                keywords_matched TEXT,
                hold_until TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moderation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                pattern TEXT NOT NULL,
                action TEXT DEFAULT 'HOLD',
                priority INTEGER DEFAULT 100,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                action TEXT NOT NULL,
                user TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT
            )
        ''')
        
        # Insert default moderation rules
        default_rules = [
            ("Invoice Detection", "KEYWORD", "invoice|billing|payment|receipt", "HOLD", 90),
            ("Urgent Messages", "KEYWORD", "urgent|asap|immediate|emergency", "HOLD", 80),
            ("Attachment Detection", "ATTACHMENT", ".*\\.(pdf|doc|docx|xls|xlsx)", "HOLD", 85),
            ("External Recipients", "SENDER_RECIPIENT", "@(?!yourdomain\\.com)", "HOLD", 70)
        ]
        
        for rule in default_rules:
            cursor.execute('''
                INSERT OR IGNORE INTO moderation_rules (name, rule_type, pattern, action, priority)
                VALUES (?, ?, ?, ?, ?)
            ''', rule)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def load_moderation_rules(self):
        """Load active moderation rules from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, rule_type, pattern, action, priority 
            FROM moderation_rules 
            WHERE is_active = 1 
            ORDER BY priority DESC
        ''')
        self.rules = cursor.fetchall()
        conn.close()
        logger.info(f"Loaded {len(self.rules)} moderation rules")
    
    def check_moderation_rules(self, message, sender, recipients):
        """Check if email matches any moderation rules"""
        matched_rules = []
        
        for rule_name, rule_type, pattern, action, priority in self.rules:
            try:
                if rule_type == "KEYWORD":
                    # Check subject and body for keywords
                    subject = message.get('Subject', '')
                    body = self.extract_body_text(message)
                    if re.search(pattern, subject + " " + body, re.IGNORECASE):
                        matched_rules.append(rule_name)
                
                elif rule_type == "SENDER_RECIPIENT":
                    # Check sender and recipient patterns
                    all_addresses = [sender] + recipients
                    for addr in all_addresses:
                        if re.search(pattern, addr, re.IGNORECASE):
                            matched_rules.append(rule_name)
                            break
                
                elif rule_type == "ATTACHMENT":
                    # Check attachment filenames
                    if message.is_multipart():
                        for part in message.walk():
                            filename = part.get_filename()
                            if filename and re.search(pattern, filename, re.IGNORECASE):
                                matched_rules.append(rule_name)
                                break
                
            except Exception as e:
                logger.error(f"Error checking rule {rule_name}: {e}")
        
        return matched_rules
    
    def extract_body_text(self, message):
        """Extract text content from email message"""
        body = ""
        try:
            if message.is_multipart():
                for part in message.walk():
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                if message.get_content_type() == "text/plain":
                    body = message.get_payload(decode=True).decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Error extracting body text: {e}")
        return body
    
    async def handle_DATA(self, server, session, envelope):
        """Handle incoming SMTP DATA command"""
        try:
            # Parse the email message
            message = message_from_bytes(envelope.content, policy=policy.default)
            message_id = str(uuid.uuid4())
            
            sender = envelope.mail_from
            recipients = envelope.rcpt_tos
            subject = message.get('Subject', 'No Subject')
            
            logger.info(f"Intercepted email: {sender} -> {recipients}, Subject: {subject}")
            
            # Check moderation rules
            matched_rules = self.check_moderation_rules(message, sender, recipients)
            
            # Determine if email should be held
            should_hold = len(matched_rules) > 0
            status = 'PENDING' if should_hold else 'APPROVED'
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO email_messages 
                (message_id, sender, recipients, subject, raw_content, status, keywords_matched, hold_until)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_id,
                sender,
                json.dumps(recipients),
                subject,
                envelope.content,
                status,
                json.dumps(matched_rules),
                datetime.now(timezone.utc) + timedelta(hours=24)  # Default 24h hold
            ))
            
            # Log the action
            cursor.execute('''
                INSERT INTO audit_logs (message_id, action, details)
                VALUES (?, ?, ?)
            ''', (
                message_id,
                'EMAIL_INTERCEPTED',
                f"Matched rules: {', '.join(matched_rules) if matched_rules else 'None'}"
            ))
            
            conn.commit()
            conn.close()
            
            if should_hold:
                logger.info(f"Email held for review (ID: {message_id})")
                return f'250 Message accepted for delivery (ID: {message_id}) - Held for review'
            else:
                logger.info(f"Email approved automatically (ID: {message_id})")
                # TODO: Forward to destination immediately
                return f'250 Message accepted for delivery (ID: {message_id})'
        
        except Exception as e:
            logger.error(f"Error handling email: {e}")
            return '451 Temporary failure'

class SMTPProxyServer:
    """SMTP Proxy Server"""
    
    def __init__(self, config_path="config/config.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.handler = EmailModerationHandler(config_path)
        
    def start(self):
        """Start the SMTP proxy server"""
        host = self.config.get('SMTP_PROXY', 'host', fallback='0.0.0.0')
        port = self.config.getint('SMTP_PROXY', 'port', fallback=8587)
        
        controller = Controller(
            self.handler,
            hostname=host,
            port=port,
            # Note: For production, add TLS/SSL configuration
        )
        
        controller.start()
        logger.info(f"SMTP Proxy started on {host}:{port}")
        
        try:
            # Keep the server running
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            logger.info("Stopping SMTP Proxy...")
            controller.stop()

def run_smtp_proxy():
    """Run the SMTP proxy server"""
    server = SMTPProxyServer()
    server.start()

if __name__ == "__main__":
    run_smtp_proxy()
'''

with open("email_moderation_system/app/smtp_proxy.py", "w") as f:
    f.write(smtp_proxy_content)

print("Created SMTP Proxy Server (smtp_proxy.py)")
print("✓ Email interception with aiosmtpd")
print("✓ Rule-based email filtering")
print("✓ SQLite database integration")
print("✓ Audit logging")
print("✓ Configurable moderation rules")