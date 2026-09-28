"""Inbound Webhook Ingestion Routes for GitHub Actions and Jenkins CI."""

from datetime import datetime, timezone
import json
import os
from flask import Blueprint, jsonify, request
from services.event_stream import broadcast_event

webhooks_bp = Blueprint("webhooks", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
WEBHOOK_LOGS_FILE = os.path.join(DATA_DIR, "webhook_logs.json")


def _save_webhook_event(event_data: dict):
    """Persist received webhook event to disk atomically."""
    os.makedirs(DATA_DIR, exist_ok=True)
    events = []
    if os.path.exists(WEBHOOK_LOGS_FILE):
        try:
            with open(WEBHOOK_LOGS_FILE, encoding="utf-8") as f:
                events = json.load(f)
                if not isinstance(events, list):
                    events = []
        except Exception:
            events = []

    events.insert(0, event_data)
    events = events[:50]  # Retain latest 50 events

    temp_file = f"{WEBHOOK_LOGS_FILE}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
        os.replace(temp_file, WEBHOOK_LOGS_FILE)
    except Exception:
        pass


@webhooks_bp.route("/api/webhooks/github", methods=["POST"])
def github_webhook():
    """Ingest GitHub Actions / Push / Release webhooks."""
    event_type = request.headers.get("X-GitHub-Event", "push")
    payload = request.get_json(force=True, silent=True) or {}

    # Extract repository and commit details
    repo = payload.get("repository", {}).get("full_name", "enterprise/service")
    ref = payload.get("ref", "refs/heads/main")
    branch = ref.replace("refs/heads/", "") if "refs/heads/" in ref else ref

    commit_info = payload.get("head_commit") or {}
    commit_sha = commit_info.get("id", payload.get("after", "unknown_sha"))[:8]
    commit_msg = commit_info.get("message", "Triggered via GitHub Webhook")
    author = commit_info.get("author", {}).get("username", "github-bot")

    # If it's a release event, grab the tag
    release_tag = payload.get("release", {}).get("tag_name")

    record = {
        "source": "github",
        "event_type": event_type,
        "repo": repo,
        "branch": branch,
        "commit_sha": commit_sha,
        "commit_message": commit_msg,
        "author": author,
        "release_tag": release_tag,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "status": "PROCESSED",
    }

    _save_webhook_event(record)

    # Broadcast live SSE update
    broadcast_event("webhook_received", record)

    return jsonify({
        "message": "GitHub webhook processed successfully",
        "event": record,
    }), 200


@webhooks_bp.route("/api/webhooks/jenkins", methods=["POST"])
def jenkins_webhook():
    """Ingest Jenkins build completion notifications."""
    payload = request.get_json(force=True, silent=True) or {}

    job_name = payload.get("name", payload.get("job_name", "pipeline-build"))
    build_num = payload.get("build", {}).get("number", payload.get("build_number", 1))
    status = payload.get("build", {}).get("status", payload.get("status", "SUCCESS"))
    commit_sha = payload.get("commit_sha", payload.get("scm", {}).get("commit", "unknown"))[:8]

    record = {
        "source": "jenkins",
        "job_name": job_name,
        "build_number": build_num,
        "status": status,
        "commit_sha": commit_sha,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    _save_webhook_event(record)
    broadcast_event("webhook_received", record)

    return jsonify({
        "message": "Jenkins webhook processed successfully",
        "event": record,
    }), 200


@webhooks_bp.route("/api/webhooks/logs", methods=["GET"])
def get_webhook_logs():
    """Retrieve history of ingested webhooks."""
    if not os.path.exists(WEBHOOK_LOGS_FILE):
        return jsonify({"events": [], "count": 0})
    try:
        with open(WEBHOOK_LOGS_FILE, encoding="utf-8") as f:
            events = json.load(f)
            return jsonify({"events": events, "count": len(events)})
    except Exception:
        return jsonify({"events": [], "count": 0})
