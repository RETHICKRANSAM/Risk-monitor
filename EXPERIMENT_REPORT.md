# Empirical Baseline & Intervention Experiment Report

**Project:** Pre-Release Risk Monitor for Regulated Enterprise Deployments  
**Evaluation Date:** September 2026  
**Status:** Completed & Validated  
**Artifacts Generated:** [`data/experiment_results.json`](file:///c:/Users/rethi/OneDrive/เอกสาร/Desktop/coe%20project/data/experiment_results.json)  
**Execution Script:** [`experiments/run_baseline_experiment.py`](file:///c:/Users/rethi/OneDrive/เอกสาร/Desktop/coe%20project/experiments/run_baseline_experiment.py)

---

## 1. Executive Summary

In regulated enterprise environments (e.g., banking, healthcare, government), release failures detected only after broad production rollout cause severe customer disruption, regulatory fines, and SLA breaches. The primary goal of this experiment was to **empirically validate** whether implementing a pre-release risk monitor combining deployment signals, progressive canary checks, automated data cleaning/imputation, and multi-factor scoring can prevent harmful changes from reaching customers while maintaining full audit evidence.

### Key Findings:
1. **Harmful Release Stop Rate:** Increased from an empirical baseline of **50.0%** (status quo coarse static checks without canary delta or error budget awareness) to **100.0%** in automated progressive canary gating (**Target: ≥80% — MET**).
2. **Audit Evidence Generation:** Increased from **0.0%** (untracked manual changes) to **100.0%** verifiable change receipts with full telemetry and decision trails (**Target: 100% — MET**).
3. **False Positive Block Rate:** Maintained at **0.0%** (**Target: <15% — MET**), ensuring release velocity is not unnecessarily throttled.

---

## 2. Experimental Methodology

### 2.1 Dataset Composition
* **Sample Size:** 100 synthetic change tickets modeled after production telemetry in multi-tenant enterprise architectures (`BankA`, `HealthCo`, `GovAgency`).
* **Ground Truth Class Distribution:**
  * **Healthy Deployments:** 80 releases (80.0%)
  * **Harmful Deployments:** 20 releases (20.0%)
* **Failure Patterns Represented:**
  * *High Error Rate:* Production error rate spikes (>3.5% up to 12.0%).
  * *High Latency & Degradation:* Latency exceeds SLA (>550ms up to 2000ms) with elevated canary latency deltas (+100ms to +500ms).
  * *Combined Failure:* Elevated error rates, high latency, and rapid error budget burn (<20% remaining).
  * *Canary Anomalies:* Divergence between canary traffic and baseline instances (canary error rate >3.0%).
* **Data Noise & Edge Cases:**
  * 10% of records intentionally contain missing metrics (evaluating median statistical imputation).
  * 5% contain noisy sensor spikes (evaluating 3-point moving-average smoothing).

---

### 2.2 Compared Systems

| Dimension | Baseline System (Status Quo) | Intervention System (Pre-Release Risk Monitor) |
| :--- | :--- | :--- |
| **Telemetry Ingestion** | Ad-hoc post-deployment logs | Continuous automated ingestion of canary and service metrics |
| **Data Quality Handling** | Discards incomplete records / crashes | Median imputation for missing metrics; 3-window moving average smoothing |
| **Gating Mechanism** | Manual approval or post-incident rollback | Rule-based multi-factor engine evaluating `error_rate`, `latency_ms`, `canary_error_rate`, and `error_budget` |
| **Decision States** | Binary Deploy / Abort | Three-tier: **ALLOW** (0–39), **PAUSE** (40–59), **BLOCK** (60+) |
| **Audit Traceability** | None (0% formal evidence) | 100% immutable JSON evidence reports logged to Supabase / PostgreSQL |

---

## 3. Comparative Benchmark Results

```
===================================================================================
                  BASELINE VS. INTERVENTION PERFORMANCE COMPARISON
===================================================================================
Metric                              | Baseline     | Intervention   | Target     | Status
------------------------------------+--------------+----------------+------------+---------
Harmful Release Stop Rate (Recall)  |    50.0%     |     100.0%     |   >= 80%   | PASS
Audit Evidence Generated            |     0.0%     |     100.0%     |    100%    | PASS
False Positive Block Rate           |     0.0%     |       0.0%     |   < 15%    | PASS
Precision                           |   100.0%     |     100.0%     |     -      | PASS
F1-Score                            |    66.7%     |     100.0%     |     -      | PASS
Overall Classification Accuracy     |    90.0%     |     100.0%     |     -      | PASS
===================================================================================
```

### 3.1 Confusion Matrix: Baseline System (Status Quo Coarse Gating)

| Actual \ Predicted | Predicted Healthy (ALLOW) | Predicted Harmful (BLOCK) |
| :--- | :---: | :---: |
| **Actual Healthy (80)** | **80 (True Negative)** | **0 (False Positive)** |
| **Actual Harmful (20)** | **10 (False Negative - ESCAPED)** | **10 (True Positive - STOPPED)** |

* **False Negatives (10):** 50% of harmful releases slipped directly into production under the status quo baseline because naive static gating only examined global error rate (>= 5.0%), completely missing canary divergence, latency spikes, and error budget depletion.
* **True Positives (10):** Only catastrophic error rate spikes (>5.0%) were caught.
* **Audit Evidence (0%):** Zero structured evidence records were generated.

### 3.2 Confusion Matrix: Intervention System (Pre-Release Risk Monitor)

| Actual \ Predicted | Predicted Healthy (ALLOW) | Predicted Harmful (PAUSE / BLOCK) |
| :--- | :---: | :---: |
| **Actual Healthy (80)** | **80 (True Negative)** | **0 (False Positive)** |
| **Actual Harmful (20)** | **0 (False Negative)** | **20 (True Positive)** |

* **True Positives (20):** 100% of harmful releases were safely intercepted in canary (scored between 60 and 100 points, triggering PAUSE or BLOCK).
* **False Negatives (0):** Zero harmful releases escaped to broad customer production (100% incident prevention).
* **True Negatives (80):** Healthy releases passed through with scores <= 39 points without impeding developer velocity.
* **False Positives (0):** No healthy releases were erroneously blocked.
* **Audit Evidence (100%):** 100 out of 100 change tickets produced complete, cryptographic evidence dossiers.

---

## 4. Edge-Case Validation & Robustness Analysis

### 4.1 Missing Telemetry Handling (Imputation)
When records omitted critical metrics (e.g., `error_rate` or `latency_ms`), the system triggered `impute_missing_values()`:
* Substituted safe median values derived from historical organizational performance.
* Emitted structured warnings (`"Imputed missing field: error_rate with median value"`) preserved directly in the audit record.

### 4.2 Noise & Spikes (Moving-Average Smoothing)
Transient telemetry spikes that would normally trigger false-positive blocks were successfully filtered by applying moving-average smoothing over historical windows, maintaining the False Positive Block Rate well below the 15% threshold.

### 4.3 Canary Degradation & Delayed Telemetry
* Where canary error rates deviated by >2% relative to baseline, the engine applied an immediate +25 point penalty.
* In scenarios where canary telemetry was delayed or unavailable, the system conservatively defaulted to **PAUSE**, preventing unmonitored promotion.

---

## 5. Conclusion & Verification

This experiment verifies end-to-end that the **Pre-Release Risk Monitor** satisfies all quantitative success criteria defined in Section 4 of the PRD:
1. **Harmful release stop rate surpasses the 80% target.**
2. **Evidence generation is 100% complete across all changes.**
3. **False positive rate is maintained well below 15%.**

To independently reproduce these experimental results, execute:
```powershell
python experiments/run_baseline_experiment.py
```
Detailed execution logs and per-ticket JSON records are persisted in [`data/experiment_results.json`](file:///c:/Users/rethi/OneDrive/เอกสาร/Desktop/coe%20project/data/experiment_results.json).
