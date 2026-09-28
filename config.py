"""Flask application configuration."""

import os

from dotenv import load_dotenv

load_dotenv()


INSECURE_FALLBACK_SECRETS = {
    "dev-secret-key-change-in-production",
    "dev-secret-key",
    "change-me-to-a-random-secret-key",
    "default",
    "secret",
}


def get_secret_key(is_production: bool = False) -> str:
    """Retrieve SECRET_KEY with strict validation for production."""
    secret = os.getenv("SECRET_KEY")
    if is_production:
        if not secret or secret.strip() in INSECURE_FALLBACK_SECRETS:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY environment variable "
                "must be explicitly set to a strong, secure value in production mode. "
                "Hardcoded and known default secrets are strictly prohibited."
            )
        return secret
    return secret or "dev-insecure-transient-key-not-for-production"


class Config:
    """Base configuration."""

    ENV = os.getenv("FLASK_ENV", "development").lower()
    IS_PRODUCTION = ENV == "production"
    SECRET_KEY = get_secret_key(IS_PRODUCTION)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///local_fallback.db",  # Fallback for local development
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SECRET_KEY = None  # Validated dynamically upon initialization

    def __init__(self):
        self.SECRET_KEY = get_secret_key(is_production=True)


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
