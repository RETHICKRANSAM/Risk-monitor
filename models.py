"""SQLAlchemy ORM models for Pre-Release Risk Monitor."""

import uuid
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def generate_uuid():
    return str(uuid.uuid4())


class Organization(db.Model):
    __tablename__ = "organizations"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.Text, nullable=False, unique=True)

    # Relationships
    users = db.relationship(
        "User", backref="organization", lazy=True, cascade="all, delete-orphan"
    )
    releases = db.relationship(
        "Release", backref="organization", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
        }


class User(db.Model):
    __tablename__ = "users"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    username = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False)
    org_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "role": self.role,
            "org_id": self.org_id,
            "org_name": self.organization.name if self.organization else None,  # type: ignore
        }


class Release(db.Model):
    __tablename__ = "releases"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    release_id = db.Column(db.Text, nullable=False)
    org_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    version = db.Column(db.Text, nullable=False)
    stage = db.Column(db.Text, nullable=False, default="canary")
    deployed_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    metrics = db.relationship(
        "DeploymentMetric", backref="release", lazy=True, cascade="all, delete-orphan"
    )
    decisions = db.relationship(
        "RiskDecision", backref="release", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "release_id": self.release_id,
            "org_id": self.org_id,
            "org_name": self.organization.name if self.organization else None,  # type: ignore
            "version": self.version,
            "stage": self.stage,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
        }


class DeploymentMetric(db.Model):
    __tablename__ = "deployment_metrics"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    release_id = db.Column(db.String(36), db.ForeignKey("releases.id"), nullable=False)
    error_rate = db.Column(db.Numeric(6, 3))
    latency_ms = db.Column(db.Integer)
    availability = db.Column(db.Numeric(6, 3))
    error_budget_remaining = db.Column(db.Numeric(6, 3))
    canary_error_rate = db.Column(db.Numeric(6, 3))
    canary_latency_delta = db.Column(db.Integer)
    cpu_usage = db.Column(db.Numeric(5, 2))
    memory_usage = db.Column(db.Numeric(5, 2))
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "release_id": self.release_id,
            "error_rate": float(self.error_rate)
            if self.error_rate is not None
            else None,
            "latency_ms": self.latency_ms,
            "availability": float(self.availability)
            if self.availability is not None
            else None,
            "error_budget_remaining": float(self.error_budget_remaining)
            if self.error_budget_remaining is not None
            else None,
            "canary_error_rate": float(self.canary_error_rate)
            if self.canary_error_rate is not None
            else None,
            "canary_latency_delta": self.canary_latency_delta,
            "cpu_usage": float(self.cpu_usage) if self.cpu_usage is not None else None,
            "memory_usage": float(self.memory_usage)
            if self.memory_usage is not None
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RiskDecision(db.Model):
    __tablename__ = "risk_decisions"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    release_id = db.Column(db.String(36), db.ForeignKey("releases.id"), nullable=False)
    risk_score = db.Column(db.Integer, nullable=False)
    decision = db.Column(db.Text, nullable=False)
    reasons = db.Column(db.Text)
    reviewer = db.Column(db.Text)
    decided_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "release_id": self.release_id,
            "risk_score": self.risk_score,
            "decision": self.decision,
            "reasons": self.reasons,
            "reviewer": self.reviewer,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
        }
