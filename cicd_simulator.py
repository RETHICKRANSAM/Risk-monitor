"""FalconEye — CI/CD Pipeline Simulator
Simulates a multi-stage CI/CD pipeline with realistic timing and pass/fail results.
Persists run history to data/cicd_results.json.
"""

import json
import os
import random
import re
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


def _extract_test_counts(stages):
    """Extract total passed and failed test counts from stage details."""
    passed_count = 0
    failed_count = 0
    for s in stages:
        details = s.get("details") or ""
        if not details:
            continue
        m = re.search(r"(\d+)/(\d+)\s+(?:tests|integration tests)\s+passed", details)
        if m:
            passed_count += int(m.group(1))
        m_fail = re.search(r"(\d+)\s+failed", details)
        if m_fail:
            failed_count += int(m_fail.group(1))
    return passed_count, failed_count


def _load_results():
    """Load CI/CD results from disk."""
    if not os.path.exists(CICD_FILE):
        return []
    try:
        with open(CICD_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_results(results):
    """Persist CI/CD results to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_file = f"{CICD_FILE}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        os.replace(temp_file, CICD_FILE)
    except OSError:
        with open(CICD_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


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
    if not branch:
        branch = "main"
    if not commit_sha:
        commit_sha = uuid.uuid4().hex[:7]
    if not triggered_by:
        triggered_by = "ci-bot"

    run_id = str(uuid.uuid4())[:8]

    # Pre-simulate stages to calculate exact total duration
    stage_plan = []
    pipeline_failed = False
    total_duration = 0.0

    for stage_def in PIPELINE_STAGES:
        if pipeline_failed:
            stage_plan.append(
                {
                    "name": stage_def["name"],
                    "status": "skipped",
                    "duration": 0.0,
                    "details": "Skipped due to previous stage failure",
                }
            )
            continue

        min_dur = float(stage_def.get("min_duration") or 10.0)
        max_dur = float(stage_def.get("max_duration") or 60.0)
        if min_dur > max_dur:
            min_dur, max_dur = max_dur, min_dur
        duration = round(random.uniform(min_dur, max_dur), 2)
        fail_rate = float(stage_def.get("fail_rate") or 0.0)
        passed = random.random() >= fail_rate

        if not passed and stage_def.get("name") == "deployment":
            duration = max(duration, 120.0)

        stage_plan.append(
            {
                "name": stage_def["name"],
                "status": "passed" if passed else "failed",
                "duration": duration,
                "details": _generate_stage_details(stage_def["name"], passed),
            }
        )

        total_duration += duration
        if not passed:
            pipeline_failed = True

    # Anchor pipeline completion to the current time so timestamps don't drift into the future
    pipeline_end = datetime.now(timezone.utc)
    stage_cursor = pipeline_end - timedelta(seconds=total_duration)
    pipeline_start = stage_cursor

    stages = []
    for plan in stage_plan:
        if plan["status"] == "skipped":
            stages.append(
                {
                    "name": plan["name"],
                    "status": "skipped",
                    "start_time": None,
                    "end_time": None,
                    "duration_seconds": 0.0,
                    "details": plan["details"],
                }
            )
        else:
            s_start = stage_cursor
            s_end = s_start + timedelta(seconds=plan["duration"])
            stage_cursor = s_end

            stages.append(
                {
                    "name": plan["name"],
                    "status": plan["status"],
                    "start_time": s_start.isoformat(),
                    "end_time": s_end.isoformat(),
                    "duration_seconds": round(plan["duration"], 2),
                    "details": plan["details"],
                }
            )

    # Count vulnerabilities found in security scan
    sec_scan = next((s for s in stages if s["name"] == "security_scan"), None)
    vulnerabilities = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    if sec_scan and sec_scan["status"] == "passed":
        vulnerabilities = {
            "critical": 0,
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

    tests_passed, tests_failed = _extract_test_counts(stages)
    status_val = "failed" if pipeline_failed else "passed"

    run_result = {
        "run_id": run_id,
        "branch": branch,
        "commit_sha": commit_sha,
        "triggered_by": triggered_by,
        "start_time": pipeline_start.isoformat(),
        "end_time": stage_cursor.isoformat(),
        "total_duration_seconds": round(total_duration, 2),
        "duration_seconds": round(total_duration, 2),
        "status": status_val,
        "overall_status": status_val,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
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
    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 10
    if limit <= 0:
        return []
    return results[:limit]


def init_cicd_file():
    """Create cicd_results.json with seed data if it doesn't exist or is empty."""
    if os.path.exists(CICD_FILE):
        try:
            if os.path.getsize(CICD_FILE) > 2:
                with open(CICD_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return
        except (OSError, json.JSONDecodeError):
            pass

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
                        "duration_seconds": 0.0,
                        "details": "Skipped due to previous stage failure",
                    }
                )
                continue

            min_dur = float(stage_def.get("min_duration") or 10.0)
            max_dur = float(stage_def.get("max_duration") or 60.0)
            if min_dur > max_dur:
                min_dur, max_dur = max_dur, min_dur
            dur = round(random.uniform(min_dur, max_dur), 2)

            # Make the 2nd run fail at security_scan
            if i == 1 and stage_def.get("name") == "security_scan":
                passed = False
            else:
                passed = True

            if not passed and stage_def.get("name") == "deployment":
                dur = max(dur, 120.0)

            s_start = current
            s_end = s_start + timedelta(seconds=dur)
            current = s_end

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
        tests_passed, tests_failed = _extract_test_counts(stages)
        status_val = "failed" if failed else "passed"

        sec_scan = next((s for s in stages if s["name"] == "security_scan"), None)
        vulnerabilities = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        if sec_scan and sec_scan["status"] == "passed":
            vulnerabilities = {
                "critical": 0,
                "high": random.randint(0, 4),
                "medium": random.randint(1, 10),
                "low": random.randint(3, 15),
            }
        elif sec_scan and sec_scan["status"] == "failed":
            vulnerabilities = {
                "critical": random.randint(2, 5),
                "high": random.randint(4, 10),
                "medium": random.randint(5, 15),
                "low": random.randint(5, 20),
            }

        seed_runs.append(
            {
                "run_id": str(uuid.uuid4())[:8],
                "branch": "main",
                "commit_sha": uuid.uuid4().hex[:7],
                "triggered_by": ["sarah.chen", "ci-bot", "mike.ops"][i],
                "start_time": run_time.isoformat(),
                "end_time": current.isoformat(),
                "total_duration_seconds": round(total_dur, 2),
                "duration_seconds": round(total_dur, 2),
                "status": status_val,
                "overall_status": status_val,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "stages": stages,
                "vulnerabilities": vulnerabilities,
            }
        )

    seed_runs.reverse()  # Most recent first
    _save_results(seed_runs)


if __name__ == "__main__":
    init_cicd_file()
    print("CI/CD Simulator initialized.")
    latest = get_latest_run()
    if latest:
        run_id = latest.get("run_id")
        status = latest.get("overall_status") or latest.get("status")
        dur = latest.get("duration_seconds") or latest.get("total_duration_seconds")
        print(f"Latest run: {run_id} | Status: {status} | Duration: {dur}s")
    print("Triggering new pipeline run simulation...")
    new_run = run_pipeline(branch="feature/pipeline-test", triggered_by="cli-test")
    print(
        f"Run completed: ID={new_run['run_id']} | Status={new_run['overall_status']} | "
        f"Tests: {new_run['tests_passed']} passed, {new_run['tests_failed']} failed"
    )
