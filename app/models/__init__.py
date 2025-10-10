"""
Database models for Email Management Tool
"""
from .base import db, Base
from .user import User, Role
from .email import EmailMessage, EmailAttachment
from .rule import ModerationRule, RuleType, RuleAction
from .account import EmailAccount
# TODO Phase 2: Fix AuditLog model (metadata is reserved word in SQLAlchemy)
# from .audit import AuditLog

__all__ = [
    'db',
    'Base',
    'User',
    'Role',
    'EmailMessage',
    'EmailAttachment',
    'ModerationRule',
    'RuleType',
    'RuleAction',
    'EmailAccount',
    # 'AuditLog'  # Temporarily disabled - has SQLAlchemy reserved word issue
]