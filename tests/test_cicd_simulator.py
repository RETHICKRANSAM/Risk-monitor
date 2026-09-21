"""Tests for cicd_simulator module."""

import json

import cicd_simulator


def test_run_pipeline_structure():
    result = cicd_simulator.run_pipeline(branch="test-branch", triggered_by="unit-test")
    assert result is not None
    assert "run_id" in result
    assert result["branch"] == "test-branch"
    assert result["triggered_by"] == "unit-test"
    assert result["status"] in ("passed", "failed")
    assert result["overall_status"] in ("passed", "failed")
    assert isinstance(result["duration_seconds"], (int, float))
    assert isinstance(result["total_duration_seconds"], (int, float))
    assert isinstance(result["tests_passed"], int)
    assert isinstance(result["tests_failed"], int)
    assert isinstance(result["stages"], list)
    assert len(result["stages"]) == len(cicd_simulator.PIPELINE_STAGES)

    # Vulnerabilities must contain standard severity keys
    vulns = result["vulnerabilities"]
    assert "critical" in vulns
    assert "high" in vulns
    assert "medium" in vulns
    assert "low" in vulns

    # If security scan passed, critical vulns must be 0
    sec_stage = next((s for s in result["stages"] if s["name"] == "security_scan"), None)
    if sec_stage and sec_stage["status"] == "passed":
        assert vulns["critical"] == 0

    # End time should be at or before now, not in the future
    from datetime import datetime, timezone
    end_dt = datetime.fromisoformat(result["end_time"])
    now_dt = datetime.now(timezone.utc)
    assert end_dt <= now_dt


def test_get_latest_run_and_history():
    latest = cicd_simulator.get_latest_run()
    assert latest is not None

    history = cicd_simulator.get_run_history(limit=2)
    assert isinstance(history, list)
    assert len(history) <= 2

    # Negative limit should return empty list rather than slice from the end
    empty_history = cicd_simulator.get_run_history(limit=-1)
    assert empty_history == []

    zero_history = cicd_simulator.get_run_history(limit=0)
    assert zero_history == []


def test_corrupted_json_loading(tmp_path, monkeypatch):
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(cicd_simulator, "CICD_FILE", str(corrupt_file))
    assert cicd_simulator._load_results() == []

    dict_file = tmp_path / "dict.json"
    dict_file.write_text(json.dumps({"unexpected": "dict"}), encoding="utf-8")
    monkeypatch.setattr(cicd_simulator, "CICD_FILE", str(dict_file))
    assert cicd_simulator._load_results() == []
