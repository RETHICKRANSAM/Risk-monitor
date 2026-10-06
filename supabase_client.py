"""Supabase client initialization and utilities for Pre-Release Risk Monitor."""

import logging
import os
import urllib.parse
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger(__name__)


def mask_key(key: str | None) -> str:
    """Safely mask API key for logging or terminal display."""
    if not key:
        return "<not set>"
    key = key.strip()
    if len(key) <= 10:
        return "..."
    return f"{key[:10]}..."


def validate_supabase_url(url: str | None) -> tuple[bool, str, str]:
    """Validate SUPABASE_URL structure.

    Returns:
        tuple[bool, str, str]: (is_valid, hostname, error_message)
    """
    if not url:
        return False, "", "SUPABASE_URL environment variable is missing or empty."
    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("https", "http"):
            return False, "", f"SUPABASE_URL must use https:// (got scheme '{parsed.scheme}')."
        if not parsed.netloc:
            return False, "", "SUPABASE_URL does not contain a valid hostname."
        return True, parsed.netloc, ""
    except Exception as e:
        return False, "", f"Failed to parse SUPABASE_URL: {e}"


class SupabaseConnectionError(RuntimeError):
    """Raised when Supabase host cannot be resolved or reached."""


class SupabaseClient:
    """Singleton Supabase client wrapper with resilient validation."""

    _instance = None
    _client: Client | None = None
    _hostname: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for re-testing with updated env vars)."""
        cls._instance = None
        cls._client = None
        cls._hostname = ""

    def _initialize_client(self):
        """Initialize the Supabase client with URL format validation."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables (.env)",
            )

        is_valid, hostname, err = validate_supabase_url(supabase_url)
        if not is_valid:
            raise ValueError(f"Invalid SUPABASE_URL: {err}")

        self._hostname = hostname

        try:
            self._client = create_client(supabase_url.strip(), supabase_key.strip())
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Supabase client for host '{self._hostname}': {e}"
            ) from e

    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        return self._client  # type: ignore

    @property
    def hostname(self) -> str:
        """Get the configured Supabase hostname."""
        return self._hostname


# Convenience function to get Supabase client
def get_supabase_client() -> Client:
    """Get the Supabase client instance.

    Returns:
        Client: Supabase client instance
    """
    return SupabaseClient().client


def _handle_supabase_error(e: Exception, operation: str, table_name: str) -> None:
    """Format clear diagnostic error messages for Supabase operations."""
    err_str = str(e)
    hostname = SupabaseClient().hostname or "supabase.co"
    if "11001" in err_str or "getaddrinfo failed" in err_str or "gaierror" in err_str:
        msg = (
            f"Supabase {operation} on table '{table_name}' failed because hostname "
            f"'{hostname}' could not be resolved (DNS failure). "
            f"The project URL in SUPABASE_URL appears invalid, paused, or outdated. "
            f"Please update SUPABASE_URL in .env with your Project URL from Supabase Dashboard → Settings → API."
        )
        logger.error(msg)
        raise SupabaseConnectionError(msg) from e
    raise e


# Safe query helper functions
def query_table(table_name: str, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Query a Supabase table with optional filters."""
    try:
        supabase = get_supabase_client()
        query = supabase.table(table_name).select("*")
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        response = query.execute()
        return response.data
    except Exception as e:
        _handle_supabase_error(e, "query", table_name)
        return []


def insert_data(table_name: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    """Insert data into a Supabase table."""
    try:
        supabase = get_supabase_client()
        response = supabase.table(table_name).insert(data).execute()
        return response.data
    except Exception as e:
        _handle_supabase_error(e, "insert", table_name)
        return []


def update_data(table_name: str, filters: dict[str, Any], updates: dict[str, Any]) -> list[dict[str, Any]]:
    """Update data in a Supabase table."""
    try:
        supabase = get_supabase_client()
        query = supabase.table(table_name).update(updates)
        for column, value in filters.items():
            query = query.eq(column, value)
        response = query.execute()
        return response.data
    except Exception as e:
        _handle_supabase_error(e, "update", table_name)
        return []


def delete_data(table_name: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Delete data from a Supabase table."""
    try:
        supabase = get_supabase_client()
        query = supabase.table(table_name).delete()
        for column, value in filters.items():
            query = query.eq(column, value)
        response = query.execute()
        return response.data
    except Exception as e:
        _handle_supabase_error(e, "delete", table_name)
        return []
