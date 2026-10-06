"""Example usage of Supabase client in the Pre-Release Risk Monitor application.

Demonstrates querying, inserting, and filtering operations on project tables:
organizations, releases, deployment_metrics, and risk_decisions.
"""

from flask import jsonify, request
from supabase_client import get_supabase_client, insert_data, query_table


def example_query_organizations():
    """Query all registered enterprise organizations."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("organizations").select("*").execute()
        return jsonify({
            "success": True,
            "data": response.data,
            "count": len(response.data),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def example_query_releases_with_filters():
    """Query canary releases sorted by deployment timestamp."""
    try:
        supabase = get_supabase_client()
        response = (
            supabase.table("releases")
            .select("id, release_id, version, stage, deployed_at")
            .eq("stage", "canary")
            .order("deployed_at", desc=True)
            .limit(10)
            .execute()
        )
        return jsonify({
            "success": True,
            "data": response.data,
            "count": len(response.data),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def example_insert_risk_decision(release_id: str, risk_score: int, decision: str):
    """Insert an evaluated risk gating decision."""
    try:
        data = {
            "release_id": release_id,
            "risk_score": risk_score,
            "decision": decision,
            "reasons": "Canary delta evaluation complete",
            "reviewer": "system_auto",
        }
        result = insert_data("risk_decisions", data)
        return jsonify({"success": True, "data": result}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
