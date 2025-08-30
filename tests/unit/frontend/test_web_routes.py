"""
Unit Tests for Flask Web Routes
Tests dashboard, authentication, and email management endpoints
"""
import pytest
import json
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash


class TestAuthenticationRoutes:
    """Test suite for authentication endpoints"""
    
    @pytest.mark.unit
    def test_login_page_loads(self, client):
        """Test login page renders correctly"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data
        assert b'Username' in response.data
        assert b'Password' in response.data
    
    @pytest.mark.unit
    def test_successful_login(self, client):
        """Test successful login with valid credentials"""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Dashboard' in response.data
    
    @pytest.mark.unit
    def test_failed_login(self, client):
        """Test failed login with invalid credentials"""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
        assert b'Invalid username or password' in response.data
    
    @pytest.mark.unit
    def test_logout(self, authenticated_client):
        """Test logout functionality"""
        response = authenticated_client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'Login' in response.data
    
    @pytest.mark.unit
    def test_login_rate_limiting(self, client):
        """Test login rate limiting after failed attempts"""
        # Make 5 failed login attempts
        for i in range(6):
            response = client.post('/login', data={
                'username': 'admin',
                'password': f'wrong{i}'
            })
        
        # Should be locked out after 5 attempts
        assert b'Too many failed attempts' in response.data or \
               b'Account locked' in response.data
    
    @pytest.mark.unit
    def test_session_timeout(self, authenticated_client, app):
        """Test session timeout after inactivity"""
        with app.app_context():
            # Simulate session timeout
            with patch('flask_login.utils._get_user') as mock_user:
                mock_user.return_value = None
                
                response = authenticated_client.get('/dashboard')
                assert response.status_code == 302  # Redirect to login


class TestDashboardRoutes:
    """Test suite for dashboard endpoints"""
    
    @pytest.mark.unit
    def test_dashboard_requires_auth(self, client):
        """Test dashboard requires authentication"""
        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirect to login
        assert '/login' in response.location
    
    @pytest.mark.unit
    def test_dashboard_loads_authenticated(self, authenticated_client):
        """Test dashboard loads for authenticated user"""
        response = authenticated_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Email Management Dashboard' in response.data
    
    @pytest.mark.unit
    def test_dashboard_statistics(self, authenticated_client, db_session):
        """Test dashboard shows correct statistics"""
        # Add test emails to database
        from simple_app import EmailMessage
        
        for i in range(5):
            email = EmailMessage(
                message_id=f'test-{i}',
                sender=f'sender{i}@test.com',
                recipients=json.dumps([f'recipient{i}@test.com']),
                subject=f'Test Email {i}',
                status='PENDING' if i < 3 else 'APPROVED'
            )
            db_session.add(email)
        db_session.commit()
        
        response = authenticated_client.get('/dashboard')
        assert response.status_code == 200
        assert b'3' in response.data  # 3 pending
        assert b'2' in response.data  # 2 approved
    
    @pytest.mark.unit
    def test_dashboard_charts_data(self, authenticated_client):
        """Test dashboard chart data endpoint"""
        response = authenticated_client.get('/api/dashboard/charts')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'email_flow' in data
        assert 'status_breakdown' in data
        assert 'risk_distribution' in data


class TestEmailQueueRoutes:
    """Test suite for email queue management"""
    
    @pytest.mark.unit
    def test_email_queue_page(self, authenticated_client):
        """Test email queue page loads"""
        response = authenticated_client.get('/emails')
        assert response.status_code == 200
        assert b'Email Queue' in response.data
    
    @pytest.mark.unit
    def test_email_queue_filtering(self, authenticated_client, db_session):
        """Test email queue filtering by status"""
        from simple_app import EmailMessage
        
        # Add emails with different statuses
        statuses = ['PENDING', 'APPROVED', 'REJECTED', 'SENT']
        for status in statuses:
            email = EmailMessage(
                message_id=f'test-{status}',
                sender='sender@test.com',
                recipients=json.dumps(['recipient@test.com']),
                subject=f'{status} Email',
                status=status
            )
            db_session.add(email)
        db_session.commit()
        
        # Test filtering by status
        response = authenticated_client.get('/emails?status=PENDING')
        assert response.status_code == 200
        assert b'PENDING Email' in response.data
        assert b'APPROVED Email' not in response.data
    
    @pytest.mark.unit
    def test_email_search(self, authenticated_client, db_session):
        """Test email search functionality"""
        from simple_app import EmailMessage
        
        email = EmailMessage(
            message_id='search-test',
            sender='unique@test.com',
            recipients=json.dumps(['recipient@test.com']),
            subject='Unique Subject for Search',
            body_text='Searchable content here'
        )
        db_session.add(email)
        db_session.commit()
        
        response = authenticated_client.get('/emails?search=unique')
        assert response.status_code == 200
        assert b'Unique Subject' in response.data
    
    @pytest.mark.unit
    def test_email_pagination(self, authenticated_client, db_session):
        """Test email queue pagination"""
        from simple_app import EmailMessage
        
        # Add 25 emails
        for i in range(25):
            email = EmailMessage(
                message_id=f'page-test-{i}',
                sender='sender@test.com',
                recipients=json.dumps(['recipient@test.com']),
                subject=f'Email {i}'
            )
            db_session.add(email)
        db_session.commit()
        
        # Test first page
        response = authenticated_client.get('/emails?page=1')
        assert response.status_code == 200
        
        # Test second page
        response = authenticated_client.get('/emails?page=2')
        assert response.status_code == 200


class TestEmailDetailRoutes:
    """Test suite for individual email operations"""
    
    @pytest.mark.unit
    def test_view_email_detail(self, authenticated_client, db_session):
        """Test viewing email details"""
        from simple_app import EmailMessage
        
        email = EmailMessage(
            message_id='detail-test',
            sender='sender@test.com',
            recipients=json.dumps(['recipient@test.com']),
            subject='Detail Test Email',
            body_text='This is the email body',
            body_html='<p>This is the email body</p>'
        )
        db_session.add(email)
        db_session.commit()
        
        response = authenticated_client.get(f'/email/{email.id}')
        assert response.status_code == 200
        assert b'Detail Test Email' in response.data
        assert b'sender@test.com' in response.data
        assert b'This is the email body' in response.data
    
    @pytest.mark.unit
    def test_edit_email(self, authenticated_client, db_session):
        """Test editing email content"""
        from simple_app import EmailMessage
        
        email = EmailMessage(
            message_id='edit-test',
            sender='sender@test.com',
            recipients=json.dumps(['recipient@test.com']),
            subject='Original Subject',
            body_text='Original body'
        )
        db_session.add(email)
        db_session.commit()
        
        response = authenticated_client.post(f'/email/{email.id}/edit', data={
            'subject': 'Edited Subject',
            'body_text': 'Edited body'
        })
        
        assert response.status_code in [200, 302]
        
        # Verify changes
        updated_email = EmailMessage.query.get(email.id)
        assert updated_email.subject == 'Edited Subject'
        assert updated_email.body_text == 'Edited body'
    
    @pytest.mark.unit
    def test_approve_email(self, authenticated_client, db_session):
        """Test approving email for delivery"""
        from simple_app import EmailMessage
        
        email = EmailMessage(
            message_id='approve-test',
            sender='sender@test.com',
            recipients=json.dumps(['recipient@test.com']),
            subject='Approval Test',
            status='PENDING'
        )
        db_session.add(email)
        db_session.commit()
        
        response = authenticated_client.post(f'/email/{email.id}/approve')
        assert response.status_code in [200, 302]
        
        # Verify status change
        updated_email = EmailMessage.query.get(email.id)
        assert updated_email.status == 'APPROVED'
    
    @pytest.mark.unit
    def test_reject_email(self, authenticated_client, db_session):
        """Test rejecting email"""
        from simple_app import EmailMessage
        
        email = EmailMessage(
            message_id='reject-test',
            sender='sender@test.com',
            recipients=json.dumps(['recipient@test.com']),
            subject='Rejection Test',
            status='PENDING'
        )
        db_session.add(email)
        db_session.commit()
        
        response = authenticated_client.post(f'/email/{email.id}/reject', data={
            'reason': 'Contains inappropriate content'
        })
        
        assert response.status_code in [200, 302]
        
        # Verify status change
        updated_email = EmailMessage.query.get(email.id)
        assert updated_email.status == 'REJECTED'
        assert 'inappropriate content' in updated_email.review_notes


class TestAPIEndpoints:
    """Test suite for API endpoints"""
    
    @pytest.mark.unit
    def test_api_requires_auth(self, client):
        """Test API endpoints require authentication"""
        endpoints = ['/api/emails', '/api/statistics', '/api/rules']
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [401, 302]
    
    @pytest.mark.unit
    def test_api_emails_list(self, authenticated_client, db_session):
        """Test API emails list endpoint"""
        from simple_app import EmailMessage
        
        # Add test emails
        for i in range(3):
            email = EmailMessage(
                message_id=f'api-test-{i}',
                sender='sender@test.com',
                recipients=json.dumps(['recipient@test.com']),
                subject=f'API Test {i}'
            )
            db_session.add(email)
        db_session.commit()
        
        response = authenticated_client.get('/api/emails')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'emails' in data
        assert len(data['emails']) == 3
    
    @pytest.mark.unit
    def test_api_statistics(self, authenticated_client, db_session):
        """Test API statistics endpoint"""
        from simple_app import EmailMessage
        
        # Add emails with different statuses
        for status in ['PENDING', 'PENDING', 'APPROVED', 'REJECTED']:
            email = EmailMessage(
                message_id=f'stat-{status}',
                sender='sender@test.com',
                recipients=json.dumps(['recipient@test.com']),
                subject=f'{status} Email',
                status=status
            )
            db_session.add(email)
        db_session.commit()
        
        response = authenticated_client.get('/api/statistics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['total'] == 4
        assert data['pending'] == 2
        assert data['approved'] == 1
        assert data['rejected'] == 1
    
    @pytest.mark.unit
    def test_api_bulk_operations(self, authenticated_client, db_session):
        """Test API bulk email operations"""
        from simple_app import EmailMessage
        
        # Add test emails
        email_ids = []
        for i in range(3):
            email = EmailMessage(
                message_id=f'bulk-test-{i}',
                sender='sender@test.com',
                recipients=json.dumps(['recipient@test.com']),
                subject=f'Bulk Test {i}',
                status='PENDING'
            )
            db_session.add(email)
            db_session.flush()
            email_ids.append(email.id)
        db_session.commit()
        
        # Bulk approve
        response = authenticated_client.post('/api/emails/bulk', json={
            'action': 'approve',
            'email_ids': email_ids
        })
        
        assert response.status_code == 200
        
        # Verify all approved
        for email_id in email_ids:
            email = EmailMessage.query.get(email_id)
            assert email.status == 'APPROVED'


class TestSecurityHeaders:
    """Test suite for security headers and CSRF protection"""
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_security_headers_present(self, client):
        """Test security headers are set"""
        response = client.get('/login')
        
        headers = response.headers
        assert 'X-Content-Type-Options' in headers
        assert headers['X-Content-Type-Options'] == 'nosniff'
        assert 'X-Frame-Options' in headers
        assert headers['X-Frame-Options'] == 'DENY'
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_csrf_protection(self, client):
        """Test CSRF protection on forms"""
        response = client.get('/login')
        assert b'csrf_token' in response.data
    
    @pytest.mark.unit
    @pytest.mark.security
    def test_xss_prevention(self, authenticated_client, db_session):
        """Test XSS prevention in user input"""
        from simple_app import EmailMessage
        
        # Create email with XSS attempt
        email = EmailMessage(
            message_id='xss-test',
            sender='sender@test.com',
            recipients=json.dumps(['recipient@test.com']),
            subject='<script>alert("XSS")</script>',
            body_text='<script>alert("XSS")</script>'
        )
        db_session.add(email)
        db_session.commit()
        
        response = authenticated_client.get(f'/email/{email.id}')
        assert response.status_code == 200
        
        # Script tags should be escaped
        assert b'<script>' not in response.data
        assert b'&lt;script&gt;' in response.data or b'\\u003cscript' in response.data