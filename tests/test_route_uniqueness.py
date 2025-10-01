"""
Test for route uniqueness between simple_app.py and interception blueprint.
Ensures no duplicate routes exist after migration to blueprint pattern.
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_no_duplicate_routes():
    """Verify no duplicate routes between main app and blueprint"""
    from simple_app import app

    # Collect all registered routes
    routes = []
    for rule in app.url_map.iter_rules():
        route_info = {
            'rule': rule.rule,
            'methods': sorted(rule.methods - {'HEAD', 'OPTIONS'}),
            'endpoint': rule.endpoint
        }
        routes.append(route_info)

    # Check for duplicates by (rule, methods) tuple
    seen = {}
    duplicates = []

    for route in routes:
        key = (route['rule'], tuple(route['methods']))
        if key in seen:
            duplicates.append({
                'route': route['rule'],
                'methods': route['methods'],
                'endpoints': [seen[key], route['endpoint']]
            })
        else:
            seen[key] = route['endpoint']

    # Assert no duplicates found
    if duplicates:
        error_msg = "Duplicate routes detected:\n"
        for dup in duplicates:
            error_msg += f"  {dup['route']} {dup['methods']} -> {dup['endpoints']}\n"
        pytest.fail(error_msg)

    print(f"✓ No duplicate routes found ({len(routes)} unique routes)")

def test_interception_routes_in_blueprint():
    """Verify interception routes are properly registered via blueprint"""
    from simple_app import app

    # Expected interception routes that should be in blueprint
    expected_blueprint_routes = [
        '/healthz',
        '/interception',
        '/api/interception/held',
        '/api/interception/held/<int:msg_id>',
        '/api/interception/release/<int:msg_id>',
        '/api/interception/discard/<int:msg_id>',
        '/api/inbox',
        '/api/email/<int:email_id>/edit'
    ]

    # Collect routes from blueprint
    blueprint_routes = [
        rule.rule for rule in app.url_map.iter_rules()
        if rule.endpoint.startswith('interception_bp.')
    ]

    # Check each expected route is registered
    missing = []
    for route in expected_blueprint_routes:
        if route not in blueprint_routes:
            missing.append(route)

    if missing:
        pytest.fail(f"Missing blueprint routes: {missing}")

    print(f"✓ All {len(expected_blueprint_routes)} interception routes properly registered in blueprint")

def test_no_interception_routes_in_main_app():
    """Verify interception routes are NOT duplicated in main app"""
    from simple_app import app

    # Interception route patterns that should NOT be in main app
    forbidden_patterns = [
        'api/interception/held',
        'api/interception/release',
        'api/interception/discard',
        'api/inbox',
        'api/email/<int:email_id>/edit'
    ]

    # Collect routes from main app (not blueprint)
    main_app_routes = [
        rule.rule for rule in app.url_map.iter_rules()
        if not rule.endpoint.startswith('interception_bp.')
    ]

    # Check for forbidden patterns
    violations = []
    for route in main_app_routes:
        for pattern in forbidden_patterns:
            if pattern in route:
                violations.append(route)

    if violations:
        pytest.fail(f"Interception routes found in main app (should be blueprint-only): {violations}")

    print(f"✓ No interception routes duplicated in main app")

if __name__ == '__main__':
    # Run tests when executed directly
    pytest.main([__file__, '-v'])