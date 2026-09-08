"""Supabase client initialization and utilities."""

import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


class SupabaseClient:
    """Singleton Supabase client wrapper."""

    _instance = None
    _client: Client | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        """Initialize the Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables",
            )

        self._client = create_client(supabase_url, supabase_key)

    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        return self._client  # type: ignore


# Convenience function to get Supabase client
def get_supabase_client() -> Client:
    """Get the Supabase client instance.

    Returns:
        Client: Supabase client instance

    Example:
        >>> supabase = get_supabase_client()
        >>> data = supabase.table('your_table').select("*").execute()

    """
    return SupabaseClient().client


# Example usage functions
def query_table(table_name: str, filters: dict | None = None):
    """Query a Supabase table with optional filters.

    Args:
        table_name: Name of the table to query
        filters: Dictionary of column:value pairs to filter by

    Returns:
        Query result data

    Example:
        >>> data = query_table('users', {'email': 'test@example.com'})

    """
    supabase = get_supabase_client()
    query = supabase.table(table_name).select("*")

    if filters:
        for column, value in filters.items():
            query = query.eq(column, value)

    response = query.execute()
    return response.data


def insert_data(table_name: str, data: dict):
    """Insert data into a Supabase table.

    Args:
        table_name: Name of the table
        data: Dictionary of data to insert

    Returns:
        Inserted data

    Example:
        >>> result = insert_data('users', {'name': 'John', 'email': 'john@example.com'})

    """
    supabase = get_supabase_client()
    response = supabase.table(table_name).insert(data).execute()
    return response.data


def update_data(table_name: str, filters: dict, updates: dict):
    """Update data in a Supabase table.

    Args:
        table_name: Name of the table
        filters: Dictionary of column:value pairs to filter records
        updates: Dictionary of updates to apply

    Returns:
        Updated data

    Example:
        >>> result = update_data('users', {'id': 1}, {'name': 'Jane'})

    """
    supabase = get_supabase_client()
    query = supabase.table(table_name).update(updates)

    for column, value in filters.items():
        query = query.eq(column, value)

    response = query.execute()
    return response.data


def delete_data(table_name: str, filters: dict):
    """Delete data from a Supabase table.

    Args:
        table_name: Name of the table
        filters: Dictionary of column:value pairs to filter records

    Returns:
        Deleted data

    Example:
        >>> result = delete_data('users', {'id': 1})

    """
    supabase = get_supabase_client()
    query = supabase.table(table_name).delete()

    for column, value in filters.items():
        query = query.eq(column, value)

    response = query.execute()
    return response.data
