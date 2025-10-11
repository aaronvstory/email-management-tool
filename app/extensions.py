"""
Flask extensions initialization
Shared instances for limiter and csrf to be used across blueprints.

These are created here (module import time) so blueprints can safely
reference them in decorators. The actual app binding happens in
simple_app.py via .init_app(app).
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect

# Global extension instances (configured in simple_app.py)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

csrf = CSRFProtect()
