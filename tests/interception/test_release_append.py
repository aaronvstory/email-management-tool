"""
Tests for Release Editor

Structural tests for message release functionality.
Full integration tests require live IMAP server access.
"""

import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def test_import_release_editor():
    """Test that release_editor module can be imported"""
    from app.services.interception import release_editor
    assert release_editor is not None


def test_import_append_edited():
    """Test that append_edited function exists and is callable"""
    from app.services.interception.release_editor import append_edited
    assert callable(append_edited)


def test_import_build_edited_mime():
    """Test that build_edited_mime function exists"""
    from app.services.interception.release_editor import build_edited_mime
    assert callable(build_edited_mime)


def test_build_edited_mime_basic():
    """Test building a basic MIME message"""
    from app.services.interception.release_editor import build_edited_mime
    
    mime_bytes = build_edited_mime(
        sender="sender@example.com",
        recipients="recipient@example.com",
        subject="Test Subject",
        body_text="This is a test message"
    )
    
    assert isinstance(mime_bytes, bytes)
    assert len(mime_bytes) > 0
    assert b"From: sender@example.com" in mime_bytes
    assert b"To: recipient@example.com" in mime_bytes
    assert b"Subject: Test Subject" in mime_bytes
    assert b"This is a test message" in mime_bytes


def test_build_edited_mime_with_html():
    """Test building MIME message with HTML body"""
    from app.services.interception.release_editor import build_edited_mime
    
    mime_bytes = build_edited_mime(
        sender="sender@example.com",
        recipients="recipient@example.com",
        subject="Test Subject",
        body_text="Plain text version",
        body_html="<html><body><p>HTML version</p></body></html>"
    )    
    assert isinstance(mime_bytes, bytes)
    assert b"Plain text version" in mime_bytes
    # HTML part should be in the message
    assert b"HTML version" in mime_bytes


def test_build_edited_mime_with_custom_message_id():
    """Test building MIME message with custom Message-ID"""
    from app.services.interception.release_editor import build_edited_mime
    
    custom_msg_id = "<test123@example.com>"
    
    mime_bytes = build_edited_mime(
        sender="sender@example.com",
        recipients="recipient@example.com",
        subject="Test Subject",
        body_text="Test body",
        message_id=custom_msg_id
    )
    
    assert custom_msg_id.encode() in mime_bytes