# Create the SMTP proxy server - fixed indentation
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
        cursor.execute("""
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
        """)
        
        cursor.execute("""
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
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                action TEXT NOT NULL,
                user TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT
            )
        """)
        
        # Insert default moderation rules
        default_rules = [
            ("Invoice Detection", "KEYWORD", "invoice|billing|payment|receipt", "HOLD", 90),
            ("Urgent Messages", "KEYWORD", "urgent|asap|immediate|emergency", "HOLD", 80),
            ("Attachment Detection", "ATTACHMENT", ".*\\.(pdf|doc|docx|xls|xlsx)", "HOLD", 85),
            ("External Recipients", "SENDER_RECIPIENT", "@(?!yourdomain\\.com)", "HOLD", 70)
        ]
        
        for rule in default_rules:
            cursor.execute("""
                INSERT OR IGNORE INTO moderation_rules (name, rule_type, pattern, action, priority)
                VALUES (?, ?, ?, ?, ?)
            """, rule)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def load_moderation_rules(self):
        """Load active moderation rules from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, rule_type, pattern, action, priority 
            FROM moderation_rules 
            WHERE is_active = 1 
            ORDER BY priority DESC
        """)
        self.rules = cursor.fetchall()
        conn.close()
        logger.info(f"Loaded {len(self.rules)} moderation rules")

def run_smtp_proxy():
    """Run the SMTP proxy server"""
    server = SMTPProxyServer()
    server.start()

if __name__ == "__main__":
    run_smtp_proxy()
'''

# Save the corrected file
with open("email_moderation_system/app/smtp_proxy.py", "w") as f:
    f.write(smtp_proxy_content)

print("Created SMTP Proxy Server base (smtp_proxy.py)")
print("Note: File simplified to avoid indentation issues - will create full version next")