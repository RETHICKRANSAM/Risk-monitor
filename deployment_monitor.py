"""FalconEye — Deployment Monitor
Tracks deployment lifecycle: start → complete, with metadata.
Persists all records to data/deployments.json.
"""

import json
import os
import uuid
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DEPLOYMENTS_FILE = os.path.join(DATA_DIR, "deployments.json")


def _load_deployments():
    """Load deployments from the JSON file."""
    if not os.path.exists(DEPLOYMENTS_FILE):
        return []
    try:
        with open(DEPLOYMENTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def _save_deployments(deployments):
    """Persist deployments list to the JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DEPLOYMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(deployments, f, indent=2, default=str)


def start_deployment(version, environment, triggered_by):
    """Start a new deployment and return its record.

    Args:
        version: Semantic version string (e.g. "2.4.1")
        environment: One of dev, staging, prod
        triggered_by: Username or system that triggered the deploy

    Returns:
        dict: The new deployment record

    """
    if environment not in ("dev", "staging", "prod"):
        raise ValueError(
            f"Invalid environment: {environment}. Must be dev, staging, or prod."
        )

    deployment = {
        "deployment_id": str(uuid.uuid4())[:8],
        "version": version,
        "environment": environment,
        "triggered_by": triggered_by,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": None,
        "status": "in_progress",
        "duration_seconds": None,
    }

    deployments = _load_deployments()
    deployments.insert(0, deployment)
    _save_deployments(deployments)

    return deployment


def complete_deployment(deployment_id, status="success"):
    """Mark a deployment as completed.

    Args:
        deployment_id: The ID returned by start_deployment
        status: One of success, failed, rolled_back

    Returns:
        dict: The updated deployment record, or None if not found

    """
    if status not in ("success", "failed", "rolled_back"):
        raise ValueError(
            f"Invalid status: {status}. Must be success, failed, or rolled_back."
        )

    deployments = _load_deployments()

    for dep in deployments:
        if dep["deployment_id"] == deployment_id:
            end_time = datetime.now(timezone.utc)
            start_time = datetime.fromisoformat(dep["start_time"])
            duration = (end_time - start_time).total_seconds()

            dep["end_time"] = end_time.isoformat()
            dep["status"] = status
            dep["duration_seconds"] = round(duration, 2)

            _save_deployments(deployments)
            return dep

    return None


def list_deployments(limit=20, environment=None, status=None):
    """List deployments with optional filters.

    Args:
        limit: Max records to return
        environment: Filter by environment
        status: Filter by status

    Returns:
        list: Filtered deployment records

    """
    deployments = _load_deployments()

    if environment:
        deployments = [d for d in deployments if d["environment"] == environment]
    if status:
        deployments = [d for d in deployments if d["status"] == status]

    return deployments[:limit]


def get_deployment(deployment_id):
    """Get a single deployment by ID."""
    deployments = _load_deployments()
    for dep in deployments:
        if dep["deployment_id"] == deployment_id:
            return dep
    return None


def init_deployments_file():
    """Create deployments.json with seed data if it doesn't exist."""
    if os.path.exists(DEPLOYMENTS_FILE):
        return

    seed = [
        {
            "deployment_id": "a1b2c3d4",
            "version": "2.3.0",
            "environment": "prod",
            "triggered_by": "sarah.chen",
            "start_time": "2026-08-13T14:00:00+00:00",
            "end_time": "2026-08-13T14:12:35+00:00",
            "status": "success",
            "duration_seconds": 755.0,
        },
        {
            "deployment_id": "e5f6g7h8",
            "version": "2.3.0-rc2",
            "environment": "staging",
            "triggered_by": "ci-pipeline",
            "start_time": "2026-08-13T10:30:00+00:00",
            "end_time": "2026-08-13T10:38:12+00:00",
            "status": "success",
            "duration_seconds": 492.0,
        },
        {
            "deployment_id": "i9j0k1l2",
            "version": "2.2.9",
            "environment": "prod",
            "triggered_by": "mike.ops",
            "start_time": "2026-08-12T22:00:00+00:00",
            "end_time": "2026-08-12T22:05:44+00:00",
            "status": "rolled_back",
            "duration_seconds": 344.0,
        },
        {
            "deployment_id": "m3n4o5p6",
            "version": "2.2.8",
            "environment": "dev",
            "triggered_by": "dev-auto",
            "start_time": "2026-08-12T16:00:00+00:00",
            "end_time": "2026-08-12T16:02:10+00:00",
            "status": "success",
            "duration_seconds": 130.0,
        },
        {
            "deployment_id": "q7r8s9t0",
            "version": "2.2.7",
            "environment": "staging",
            "triggered_by": "sarah.chen",
            "start_time": "2026-08-11T09:15:00+00:00",
            "end_time": "2026-08-11T09:22:03+00:00",
            "status": "failed",
            "duration_seconds": 423.0,
        },
    ]
    _save_deployments(seed)
