#!/usr/bin/env python3
"""
Comprehensive unit tests for email account management functionality
"""

import unittest
import sqlite3
import json
import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simple_app import app, init_database, encrypt_credential, decrypt_credential
from simple_app import test_email_connection, User

class TestAccountManagement(unittest.TestCase):
    """Test suite for account management functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        # Initialize test database
        self.db_path = 'data/test_emails.db'
        os.makedirs('data', exist_ok=True)
        
        # Create test database
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        # Initialize database with test schema
        self._init_test_database()
        
        # Login as admin
        self._login_admin()
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove test database
        if os.path.exists(self.db_path):
            os.remove(self.db_path)    
    def _init_test_database(self):
        """Initialize test database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'reviewer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create email_accounts table with all fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT UNIQUE NOT NULL,
                email_address TEXT NOT NULL,
                provider_type TEXT DEFAULT 'custom',
                imap_host TEXT NOT NULL,
                imap_port INTEGER DEFAULT 993,
                imap_username TEXT NOT NULL,
                imap_password TEXT NOT NULL,
                imap_use_ssl BOOLEAN DEFAULT 1,
                imap_health_status TEXT DEFAULT 'unknown',
                smtp_host TEXT NOT NULL,
                smtp_port INTEGER DEFAULT 465,
                smtp_username TEXT NOT NULL,
                smtp_password TEXT NOT NULL,
                smtp_use_ssl BOOLEAN DEFAULT 1,
                smtp_use_tls BOOLEAN DEFAULT 0,
                smtp_health_status TEXT DEFAULT 'unknown',
                pop3_host TEXT,
                pop3_port INTEGER DEFAULT 995,
                pop3_username TEXT,
                pop3_password TEXT,
                pop3_use_ssl BOOLEAN DEFAULT 1,
                pop3_health_status TEXT DEFAULT 'unknown',
                is_active BOOLEAN DEFAULT 1,
                connection_status TEXT DEFAULT 'unknown',
                last_checked TIMESTAMP,
                last_error TEXT,
                last_successful_connection TIMESTAMP,
                last_health_check TIMESTAMP,
                total_emails_processed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create admin user
        from werkzeug.security import generate_password_hash
        admin_hash = generate_password_hash('test123')
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, ?)",
            ('admin', admin_hash, 'admin@test.com', 'admin')
        )
        
        conn.commit()
        conn.close()
    
    def _login_admin(self):
        """Login as admin user"""
        with self.client:
            response = self.client.post('/login', data={
                'username': 'admin',
                'password': 'test123'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
    
    def test_account_creation(self):
        """Test creating a new email account"""
        with patch('simple_app.test_email_connection') as mock_test:
            mock_test.return_value = (True, "Connection successful")
            
            response = self.client.post('/accounts/add', data={
                'account_name': 'Test Account',
                'email_address': 'test@example.com',
                'imap_host': 'imap.example.com',
                'imap_port': '993',
                'imap_username': 'test@example.com',
                'imap_password': 'password123',
                'imap_use_ssl': 'on',
                'smtp_host': 'smtp.example.com',
                'smtp_port': '465',
                'smtp_username': 'test@example.com',
                'smtp_password': 'password123',
                'smtp_use_ssl': 'on'
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            
            # Verify account was created
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            account = cursor.execute(
                "SELECT * FROM email_accounts WHERE account_name = ?",
                ('Test Account',)
            ).fetchone()
            conn.close()
            
            self.assertIsNotNone(account)
            self.assertEqual(account[2], 'test@example.com')  # email_address    
    def test_account_health_check(self):
        """Test account health monitoring"""
        # Create test account
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO email_accounts 
            (account_name, email_address, imap_host, imap_port, imap_username, 
             imap_password, smtp_host, smtp_port, smtp_username, smtp_password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('Health Test', 'health@test.com', 'imap.test.com', 993, 'user',
              encrypt_credential('pass'), 'smtp.test.com', 465, 'user', 
              encrypt_credential('pass')))
        account_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Test health check endpoint
        response = self.client.get(f'/api/accounts/{account_id}/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('overall', data)
        self.assertIn('smtp', data)
        self.assertIn('imap', data)
        self.assertIn('pop3', data)
    
    def test_account_update(self):
        """Test updating account details"""
        # Create test account
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO email_accounts 
            (account_name, email_address, imap_host, imap_port, imap_username, 
             imap_password, smtp_host, smtp_port, smtp_username, smtp_password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('Update Test', 'update@test.com', 'imap.test.com', 993, 'user',
              encrypt_credential('pass'), 'smtp.test.com', 465, 'user', 
              encrypt_credential('pass')))
        account_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Update account
        response = self.client.put(f'/api/accounts/{account_id}',
                                  json={
                                      'account_name': 'Updated Account',
                                      'email_address': 'updated@test.com',
                                      'smtp_port': 587
                                  })
        self.assertEqual(response.status_code, 200)
        
        # Verify update
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        account = cursor.execute(
            "SELECT account_name, email_address, smtp_port FROM email_accounts WHERE id = ?",
            (account_id,)
        ).fetchone()
        conn.close()
        
        self.assertEqual(account[0], 'Updated Account')
        self.assertEqual(account[1], 'updated@test.com')
        self.assertEqual(account[2], 587)
    
    def test_account_deletion(self):
        """Test deleting an account"""
        # Create test account
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO email_accounts 
            (account_name, email_address, imap_host, imap_port, imap_username, 
             imap_password, smtp_host, smtp_port, smtp_username, smtp_password)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('Delete Test', 'delete@test.com', 'imap.test.com', 993, 'user',
              encrypt_credential('pass'), 'smtp.test.com', 465, 'user', 
              encrypt_credential('pass')))
        account_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Delete account
        response = self.client.delete(f'/api/accounts/{account_id}')
        self.assertEqual(response.status_code, 200)
        
        # Verify deletion
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        account = cursor.execute(
            "SELECT * FROM email_accounts WHERE id = ?",
            (account_id,)
        ).fetchone()
        conn.close()
        
        self.assertIsNone(account)
    
    def test_connection_testing(self):
        """Test email connection testing"""
        with patch('simple_app.test_email_connection') as mock_test:
            mock_test.return_value = (True, "Connection successful")
            
            response = self.client.post('/api/test-connection/smtp',
                                       json={
                                           'host': 'smtp.test.com',
                                           'port': 465,
                                           'username': 'test@test.com',
                                           'password': 'testpass',
                                           'use_ssl': True
                                       })
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertEqual(data['message'], "Connection successful")
    
    def test_account_export(self):
        """Test exporting accounts"""
        # Create test accounts
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for i in range(3):
            cursor.execute("""
                INSERT INTO email_accounts 
                (account_name, email_address, imap_host, imap_port, imap_username, 
                 imap_password, smtp_host, smtp_port, smtp_username, smtp_password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (f'Export Test {i}', f'export{i}@test.com', 'imap.test.com', 993, 'user',
                  encrypt_credential('pass'), 'smtp.test.com', 465, 'user', 
                  encrypt_credential('pass')))
        conn.commit()
        conn.close()
        
        # Export accounts
        response = self.client.get('/api/accounts/export')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('version', data)
        self.assertIn('accounts', data)
        self.assertEqual(len(data['accounts']), 3)
        
        # Verify passwords are not exported
        for account in data['accounts']:
            self.assertNotIn('imap_password', account)
            self.assertNotIn('smtp_password', account)

if __name__ == '__main__':
    unittest.main()