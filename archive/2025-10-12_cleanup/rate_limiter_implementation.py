#!/usr/bin/env python3
"""
Rate limiting and connection pooling implementation for Email Management Tool
"""

import time
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
import imaplib
import logging

log = logging.getLogger(__name__)

# ============================================================================
# Rate Limiter for Edit API
# ============================================================================

class RateLimiter:
    """
    Token bucket rate limiter for API endpoints.
    Prevents abuse of email edit functionality.
    """

    def __init__(self, requests_per_minute=10, burst_size=15):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.buckets = defaultdict(lambda: {
            'tokens': burst_size,
            'last_update': time.time()
        })
        self.lock = threading.Lock()

    def is_allowed(self, client_id):
        """
        Check if request is allowed for given client.
        Returns (allowed, wait_time_seconds)
        """
        with self.lock:
            now = time.time()
            bucket = self.buckets[client_id]

            # Refill tokens based on time passed
            time_passed = now - bucket['last_update']
            tokens_to_add = time_passed * (self.requests_per_minute / 60)
            bucket['tokens'] = min(self.burst_size, bucket['tokens'] + tokens_to_add)
            bucket['last_update'] = now

            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True, 0
            else:
                # Calculate wait time
                wait_time = (1 - bucket['tokens']) * 60 / self.requests_per_minute
                return False, wait_time

    def reset(self, client_id):
        """Reset rate limit for a client"""
        with self.lock:
            if client_id in self.buckets:
                del self.buckets[client_id]

# ============================================================================
# IMAP Connection Pool
# ============================================================================

class IMAPConnectionPool:
    """
    Connection pool for IMAP operations with retry logic.
    Prevents connection exhaustion and improves performance.
    """

    def __init__(self, max_connections=5, max_retries=3, retry_delay=2):
        self.max_connections = max_connections
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.pools = {}  # Per-account pools
        self.lock = threading.Lock()

    def _create_connection(self, config):
        """Create a new IMAP connection"""
        for attempt in range(self.max_retries):
            try:
                if config['use_ssl']:
                    conn = imaplib.IMAP4_SSL(config['host'], config['port'])
                else:
                    conn = imaplib.IMAP4(config['host'], config['port'])

                conn.login(config['username'], config['password'])
                log.info(f"IMAP connection established for {config['username']}")
                return conn

            except Exception as e:
                log.error(f"IMAP connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise

    @contextmanager
    def get_connection(self, account_id, config):
        """
        Get an IMAP connection from the pool.
        Creates new connection if pool is empty.
        """
        pool_key = f"{config['host']}:{config['port']}:{config['username']}"

        with self.lock:
            if pool_key not in self.pools:
                self.pools[pool_key] = {
                    'available': deque(maxlen=self.max_connections),
                    'in_use': set(),
                    'config': config
                }

            pool = self.pools[pool_key]

        conn = None
        try:
            # Try to get connection from pool
            with self.lock:
                if pool['available']:
                    conn = pool['available'].popleft()
                    # Test if connection is alive
                    try:
                        conn.noop()
                    except:
                        conn = None

            # Create new connection if needed
            if conn is None:
                conn = self._create_connection(config)

            with self.lock:
                pool['in_use'].add(conn)

            yield conn

            # Return connection to pool
            with self.lock:
                pool['in_use'].discard(conn)
                if len(pool['available']) < self.max_connections:
                    pool['available'].append(conn)
                else:
                    # Pool is full, close this connection
                    try:
                        conn.logout()
                    except:
                        pass

        except Exception as e:
            # Connection failed, don't return to pool
            if conn:
                with self.lock:
                    pool['in_use'].discard(conn)
                try:
                    conn.logout()
                except:
                    pass
            raise

    def close_all(self):
        """Close all connections in all pools"""
        with self.lock:
            for pool_key, pool in self.pools.items():
                # Close available connections
                while pool['available']:
                    conn = pool['available'].popleft()
                    try:
                        conn.logout()
                    except:
                        pass

                # Note: in_use connections will be closed when released
                pool['in_use'].clear()

            self.pools.clear()

# ============================================================================
# SMTP Proxy Health Monitor
# ============================================================================

class SMTPProxyMonitor:
    """
    Health monitoring for SMTP proxy with auto-restart capability.
    """

    def __init__(self, host='localhost', port=8587, check_interval=30):
        self.host = host
        self.port = port
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.last_healthy = time.time()
        self.restart_callback = None

    def start(self, restart_callback=None):
        """Start monitoring SMTP proxy health"""
        self.running = True
        self.restart_callback = restart_callback
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        log.info(f"SMTP proxy monitor started for {self.host}:{self.port}")

    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _monitor_loop(self):
        """Main monitoring loop"""
        consecutive_failures = 0

        while self.running:
            try:
                # Check if SMTP proxy is responsive
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((self.host, self.port))
                sock.close()

                if result == 0:
                    # Port is open, try SMTP handshake
                    import smtplib
                    try:
                        with smtplib.SMTP(self.host, self.port, timeout=5) as smtp:
                            # Just connect and quit
                            pass

                        # Healthy
                        self.last_healthy = time.time()
                        consecutive_failures = 0
                        log.debug(f"SMTP proxy health check passed")

                    except Exception as e:
                        consecutive_failures += 1
                        log.warning(f"SMTP proxy not responding properly: {e}")

                else:
                    # Port not open
                    consecutive_failures += 1
                    log.error(f"SMTP proxy port {self.port} not open")

                # Auto-restart if too many failures
                if consecutive_failures >= 3:
                    log.critical(f"SMTP proxy failed {consecutive_failures} consecutive checks")
                    if self.restart_callback:
                        log.info("Attempting to restart SMTP proxy...")
                        self.restart_callback()
                        consecutive_failures = 0
                        time.sleep(10)  # Give time for restart

            except Exception as e:
                log.error(f"Error in SMTP monitor: {e}")

            time.sleep(self.check_interval)

    def is_healthy(self):
        """Check if proxy is considered healthy"""
        return (time.time() - self.last_healthy) < (self.check_interval * 2)

# ============================================================================
# Flask Integration Example
# ============================================================================

def integrate_rate_limiting(app):
    """
    Integrate rate limiting into Flask app.
    Add this to simple_app.py after Flask app creation.
    """
    from flask import request, jsonify
    from functools import wraps

    # Create global rate limiter
    rate_limiter = RateLimiter(requests_per_minute=30, burst_size=50)

    def rate_limit(requests_per_minute=30):
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                # Use IP address as client ID
                client_id = request.remote_addr

                allowed, wait_time = rate_limiter.is_allowed(client_id)
                if not allowed:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': int(wait_time)
                    }), 429

                return f(*args, **kwargs)
            return wrapped
        return decorator

    # Apply to edit endpoint
    # In app/routes/interception.py, add @rate_limit() decorator:
    # @bp_interception.route('/api/email/<int:email_id>/edit', methods=['POST'])
    # @login_required
    # @rate_limit(requests_per_minute=30)
    # def api_email_edit(email_id:int):
    #     ...

    return rate_limiter

# ============================================================================
# Testing
# ============================================================================

def test_rate_limiter():
    """Test rate limiting functionality"""
    print("\n" + "="*60)
    print("Testing Rate Limiter")
    print("="*60)

    limiter = RateLimiter(requests_per_minute=6, burst_size=3)

    # Test burst
    print("\n1. Testing burst capacity (3 requests):")
    for i in range(5):
        allowed, wait = limiter.is_allowed("test_client")
        print(f"   Request {i+1}: {'✅ Allowed' if allowed else f'❌ Denied (wait {wait:.1f}s)'}")

    # Wait and test refill
    print("\n2. Waiting 10 seconds for token refill...")
    time.sleep(10)

    allowed, wait = limiter.is_allowed("test_client")
    print(f"   After wait: {'✅ Allowed' if allowed else f'❌ Denied'}")

    print("\n✅ Rate limiter test complete")

def test_connection_pool():
    """Test IMAP connection pooling"""
    print("\n" + "="*60)
    print("Testing Connection Pool")
    print("="*60)

    # Note: This would need real IMAP credentials to fully test
    pool = IMAPConnectionPool(max_connections=3)

    config = {
        'host': 'imap.gmail.com',
        'port': 993,
        'use_ssl': True,
        'username': 'test@example.com',
        'password': 'test_password'
    }

    print("\n1. Connection pool initialized")
    print(f"   Max connections: {pool.max_connections}")
    print(f"   Max retries: {pool.max_retries}")

    # Would need real credentials to test actual connections
    print("\n⚠️  Full test requires valid IMAP credentials")
    print("✅ Connection pool structure test complete")

if __name__ == "__main__":
    test_rate_limiter()
    test_connection_pool()