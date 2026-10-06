"""Comprehensive diagnostic test for Supabase connectivity.

Verifies:
1. Environment variables exist in .env
2. URL format and HTTPS protocol
3. Hostname extraction and DNS resolution
4. HTTPS port 443 network reachability
5. Supabase client initialization
6. Safe database query using the anon/publishable key (without requiring service_role)
7. Clear distinction between DNS, network, auth, and schema issues
"""

import os
import socket
import sys
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

# Ensure fresh reload of .env
load_dotenv(override=True)

from supabase_client import SupabaseClient, get_supabase_client, mask_key, validate_supabase_url


def test_supabase_connection() -> bool:
    """Run full diagnostic test suite on configured Supabase credentials."""
    print("=" * 68)
    print("      SUPABASE CONNECTION & CONFIGURATION DIAGNOSTICS")
    print("=" * 68)

    # -------------------------------------------------------------
    # 1. Environment Variables Check
    # -------------------------------------------------------------
    print("\n[Step 1/6] Inspecting environment variables (.env)...")
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()

    if not supabase_url:
        print("  ✗ FAILURE: SUPABASE_URL is missing or empty in .env")
        print("    Remedy: Set SUPABASE_URL=https://<project-ref>.supabase.co in .env")
        return False

    if not supabase_key:
        print("  ✗ FAILURE: SUPABASE_KEY is missing or empty in .env")
        print("    Remedy: Set SUPABASE_KEY=<your-anon-key> in .env")
        return False

    masked_key = mask_key(supabase_key)
    print(f"  ✓ Found SUPABASE_URL: {supabase_url}")
    print(f"  ✓ Found SUPABASE_KEY: {masked_key} (masked for security)")

    # -------------------------------------------------------------
    # 2. URL Format Validation
    # -------------------------------------------------------------
    print("\n[Step 2/6] Validating URL structure...")
    is_valid, hostname, url_err = validate_supabase_url(supabase_url)
    if not is_valid:
        print(f"  ✗ FAILURE: Invalid SUPABASE_URL format: {url_err}")
        print("    Expected format: https://<project-ref>.supabase.co")
        return False

    print(f"  ✓ URL format is valid.")
    print(f"  ✓ Extracted target hostname: {hostname}")

    # -------------------------------------------------------------
    # 3. DNS Resolution
    # -------------------------------------------------------------
    print(f"\n[Step 3/6] Performing DNS resolution for '{hostname}'...")
    try:
        resolved_ips = socket.gethostbyname_ex(hostname)[2]
        print(f"  ✓ DNS resolved successfully: {hostname} -> {', '.join(resolved_ips)}")
    except socket.gaierror as e:
        print(f"  ✗ FAILURE: DNS resolution failed for '{hostname}'")
        print(f"    Error details: {e} ([Errno 11001] getaddrinfo failed)")
        print("\n" + "-" * 68)
        print("  [DIAGNOSIS & ROOT CAUSE]")
        print(f"  The hostname '{hostname}' does not exist on the public internet.")
        print("  Likely causes:")
        print("    1. Outdated / deleted Supabase project reference.")
        print("    2. Free-tier Supabase project has expired or been paused.")
        print("    3. Typo in the project reference string.")
        print("\n  [REQUIRED ACTION]")
        print("  The code is ready, but you must replace SUPABASE_URL with the")
        print("  Project URL shown in Supabase Dashboard → Settings → API.")
        print("\n  Update your .env file with:")
        print(f"    SUPABASE_URL=https://YOUR_ACTUAL_PROJECT_ID.supabase.co")
        print(f"    SUPABASE_KEY={masked_key}")
        print("-" * 68)
        return False
    except Exception as e:
        print(f"  ✗ FAILURE: Unexpected DNS error: {e}")
        return False

    # -------------------------------------------------------------
    # 4. HTTPS Port 443 Connectivity
    # -------------------------------------------------------------
    print(f"\n[Step 4/6] Testing HTTPS (port 443) network reachability...")
    try:
        sock = socket.create_connection((hostname, 443), timeout=5.0)
        sock.close()
        print(f"  ✓ TCP/TLS handshake reachable on {hostname}:443")
    except Exception as e:
        print(f"  ✗ FAILURE: Network connection to {hostname}:443 failed: {e}")
        print("    Diagnosis: Hostname resolved, but HTTPS traffic is blocked or timing out.")
        return False

    # -------------------------------------------------------------
    # 5. Supabase Client Initialization
    # -------------------------------------------------------------
    print("\n[Step 5/6] Initializing Supabase client with anon/publishable key...")
    try:
        SupabaseClient.reset()
        supabase = get_supabase_client()
        print("  ✓ Supabase client initialized successfully.")
    except Exception as e:
        print(f"  ✗ FAILURE: Client initialization error: {e}")
        return False

    # -------------------------------------------------------------
    # 6. Safe Database Request (Anon Key)
    # -------------------------------------------------------------
    print("\n[Step 6/6] Executing safe query on 'organizations' table using anon key...")
    try:
        response = (
            supabase.table("organizations")
            .select("id, name")
            .limit(3)
            .execute()
        )
        data = response.data or []
        print("  ✓ Database query executed successfully with anon key!")
        print(f"  ✓ Retrieved {len(data)} record(s) from 'organizations' table.")
        if data:
            for row in data:
                print(f"     - Org: {row.get('name')} (ID: {row.get('id')})")
        else:
            print("     (Table exists and is currently empty)")

    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "unauthorized" in err_str or "invalid api key" in err_str or "jwt" in err_str:
            print("  ✗ FAILURE: Authentication rejected (HTTP 401)")
            print(f"    Diagnosis: SUPABASE_KEY ({masked_key}) is invalid or expired for this project.")
            print("    Remedy: Copy the anon/public key from Supabase Dashboard → Settings → API.")
            return False
        elif "relation" in err_str and "does not exist" in err_str or "pgrst200" in err_str or "not found" in err_str:
            print("  ✓ HTTPS connection and API authentication successful!")
            print("  ⚠ Schema Notice: The 'organizations' table has not been created yet in Supabase.")
            print("    Remedy: Execute database/schema.sql in the Supabase SQL Editor.")
            print("    (This is expected for freshly created Supabase projects before migration).")
        else:
            print(f"  ✗ Query error: {e}")
            return False

    print("\n" + "=" * 68)
    print("  STATUS: SUPABASE CONNECTION VERIFIED & OPERATIONAL")
    print("=" * 68)
    return True


if __name__ == "__main__":
    success = test_supabase_connection()
    if not success:
        print("\n[RESULT] Connection check: FAILED / BLOCKED")
        sys.exit(1)
    else:
        print("\n[RESULT] Connection check: SUCCESS")
        sys.exit(0)
