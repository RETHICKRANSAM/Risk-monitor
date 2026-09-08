"""Synthetic data generator for Pre-Release Risk Monitor.

Generates 100 deployment records across 3 organizations.
~20% of records are intentionally "harmful" for evaluation.
"""

import csv
import os
import random
import sys
from datetime import datetime, timedelta, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

random.seed(42)  # Reproducible results

ORGANIZATIONS = ["BankA", "HealthCo", "GovAgency"]
VERSIONS_BASE = ["1.0", "1.1", "1.2", "2.0", "2.1", "2.3", "3.0", "3.1"]
NUM_RECORDS = 100
HARMFUL_RATIO = 0.20  # 20% harmful

# Demo users for each organization and role
DEMO_USERS = [
    # BankA
    {
        "username": "alice_re",
        "name": "Alice Johnson",
        "role": "release_engineer",
        "org": "BankA",
        "password": "demo123",
    },
    {
        "username": "bob_co",
        "name": "Bob Smith",
        "role": "compliance_officer",
        "org": "BankA",
        "password": "demo123",
    },
    {
        "username": "charlie_sre",
        "name": "Charlie Brown",
        "role": "sre",
        "org": "BankA",
        "password": "demo123",
    },
    # HealthCo
    {
        "username": "diana_re",
        "name": "Diana Prince",
        "role": "release_engineer",
        "org": "HealthCo",
        "password": "demo123",
    },
    {
        "username": "eve_co",
        "name": "Eve Davis",
        "role": "compliance_officer",
        "org": "HealthCo",
        "password": "demo123",
    },
    {
        "username": "frank_sre",
        "name": "Frank Miller",
        "role": "sre",
        "org": "HealthCo",
        "password": "demo123",
    },
    # GovAgency
    {
        "username": "grace_re",
        "name": "Grace Lee",
        "role": "release_engineer",
        "org": "GovAgency",
        "password": "demo123",
    },
    {
        "username": "hank_ep",
        "name": "Hank Wilson",
        "role": "external_partner",
        "org": "GovAgency",
        "password": "demo123",
    },
    # Global auditor
    {
        "username": "iris_audit",
        "name": "Iris Chen",
        "role": "auditor",
        "org": "BankA",
        "password": "demo123",
    },
]


def generate_healthy_metrics():
    """Generate metrics for a healthy deployment."""
    return {
        "error_rate": round(random.uniform(0.1, 2.5), 3),
        "latency_ms": random.randint(80, 400),
        "availability": round(random.uniform(99.0, 100.0), 3),
        "error_budget_remaining": round(random.uniform(30.0, 95.0), 3),
        "canary_error_rate": round(random.uniform(0.1, 1.8), 3),
        "canary_latency_delta": random.randint(-20, 50),
        "cpu_usage": round(random.uniform(15.0, 60.0), 2),
        "memory_usage": round(random.uniform(20.0, 65.0), 2),
    }


def generate_harmful_metrics():
    """Generate metrics for a harmful deployment."""
    pattern = random.choice(["high_error", "high_latency", "combined", "canary_bad"])

    metrics = generate_healthy_metrics()  # Start with healthy base

    if pattern == "high_error":
        metrics["error_rate"] = round(random.uniform(3.5, 12.0), 3)
        metrics["canary_error_rate"] = round(random.uniform(2.5, 8.0), 3)
    elif pattern == "high_latency":
        metrics["latency_ms"] = random.randint(550, 2000)
        metrics["canary_latency_delta"] = random.randint(100, 500)
        metrics["canary_error_rate"] = round(random.uniform(2.1, 4.5), 3)
        metrics["error_budget_remaining"] = round(random.uniform(5.0, 18.0), 3)
    elif pattern == "combined":
        metrics["error_rate"] = round(random.uniform(4.0, 10.0), 3)
        metrics["latency_ms"] = random.randint(600, 1500)
        metrics["canary_error_rate"] = round(random.uniform(3.0, 7.0), 3)
        metrics["error_budget_remaining"] = round(random.uniform(2.0, 18.0), 3)
    elif pattern == "canary_bad":
        metrics["canary_error_rate"] = round(random.uniform(3.0, 9.0), 3)
        metrics["error_rate"] = round(random.uniform(2.8, 6.0), 3)
        metrics["canary_latency_delta"] = random.randint(150, 400)
        metrics["error_budget_remaining"] = round(random.uniform(5.0, 15.0), 3)

    return metrics


def introduce_noise(records):
    """Introduce missing values and noise into some records."""
    noisy_records = []
    for i, record in enumerate(records):
        r = dict(record)

        # ~10% chance of missing a metric
        if random.random() < 0.10:
            field = random.choice(
                [
                    "error_rate",
                    "latency_ms",
                    "canary_error_rate",
                    "canary_latency_delta",
                ]
            )
            r[field] = ""

        # ~5% chance of a temporarily impossible value (to be cleaned)
        if random.random() < 0.05:
            r["availability"] = round(random.uniform(100.5, 105.0), 3)

        noisy_records.append(r)
    return noisy_records


def generate_records():
    """Generate 100 synthetic deployment records."""
    records = []
    num_harmful = int(NUM_RECORDS * HARMFUL_RATIO)
    harmful_indices = set(random.sample(range(NUM_RECORDS), num_harmful))

    base_time = datetime(2026, 7, 1, 8, 0, 0, tzinfo=timezone.utc)

    for i in range(NUM_RECORDS):
        org = random.choice(ORGANIZATIONS)
        version = random.choice(VERSIONS_BASE) + "." + str(random.randint(0, 9))
        is_harmful = i in harmful_indices
        deployed_at = base_time + timedelta(hours=random.randint(0, 720))

        metrics = (
            generate_harmful_metrics() if is_harmful else generate_healthy_metrics()
        )

        record = {
            "release_id": f"R{i + 1:04d}",
            "org": org,
            "version": version,
            "stage": random.choice(["canary", "staged", "production"]),
            "deployed_at": deployed_at.isoformat(),
            "is_harmful": is_harmful,  # Ground truth for evaluation
            **metrics,
        }
        records.append(record)

    return introduce_noise(records)


def write_csv(records, filepath):
    """Write records to CSV file."""
    if not records:
        return

    fieldnames = list(records[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} records to {os.path.basename(filepath)}")


def seed_database():
    """Seed the database with synthetic data using SQLAlchemy."""
    import json

    from werkzeug.security import generate_password_hash

    from app import create_app
    from models import DeploymentMetric, Organization, Release, RiskDecision, User, db
    from risk_engine import evaluate_release

    app = create_app()

    with app.app_context():
        # Create tables
        db.create_all()

        # Seed organizations
        org_map = {}
        for org_name in ORGANIZATIONS:
            org = Organization.query.filter_by(name=org_name).first()
            if not org:
                org = Organization(name=org_name)
                db.session.add(org)
                db.session.flush()
            org_map[org_name] = org.id

        # Seed users
        for user_data in DEMO_USERS:
            existing = User.query.filter_by(username=user_data["username"]).first()
            if not existing:
                user = User(
                    username=user_data["username"],
                    password_hash=generate_password_hash(user_data["password"]),
                    name=user_data["name"],
                    role=user_data["role"],
                    org_id=org_map[user_data["org"]],
                )
                db.session.add(user)

        # Seed releases and metrics from CSV
        csv_path = os.path.join(os.path.dirname(__file__), "synthetic_releases.csv")
        if not os.path.exists(csv_path):
            records = generate_records()
            write_csv(records, csv_path)

        if os.path.exists(csv_path):
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    org_name = row["org"]
                    org_id = org_map.get(org_name)
                    if not org_id:
                        org = Organization.query.filter_by(name=org_name).first()
                        if not org:
                            org = Organization(name=org_name)
                            db.session.add(org)
                            db.session.flush()
                        org_map[org_name] = org.id
                        org_id = org.id

                    # Check if release already exists
                    existing = Release.query.filter_by(
                        release_id=row["release_id"]
                    ).first()
                    if existing:
                        continue

                    deployed_at_str = row.get("deployed_at")
                    if deployed_at_str:
                        try:
                            deployed_at = datetime.fromisoformat(deployed_at_str)
                        except ValueError:
                            deployed_at = datetime.now(timezone.utc)
                    else:
                        deployed_at = datetime.now(timezone.utc) - timedelta(
                            days=random.randint(0, 30)
                        )

                    release = Release(
                        release_id=row["release_id"],
                        org_id=org_id,
                        version=row["version"],
                        stage=row.get("stage", "production"),
                        deployed_at=deployed_at,
                    )
                    db.session.add(release)
                    db.session.flush()

                    # Add metrics
                    def safe_float(val):
                        try:
                            return float(val) if val else None
                        except (ValueError, TypeError):
                            return None

                    def safe_int(val):
                        try:
                            return int(val) if val else None
                        except (ValueError, TypeError):
                            return None

                    metric = DeploymentMetric(
                        release_id=release.id,
                        error_rate=safe_float(row.get("error_rate")),
                        latency_ms=safe_int(row.get("latency_ms")),
                        availability=safe_float(row.get("availability")),
                        error_budget_remaining=safe_float(
                            row.get("error_budget_remaining")
                        ),
                        canary_error_rate=safe_float(row.get("canary_error_rate")),
                        canary_latency_delta=safe_int(row.get("canary_latency_delta")),
                        cpu_usage=safe_float(row.get("cpu_usage")),
                        memory_usage=safe_float(row.get("memory_usage")),
                    )
                    db.session.add(metric)
                    db.session.flush()

                    metrics_dict = {
                        "error_rate": safe_float(row.get("error_rate")),
                        "latency_ms": safe_int(row.get("latency_ms")),
                        "availability": safe_float(row.get("availability")),
                        "error_budget_remaining": safe_float(
                            row.get("error_budget_remaining")
                        ),
                        "canary_error_rate": safe_float(row.get("canary_error_rate")),
                        "canary_latency_delta": safe_int(
                            row.get("canary_latency_delta")
                        ),
                    }
                    evaluation = evaluate_release(metrics_dict)

                    decision = RiskDecision(
                        release_id=release.id,
                        risk_score=evaluation["risk_score"],
                        decision=evaluation["decision"],
                        reasons=json.dumps(evaluation["reasons"]),
                        reviewer="system",
                        decided_at=deployed_at,
                    )
                    db.session.add(decision)

        db.session.commit()
        print("Database seeded successfully!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate synthetic data for Pre-Release Risk Monitor"
    )
    parser.add_argument(
        "--csv-only",
        action="store_true",
        help="Only generate CSV, do not seed database",
    )
    parser.add_argument(
        "--seed-db", action="store_true", help="Seed the database from CSV"
    )
    args = parser.parse_args()

    if args.seed_db:
        seed_database()
    else:
        records = generate_records()
        csv_path = os.path.join(os.path.dirname(__file__), "synthetic_releases.csv")
        write_csv(records, csv_path)

        # Print summary
        harmful_count = sum(1 for r in records if r.get("is_harmful"))
        print("\nSummary:")
        print(f"  Total records: {len(records)}")
        print(f"  Harmful: {harmful_count}")
        print(f"  Healthy: {len(records) - harmful_count}")
        print(f"  Organizations: {', '.join(ORGANIZATIONS)}")
