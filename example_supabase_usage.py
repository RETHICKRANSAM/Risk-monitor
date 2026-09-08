"""Example usage of Supabase client in the Flask application.

This file demonstrates how to use Supabase for various operations.
"""

from flask import jsonify, request

from supabase_client import get_supabase_client


def example_query_alerts():
    """Example: Query all alerts from Supabase.

    Usage in a route:
        @app.route('/api/alerts')
        def get_alerts():
            return example_query_alerts()
    """
    try:
        supabase = get_supabase_client()

        # Query all alerts
        response = supabase.table("alerts").select("*").execute()

        return jsonify(
            {
                "success": True,
                "data": response.data,
                "count": len(response.data),
            }
        ), 200

    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": str(e),
            }
        ), 500


def example_query_with_filters():
    """Example: Query alerts with filters (e.g., critical severity).

    Usage in a route:
        @app.route('/api/alerts/critical')
        def get_critical_alerts():
            return example_query_with_filters()
    """
    try:
        supabase = get_supabase_client()

        # Query with filters
        response = (
            supabase.table("alerts")
            .select("*")
            .eq("severity", "critical")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        return jsonify(
            {
                "success": True,
                "data": response.data,
                "count": len(response.data),
            }
        ), 200

    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": str(e),
            }
        ), 500


def example_insert_alert():
    """Example: Insert a new alert into Supabase.

    Usage in a route:
        @app.route('/api/alerts', methods=['POST'])
        def create_alert():
            data = request.get_json()
            return example_insert_alert(data)
    """
    try:
        # Get data from request
        data = request.get_json()

        # Insert into Supabase
        supabase = get_supabase_client()
        response = supabase.table("alerts").insert(data).execute()

        return jsonify(
            {
                "success": True,
                "data": response.data,
                "message": "Alert created successfully",
            }
        ), 201

    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": str(e),
            }
        ), 500


def example_update_alert(alert_id):
    """Example: Update an existing alert.

    Usage in a route:
        @app.route('/api/alerts/<int:alert_id>', methods=['PUT'])
        def update_alert(alert_id):
            data = request.get_json()
            return example_update_alert(alert_id, data)
    """
    try:
        # Get update data from request
        updates = request.get_json()

        # Update in Supabase
        supabase = get_supabase_client()
        response = supabase.table("alerts").update(updates).eq("id", alert_id).execute()

        return jsonify(
            {
                "success": True,
                "data": response.data,
                "message": "Alert updated successfully",
            }
        ), 200

    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": str(e),
            }
        ), 500


def example_delete_alert(alert_id):
    """Example: Delete an alert.

    Usage in a route:
        @app.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
        def delete_alert(alert_id):
            return example_delete_alert(alert_id)
    """
    try:
        # Delete from Supabase
        supabase = get_supabase_client()
        supabase.table("alerts").delete().eq("id", alert_id).execute()

        return jsonify(
            {
                "success": True,
                "message": "Alert deleted successfully",
            }
        ), 200

    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": str(e),
            }
        ), 500


def example_realtime_subscription():
    """Example: Subscribe to real-time changes in a table.

    Note: Real-time subscriptions work differently in Python.
    This is a reference for how to set it up.
    """
    get_supabase_client()

    def handle_alert_changes(payload):
        """Handle incoming real-time changes."""
        print(f"Change detected: {payload}")
        # Process the change here

    # Subscribe to INSERT events
    # Note: Supabase Python client has limited real-time support
    # Consider using websockets or polling for real-time updates


def example_storage_upload():
    """Example: Upload a file to Supabase Storage.

    Usage in a route:
        @app.route('/api/upload', methods=['POST'])
        def upload_file():
            file = request.files['file']
            return example_storage_upload(file)
    """
    try:
        file = request.files.get("file")

        if not file:
            return jsonify(
                {
                    "success": False,
                    "error": "No file provided",
                }
            ), 400

        # Upload to Supabase Storage
        supabase = get_supabase_client()

        # Read file content
        file_content = file.read()
        file_name = file.filename or "uploaded"

        # Upload to bucket
        supabase.storage.from_("your-bucket-name").upload(
            file_name, file_content
        )

        # Get public URL
        public_url = supabase.storage.from_("your-bucket-name").get_public_url(
            file_name
        )

        return jsonify(
            {
                "success": True,
                "url": public_url,
                "message": "File uploaded successfully",
            }
        ), 200

    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": str(e),
            }
        ), 500


def example_authentication():
    """Example: Authenticate a user with Supabase Auth.

    Usage in a route:
        @app.route('/api/auth/login', methods=['POST'])
        def login():
            data = request.get_json()
            return example_authentication(data['email'], data['password'])
    """
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify(
                {
                    "success": False,
                    "error": "Email and password required",
                }
            ), 400

        # Sign in with Supabase Auth
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

        return jsonify(
            {
                "success": True,
                "session": response.session.dict() if response.session else None,
                "user": response.user.dict() if response.user else None,
            }
        ), 200

    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": str(e),
            }
        ), 401


# Example of using Supabase in your existing routes
def get_dashboard_data():
    """Example: Get aggregated data for dashboard using Supabase."""
    try:
        supabase = get_supabase_client()

        # Get counts for different severity levels
        critical_alerts = (
            supabase.table("alerts")
            .select("*", count="exact")  # type: ignore
            .eq("severity", "critical")
            .execute()
        )

        high_alerts = (
            supabase.table("alerts")
            .select("*", count="exact")  # type: ignore
            .eq("severity", "high")
            .execute()
        )

        # Get recent alerts
        recent_alerts = (
            supabase.table("alerts")
            .select("*")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        return jsonify(
            {
                "success": True,
                "data": {
                    "critical_count": critical_alerts.count,
                    "high_count": high_alerts.count,
                    "recent_alerts": recent_alerts.data,
                },
            }
        ), 200

    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": str(e),
            }
        ), 500
