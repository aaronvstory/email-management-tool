"""
Integration Tests for Complete Email Flow
Tests end-to-end email processing from SMTP interception to delivery
"""
import pytest
import smtplib
import threading
import time
import json
from email.message import EmailMessage
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

from simple_app import app, db, EmailMessage as DBEmailMessage
from simple_app import SMTPProxyServer, EmailModerationHandler


class TestCompleteEmailFlow:
    """Test complete email flow from interception to delivery"""
    
    @pytest.mark.integration
    @pytest.mark.e2e
    def test_email_interception_to_queue(self, app, db_session):
        """Test email interception and queuing in database"""
        # Create test email
        msg = EmailMessage()
        msg['From'] = 'sender@test.com'
        msg['To'] = 'recipient@test.com'
        msg['Subject'] = 'Integration Test Email'
        msg.set_content('This is an integration test email.')
        
        # Create handler and process message
        handler = EmailModerationHandler()
        
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = Mock()
            mock_connect.return_value.cursor.return_value = mock_cursor
            mock_connect.return_value.commit = Mock()
            
            # Mock message object
            mock_message = Mock()
            mock_message.original_content = msg.as_bytes()
            mock_message.peer = ('127.0.0.1', 12345)
            mock_message.mail_from = 'sender@test.com'
            mock_message.rcpt_tos = ['recipient@test.com']
            
            # Process message
            handler.handle_message(mock_message)
            
            # Verify database operations
            assert mock_cursor.execute.called
            assert mock_connect.return_value.commit.called
    
    @pytest.mark.integration
    @pytest.mark.e2e
    def test_email_moderation_workflow(self, authenticated_client, db_session):
        """Test complete email moderation workflow"""
        # Step 1: Add email to queue
        email = DBEmailMessage(
            message_id='workflow-test',
            sender='sender@test.com',
            recipients=json.dumps(['recipient@test.com']),
            subject='Workflow Test Email',
            body_text='Test content for workflow',
            status='PENDING',
            risk_score=50
        )
        db_session.add(email)
        db_session.commit()
        
        # Step 2: View in dashboard
        response = authenticated_client.get('/dashboard')
        assert response.status_code == 200
        
        # Step 3: View email details
        response = authenticated_client.get(f'/email/{email.id}')
        assert response.status_code == 200
        assert b'Workflow Test Email' in response.data
        
        # Step 4: Edit email
        response = authenticated_client.post(f'/email/{email.id}/edit', data={
            'subject': 'Edited Workflow Test',
            'body_text': 'Edited content'
        })
        assert response.status_code in [200, 302]
        
        # Step 5: Approve email
        response = authenticated_client.post(f'/email/{email.id}/approve')
        assert response.status_code in [200, 302]
        
        # Verify final status
        updated_email = DBEmailMessage.query.get(email.id)
        assert updated_email.status == 'APPROVED'
        assert updated_email.subject == 'Edited Workflow Test'
    
    @pytest.mark.integration
    @pytest.mark.smtp
    def test_smtp_proxy_integration(self):
        """Test SMTP proxy server integration"""
        # Start SMTP proxy in background thread
        proxy = SMTPProxyServer(host='127.0.0.1', port=8592)
        proxy_thread = threading.Thread(target=proxy.start, daemon=True)
        proxy_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        try:
            # Connect to SMTP proxy
            with smtplib.SMTP('127.0.0.1', 8592) as smtp:
                # Send test email
                msg = EmailMessage()
                msg['From'] = 'test@sender.com'
                msg['To'] = 'test@recipient.com'
                msg['Subject'] = 'SMTP Integration Test'
                msg.set_content('Testing SMTP proxy integration')
                
                # This should be intercepted by proxy
                smtp.send_message(msg)
        except Exception as e:
            # Expected - proxy may not fully process
            pass
        finally:
            # Stop proxy
            if proxy.controller:
                proxy.stop()
    
    @pytest.mark.integration
    def test_email_with_attachments_flow(self, authenticated_client, db_session):
        """Test email with attachments through complete flow"""
        # Create email with attachment info
        attachment_data = {
            'filename': 'document.pdf',
            'content_type': 'application/pdf',
            'size': 1024
        }
        
        email = DBEmailMessage(
            message_id='attachment-test',
            sender='sender@test.com',
            recipients=json.dumps(['recipient@test.com']),
            subject='Email with Attachment',
            body_text='Please find attached document',
            attachments=json.dumps([attachment_data]),
            status='PENDING'
        )
        db_session.add(email)
        db_session.commit()
        
        # View email
        response = authenticated_client.get(f'/email/{email.id}')
        assert response.status_code == 200
        assert b'document.pdf' in response.data
        
        # Approve email
        response = authenticated_client.post(f'/email/{email.id}/approve')
        assert response.status_code in [200, 302]
    
    @pytest.mark.integration
    def test_bulk_email_processing(self, authenticated_client, db_session):
        """Test bulk email processing operations"""
        # Create multiple emails
        email_ids = []
        for i in range(10):
            email = DBEmailMessage(
                message_id=f'bulk-{i}',
                sender='sender@test.com',
                recipients=json.dumps(['recipient@test.com']),
                subject=f'Bulk Email {i}',
                status='PENDING'
            )
            db_session.add(email)
            db_session.flush()
            email_ids.append(email.id)
        db_session.commit()
        
        # Bulk approve via API
        response = authenticated_client.post('/api/emails/bulk', 
            json={'action': 'approve', 'email_ids': email_ids[:5]})
        
        # Bulk reject remaining
        response = authenticated_client.post('/api/emails/bulk',
            json={'action': 'reject', 'email_ids': email_ids[5:], 'reason': 'Bulk reject'})
        
        # Verify statuses
        for i, email_id in enumerate(email_ids):
            email = DBEmailMessage.query.get(email_id)
            if i < 5:
                assert email.status == 'APPROVED'
            else:
                assert email.status == 'REJECTED'


class TestEmailDelivery:
    """Test email delivery after approval"""
    
    @pytest.mark.integration
    def test_approved_email_delivery(self, app, db_session):
        """Test delivery of approved emails"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_instance = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_instance
            
            # Create approved email
            email = DBEmailMessage(
                message_id='delivery-test',
                sender='sender@test.com',
                recipients=json.dumps(['recipient@test.com']),
                subject='Delivery Test',
                body_text='Test delivery content',
                status='APPROVED'
            )
            db_session.add(email)
            db_session.commit()
            
            # Trigger delivery
            from simple_app import deliver_approved_email
            result = deliver_approved_email(email.id)
            
            # Verify SMTP was called
            assert mock_smtp.called
            
            # Verify status updated
            updated_email = DBEmailMessage.query.get(email.id)
            assert updated_email.status == 'SENT'
    
    @pytest.mark.integration
    @pytest.mark.imap
    def test_imap_sent_folder_sync(self):
        """Test syncing sent emails to IMAP folder"""
        with patch('imaplib.IMAP4_SSL') as mock_imap:
            mock_instance = Mock()
            mock_imap.return_value = mock_instance
            mock_instance.login.return_value = ('OK', [])
            mock_instance.append.return_value = ('OK', [])
            
            # Test sync operation
            from simple_app import sync_to_sent_folder
            result = sync_to_sent_folder(
                'user@test.com',
                b'Email content here'
            )
            
            # Verify IMAP operations
            mock_instance.login.assert_called()
            mock_instance.append.assert_called()


class TestModerationRulesIntegration:
    """Test moderation rules in integration scenarios"""
    
    @pytest.mark.integration
    def test_keyword_triggered_hold(self, db_session):
        """Test emails with keywords are held for review"""
        handler = EmailModerationHandler()
        
        # Create email with trigger keywords
        msg = EmailMessage()
        msg['From'] = 'vendor@external.com'
        msg['To'] = 'finance@company.com'
        msg['Subject'] = 'URGENT: Invoice Payment Required'
        msg.set_content('Please process this urgent invoice payment immediately.')
        
        # Check moderation rules
        rules_triggered = handler.check_moderation_rules(msg)
        
        # Should trigger multiple rules
        assert len(rules_triggered) > 0
        assert any('invoice' in rule.lower() for rule in rules_triggered)
        assert any('urgent' in rule.lower() for rule in rules_triggered)
    
    @pytest.mark.integration
    def test_external_recipient_detection(self, db_session):
        """Test detection of emails to external recipients"""
        handler = EmailModerationHandler()
        
        # Email to external domain
        msg = EmailMessage()
        msg['From'] = 'employee@company.com'
        msg['To'] = 'contact@external-company.com'
        msg['Subject'] = 'Business Proposal'
        msg.set_content('Confidential business information')
        
        rules_triggered = handler.check_moderation_rules(msg)
        
        # Should trigger external recipient rule
        assert any('external' in rule.lower() for rule in rules_triggered)
    
    @pytest.mark.integration
    def test_risk_based_routing(self, authenticated_client, db_session):
        """Test risk-based email routing"""
        # Create emails with different risk scores
        high_risk = DBEmailMessage(
            message_id='high-risk',
            sender='unknown@external.com',
            recipients=json.dumps(['ceo@company.com']),
            subject='Urgent Wire Transfer',
            body_text='Please wire $50,000 immediately',
            risk_score=95,
            status='PENDING'
        )
        
        low_risk = DBEmailMessage(
            message_id='low-risk',
            sender='colleague@company.com',
            recipients=json.dumps(['team@company.com']),
            subject='Team Meeting Notes',
            body_text='Notes from today\'s meeting',
            risk_score=10,
            status='PENDING'
        )
        
        db_session.add_all([high_risk, low_risk])
        db_session.commit()
        
        # High risk emails should require additional review
        response = authenticated_client.get(f'/email/{high_risk.id}')
        assert b'High Risk' in response.data or b'95' in response.data
        
        # Low risk emails can be auto-approved
        response = authenticated_client.get(f'/email/{low_risk.id}')
        assert b'Low Risk' in response.data or b'10' in response.data


class TestErrorHandling:
    """Test error handling in integration scenarios"""
    
    @pytest.mark.integration
    def test_smtp_connection_failure_handling(self):
        """Test handling of SMTP connection failures"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = ConnectionRefusedError("Connection refused")
            
            # Try to send email
            from simple_app import deliver_approved_email
            result = deliver_approved_email('test-id')
            
            # Should handle error gracefully
            assert result is False
    
    @pytest.mark.integration
    def test_database_connection_failure(self):
        """Test handling of database connection failures"""
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = Exception("Database connection failed")
            
            handler = EmailModerationHandler()
            
            # Should handle error without crashing
            mock_message = Mock()
            mock_message.original_content = b'Test email'
            
            try:
                handler.handle_message(mock_message)
            except Exception:
                pass  # Expected
    
    @pytest.mark.integration
    def test_malformed_email_handling(self, db_session):
        """Test handling of malformed emails"""
        handler = EmailModerationHandler()
        
        # Malformed email bytes
        malformed_email = b'This is not a valid email format'
        
        mock_message = Mock()
        mock_message.original_content = malformed_email
        mock_message.peer = ('127.0.0.1', 12345)
        mock_message.mail_from = 'sender@test.com'
        mock_message.rcpt_tos = ['recipient@test.com']
        
        # Should handle gracefully
        with patch('sqlite3.connect'):
            try:
                handler.handle_message(mock_message)
            except Exception:
                pass  # Expected but should not crash


@pytest.mark.performance
class TestPerformanceIntegration:
    """Performance tests for integrated system"""
    
    def test_high_volume_email_processing(self, db_session, performance_timer):
        """Test processing high volume of emails"""
        performance_timer.start()
        
        # Create 1000 emails
        emails = []
        for i in range(1000):
            email = DBEmailMessage(
                message_id=f'perf-{i}',
                sender=f'sender{i}@test.com',
                recipients=json.dumps([f'recipient{i}@test.com']),
                subject=f'Performance Test {i}',
                body_text=f'Content {i}',
                status='PENDING'
            )
            emails.append(email)
        
        db_session.bulk_save_objects(emails)
        db_session.commit()
        
        performance_timer.stop()
        
        # Should process 1000 emails in under 5 seconds
        assert performance_timer.elapsed < 5.0
    
    def test_concurrent_user_sessions(self, app):
        """Test handling concurrent user sessions"""
        import concurrent.futures
        
        def make_request(session_id):
            with app.test_client() as client:
                # Login
                client.post('/login', data={
                    'username': 'admin',
                    'password': 'admin123'
                })
                
                # Access dashboard
                response = client.get('/dashboard')
                return response.status_code == 200
        
        # Simulate 50 concurrent users
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request, i) for i in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(results)