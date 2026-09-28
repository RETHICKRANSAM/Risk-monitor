"""Tests for deployment_monitor module including atomic write validation."""

import os
import pytest
from deployment_monitor import (
    DEPLOYMENTS_FILE,
    start_deployment,
    complete_deployment,
    list_deployments,
    get_deployment,
    _save_deployments,
)


def test_atomic_save_leaves_no_tmp_file():
    """Verify that _save_deployments writes atomically and cleans up temporary files."""
    test_data = [{"deployment_id": "test001", "version": "9.9.9", "status": "success"}]
    _save_deployments(test_data)

    tmp_file = f"{DEPLOYMENTS_FILE}.tmp"
    assert not os.path.exists(tmp_file), "Temporary file must not linger after atomic replace"
    assert os.path.exists(DEPLOYMENTS_FILE), "Target deployments file must exist"


def test_start_and_complete_deployment_lifecycle():
    """Verify complete deployment lifecycle tracking."""
    dep = start_deployment("3.0.0", "staging", "qa_bot")
    dep_id = dep["deployment_id"]
    assert dep["status"] == "in_progress"
    assert dep["environment"] == "staging"

    completed = complete_deployment(dep_id, "success")
    assert completed is not None
    assert completed["status"] == "success"
    assert completed["end_time"] is not None
    assert completed["duration_seconds"] is not None

    found = get_deployment(dep_id)
    assert found is not None
    assert found["deployment_id"] == dep_id


def test_invalid_parameters_raise_value_error():
    """Invalid environment or completion status must raise ValueError."""
    with pytest.raises(ValueError):
        start_deployment("1.0.0", "invalid_env", "user")

    with pytest.raises(ValueError):
        complete_deployment("fake_id", "invalid_status")
