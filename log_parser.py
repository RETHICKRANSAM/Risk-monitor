"""FalconEye — Log Parsing Engine
Parses application log files and extracts security-relevant statistics.
Supports standard log formats with severity levels and pattern matching.
"""

import os
import re
from collections import Counter
from datetime import datetime

# Regex patterns for log analysis
LOG_LINE_PATTERN = re.compile(
    r"^\[?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})\]?\s*"
    r"[\[\(]?\s*(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\s*[\]\)]?\s*"
    r"(.+)$",
    re.IGNORECASE,
)

# Security-critical keyword patterns
CRITICAL_PATTERNS = {
    "failed_login": re.compile(
        r"(failed\s+login|authentication\s+fail|invalid\s+(credentials|password)|"
        r"login\s+attempt\s+failed|unauthorized\s+access)",
        re.IGNORECASE,
    ),
    "database_error": re.compile(
        r"(database\s+(connection|error|timeout|refused)|"
        r"db\s+(error|connection|timeout)|sql\s+(error|exception)|"
        r"connection\s+pool\s+exhausted)",
        re.IGNORECASE,
    ),
    "timeout": re.compile(
        r"(timeout|timed?\s*out|request\s+timeout|"
        r"connection\s+timeout|read\s+timeout|gateway\s+timeout)",
        re.IGNORECASE,
    ),
    "permission_denied": re.compile(
        r"(permission\s+denied|access\s+denied|forbidden|"
        r"insufficient\s+privileges|not\s+authorized)",
        re.IGNORECASE,
    ),
    "memory_issue": re.compile(
        r"(out\s+of\s+memory|memory\s+(leak|exhausted|limit)|"
        r"heap\s+(overflow|exhausted)|oom\s+kill)",
        re.IGNORECASE,
    ),
    "suspicious_activity": re.compile(
        r"(sql\s+injection|xss\s+attempt|brute\s+force|"
        r"port\s+scan|suspicious\s+(request|activity|payload)|"
        r"malicious|exploit)",
        re.IGNORECASE,
    ),
}


def parse_log_file(filepath):
    """Parse a log file and extract statistics.

    Args:
        filepath: Path to the log file

    Returns:
        dict: Parsed statistics including severity counts,
              critical events, top errors, and timeline

    """
    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    severity_counts = Counter()
    critical_events = {key: [] for key in CRITICAL_PATTERNS}
    error_messages = Counter()
    warning_messages = Counter()
    total_lines = 0
    parsed_lines = 0
    timeline = Counter()  # errors per hour

    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            for line in f:
                total_lines += 1
                line = line.strip()
                if not line:
                    continue

                match = LOG_LINE_PATTERN.match(line)
                if match:
                    parsed_lines += 1
                    timestamp_str = match.group(1)
                    severity = match.group(2).upper()
                    message = match.group(3).strip()

                    # Normalize WARN → WARNING, FATAL → CRITICAL
                    if severity == "WARN":
                        severity = "WARNING"
                    elif severity == "FATAL":
                        severity = "CRITICAL"

                    severity_counts[severity] += 1

                    # Track error/warning messages
                    if severity == "ERROR" or severity == "CRITICAL":
                        # Truncate for grouping
                        short_msg = message[:120]
                        error_messages[short_msg] += 1

                        # Timeline tracking
                        try:
                            ts = datetime.fromisoformat(timestamp_str.replace(" ", "T"))
                            hour_key = ts.strftime("%Y-%m-%d %H:00")
                            timeline[hour_key] += 1
                        except ValueError:
                            pass

                    elif severity == "WARNING":
                        short_msg = message[:120]
                        warning_messages[short_msg] += 1

                    # Check critical patterns
                    for pattern_name, pattern in CRITICAL_PATTERNS.items():
                        if pattern.search(message):
                            critical_events[pattern_name].append(
                                {
                                    "timestamp": timestamp_str,
                                    "severity": severity,
                                    "message": message[:200],
                                }
                            )

    except OSError as e:
        return {"error": f"Failed to read file: {e!s}"}

    # Build result
    top_errors = [
        {"message": msg, "count": count}
        for msg, count in error_messages.most_common(10)
    ]

    top_warnings = [
        {"message": msg, "count": count}
        for msg, count in warning_messages.most_common(5)
    ]

    # Summarize critical events (keep only first 5 of each type)
    critical_summary = {}
    for key, events in critical_events.items():
        critical_summary[key] = {
            "count": len(events),
            "recent": events[-5:] if events else [],
        }

    # Sort timeline
    sorted_timeline = sorted(timeline.items())

    return {
        "file": os.path.basename(filepath),
        "total_lines": total_lines,
        "parsed_lines": parsed_lines,
        "parse_rate": round(parsed_lines / total_lines * 100, 1)
        if total_lines > 0
        else 0,
        "severity_counts": {
            "DEBUG": severity_counts.get("DEBUG", 0),
            "INFO": severity_counts.get("INFO", 0),
            "WARNING": severity_counts.get("WARNING", 0),
            "ERROR": severity_counts.get("ERROR", 0),
            "CRITICAL": severity_counts.get("CRITICAL", 0),
        },
        "critical_events": critical_summary,
        "top_errors": top_errors,
        "top_warnings": top_warnings,
        "error_timeline": [{"hour": h, "count": c} for h, c in sorted_timeline],
        "risk_indicators": {
            "failed_logins": critical_summary.get("failed_login", {}).get("count", 0),
            "database_errors": critical_summary.get("database_error", {}).get(
                "count", 0
            ),
            "timeouts": critical_summary.get("timeout", {}).get("count", 0),
            "permission_denied": critical_summary.get("permission_denied", {}).get(
                "count", 0
            ),
            "memory_issues": critical_summary.get("memory_issue", {}).get("count", 0),
            "suspicious_activity": critical_summary.get("suspicious_activity", {}).get(
                "count", 0
            ),
        },
    }


def parse_log_text(log_text):
    """Parse log content from a text string (for POST body uploads).

    Args:
        log_text: Raw log content as a string

    Returns:
        dict: Same structure as parse_log_file

    """
    import tempfile

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(log_text)
            tmp_path = tmp.name
        return parse_log_file(tmp_path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def init_sample_log():
    """Create sample_app.log with realistic entries if it doesn't exist."""
    log_path = os.path.join(os.path.dirname(__file__), "data", "sample_app.log")
    if os.path.exists(log_path):
        return log_path

    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    entries = [
        "[2026-08-14T00:00:12] INFO  Application started on port 5000",
        "[2026-08-14T00:00:12] INFO  Database connection pool initialized (max=20)",
        "[2026-08-14T00:00:13] INFO  Loading risk engine rules... 4 rules loaded",
        "[2026-08-14T00:00:14] DEBUG Cache warmed with 1,204 endpoint records",
        "[2026-08-14T00:01:02] INFO  GET /dashboard 200 — 142ms",
        "[2026-08-14T00:01:05] INFO  GET /api/findings?page=1 200 — 88ms",
        "[2026-08-14T00:02:15] WARNING Request latency exceeded threshold: GET /api/endpoints 1,240ms",
        "[2026-08-14T00:02:44] ERROR  Database connection timeout after 30s — retrying (attempt 1/3)",
        "[2026-08-14T00:02:47] ERROR  Database connection timeout after 30s — retrying (attempt 2/3)",
        "[2026-08-14T00:02:50] INFO  Database connection re-established on attempt 3",
        "[2026-08-14T00:03:10] WARNING Memory usage at 78% (3.1GB / 4GB)",
        "[2026-08-14T00:04:22] INFO  POST /api/cicd/run 200 — 2,104ms",
        "[2026-08-14T00:05:00] ERROR  Failed login attempt for user 'admin' from 192.168.1.105",
        "[2026-08-14T00:05:01] ERROR  Failed login attempt for user 'admin' from 192.168.1.105",
        "[2026-08-14T00:05:02] ERROR  Failed login attempt for user 'admin' from 192.168.1.105",
        "[2026-08-14T00:05:03] WARNING Brute force detection: 3 failed attempts from 192.168.1.105 in 3s",
        "[2026-08-14T00:05:03] CRITICAL Suspicious activity: possible brute force attack from 192.168.1.105",
        "[2026-08-14T00:06:11] INFO  GET /dashboard 200 — 95ms",
        "[2026-08-14T00:07:30] WARNING Disk usage at 85% on /var/log",
        "[2026-08-14T00:08:00] ERROR  Request timeout: POST /api/risk/evaluate — gateway timeout after 60s",
        "[2026-08-14T00:08:45] INFO  CI/CD pipeline run abc1234 completed — status: passed",
        "[2026-08-14T00:09:12] ERROR  Permission denied: user 'readonly' attempted write on /api/deployments/start",
        "[2026-08-14T00:10:00] INFO  Health check passed — all systems operational",
        "[2026-08-14T00:11:30] WARNING SSL certificate expiring in 14 days for api.falconeye.local",
        "[2026-08-14T00:12:00] ERROR  Database connection refused — connection pool exhausted",
        "[2026-08-14T00:12:05] CRITICAL Database connection pool exhausted. Active: 20/20, Waiting: 8",
        "[2026-08-14T00:12:15] INFO  Emergency pool expansion: max connections increased to 30",
        "[2026-08-14T00:13:00] INFO  GET /endpoints 200 — 210ms",
        "[2026-08-14T00:14:22] WARNING Rate limit approaching for API key 'ext-scanner-01' (480/500 req/min)",
        "[2026-08-14T00:15:00] ERROR  Failed login attempt for user 'svc-account' from 10.0.0.55",
        "[2026-08-14T00:15:30] INFO  Deployment a1b2c3d4 started — version 2.3.0 to prod",
        "[2026-08-14T00:16:00] INFO  Deployment a1b2c3d4 — health check passed",
        "[2026-08-14T00:16:10] INFO  Deployment a1b2c3d4 completed successfully (duration: 755s)",
        "[2026-08-14T00:17:00] ERROR  Unexpected error in risk_engine.evaluate_release: KeyError 'canary_error_rate'",
        "[2026-08-14T00:17:01] WARNING Falling back to default canary_error_rate=1.0",
        "[2026-08-14T00:18:00] DEBUG Garbage collection: freed 128MB in 45ms",
        "[2026-08-14T00:19:00] INFO  Scheduled job: stale-alert-cleanup completed — removed 23 alerts older than 90d",
        "[2026-08-14T00:20:00] ERROR  Connection timeout: SIEM connector lost connection to 10.0.1.200:9200",
        "[2026-08-14T00:20:30] WARNING SIEM connector: reconnecting (attempt 1/5)",
        "[2026-08-14T00:20:45] INFO  SIEM connector: reconnected to 10.0.1.200:9200",
        "[2026-08-14T00:21:00] CRITICAL Out of memory warning: process RSS at 3.8GB approaching 4GB limit",
        "[2026-08-14T00:21:05] WARNING Initiating emergency memory cleanup",
        "[2026-08-14T00:21:10] INFO  Memory cleanup completed: freed 800MB, current usage 3.0GB",
        "[2026-08-14T00:22:00] INFO  GET /api/findings?severity=critical 200 — 67ms",
        "[2026-08-14T00:23:00] ERROR  SQL injection attempt detected in query parameter: id=1 OR 1=1",
        "[2026-08-14T00:23:00] CRITICAL Suspicious activity: SQL injection attempt blocked from 203.0.113.42",
        "[2026-08-14T00:24:00] INFO  Threat intel feed updated: 1,204 new IOCs ingested",
        "[2026-08-14T00:25:00] INFO  Health check passed — all systems operational",
        "[2026-08-14T00:26:00] WARNING Endpoint DESKTOP-UX892 agent heartbeat missed (last seen 12m ago)",
        "[2026-08-14T00:27:00] ERROR  Failed to send alert notification via email — SMTP connection refused",
        "[2026-08-14T00:28:00] INFO  Alert auto-assignment: 5 new critical alerts assigned to L3 team",
    ]

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(entries) + "\n")

    return log_path
