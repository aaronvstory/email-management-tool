#!/usr/bin/env python3
"""
API Performance and Functionality Testing
Tests web interface, API endpoints, response times, and system reliability
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def test_endpoint(name, url, method='GET', data=None, expected_status=200, auth=None):
    """Test a single endpoint and measure performance"""
    try:
        start = time.time()
        
        if method == 'GET':
            response = requests.get(url, auth=auth, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, auth=auth, timeout=10)
        else:
            return {'success': False, 'error': f'Unsupported method: {method}'}
        
        elapsed_ms = int((time.time() - start) * 1000)
        
        success = response.status_code == expected_status
        
        result = {
            'name': name,
            'url': url,
            'method': method,
            'status_code': response.status_code,
            'expected_status': expected_status,
            'success': success,
            'latency_ms': elapsed_ms,
            'content_length': len(response.content)
        }
        
        # Try to parse JSON
        try:
            result['json'] = response.json()
        except:
            result['json'] = None
        
        status_icon = "✓" if success else "✗"
        print(f"{status_icon} {name}")
        print(f"   Status: {response.status_code} (expected {expected_status})")
        print(f"   Latency: {elapsed_ms}ms")
        print(f"   Size: {len(response.content)} bytes")
        
        return result
        
    except Exception as e:
        print(f"✗ {name}")
        print(f"   Error: {e}")
        return {'success': False, 'error': str(e)}

def main():
    print_section("API PERFORMANCE & FUNCTIONALITY TEST")
    
    results = []
    
    # Test health endpoint
    print_section("1. HEALTH & STATUS ENDPOINTS")
    results.append(test_endpoint("Health Check", f"{BASE_URL}/healthz"))
    
    # Test authentication (should redirect without auth)
    print_section("2. AUTHENTICATION ENDPOINTS")
    results.append(test_endpoint("Login Page", f"{BASE_URL}/login", expected_status=200))
    results.append(test_endpoint("Dashboard (no auth)", f"{BASE_URL}/dashboard", expected_status=302))
    
    # Test with authentication
    print_section("3. AUTHENTICATED API ENDPOINTS")
    session = requests.Session()
    
    # Login first
    login_data = {'username': 'admin', 'password': 'admin123'}
    login_response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    
    if login_response.status_code in [200, 302]:
        print("✓ Login successful")
        
        # Test authenticated endpoints
        endpoints = [
            ("Dashboard", "/dashboard", 200),
            ("Email Queue", "/emails", 200),
            ("Accounts Page", "/accounts", 200),
            ("API Stats", "/api/stats", 200),
            ("API Unified Stats", "/api/unified-stats", 200),
            ("API Interception Held", "/api/interception/held", 200),
            ("Compose Page", "/compose", 200),
            ("Inbox Page", "/inbox", 200),
        ]
        
        for name, endpoint, expected in endpoints:
            try:
                start = time.time()
                resp = session.get(f"{BASE_URL}{endpoint}", timeout=10)
                elapsed_ms = int((time.time() - start) * 1000)
                
                success = resp.status_code == expected
                status_icon = "✓" if success else "✗"
                
                print(f"{status_icon} {name}")
                print(f"   Status: {resp.status_code} (expected {expected})")
                print(f"   Latency: {elapsed_ms}ms")
                print(f"   Size: {len(resp.content)} bytes")
                
                results.append({
                    'name': name,
                    'url': endpoint,
                    'status_code': resp.status_code,
                    'expected_status': expected,
                    'success': success,
                    'latency_ms': elapsed_ms,
                    'content_length': len(resp.content)
                })
            except Exception as e:
                print(f"✗ {name}: {e}")
                results.append({'name': name, 'success': False, 'error': str(e)})
    else:
        print(f"✗ Login failed: {login_response.status_code}")
    
    # Performance metrics
    print_section("4. PERFORMANCE METRICS")
    
    successful_tests = [r for r in results if r.get('success')]
    if successful_tests:
        latencies = [r['latency_ms'] for r in successful_tests if 'latency_ms' in r]
        
        print(f"Total endpoints tested: {len(results)}")
        print(f"Successful: {len(successful_tests)}")
        print(f"Failed: {len(results) - len(successful_tests)}")
        
        if latencies:
            print(f"\nLatency statistics:")
            print(f"  Min: {min(latencies)}ms")
            print(f"  Max: {max(latencies)}ms")
            print(f"  Average: {sum(latencies)/len(latencies):.1f}ms")
            print(f"  Median: {sorted(latencies)[len(latencies)//2]}ms")
    
    # Save results
    output_file = f"api_test_results_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'summary': {
                'total': len(results),
                'successful': len(successful_tests),
                'failed': len(results) - len(successful_tests)
            }
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    return 0 if len(successful_tests) == len(results) else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())