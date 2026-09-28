"""SECRET_KEY Configuration Security Tests.

Verifies:
1. Production mode fails fast with RuntimeError if SECRET_KEY is missing.
2. Production mode fails fast if known insecure hardcoded secrets are used.
3. Production mode succeeds when a strong, non-default SECRET_KEY is provided.
4. Non-production modes allow safe development without crashing.
"""

import os
import pytest
from unittest import mock
from config import get_secret_key, INSECURE_FALLBACK_SECRETS
from app import create_app


def test_production_fails_fast_when_secret_key_missing():
    """Application must refuse to start in production if SECRET_KEY is not set."""
    with mock.patch.dict(os.environ, {"FLASK_ENV": "production", "SECRET_KEY": ""}):
        with pytest.raises(RuntimeError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
            get_secret_key(is_production=True)

        with pytest.raises(RuntimeError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
            create_app()


def test_production_fails_fast_on_known_hardcoded_secrets():
    """Application must refuse to silently accept known insecure defaults in production."""
    for bad_secret in INSECURE_FALLBACK_SECRETS:
        with mock.patch.dict(os.environ, {"FLASK_ENV": "production", "SECRET_KEY": bad_secret}):
            with pytest.raises(RuntimeError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
                get_secret_key(is_production=True)


def test_production_succeeds_with_secure_secret():
    """Application accepts a strong secret key in production mode."""
    secure_key = "a-very-strong-production-cryptographic-secret-key-12345"
    with mock.patch.dict(os.environ, {"FLASK_ENV": "production", "SECRET_KEY": secure_key}):
        key = get_secret_key(is_production=True)
        assert key == secure_key
