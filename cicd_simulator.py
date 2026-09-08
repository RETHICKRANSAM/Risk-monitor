"""FalconEye — CI/CD Pipeline Simulator
Simulates a multi-stage CI/CD pipeline with realistic timing and pass/fail results.
Persists run history to data/cicd_results.json.
"""

import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CICD_FILE = os.path.join(DATA_DIR, "cicd_results.json")

# Pipeline stage definitions with typical durations (seconds)
PIPELINE_STAGES = [
    {"name": "build", "min_duration": 15, "max_duration": 90, "fail_rate": 0.05},
    {"name": "unit_tests", "min_duration": 10, "max_duration": 60, "fail_rate": 0.08},
    {
        "name": "integration_tests",
        "min_duration": 30,
        "max_duration": 180,
        "fail_rate": 0.10,
    },
    {
        "name": "security_scan",
        "min_duration": 20,
        "max_duration": 120,
        "fail_rate": 0.12,
    },
    {
        "name": "container_scan",
        "min_duration": 10,
        "max_duration": 45,
        "fail_rate": 0.06,
    },
    {"name": "deployment", "min_duration": 20, "max_duration": 150, "fail_rate": 0.04},
]


def _load_results():
    """Load CI/CD results from disk."""
    if not os.path.exists(CICD_FILE):
        return []
    try:
        with open(CICD_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def _save_results(results):
    """Persist CI/CD results to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CICD_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)


def run_pipeline(branch="main", commit_sha=None, triggered_by="ci-bot"):
    """Simulate a full CI/CD pipeline run.

    Each stage runs sequentially. If a stage fails, subsequent stages
    are skipped and marked as 'skipped'.

    Args:
        branch: Git branch name
        commit_sha: Commit hash (auto-generated if None)
        triggered_by: User or system that triggered the run

    Returns:
        dict: Complete pipeline run result

    """
    if commit_sha is None:
        commit_sha = uuid.uuid4().hex[:7]

    run_id = str(uuid.uuid4())[:8]
    pipeline_start = datetime.now(timezone.utc)
    current_time = pipeline_start

    stages = []
    pipeline_failed = False

    for stage_def in PIPELINE_STAGES:
        if pipeline_failed:
            stages.append(
                {
                    "name": stage_def["name"],
                    "status": "skipped",
                    "start_time": None,
                    "end_time": None,
                    "duration_seconds": 0,
                    "details": "Skipped due to previous stage failure",
                }
            )
            continue

        # Simulate stage execution
        duration = random.uniform(stage_def["min_duration"], stage_def["max_duration"])
        stage_start = current_time
        stage_end = stage_start + timedelta(seconds=duration)
        current_time = stage_end

        passed = random.random() > stage_def["fail_rate"]

        stage_result = {
            "name": stage_def["name"],
            "status": "passed" if passed else "failed",
            "start_time": stage_start.isoformat(),
            "end_time": stage_end.isoformat(),
            "duration_seconds": round(duration, 2),
            "details": _generate_stage_details(stage_def["name"], passed),
        }

        stages.append(stage_result)

        if not passed:
            pipeline_failed = True

    total_duration = (current_time - pipeline_start).total_seconds()

    # Count vulnerabilities found in security scan
    sec_scan = next((s for s in stages if s["name"] == "security_scan"), None)
    vulnerabilities = {}
    if sec_scan and sec_scan["status"] == "passed":
        vulnerabilities = {
            "critical": random.randint(0, 1),
            "high": random.randint(0, 3),
            "medium": random.randint(1, 8),
            "low": random.randint(2, 15),
        }
    elif sec_scan and sec_scan["status"] == "failed":
        vulnerabilities = {
            "critical": random.randint(2, 6),
            "high": random.randint(4, 12),
            "medium": random.randint(5, 20),
            "low": random.randint(5, 25),
        }

    run_result = {
        "run_id": run_id,
        "branch": branch,
        "commit_sha": commit_sha,
        "triggered_by": triggered_by,
        "start_time": pipeline_start.isoformat(),
        "end_time": current_time.isoformat(),
        "total_duration_seconds": round(total_duration, 2),
        "overall_status": "failed" if pipeline_failed else "passed",
        "stages": stages,
        "vulnerabilities": vulnerabilities,
    }

    # Persist
    results = _load_results()
    results.insert(0, run_result)
    # Keep only the last 50 runs
    results = results[:50]
    _save_results(results)

    return run_result


def _generate_stage_details(stage_name, passed):
    """Generate realistic detail messages for each stage."""
    if stage_name == "build":
        if passed:
            return f"Build successful. Artifact size: {random.randint(12, 85)}MB."
        return "Build failed: compilation error in module auth_service."

    if stage_name == "unit_tests":
        total = random.randint(180, 420)
        if passed:
            return f"{total}/{total} tests passed. Coverage: {random.randint(78, 96)}%."
        failed = random.randint(1, 8)
        return f"{total - failed}/{total} tests passed, {failed} failed. Coverage: {random.randint(60, 75)}%."

    if stage_name == "integration_tests":
        total = random.randint(30, 80)
        if passed:
            return f"{total}/{total} integration tests passed."
        failed = random.randint(1, 5)
        return f"{total - failed}/{total} integration tests passed, {failed} failed."

    if stage_name == "security_scan":
        if passed:
            return "No critical vulnerabilities found. Review recommended for medium findings."
        return (
            "Critical vulnerabilities detected. Deployment blocked by security policy."
        )

    if stage_name == "container_scan":
        if passed:
            return f"Container image scanned. Base image up to date. Size: {random.randint(80, 250)}MB."
        return "Container scan failed: outdated base image with known CVEs."

    if stage_name == "deployment":
        if passed:
            return f"Deployed to target environment. Health check passed after {random.randint(5, 30)}s."
        return "Deployment failed: health check timeout after 120s."

    return "Completed." if passed else "Failed."


def get_latest_run():
    """Return the most recent pipeline run."""
    results = _load_results()
    return results[0] if results else None


def get_run_history(limit=10):
    """Return recent pipeline run history."""
    results = _load_results()
    return results[:limit]


def init_cicd_file():
    """Create cicd_results.json with seed data if it doesn't exist."""
    if os.path.exists(CICD_FILE):
        return

    # Generate 3 seed runs
    seed_runs = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=6)

    for i in range(3):
        run_time = base_time + timedelta(hours=i * 2)
        stages = []
        current = run_time
        failed = False

        for stage_def in PIPELINE_STAGES:
            if failed:
                stages.append(
                    {
                        "name": stage_def["name"],
                        "status": "skipped",
                        "start_time": None,
                        "end_time": None,
                        "duration_seconds": 0,
                        "details": "Skipped due to previous stage failure",
                    }
                )
                continue

            dur = random.uniform(stage_def["min_duration"], stage_def["max_duration"])
            s_start = current
            s_end = s_start + timedelta(seconds=dur)
            current = s_end

            # Make the 2nd run fail at security_scan
            if i == 1 and stage_def["name"] == "security_scan":
                passed = False
            else:
                passed = True

            stages.append(
                {
                    "name": stage_def["name"],
                    "status": "passed" if passed else "failed",
                    "start_time": s_start.isoformat(),
                    "end_time": s_end.isoformat(),
                    "duration_seconds": round(dur, 2),
                    "details": _generate_stage_details(stage_def["name"], passed),
                }
            )
            if not passed:
                failed = True

        total_dur = (current - run_time).total_seconds()

        seed_runs.append(
            {
                "run_id": str(uuid.uuid4())[:8],
                "branch": "main",
                "commit_sha": uuid.uuid4().hex[:7],
                "triggered_by": ["sarah.chen", "ci-bot", "mike.ops"][i],
                "start_time": run_time.isoformat(),
                "end_time": current.isoformat(),
                "total_duration_seconds": round(total_dur, 2),
                "overall_status": "failed" if failed else "passed",
                "stages": stages,
                "vulnerabilities": {
                    "critical": random.randint(0, 2)
                    if not failed
                    else random.randint(2, 5),
                    "high": random.randint(0, 4),
                    "medium": random.randint(1, 10),
                    "low": random.randint(3, 15),
                },
            }
        )

    seed_runs.reverse()  # Most recent first
    _save_results(seed_runs)
