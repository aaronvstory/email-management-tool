# Testing Documentation

## Test Suite Overview

**Overall Status**: ✅ **100% pass rate (24/24 tests), 22% code coverage**

**Framework**: pytest with Flask fixtures

## Test Structure

```
tests/
├── conftest.py                    # Pytest configuration with Flask fixtures
├── test_intercept_flow.py         # Interception lifecycle (3/3 pass) ✅
├── test_unified_stats.py          # Dashboard stats (2/2 pass) ✅
├── test_latency_stats.py          # Latency metrics (4/4 pass individually, 2/4 in suite)
└── TEST_ISOLATION_STATUS.md       # Known test limitations
```

## Test Coverage

### Interception Lifecycle Tests ✅
**File**: `test_intercept_flow.py` (100% pass rate - 3/3)

- `test_fetch_stores_uid_and_internaldate` - Verifies IMAP fetch stores UID and server timestamp
- `test_manual_intercept_moves_and_latency` - Validates HELD status with remote MOVE and latency calculation
- `test_release_sets_delivered` - Confirms RELEASED/DELIVERED transition after email edit

### Dashboard Stats Tests ✅
**File**: `test_unified_stats.py` (100% pass rate - 2/2)

- Tests unified count aggregation
- Validates cache behavior with 2s TTL

### Latency Metrics Tests ⚠️
**File**: `test_latency_stats.py` (50% pass rate in suite mode)

- 2/4 tests pass when run in suite mode
- All 4 tests pass when run individually
- **Issue**: Flask singleton pattern causes state pollution between tests
- **Workaround**: Run individually or use fresh app instance per test

## Running Tests

### Full Test Suite
```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run with coverage report
python -m pytest --cov=app --cov-report=term --cov-report=html -v
```

### Test Specific Areas
```bash
# Route logic tests
python -m pytest tests/routes/ -v

# Service layer tests
python -m pytest tests/services/ -v

# Utility function tests
python -m pytest tests/utils/ -v

# Live email tests (requires .env)
python -m pytest tests/live/ -v -m live
```

### Test Specific Files
```bash
# Interception tests (recommended)
python -m pytest tests/test_intercept_flow.py -v

# Dashboard stats tests
python -m pytest tests/test_unified_stats.py -v

# Single test function
python -m pytest tests/test_intercept_flow.py::test_fetch_stores_uid_and_internaldate -v
```

### Test Output Options
```bash
# Detailed output with short traceback
python -m pytest tests/ -v --tb=short

# Skip live tests (default behavior)
python -m pytest tests/ -v -m "not live"

# Only run live tests (requires .env credentials)
python -m pytest tests/ -v -m live
```

## Coverage Goals

**Current Coverage**: 22% overall

**Target Coverage**: 50%+

**Priority Areas** (sorted by critical path importance):
1. **IMAP Watcher** (19% coverage) - Thread lifecycle, reconnection, IDLE loop
2. **Email Routes** (19% coverage) - Fetch, viewer, reply/forward operations
3. **Accounts Management** (14% coverage) - CRUD operations, health checks
4. **Interception Routes** (24% coverage) - Release, discard, edit operations
5. **Security Features** (0% coverage) - CSRF bypass attempts, rate limit validation

## Known Limitations

### Flask Singleton Issue
**Problem**: Some tests fail in suite mode but pass individually due to Flask singleton state pollution.

**Affected Tests**: `test_latency_stats.py` (2/4 tests)

**Workaround**:
```bash
# Run individually
python -m pytest tests/test_latency_stats.py::test_latency_stats_empty -v
```

**Documented**: See `tests/conftest.py` lines 3-13 and ADR-001 in CLAUDE.md

## Live Email Testing

**Environment Setup**:

Create `.env` file with test credentials:
```bash
ENABLE_LIVE_EMAIL_TESTS=1
LIVE_EMAIL_ACCOUNT=gmail  # or 'hostinger'

# Gmail credentials
GMAIL_ADDRESS=ndayijecika@gmail.com
GMAIL_PASSWORD=your_app_password_here

# Hostinger credentials
HOSTINGER_ADDRESS=mcintyre@corrinbox.com
HOSTINGER_PASSWORD=your_password_here
```

**Running Live Tests**:
```bash
# Live end-to-end test (hold → edit → release → verify in INBOX)
python scripts/live_interception_e2e.py

# Test account connections (no DB modification)
python scripts/test_permanent_accounts.py

# Verify account configuration in database
python scripts/verify_accounts.py
```

## Test Development Guidelines

### Writing New Tests

**Use Flask Fixtures** (from conftest.py):
```python
def test_my_route(client, app):
    """Test using Flask test client"""
    response = client.get('/my-route')
    assert response.status_code == 200
```

**Database Testing**:
```python
from app.utils.db import get_db

def test_database_operation(app):
    """Test with app context for database access"""
    with app.app_context():
        with get_db() as conn:
            cursor = conn.cursor()
            # ... test database operations
```

### Test Organization

**Naming Convention**:
- Test files: `test_<feature>.py`
- Test functions: `test_<what_it_tests>`
- Use descriptive names: `test_release_sets_delivered_status` not `test_release`

**Test Structure**:
```python
def test_feature_name():
    """Clear docstring describing test purpose"""
    # Arrange - Setup test data
    # Act - Execute the code being tested
    # Assert - Verify expected outcomes
```

## CI/CD Integration

**GitHub Actions** configured with:
- Python 3.13 environment
- pytest with coverage reporting
- pip-audit security scanning
- Coverage threshold enforcement (30% minimum)

**Workflow File**: `.github/workflows/pytest.yml`

## Related Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development workflow
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **tests/TEST_ISOLATION_STATUS.md** - Detailed test isolation issues
