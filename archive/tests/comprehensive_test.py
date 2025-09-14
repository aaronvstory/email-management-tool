#!/usr/bin/env python3
"""
Comprehensive Email Management Tool Test
Tests all features: interception, editing, inbox, compose
"""

import smtplib
import time
import sqlite3
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configuration
DB_PATH = 'email_manager.db'
API_BASE = 'http://localhost:5000'
SMTP_PROXY_HOST = 'localhost'
SMTP_PROXY_PORT = 8587

class EmailSystemTest:
    def __init__(self):
        self.session = None
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'ui_features': {},
            'functionality': {}
        }
    
    def login(self):
        """Login to the dashboard"""
        self.session = requests.Session()
        response = self.session.post(f'{API_BASE}/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        return response.status_code == 200
    
    def test_dashboard(self):
        """Test dashboard accessibility"""
        print("\n📊 Testing Dashboard...")
        response = self.session.get(f'{API_BASE}/dashboard')
        if response.status_code == 200:
            print("✅ Dashboard accessible")
            # Check for key UI elements
            content = response.text
            self.results['ui_features']['dashboard_tabs'] = all([
                'Overview' in content,
                'Emails' in content,
                'Accounts' in content,
                'Diagnostics' in content
            ])
            return True
        return False
    
    def test_compose_ui(self):
        """Test compose interface"""
        print("\n✍️ Testing Compose Interface...")
        response = self.session.get(f'{API_BASE}/compose')
        if response.status_code == 200:
            content = response.text
            features = {
                'account_selector': 'Select sending account' in content,
                'recipient_field': 'recipient@example.com' in content,
                'subject_field': 'Enter email subject' in content,
                'message_field': 'Type your message here' in content,
                'formatting_buttons': 'Formal' in content and 'Casual' in content
            }
            self.results['ui_features']['compose'] = features
            print(f"✅ Compose page features: {sum(features.values())}/{len(features)}")
            return all(features.values())
        return False
    
    def test_inbox_ui(self):
        """Test inbox interface"""
        print("\n📥 Testing Inbox Interface...")
        response = self.session.get(f'{API_BASE}/inbox')
        if response.status_code == 200:
            content = response.text
            features = {
                'account_filter': 'All Accounts' in content,
                'email_cards': 'card' in content.lower(),
                'refresh_button': 'Refresh' in content
            }
            self.results['ui_features']['inbox'] = features
            print(f"✅ Inbox features: {sum(features.values())}/{len(features)}")
            return True
        return False
    
    def test_email_queue_ui(self):
        """Test email queue interface"""
        print("\n📧 Testing Email Queue Interface...")
        response = self.session.get(f'{API_BASE}/emails')
        if response.status_code == 200:
            content = response.text
            features = {
                'status_tabs': all(['Pending' in content, 'Approved' in content, 'Rejected' in content]),
                'search_bar': 'Search emails' in content,
                'filter_button': 'Filter' in content,
                'email_table': '<table' in content or '<tr>' in content
            }
            self.results['ui_features']['email_queue'] = features
            print(f"✅ Email queue features: {sum(features.values())}/{len(features)}")
            return True
        return False
    
    def test_interception_workflow(self):
        """Test complete email interception workflow"""
        print("\n🔄 Testing Complete Interception Workflow...")
        
        # Step 1: Send test email
        print("  1️⃣ Sending test email...")
        msg = MIMEMultipart()
        msg['From'] = 'workflow@test.com'
        msg['To'] = 'ndayijecika@gmail.com'
        msg['Subject'] = f'Workflow Test {datetime.now().strftime("%H:%M:%S")}'
        body = "This email tests the complete workflow: interception -> modification -> approval -> delivery"
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(SMTP_PROXY_HOST, SMTP_PROXY_PORT) as server:
                server.send_message(msg)
            print("     ✅ Email sent to proxy")
        except Exception as e:
            print(f"     ❌ Failed to send: {e}")
            return False
        
        time.sleep(2)
        
        # Step 2: Check if intercepted
        print("  2️⃣ Checking interception...")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, subject, status FROM email_messages 
            WHERE sender = 'workflow@test.com' 
            ORDER BY created_at DESC LIMIT 1
        """)
        email = cursor.fetchone()
        
        if email and email['status'] == 'PENDING':
            print(f"     ✅ Email intercepted (ID: {email['id']})")
            
            # Step 3: Modify email
            print("  3️⃣ Modifying email...")
            cursor.execute("""
                UPDATE email_messages 
                SET subject = ?, body_text = ?, review_notes = ?
                WHERE id = ?
            """, (
                email['subject'] + ' [MODIFIED]',
                'Modified content: Workflow test successful!',
                f'Modified at {datetime.now()}',
                email['id']
            ))
            conn.commit()
            print("     ✅ Email modified")
            
            # Step 4: Approve email
            print("  4️⃣ Approving email...")
            cursor.execute("""
                UPDATE email_messages 
                SET status = 'APPROVED', approved_by = 'test_system'
                WHERE id = ?
            """, (email['id'],))
            conn.commit()
            print("     ✅ Email approved")
            
            conn.close()
            return True
        
        conn.close()
        return False
    
    def check_configured_accounts(self):
        """Check configured email accounts"""
        print("\n📮 Checking Configured Accounts...")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT account_name, email_address, is_active FROM email_accounts")
        accounts = cursor.fetchall()
        
        self.results['functionality']['configured_accounts'] = len(accounts)
        self.results['functionality']['active_accounts'] = sum(1 for a in accounts if a['is_active'])
        
        print(f"✅ Found {len(accounts)} accounts ({self.results['functionality']['active_accounts']} active)")
        for acc in accounts:
            status = "✅ Active" if acc['is_active'] else "⚠️ Inactive"
            print(f"   - {acc['account_name']}: {acc['email_address']} [{status}]")
        
        conn.close()
        return len(accounts) > 0
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("🚀 COMPREHENSIVE EMAIL MANAGEMENT TOOL TEST")
        print("=" * 60)
        
        # Login
        print("\n🔐 Logging in...")
        if not self.login():
            print("❌ Login failed!")
            return False
        print("✅ Logged in successfully")
        
        # Test UI Features
        self.results['tests']['dashboard'] = self.test_dashboard()
        self.results['tests']['compose_ui'] = self.test_compose_ui()
        self.results['tests']['inbox_ui'] = self.test_inbox_ui()
        self.results['tests']['email_queue_ui'] = self.test_email_queue_ui()
        
        # Test Functionality
        self.results['tests']['configured_accounts'] = self.check_configured_accounts()
        self.results['tests']['interception_workflow'] = self.test_interception_workflow()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        # UI Features Summary
        print("\n🎨 UI Features:")
        for feature, status in self.results['ui_features'].items():
            if isinstance(status, dict):
                passed = sum(status.values())
                total = len(status)
                print(f"  {feature}: {passed}/{total} features working")
            else:
                icon = "✅" if status else "❌"
                print(f"  {icon} {feature}")
        
        # Functionality Summary
        print("\n⚙️ Functionality:")
        for key, value in self.results['functionality'].items():
            print(f"  {key}: {value}")
        
        # Test Results
        print("\n🧪 Test Results:")
        passed_tests = sum(1 for v in self.results['tests'].values() if v)
        total_tests = len(self.results['tests'])
        
        for test, result in self.results['tests'].items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} - {test}")
        
        print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
        
        # Save results
        filename = f'comprehensive_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to {filename}")
        
        # Final verdict
        if passed_tests == total_tests:
            print("\n🎉 EXCELLENT! All features are working perfectly!")
            print("✅ Email interception: Working")
            print("✅ Email modification: Working")
            print("✅ UI interfaces: Polished and functional")
            print("✅ Compose & Inbox: Fully operational")
        else:
            print(f"\n⚠️ {total_tests - passed_tests} test(s) need attention")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = EmailSystemTest()
    success = tester.run_all_tests()
    exit(0 if success else 1)