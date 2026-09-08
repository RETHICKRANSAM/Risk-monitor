"""FalconEye — Enterprise SOC Flask Application
Reads all data from JSON files in the data/ folder.
Includes backend APIs: deployments, CI/CD, log analysis, health, risk evaluation.
No database or Supabase connection required.
"""

import json
import os

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS


def load_json(filename):
    """Load a JSON file from the data/ directory."""
    filepath = os.path.join(os.path.dirname(__file__), "data", filename)
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def init_data_files():
    """Initialize all required data and log files if they are missing."""
    from cicd_simulator import init_cicd_file
    from deployment_monitor import init_deployments_file
    from log_parser import init_sample_log

    init_deployments_file()
    init_cicd_file()
    init_sample_log()

    print("[INIT] Data files initialized.")


def create_app():
    """Application factory."""
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static",
        template_folder="templates",
    )

    from config import Config
    from models import db

    app.config.from_object(Config)
    CORS(app, supports_credentials=True)

    # Initialize database
    db.init_app(app)

    # Initialize seed data files on first run
    init_data_files()

    # Register Pre-Release Risk Monitor blueprints
    from routes.dashboard import dashboard_bp
    from routes.releases import releases_bp
    from routes.metrics import metrics_bp
    from routes.auth import auth_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(releases_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(auth_bp)

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"[DB] Notice on init: {e}")

    # ── Page Routes ──────────────────────────────────────────────

    @app.route("/")
    def serve_index():
        return render_template("dashboard.html")

    @app.route("/login")
    def serve_login():
        return render_template("login.html")

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/risk-detail")
    def risk_detail():
        return render_template("risk-detail.html")

    @app.route("/evidence")
    def evidence():
        return render_template("evidence.html")

    @app.route("/audit")
    def audit():
        return render_template("audit.html")

    @app.route("/api/dashboard-summary")
    def dashboard_summary():
        """Returns risk monitor summary and evaluations."""
        exp_file = os.path.join(os.path.dirname(__file__), "data", "experiment_results.json")
        if os.path.exists(exp_file):
            with open(exp_file, encoding="utf-8") as f:
                return jsonify(json.load(f))
        return jsonify({"message": "Run experiments/run_baseline_experiment.py to generate dataset"}), 200

    # ══════════════════════════════════════════════════════════════
    # BACKEND API ROUTES
    # ══════════════════════════════════════════════════════════════

    # ── 1. Deployment Monitoring ─────────────────────────────────

    @app.route("/api/deployments/start", methods=["POST"])
    def api_deployment_start():
        """Start a new deployment."""
        from deployment_monitor import start_deployment

        data = request.get_json(force=True, silent=True) or {}

        version = data.get("version")
        environment = data.get("environment")
        triggered_by = data.get("triggered_by", "api-user")

        if not version or not environment:
            return jsonify(
                {"error": "Missing required fields: version, environment"}
            ), 400

        try:
            deployment = start_deployment(version, environment, triggered_by)
            return jsonify(
                {
                    "message": "Deployment started",
                    "deployment": deployment,
                }
            ), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/deployments/complete", methods=["POST"])
    def api_deployment_complete():
        """Mark a deployment as completed."""
        from deployment_monitor import complete_deployment

        data = request.get_json(force=True, silent=True) or {}

        deployment_id = data.get("deployment_id")
        status = data.get("status", "success")

        if not deployment_id:
            return jsonify({"error": "Missing required field: deployment_id"}), 400

        try:
            result = complete_deployment(deployment_id, status)
            if result is None:
                return jsonify({"error": f"Deployment {deployment_id} not found"}), 404
            return jsonify(
                {
                    "message": "Deployment completed",
                    "deployment": result,
                }
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/deployments", methods=["GET"])
    def api_deployments_list():
        """List deployments with optional filters."""
        from deployment_monitor import list_deployments

        limit = request.args.get("limit", 20, type=int)
        environment = request.args.get("environment")
        status = request.args.get("status")

        deployments = list_deployments(
            limit=limit, environment=environment, status=status
        )
        return jsonify(
            {
                "count": len(deployments),
                "deployments": deployments,
            }
        )

    # ── 2. CI/CD Integration Simulator ───────────────────────────

    @app.route("/api/cicd/run", methods=["POST"])
    def api_cicd_run():
        """Trigger a new CI/CD pipeline run."""
        from cicd_simulator import run_pipeline

        data = request.get_json(force=True, silent=True) or {}

        branch = data.get("branch", "main")
        commit_sha = data.get("commit_sha")
        triggered_by = data.get("triggered_by", "api-user")

        result = run_pipeline(
            branch=branch, commit_sha=commit_sha, triggered_by=triggered_by
        )
        return jsonify(
            {
                "message": "Pipeline run completed",
                "result": result,
            }
        ), 201

    @app.route("/api/cicd/latest", methods=["GET"])
    def api_cicd_latest():
        """Get the latest CI/CD pipeline run."""
        from cicd_simulator import get_latest_run, get_run_history

        limit = request.args.get("limit", 1, type=int)

        if limit == 1:
            latest = get_latest_run()
            if latest is None:
                return jsonify({"message": "No pipeline runs yet"}), 404
            return jsonify(latest)
        history = get_run_history(limit=limit)
        return jsonify(
            {
                "count": len(history),
                "runs": history,
            }
        )

    # ── 3. Log Parsing Engine ────────────────────────────────────

    @app.route("/api/logs/analyze", methods=["POST"])
    def api_logs_analyze():
        """Analyze log data.
        Accepts either:
          - JSON body with {"file": "filename"} to analyze a file in data/
          - JSON body with {"log_text": "..."} to analyze raw log text
        """
        from log_parser import parse_log_file, parse_log_text

        data = request.get_json(force=True, silent=True) or {}

        # Option 1: Analyze a named file
        filename = data.get("file")
        if filename:
            filepath = os.path.join(os.path.dirname(__file__), "data", filename)
            if not os.path.exists(filepath):
                return jsonify({"error": f"File not found: {filename}"}), 404
            result = parse_log_file(filepath)
            if "error" in result:
                return jsonify(result), 500
            return jsonify(result)

        # Option 2: Analyze raw log text
        log_text = data.get("log_text")
        if log_text:
            result = parse_log_text(log_text)
            if "error" in result:
                return jsonify(result), 500
            return jsonify(result)

        return jsonify(
            {"error": 'Provide either "file" or "log_text" in request body'}
        ), 400

    # ── 4. Health Checks ─────────────────────────────────────────

    @app.route("/health", methods=["GET"])
    def api_health():
        """System health check endpoint."""
        from health_checks import full_health_check

        report = full_health_check()

        status_code = 200
        if report["status"] == "unhealthy":
            status_code = 503
        elif report["status"] == "degraded":
            status_code = 200  # Still operational

        return jsonify(report), status_code

    # ── 5. Risk Evaluation Engine ────────────────────────────────

    @app.route("/api/risk/evaluate", methods=["POST"])
    def api_risk_evaluate():
        """Evaluate deployment risk.
        Expects JSON body with: failed_tests, critical_vulnerabilities,
        high_vulnerabilities, warning_count, error_count, health_status.
        """
        from risk_engine import evaluate_deployment_risk

        data = request.get_json(force=True, silent=True) or {}

        if not data:
            return jsonify(
                {"error": "Request body must be JSON with risk factors"}
            ), 400

        try:
            result = evaluate_deployment_risk(data)
            return jsonify(result)
        except (ValueError, TypeError) as e:
            return jsonify({"error": f"Invalid input: {e!s}"}), 400

    # ── Error Handlers ───────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Resource not found"}, 404

    @app.errorhandler(500)
    def internal_error(e):
        return {"error": "Internal server error"}, 500

    return app


if __name__ == "__main__":
    app = create_app()
    print("=" * 60)
    print("  Pre-Release Risk Monitor — http://127.0.0.1:5000")
    print("=" * 60)
    print("  Pages:")
    print("    /                 — Pre-Release Risk Dashboard")
    print("    /dashboard        — Pre-Release Risk Dashboard")
    print("    /risk-detail      — Risk Reasoning & Multi-Factor Inspection")
    print("    /evidence         — Regulatory Compliance Evidence Report")
    print("    /audit            — Immutable Audit History")
    print("  APIs:")
    print("    POST /api/deployments/start    — Start deployment")
    print("    POST /api/deployments/complete — Complete deployment")
    print("    GET  /api/deployments          — List deployments")
    print("    POST /api/cicd/run             — Run CI/CD pipeline")
    print("    GET  /api/cicd/latest          — Latest pipeline run")
    print("    POST /api/logs/analyze         — Analyze logs")
    print("    GET  /health                   — System health")
    print("    POST /api/risk/evaluate        — Evaluate risk")
    print("    GET  /api/dashboard-summary    — Experiment summary & evaluations")
    print("=" * 60)
    app.run(debug=True, port=5000)
