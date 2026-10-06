"""Unit tests for Supabase configuration, URL validation, and connection diagnostics."""

import os
from unittest import mock

import pytest

from supabase_client import mask_key, validate_supabase_url
from test_supabase_connection import test_supabase_connection as run_connection_test


def test_mask_key():
    """Verify that sensitive keys are masked and not leaked."""
    assert mask_key("") == "<not set>"
    assert mask_key(None) == "<not set>"
    assert mask_key("short") == "..."
    # 20+ char key
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    masked = mask_key(key)
    assert masked.startswith("eyJhbGciOi...")
    assert key not in masked or len(masked) < len(key)
    assert len(masked) == 13  # 10 chars + 3 dots


def test_validate_supabase_url():
    """Verify URL validation rejects invalid URLs and parses valid ones."""
    # Missing / empty
    valid, _, err = validate_supabase_url("")
    assert not valid
    assert "missing" in err.lower()

    # Wrong scheme
    valid, _, err = validate_supabase_url("ftp://example.supabase.co")
    assert not valid
    assert "https://" in err

    # Missing netloc
    valid, _, err = validate_supabase_url("https://")
    assert not valid

    # Valid Supabase URL
    valid, hostname, err = validate_supabase_url("https://abcxyz123.supabase.co")
    assert valid
    assert hostname == "abcxyz123.supabase.co"
    assert err == ""


def test_connection_diagnostic_missing_env():
    """Diagnostic test must return False when environment variables are missing."""
    with mock.patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""}):
        result = run_connection_test()
        assert result is False


def test_connection_diagnostic_unresolvable_domain():
    """Diagnostic test must return False and not crash when domain is unresolvable."""
    with mock.patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://nonexistent-domain-test-123456789.supabase.co",
            "SUPABASE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy",
        },
    ):
        result = run_connection_test()
        assert result is False
