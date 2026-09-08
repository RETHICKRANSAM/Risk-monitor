"""FalconEye — Health Checks Module
Monitors system health: Flask app, SQLite database, JSON data files,
disk space, and memory usage.
"""

import json
import os
import platform
import sqlite3
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "falconeye.db")

# Required data files for the application
REQUIRED_DATA_FILES = [
    "endpoints.json",
    "test_data.json",
    "deployments.json",
    "cicd_results.json",
]


def check_flask_app():
    """Check Flask application health.

    Returns:
        dict: Status and details of the Flask app check

    """
    try:
        from app import create_app

        app = create_app()
        # Verify the app object is valid and has routes
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        return {
            "status": "healthy",
            "routes_registered": len(rules),
            "debug_mode": app.debug,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def check_database():
    """Check SQLite database connectivity and integrity.

    Returns:
        dict: Status and details of the database check

    """
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]

        # Get DB size
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0

        # Get table count
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]

        conn.close()

        return {
            "status": "healthy" if integrity == "ok" else "degraded",
            "integrity": integrity,
            "size_bytes": db_size,
            "size_mb": round(db_size / (1024 * 1024), 2),
            "tables": table_count,
            "path": DB_PATH,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def check_data_files():
    """Check that all required JSON data files exist and are valid.

    Returns:
        dict: Status and details for each data file

    """
    results = {}
    all_ok = True

    for filename in REQUIRED_DATA_FILES:
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            results[filename] = {
                "status": "missing",
                "size_bytes": 0,
            }
            all_ok = False
            continue

        try:
            size = os.path.getsize(filepath)
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            record_count = len(data) if isinstance(data, list) else 1

            results[filename] = {
                "status": "healthy",
                "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 2),
                "records": record_count,
            }
        except json.JSONDecodeError:
            results[filename] = {
                "status": "corrupt",
                "error": "Invalid JSON",
            }
            all_ok = False
        except Exception as e:
            results[filename] = {
                "status": "error",
                "error": str(e),
            }
            all_ok = False

    return {
        "status": "healthy" if all_ok else "degraded",
        "files": results,
    }


def check_disk_space():
    """Check available disk space on the application volume.

    Returns:
        dict: Disk usage statistics

    """
    try:
        import shutil

        total, used, free = shutil.disk_usage(os.path.dirname(__file__))

        free_pct = round(free / total * 100, 1)
        status = "healthy"
        if free_pct < 10:
            status = "critical"
        elif free_pct < 20:
            status = "warning"

        return {
            "status": status,
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "free_percent": free_pct,
        }
    except Exception as e:
        return {
            "status": "unknown",
            "error": str(e),
        }


def check_memory():
    """Check process memory usage.
    Uses OS-specific methods; no psutil dependency.

    Returns:
        dict: Memory usage statistics

    """
    try:
        if platform.system() == "Windows":
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.psapi.GetProcessMemoryInfo(
                handle,
                ctypes.byref(pmc),
                pmc.cb,
            )
            rss = pmc.WorkingSetSize
        else:
            # Linux/Mac: read /proc/self/status
            rss = 0
            try:
                with open("/proc/self/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            rss = int(line.split()[1]) * 1024  # KB to bytes
                            break
            except FileNotFoundError:
                # macOS fallback
                import resource  # pyright: ignore[reportMissingImports]

                rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]  # noqa: E501
                if platform.system() == "Darwin":
                    pass  # macOS returns bytes
                else:
                    rss *= 1024  # Linux returns KB

        rss_mb = round(rss / (1024 * 1024), 2)
        status = "healthy"
        if rss_mb > 500:
            status = "critical"
        elif rss_mb > 256:
            status = "warning"

        return {
            "status": status,
            "rss_bytes": rss,
            "rss_mb": rss_mb,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        }
    except Exception as e:
        return {
            "status": "unknown",
            "error": str(e),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        }


def full_health_check():
    """Run all health checks and return a combined report.

    Returns:
        dict: Complete health status with all subsystem checks

    """
    db_check = check_database()
    data_check = check_data_files()
    disk_check = check_disk_space()
    mem_check = check_memory()

    # Determine overall status
    statuses = [
        db_check["status"],
        data_check["status"],
        disk_check["status"],
        mem_check["status"],
    ]

    if "unhealthy" in statuses or "critical" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses or "warning" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": db_check,
            "data_files": data_check,
            "disk": disk_check,
            "memory": mem_check,
        },
    }
