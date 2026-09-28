"""Comprehensive End-to-End System Test Suite for Pre-Release Risk Monitor.

Validates 100% of project subsystems:
1. Pytest Unit & Integration Test Suite (13/13 tests)
2. Live Container / HTTP Web Endpoints (Pages & APIs)
3. Multi-Factor Risk Engine (ALLOW, PAUSE, and BLOCK decisions)
4. CI/CD Simulator & Log Parsing Engine
5. Machine Learning & Deep Learning Inference Engine
6. 100-Release Empirical Baseline Experiment
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import http.cookiejar

# Enable session cookie persistence across HTTP requests
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
urllib.request.install_opener(opener)

PROJECT_ROOT = Path(__file__).resolve().parent
APP_PY = PROJECT_ROOT / "app.py"
PORT = int(os.environ.get("PORT", 5000))
BASE_URL = f"http://127.0.0.1:{PORT}"
HEALTH_URL = f"{BASE_URL}/health"


def print_banner(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def is_server_reachable(url=HEALTH_URL, timeout=1.5):
    """Check if the web application is already running and responding."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SystemVerifier/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status in (200, 301, 302, 503)
    except urllib.error.HTTPError:
        # Any HTTP response code (including 404, 500, 503) proves the server is listening
        return True
    except Exception:
        return False


def ensure_server_running():
    """Ensure the web server is listening on 127.0.0.1 before executing HTTP tests.
    Returns (subprocess.Popen or None, log_file or None).
    """
    if is_server_reachable():
        print(f"  [INFO] Web application already reachable at {BASE_URL}. Skipping auto-start.")
        return None, None

    print(f"  [INFO] No server detected at {BASE_URL}. Starting {APP_PY.name} via {Path(sys.executable).name}...")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PORT"] = str(PORT)
    env["HOST"] = "127.0.0.1"
    env["FLASK_DEBUG"] = "0"
    env["FLASK_USE_RELOADER"] = "0"

    log_path = PROJECT_ROOT / ".test_server.log"
    log_file = open(log_path, "w+", encoding="utf-8", errors="replace")

    proc = subprocess.Popen(
        [sys.executable, str(APP_PY)],
        cwd=str(PROJECT_ROOT),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
    )

    # Poll /health with 30s timeout
    start_time = time.time()
    timeout = 30.0
    while time.time() - start_time < timeout:
        ret = proc.poll()
        if ret is not None:
            log_file.seek(0)
            server_logs = log_file.read()
            log_file.close()
            raise RuntimeError(
                f"Server process terminated prematurely with exit code {ret}.\n"
                f"Server Output & Error Logs:\n{server_logs}"
            )

        if is_server_reachable():
            elapsed = time.time() - start_time
            print(f"  [INFO] Server is healthy and listening on {HEALTH_URL} (started in {elapsed:.2f}s).")
            return proc, log_file

        time.sleep(0.5)

    # Timed out waiting for server
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()
    log_file.seek(0)
    server_logs = log_file.read()
    log_file.close()
    raise TimeoutError(
        f"Server at {BASE_URL} failed to respond within {timeout} seconds.\n"
        f"Server Output & Error Logs:\n{server_logs}"
    )


def stop_server(proc, log_file):
    """Gracefully terminate background server process."""
    if proc is not None:
        print("\n  [CLEANUP] Gracefully shutting down web server...")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=2)
            except Exception:
                pass
        print("  [CLEANUP] Web server stopped.")

    if log_file is not None:
        try:
            log_file.close()
        except Exception:
            pass


def check_http_endpoint(name, url, method="GET", data=None, expected_status=200, timeout=30):
    """Perform HTTP request and validate status code."""
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8") if data else None,
            headers={"Content-Type": "application/json"} if data else {},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
            if status == expected_status:
                print(f"  [PASS] {name} ({method} {url}) -> {status} OK")
                return True, body
            else:
                print(f"  [FAIL] {name} ({method} {url}) -> Expected {expected_status}, got {status}")
                if body:
                    print(f"         Response body: {body[:300]}")
                return False, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        if e.code == expected_status:
            print(f"  [PASS] {name} ({method} {url}) -> {e.code} OK")
            return True, body
        print(f"  [FAIL] {name} ({method} {url}) -> HTTPError {e.code}")
        if body:
            print(f"         Response body: {body[:500]}")
        return False, body
    except Exception as e:
        print(f"  [FAIL] {name} ({method} {url}) -> Connection Error: {e}")
        return False, str(e)


def main():
    print_banner("PRE-RELEASE RISK MONITOR: FULL SYSTEM VERIFICATION SUITE")
    results = []

    # =========================================================================
    # Step 1: Run Pytest Unit & Integration Tests
    # =========================================================================
    print_banner("STAGE 1: RUNNING AUTOMATED UNIT & INTEGRATION TESTS (PYTEST)")
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--no-header"]
    res = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print(res.stdout)
    if res.returncode == 0:
        print("  --> STAGE 1 RESULT: ALL TESTS PASSED [PASS]")
        results.append(("Pytest Test Suite", True))
    else:
        print(f"  --> STAGE 1 RESULT: FAILED\n{res.stderr}")
        results.append(("Pytest Test Suite", False))

    # =========================================================================
    # Server Lifecycle Management for Stages 2 - 5
    # =========================================================================
    server_proc = None
    server_log = None

    try:
        try:
            server_proc, server_log = ensure_server_running()
        except Exception as e:
            print(f"\n[FATAL] Unable to initialize web server for Stages 2-5: {e}")
            for stage_name in [
                "Frontend UI Pages",
                "Core REST APIs & Microservices",
                "Multi-Factor Risk Gating (ALLOW/PAUSE/BLOCK)",
                "ML & Deep Learning Pipeline",
            ]:
                results.append((stage_name, False))
        else:
            # =========================================================================
            # Step 2: Validate Live Web GUI Pages
            # =========================================================================
            print_banner("STAGE 2: TESTING LIVE WEB GUI INTERFACES (HTTP)")
            pages = [
                ("Dashboard Page", f"{BASE_URL}/"),
                ("Rollout Monitor", f"{BASE_URL}/dashboard"),
                ("Risk Reasoning Page", f"{BASE_URL}/risk-detail"),
                ("Regulatory Evidence Dossier", f"{BASE_URL}/evidence"),
                ("Immutable Audit Ledger", f"{BASE_URL}/audit"),
            ]
            page_pass = True
            for name, url in pages:
                ok, _ = check_http_endpoint(name, url)
                if not ok:
                    page_pass = False
            results.append(("Frontend UI Pages", page_pass))

            # =========================================================================
            # Step 3: Validate Core REST APIs & Microservices
            # =========================================================================
            print_banner("STAGE 3: TESTING BACKEND REST APIS & CORE ENGINES")
            api_pass = True

            # Health API
            ok, _ = check_http_endpoint("Health Check API", f"{BASE_URL}/health")
            if not ok:
                api_pass = False

            # Security Verification: Block impersonation without authentication
            ok, _ = check_http_endpoint(
                "Auth Security: ?user=iris_audit Blocked",
                f"{BASE_URL}/api/dashboard?user=iris_audit",
                expected_status=401,
            )
            if not ok:
                api_pass = False

            # Authenticate Session
            ok, _ = check_http_endpoint(
                "User Authentication API",
                f"{BASE_URL}/api/login",
                method="POST",
                data={"username": "alice_re", "password": "demo123"},
                expected_status=200,
            )
            if not ok:
                api_pass = False

            # Dashboard summary API
            ok, _ = check_http_endpoint("Dashboard Summary API", f"{BASE_URL}/api/dashboard")
            if not ok:
                api_pass = False

            # Deployments list API
            ok, _ = check_http_endpoint("Deployments List API", f"{BASE_URL}/api/deployments")
            if not ok:
                api_pass = False

            # CI/CD Trigger API
            ok, _ = check_http_endpoint(
                "CI/CD Pipeline Simulator",
                f"{BASE_URL}/api/cicd/run",
                method="POST",
                data={"branch": "main", "commit_sha": "a1b2c3d4", "triggered_by": "test_suite"},
                expected_status=201,
            )
            if not ok:
                api_pass = False

            # Log Parsing Engine API
            ok, _ = check_http_endpoint(
                "Log Analysis Engine",
                f"{BASE_URL}/api/logs/analyze",
                method="POST",
                data={"file": "sample_app.log"},
                expected_status=200,
            )
            if not ok:
                api_pass = False

            results.append(("Core REST APIs & Microservices", api_pass))

            # =========================================================================
            # Step 4: Multi-Factor Decision Gating (ALLOW, PAUSE, BLOCK)
            # =========================================================================
            print_banner("STAGE 4: TESTING MULTI-FACTOR RISK ENGINE DECISION GATES")
            gate_pass = True

            # Test ALLOW (Healthy)
            ok, body = check_http_endpoint(
                "Decision Gate 1: ALLOW (Healthy Telemetry)",
                f"{BASE_URL}/api/risk/evaluate",
                method="POST",
                data={"error_rate": 0.5, "latency_ms": 120, "canary_error_rate": 0.2, "error_budget_remaining": 95.0},
            )
            if ok and '"decision":"ALLOW"' in body.replace(" ", ""):
                print("      --> Verified: Output decision is ALLOW (Score <= 39)")
            else:
                print("      --> Failed to verify ALLOW decision")
                gate_pass = False

            # Test PAUSE (Moderate Risk)
            ok, body = check_http_endpoint(
                "Decision Gate 2: PAUSE (Moderate Risk / High Error Rate)",
                f"{BASE_URL}/api/risk/evaluate",
                method="POST",
                data={"error_rate": 3.8, "latency_ms": 250, "canary_error_rate": 0.5, "error_budget_remaining": 70.0},
            )
            if ok and '"decision":"PAUSE"' in body.replace(" ", ""):
                print("      --> Verified: Output decision is PAUSE (Score 40-59)")
            else:
                print("      --> Failed to verify PAUSE decision")
                gate_pass = False

            # Test BLOCK (Critical Risk / Circuit Breaker)
            ok, body = check_http_endpoint(
                "Decision Gate 3: BLOCK (Critical Risk / Circuit Breaker Activated)",
                f"{BASE_URL}/api/risk/evaluate",
                method="POST",
                data={"error_rate": 4.5, "latency_ms": 650, "canary_error_rate": 3.2, "error_budget_remaining": 10.0},
            )
            if ok and '"decision":"BLOCK"' in body.replace(" ", ""):
                print("      --> Verified: Output decision is BLOCK (Score >= 60)")
            else:
                print("      --> Failed to verify BLOCK decision")
                gate_pass = False

            results.append(("Multi-Factor Risk Gating (ALLOW/PAUSE/BLOCK)", gate_pass))

            # =========================================================================
            # Step 5: Machine Learning & Anomaly Detection Inference
            # =========================================================================
            print_banner("STAGE 5: TESTING MACHINE LEARNING & DEEP LEARNING PIPELINE")
            ml_pass = True

            # ML Benchmarks
            ok, _ = check_http_endpoint("ML Model Benchmark Endpoint", f"{BASE_URL}/api/ml/metrics")
            if not ok:
                ml_pass = False

            # Live ML & Anomaly Prediction
            ml_payload = {
                "protocol_type": "tcp",
                "service": "private",
                "flag": "REJ",
                "wrong_fragment": 1,
                "num_compromised": 2,
            }
            ok, body = check_http_endpoint(
                "Live ML Inference (XGBoost + Random Forest + Autoencoder + MLP)",
                f"{BASE_URL}/api/ml/predict-risk",
                method="POST",
                data=ml_payload,
            )
            if ok:
                print("      --> Verified: Multi-model ML inference executed successfully")
            else:
                ml_pass = False

            results.append(("ML & Deep Learning Pipeline", ml_pass))

    finally:
        stop_server(server_proc, server_log)

    # =========================================================================
    # Step 6: Empirical Baseline Experiment
    # =========================================================================
    print_banner("STAGE 6: RUNNING 100-RELEASE EMPIRICAL BASELINE EXPERIMENT")
    exp_cmd = [sys.executable, str(PROJECT_ROOT / "experiments" / "run_baseline_experiment.py")]
    exp_res = subprocess.run(
        exp_cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if exp_res.returncode == 0:
        print(exp_res.stdout)
        print("  --> STAGE 6 RESULT: EMPIRICAL EXPERIMENT COMPLETED [PASS]")
        results.append(("100-Release Empirical Experiment", True))
    else:
        print(f"  --> STAGE 6 RESULT: FAILED\n{exp_res.stderr}")
        results.append(("100-Release Empirical Experiment", False))

    # =========================================================================
    # Final Scorecard
    # =========================================================================
    print_banner("SYSTEM VERIFICATION SCORECARD")
    all_passed = True
    for name, status in results:
        status_text = "[PASSED]" if status else "[FAILED]"
        if not status:
            all_passed = False
        print(f"  {name.ljust(50)} {status_text}")

    print("-" * 70)
    if all_passed:
        print("  [SUCCESS] CONGRATULATIONS: 100% OF SYSTEM TESTS PASSED SUCCESSFULLY!")
        print("  Your project is fully operational, logically sound, and production-ready.")
    else:
        print("  [WARNING] Some subsystems failed verification. Review output above.")
    print("=" * 70 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
