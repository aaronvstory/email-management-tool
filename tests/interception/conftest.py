import os
import sys
import pytest

# Minimal, isolation-focused conftest for interception tests only.
# Avoid importing the heavy global application context.
# Ensure project root is on sys.path for module discovery.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

@pytest.fixture(autouse=True)
def _isolation_env(monkeypatch):
    # Prevent dotenv or other heavy initializations if present.
    monkeypatch.setenv('PYTEST_INTERCEPTION_ISOLATED', '1')
    # Provide a temp database path if any code accidentally touches DB constants.
    monkeypatch.setenv('INTERCEPTION_TESTING', '1')
    yield
