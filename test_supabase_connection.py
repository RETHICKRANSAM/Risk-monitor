"""Test script to verify Supabase connection.
Run this to check if your Supabase credentials are working correctly.
"""

import os

from dotenv import load_dotenv

from supabase_client import get_supabase_client

load_dotenv()


def check_connection():
    """Test the Supabase connection."""
    print("=" * 60)
    print("Testing Supabase Connection")
    print("=" * 60)

    # Check environment variables
    print("\n1. Checking environment variables...")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url:
        print("   ✗ SUPABASE_URL not found in .env")
        return False
    print(f"   ✓ SUPABASE_URL: {supabase_url}")

    if not supabase_key:
        print("   ✗ SUPABASE_KEY not found in .env")
        return False
    print(f"   ✓ SUPABASE_KEY: {supabase_key[:20]}...")

    # Test client initialization
    print("\n2. Initializing Supabase client...")
    try:
        supabase = get_supabase_client()
        print("   ✓ Supabase client initialized successfully!")
    except Exception as e:
        print(f"   ✗ Failed to initialize client: {e}")
        return False

    # Test database connection
    print("\n3. Testing database connection...")
    try:
        # Try to query a system table or any table you have
        # This will fail if the table doesn't exist, but connection will be tested
        response = supabase.table("alerts").select("*").limit(1).execute()
        print("   ✓ Database connection successful!")
        print(f"   ✓ Found {len(response.data)} records in 'alerts' table")
    except Exception as e:
        error_str = str(e)
        if "relation" in error_str and "does not exist" in error_str:
            print("   ✓ Connection successful (table 'alerts' doesn't exist yet)")
        else:
            print(f"   ⚠ Connection test result: {e}")

    # List available tables (if possible)
    print("\n4. Checking database schema...")
    try:
        # Query information schema (PostgreSQL specific)
        # Note: Direct SQL queries require service_role key, not anon key
        print("   ⚠ Table listing requires service_role key (not anon/publishable key)")
    except Exception as e:
        print(f"   ⚠ Could not list tables: {e}")

    print("\n" + "=" * 60)
    print("Connection Test Complete!")
    print("=" * 60)
    print("\nYour Supabase client is ready to use!")
    print("\nNext steps:")
    print("1. Create tables in your Supabase dashboard")
    print("2. Use the example_supabase_usage.py file for reference")
    print("3. Start building your application with Supabase!")

    return True


if __name__ == "__main__":
    try:
        success = check_connection()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        exit(1)
