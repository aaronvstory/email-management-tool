"""
Performance and Load Tests
Tests system performance under various load conditions
"""
import pytest
import time
import threading
import concurrent.futures
from datetime import datetime
from locust import HttpUser, task, between
import statistics


class TestLoadPerformance:
    """Load testing for system components"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_smtp_throughput(self, performance_timer):
        """Test SMTP proxy throughput"""
        from simple_app import EmailModerationHandler
        from email.message import EmailMessage
        
        handler = EmailModerationHandler()
        
        # Create test message
        msg = EmailMessage()
        msg['From'] = 'load@test.com'
        msg['To'] = 'recipient@test.com'
        msg['Subject'] = 'Load Test'
        msg.set_content('Load test content')
        
        messages_processed = 0
        performance_timer.start()
        
        # Process messages for 10 seconds
        end_time = time.time() + 10
        while time.time() < end_time:
            handler.check_moderation_rules(msg)
            messages_processed += 1
        
        performance_timer.stop()
        
        # Calculate throughput
        throughput = messages_processed / performance_timer.elapsed
        
        # Should process at least 100 messages per second
        assert throughput > 100
        
        print(f"SMTP Throughput: {throughput:.2f} messages/second")
    
    @pytest.mark.performance
    def test_database_write_performance(self, db_session, performance_timer):
        """Test database write performance"""
        from simple_app import EmailMessage
        
        performance_timer.start()
        
        # Batch insert 10000 records
        batch_size = 1000
        total_records = 10000
        
        for batch in range(0, total_records, batch_size):
            emails = []
            for i in range(batch_size):
                email = EmailMessage(
                    message_id=f'perf-{batch}-{i}',
                    sender='sender@test.com',
                    recipients='["recipient@test.com"]',
                    subject=f'Performance Test {i}',
                    body_text='Test content',
                    status='PENDING'
                )
                emails.append(email)
            
            db_session.bulk_save_objects(emails)
            db_session.commit()
        
        performance_timer.stop()
        
        # Should insert 10000 records in under 10 seconds
        assert performance_timer.elapsed < 10.0
        
        write_rate = total_records / performance_timer.elapsed
        print(f"Database Write Rate: {write_rate:.2f} records/second")
    
    @pytest.mark.performance
    def test_database_read_performance(self, db_session, performance_timer):
        """Test database read performance"""
        from simple_app import EmailMessage
        
        # First, insert test data
        emails = []
        for i in range(1000):
            email = EmailMessage(
                message_id=f'read-test-{i}',
                sender=f'sender{i}@test.com',
                recipients='["recipient@test.com"]',
                subject=f'Read Test {i}',
                status='PENDING'
            )
            emails.append(email)
        
        db_session.bulk_save_objects(emails)
        db_session.commit()
        
        performance_timer.start()
        
        # Perform various read operations
        for _ in range(100):
            # Count queries
            total = EmailMessage.query.count()
            
            # Filter queries
            pending = EmailMessage.query.filter_by(status='PENDING').all()
            
            # Pagination queries
            page = EmailMessage.query.paginate(page=1, per_page=20)
            
            # Search queries
            search = EmailMessage.query.filter(
                EmailMessage.subject.like('%Test%')
            ).limit(10).all()
        
        performance_timer.stop()
        
        # Should complete 100 query sets in under 5 seconds
        assert performance_timer.elapsed < 5.0
        
        query_rate = 100 / performance_timer.elapsed
        print(f"Database Query Rate: {query_rate:.2f} query sets/second")
    
    @pytest.mark.performance
    def test_web_response_times(self, authenticated_client, db_session):
        """Test web interface response times"""
        response_times = []
        
        endpoints = [
            '/dashboard',
            '/emails',
            '/api/statistics',
            '/api/emails'
        ]
        
        # Measure response times for each endpoint
        for endpoint in endpoints:
            times = []
            for _ in range(10):
                start = time.time()
                response = authenticated_client.get(endpoint)
                elapsed = time.time() - start
                times.append(elapsed)
                
                assert response.status_code == 200
            
            avg_time = statistics.mean(times)
            response_times.append((endpoint, avg_time))
            
            # Each endpoint should respond in under 200ms
            assert avg_time < 0.2
        
        # Print response times
        for endpoint, avg_time in response_times:
            print(f"{endpoint}: {avg_time*1000:.2f}ms average")
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_memory_usage_under_load(self, db_session):
        """Test memory usage under sustained load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        from simple_app import EmailMessage
        
        # Create sustained load for 30 seconds
        end_time = time.time() + 30
        operations = 0
        
        while time.time() < end_time:
            # Insert records
            email = EmailMessage(
                message_id=f'mem-test-{operations}',
                sender='sender@test.com',
                recipients='["recipient@test.com"]',
                subject=f'Memory Test {operations}',
                body_text='X' * 1000,  # 1KB of text
                status='PENDING'
            )
            db_session.add(email)
            
            if operations % 100 == 0:
                db_session.commit()
            
            # Query records
            if operations % 50 == 0:
                EmailMessage.query.filter_by(status='PENDING').first()
            
            operations += 1
        
        db_session.commit()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be less than 100MB
        assert memory_increase < 100
        
        print(f"Memory Usage: Initial={initial_memory:.2f}MB, "
              f"Final={final_memory:.2f}MB, "
              f"Increase={memory_increase:.2f}MB")


class TestConcurrency:
    """Test concurrent operations"""
    
    @pytest.mark.performance
    def test_concurrent_email_processing(self, db_session):
        """Test concurrent email processing"""
        from simple_app import EmailMessage
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def process_email(email_id):
            try:
                email = EmailMessage(
                    message_id=f'concurrent-{email_id}',
                    sender='sender@test.com',
                    recipients='["recipient@test.com"]',
                    subject=f'Concurrent Test {email_id}',
                    status='PENDING'
                )
                db_session.add(email)
                db_session.commit()
                results.put(email_id)
            except Exception as e:
                errors.put((email_id, str(e)))
        
        # Process 100 emails concurrently
        threads = []
        for i in range(100):
            t = threading.Thread(target=process_email, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Check results
        assert results.qsize() == 100
        assert errors.qsize() == 0
    
    @pytest.mark.performance
    def test_concurrent_api_requests(self, app):
        """Test concurrent API requests"""
        def make_api_request(request_id):
            with app.test_client() as client:
                # Login
                client.post('/login', data={
                    'username': 'admin',
                    'password': 'admin123'
                })
                
                # Make API request
                response = client.get('/api/statistics')
                return response.status_code == 200
        
        # Make 100 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_api_request, i) for i in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        success_rate = sum(results) / len(results)
        assert success_rate > 0.95  # 95% success rate
        
        print(f"API Concurrent Success Rate: {success_rate*100:.2f}%")


class EmailLoadUser(HttpUser):
    """Locust user for load testing"""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before testing"""
        self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        })
    
    @task(3)
    def view_dashboard(self):
        """View dashboard"""
        self.client.get("/dashboard")
    
    @task(5)
    def view_email_queue(self):
        """View email queue"""
        self.client.get("/emails")
    
    @task(2)
    def view_email_detail(self):
        """View random email detail"""
        import random
        email_id = random.randint(1, 100)
        self.client.get(f"/email/{email_id}")
    
    @task(1)
    def api_statistics(self):
        """Get API statistics"""
        self.client.get("/api/statistics")


class TestStressLimits:
    """Test system stress limits"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_max_concurrent_connections(self):
        """Test maximum concurrent SMTP connections"""
        from simple_app import SMTPProxyServer
        import socket
        
        server = SMTPProxyServer(host='127.0.0.1', port=8593)
        max_connections = 0
        connections = []
        
        try:
            # Try to create as many connections as possible
            for i in range(1000):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    sock.connect(('127.0.0.1', 8593))
                    connections.append(sock)
                    max_connections = i + 1
                except:
                    break
        finally:
            # Close all connections
            for sock in connections:
                sock.close()
        
        # Should handle at least 100 concurrent connections
        assert max_connections > 100
        
        print(f"Max Concurrent Connections: {max_connections}")
    
    @pytest.mark.performance
    def test_large_email_handling(self, db_session):
        """Test handling of large emails"""
        from simple_app import EmailMessage
        
        # Create email with large content (10MB)
        large_content = 'X' * (10 * 1024 * 1024)
        
        start_time = time.time()
        
        email = EmailMessage(
            message_id='large-email',
            sender='sender@test.com',
            recipients='["recipient@test.com"]',
            subject='Large Email Test',
            body_text=large_content,
            status='PENDING'
        )
        db_session.add(email)
        db_session.commit()
        
        # Retrieve the large email
        retrieved = EmailMessage.query.filter_by(message_id='large-email').first()
        assert retrieved is not None
        assert len(retrieved.body_text) == len(large_content)
        
        elapsed = time.time() - start_time
        
        # Should handle 10MB email in under 5 seconds
        assert elapsed < 5.0
        
        print(f"Large Email Handling: {elapsed:.2f} seconds for 10MB")


# Performance benchmark results storage
BENCHMARK_RESULTS = {
    'smtp_throughput': [],
    'db_write_rate': [],
    'db_read_rate': [],
    'response_times': [],
    'memory_usage': [],
    'concurrent_success': []
}


def generate_performance_report():
    """Generate performance test report"""
    report = """
    ====================================
    PERFORMANCE TEST REPORT
    ====================================
    
    SMTP Throughput: {smtp_throughput} msgs/sec
    Database Write: {db_write} records/sec
    Database Read: {db_read} queries/sec
    API Response: {api_response}ms average
    Memory Usage: {memory}MB increase
    Concurrent Success: {concurrent}%
    
    RECOMMENDATIONS:
    - Optimize database queries for better read performance
    - Implement connection pooling for SMTP
    - Add caching for frequently accessed data
    - Consider horizontal scaling for high load
    """
    
    # Calculate averages from benchmark results
    # This would be populated during actual test runs
    
    print(report)