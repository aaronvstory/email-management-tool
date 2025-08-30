"""
Unit Tests for SMTP Proxy Server
Tests email interception, moderation rules, and message queuing
"""
import pytest
import asyncio
import smtplib
from unittest.mock import Mock, patch, MagicMock
from email.message import EmailMessage
from datetime import datetime

from simple_app import EmailModerationHandler, SMTPProxyServer


class TestEmailModerationHandler:
    """Test suite for EmailModerationHandler"""
    
    @pytest.mark.unit
    @pytest.mark.smtp
    def test_handler_initialization(self, smtp_handler):
        """Test SMTP handler initialization"""
        assert smtp_handler is not None
        assert smtp_handler.db_path == "data/email_moderation.db"
        assert smtp_handler.rules is not None
        assert len(smtp_handler.rules) > 0
    
    @pytest.mark.unit
    @pytest.mark.smtp
    def test_load_moderation_rules(self, smtp_handler):
        """Test loading moderation rules from database"""
        smtp_handler.load_moderation_rules()
        
        # Check default rules are loaded
        rule_names = [rule[0] for rule in smtp_handler.rules]
        assert "Invoice Detection" in rule_names
        assert "Urgent Messages" in rule_names
        assert "Attachment Detection" in rule_names
        assert "External Recipients" in rule_names
    
    @pytest.mark.unit
    @pytest.mark.smtp
    def test_check_keyword_rule(self, smtp_handler, sample_email_with_keywords):
        """Test keyword-based moderation rules"""
        # Create mock email message
        msg = EmailMessage()
        msg['From'] = sample_email_with_keywords['sender']
        msg['To'] = ', '.join(sample_email_with_keywords['recipients'])
        msg['Subject'] = sample_email_with_keywords['subject']
        msg.set_content(sample_email_with_keywords['body_text'])
        
        # Check if keywords are detected
        rules_triggered = smtp_handler.check_moderation_rules(msg)
        
        assert len(rules_triggered) > 0
        assert any('invoice' in rule.lower() for rule in rules_triggered)
        assert any('urgent' in rule.lower() for rule in rules_triggered)
    
    @pytest.mark.unit
    @pytest.mark.smtp
    def test_check_attachment_rule(self, smtp_handler):
        """Test attachment-based moderation rules"""
        msg = EmailMessage()
        msg['From'] = 'sender@test.com'
        msg['To'] = 'recipient@test.com'
        msg['Subject'] = 'Document Attached'
        msg.set_content('Please find the document attached.')
        
        # Add PDF attachment
        msg.add_attachment(
            b'PDF content here',
            maintype='application',
            subtype='pdf',
            filename='document.pdf'
        )
        
        rules_triggered = smtp_handler.check_moderation_rules(msg)
        assert len(rules_triggered) > 0
        assert any('attachment' in rule.lower() for rule in rules_triggered)
    
    @pytest.mark.unit
    @pytest.mark.smtp
    @patch('simple_app.sqlite3.connect')
    def test_handle_message(self, mock_connect, smtp_handler, mock_email_bytes):
        """Test handling incoming SMTP message"""
        # Setup mock database
        mock_cursor = Mock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        
        # Create mock message
        mock_message = Mock()
        mock_message.original_content = mock_email_bytes
        mock_message.peer = ('127.0.0.1', 12345)
        mock_message.mail_from = 'sender@test.com'
        mock_message.rcpt_tos = ['recipient@test.com']
        
        # Handle message
        smtp_handler.handle_message(mock_message)
        
        # Verify database insertion
        mock_cursor.execute.assert_called()
        mock_connect.return_value.commit.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.smtp
    def test_risk_score_calculation(self, smtp_handler):
        """Test email risk score calculation"""
        # Low risk email
        low_risk_msg = EmailMessage()
        low_risk_msg['From'] = 'colleague@company.com'
        low_risk_msg['To'] = 'team@company.com'
        low_risk_msg['Subject'] = 'Team Meeting Notes'
        low_risk_msg.set_content('Here are the notes from today\'s meeting.')
        
        low_risk_score = smtp_handler.calculate_risk_score(low_risk_msg)
        assert low_risk_score < 30
        
        # High risk email
        high_risk_msg = EmailMessage()
        high_risk_msg['From'] = 'external@unknown.com'
        high_risk_msg['To'] = 'finance@company.com'
        high_risk_msg['Subject'] = 'URGENT: Invoice Payment Required'
        high_risk_msg.set_content('Please pay this invoice urgently!')
        
        high_risk_score = smtp_handler.calculate_risk_score(high_risk_msg)
        assert high_risk_score > 70


class TestSMTPProxyServer:
    """Test suite for SMTP Proxy Server"""
    
    @pytest.mark.unit
    @pytest.mark.smtp
    def test_server_initialization(self):
        """Test SMTP proxy server initialization"""
        server = SMTPProxyServer(host='127.0.0.1', port=8589)
        assert server.host == '127.0.0.1'
        assert server.port == 8589
        assert server.controller is None
    
    @pytest.mark.integration
    @pytest.mark.smtp
    @pytest.mark.asyncio
    async def test_server_start_stop(self):
        """Test starting and stopping SMTP server"""
        server = SMTPProxyServer(host='127.0.0.1', port=8590)
        
        # Start server in background
        server_thread = asyncio.create_task(server.start_async())
        
        # Wait for server to start
        await asyncio.sleep(1)
        
        # Check if server is running
        assert server.controller is not None
        
        # Stop server
        server.stop()
        
        # Cancel the server task
        server_thread.cancel()
        
        try:
            await server_thread
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.integration
    @pytest.mark.smtp
    def test_smtp_connection(self):
        """Test SMTP client connection to proxy"""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_instance = Mock()
            mock_smtp.return_value = mock_instance
            
            # Try to connect
            client = smtplib.SMTP('localhost', 8587)
            
            # Verify connection attempt
            mock_smtp.assert_called_with('localhost', 8587)
    
    @pytest.mark.unit
    @pytest.mark.smtp
    def test_message_size_limit(self, smtp_handler):
        """Test message size limit enforcement"""
        # Create oversized message
        large_content = 'X' * (33554432 + 1)  # Over 32MB limit
        
        msg = EmailMessage()
        msg['From'] = 'sender@test.com'
        msg['To'] = 'recipient@test.com'
        msg['Subject'] = 'Large Message'
        msg.set_content(large_content)
        
        # Should reject oversized message
        with pytest.raises(Exception):
            smtp_handler.validate_message_size(msg)
    
    @pytest.mark.unit
    @pytest.mark.smtp
    def test_concurrent_connections(self):
        """Test handling multiple concurrent SMTP connections"""
        server = SMTPProxyServer(host='127.0.0.1', port=8591)
        
        # Simulate multiple connections
        connections = []
        for i in range(10):
            conn = Mock()
            conn.peer = (f'192.168.1.{i}', 25)
            connections.append(conn)
        
        # Server should handle all connections
        for conn in connections:
            assert server.can_accept_connection(conn)


class TestModerationRules:
    """Test suite for moderation rules engine"""
    
    @pytest.mark.unit
    def test_regex_pattern_matching(self, smtp_handler):
        """Test regex pattern matching in rules"""
        msg = EmailMessage()
        msg['From'] = 'sender@test.com'
        msg['To'] = 'recipient@test.com'
        msg['Subject'] = 'Credit Card Number'
        msg.set_content('My card number is 4111-1111-1111-1111')
        
        # Should detect credit card pattern
        rules_triggered = smtp_handler.check_sensitive_data(msg)
        assert 'credit_card' in rules_triggered
    
    @pytest.mark.unit
    def test_rule_priority_ordering(self, smtp_handler):
        """Test rule evaluation by priority"""
        # Create message that triggers multiple rules
        msg = EmailMessage()
        msg['From'] = 'external@unknown.com'
        msg['To'] = 'finance@company.com'
        msg['Subject'] = 'URGENT: Invoice Payment'
        msg.set_content('Please pay this urgent invoice immediately!')
        
        rules = smtp_handler.check_moderation_rules_with_priority(msg)
        
        # Higher priority rules should be first
        assert rules[0]['priority'] >= rules[-1]['priority']
    
    @pytest.mark.unit
    def test_custom_rule_creation(self, smtp_handler):
        """Test creating and applying custom rules"""
        # Add custom rule
        custom_rule = {
            'name': 'Confidential Detection',
            'type': 'KEYWORD',
            'pattern': 'confidential|secret|classified',
            'action': 'HOLD',
            'priority': 100
        }
        
        smtp_handler.add_custom_rule(custom_rule)
        
        # Test with message containing keyword
        msg = EmailMessage()
        msg['From'] = 'sender@test.com'
        msg['To'] = 'recipient@test.com'
        msg['Subject'] = 'Confidential Information'
        msg.set_content('This contains confidential data.')
        
        rules_triggered = smtp_handler.check_moderation_rules(msg)
        assert 'Confidential Detection' in rules_triggered


class TestEmailProcessing:
    """Test suite for email processing functionality"""
    
    @pytest.mark.unit
    def test_extract_email_headers(self, smtp_handler, mock_email_bytes):
        """Test extracting headers from email"""
        from email import message_from_bytes, policy
        
        msg = message_from_bytes(mock_email_bytes, policy=policy.default)
        headers = smtp_handler.extract_headers(msg)
        
        assert headers['From'] == 'sender@test.com'
        assert headers['To'] == 'recipient@test.com'
        assert headers['Subject'] == 'Test Email'
        assert 'Date' in headers
        assert 'Message-ID' in headers
    
    @pytest.mark.unit
    def test_extract_email_body(self, smtp_handler):
        """Test extracting body from multipart email"""
        msg = EmailMessage()
        msg['From'] = 'sender@test.com'
        msg['To'] = 'recipient@test.com'
        msg['Subject'] = 'Multipart Message'
        
        # Add both text and HTML parts
        msg.add_alternative('Plain text version', subtype='plain')
        msg.add_alternative('<p>HTML version</p>', subtype='html')
        
        text_body = smtp_handler.extract_body_text(msg)
        html_body = smtp_handler.extract_body_html(msg)
        
        assert text_body == 'Plain text version'
        assert html_body == '<p>HTML version</p>'
    
    @pytest.mark.unit
    def test_sanitize_email_content(self, smtp_handler):
        """Test sanitizing potentially malicious email content"""
        dangerous_content = """
        <script>alert('XSS')</script>
        <iframe src="malicious.com"></iframe>
        Normal text here
        """
        
        sanitized = smtp_handler.sanitize_content(dangerous_content)
        
        assert '<script>' not in sanitized
        assert '<iframe>' not in sanitized
        assert 'Normal text here' in sanitized


@pytest.mark.performance
class TestSMTPPerformance:
    """Performance tests for SMTP proxy"""
    
    def test_message_processing_speed(self, smtp_handler, performance_timer):
        """Test message processing performance"""
        msg = EmailMessage()
        msg['From'] = 'sender@test.com'
        msg['To'] = 'recipient@test.com'
        msg['Subject'] = 'Performance Test'
        msg.set_content('Test content for performance measurement.')
        
        performance_timer.start()
        
        # Process 100 messages
        for _ in range(100):
            smtp_handler.check_moderation_rules(msg)
        
        performance_timer.stop()
        
        # Should process 100 messages in under 1 second
        assert performance_timer.elapsed < 1.0
    
    def test_concurrent_message_handling(self, smtp_handler):
        """Test handling concurrent messages"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def process_message():
            msg = EmailMessage()
            msg['From'] = 'sender@test.com'
            msg['To'] = 'recipient@test.com'
            msg['Subject'] = 'Concurrent Test'
            msg.set_content('Test content')
            
            result = smtp_handler.check_moderation_rules(msg)
            results.put(result)
        
        # Create 50 threads
        threads = []
        for _ in range(50):
            t = threading.Thread(target=process_message)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # All 50 messages should be processed
        assert results.qsize() == 50