# Product Requirements Document (PRD)

## Project Title

**Pre-Release Risk Monitor for Regulated Enterprise Deployments**

---

# 1. Project Overview

The **Pre-Release Risk Monitor** is a web-based application designed for regulated enterprises such as banks, healthcare providers, insurance companies, and government organizations. The system evaluates deployment risk before a release is rolled out to all customers. It combines deployment signals, health metrics, error budgets, and canary comparison results to recommend whether a release should be **Allowed, Paused, or Blocked**.

The solution is implemented using:

* **Frontend:** HTML, CSS, JavaScript
* **Backend:** Flask (Python)
* **Database:** PostgreSQL hosted on Supabase

The prototype works entirely with **synthetic or anonymized data** and stores audit evidence for every deployment decision.

---

# 2. Problem Statement

In many regulated enterprises, release failures are detected only after customers report issues. This creates customer impact, operational disruption, and compliance risk. The organization requires a proactive monitoring solution that can detect risky releases before broad production exposure and maintain evidence for audit purposes.

---

# 3. Objectives

## Primary Objective

Prevent harmful releases from reaching the majority of users by evaluating deployment risk during progressive rollout.

## Secondary Objectives

* Generate audit evidence for every production change.
* Support canary deployment validation.
* Handle missing and noisy monitoring data.
* Support multiple organizations and role-based access.
* Provide fallback behavior during monitoring outages.
* Measure the percentage of harmful releases stopped before broad exposure.

---

# 4. Success Criteria

| Metric                                         | Baseline     | Target     |
| ---------------------------------------------- | ------------ | ---------- |
| Harmful releases stopped before broad exposure | 20%          | 80%        |
| Evidence generated for deployments             | 0%           | 100%       |
| False positive block rate                      | Not measured | <15%       |
| Dashboard response time                        | -            | <2 seconds |

---

# 5. Target Users

| User Role          | Responsibility                            |
| ------------------ | ----------------------------------------- |
| Release Engineer   | Review deployment risk and rollout status |
| Compliance Officer | Review evidence and approval records      |
| SRE / Operations   | Monitor health metrics and alerts         |
| External Partner   | View partner-specific release status      |
| Auditor            | Access read-only deployment history       |

---

# 6. User Workflow

1. Release is deployed to canary environment.
2. Monitoring metrics are collected.
3. Backend calculates risk score.
4. Dashboard displays Allow / Pause / Block.
5. Evidence record is stored in PostgreSQL.
6. Authorized users approve or reject rollout continuation.

---

# 7. Technology Stack

## Frontend

* HTML5
* CSS3
* JavaScript (Vanilla JS)
* Fetch API for backend communication
* Chart.js for visualization

## Backend

* Flask
* Pandas for data processing
* SQLAlchemy or psycopg2 for PostgreSQL connectivity

## Database

* PostgreSQL on Supabase

---

# 8. Functional Requirements

## FR-1 Release Ingestion

The system shall accept deployment events containing release ID, organization, version, deployment stage, and timestamp.

## FR-2 Health Monitoring

The system shall process:

* Error rate
* Latency
* Availability
* CPU or memory usage (optional extension)

## FR-3 Canary Comparison

The system shall compare canary metrics against baseline production metrics.

## FR-4 Error Budget Evaluation

The system shall detect low remaining error budget conditions.

## FR-5 Risk Decision

The system shall return:

* ALLOW
* PAUSE
* BLOCK

## FR-6 Evidence Storage

The system shall store all deployment decisions in PostgreSQL with timestamps and reviewer information.

## FR-7 Role-Based Access

The system shall restrict visible data based on organization and role.

## FR-8 Offline Queue

The system shall temporarily store events locally when the backend is unavailable and synchronize them later.

---

# 9. Non-Functional Requirements

| Requirement     | Target                         |
| --------------- | ------------------------------ |
| Availability    | 99% during demonstration       |
| Scalability     | Support multiple organizations |
| Security        | Role-based access control      |
| Auditability    | Immutable deployment evidence  |
| Privacy         | No PII stored                  |
| Maintainability | Modular Flask codebase         |

---

# 10. System Architecture

```text
HTML/CSS/JS Dashboard
        |
        | HTTP / Fetch API
        v
Flask Backend (Risk Engine)
        |
        | SQLAlchemy / psycopg2
        v
Supabase PostgreSQL
```

Data flow:

**Deployment Event → Flask API → Risk Engine → PostgreSQL → Dashboard**

---

# 11. Database Design (Supabase PostgreSQL)

## Table: organizations

| Column | Type |
| ------ | ---- |
| id     | UUID |
| name   | TEXT |

## Table: users

| Column | Type |
| ------ | ---- |
| id     | UUID |
| name   | TEXT |
| role   | TEXT |
| org_id | UUID |

## Table: releases

| Column      | Type      |
| ----------- | --------- |
| id          | UUID      |
| release_id  | TEXT      |
| org_id      | UUID      |
| version     | TEXT      |
| deployed_at | TIMESTAMP |

## Table: deployment_metrics

| Column                 | Type      |
| ---------------------- | --------- |
| id                     | UUID      |
| release_id             | UUID      |
| error_rate             | NUMERIC   |
| latency_ms             | INTEGER   |
| availability           | NUMERIC   |
| error_budget_remaining | NUMERIC   |
| canary_error_rate      | NUMERIC   |
| canary_latency_delta   | INTEGER   |
| created_at             | TIMESTAMP |

## Table: risk_decisions

| Column     | Type      |
| ---------- | --------- |
| id         | UUID      |
| release_id | UUID      |
| risk_score | INTEGER   |
| decision   | TEXT      |
| reasons    | TEXT      |
| decided_at | TIMESTAMP |

---

# 12. API Design

## POST /api/release

Create a release event.

Request:

```json
{
  "release_id": "R002",
  "org": "BankA",
  "version": "2.3.2"
}
```

## POST /api/metrics

Submit deployment metrics.

## GET /api/dashboard

Return dashboard summary.

## GET /api/report/<release_id>

Return evidence report.

---

# 13. Risk Scoring Logic

Example rule-based scoring:

| Condition                    | Score |
| ---------------------------- | ----- |
| error_rate > 3%              | +40   |
| latency_ms > 500             | +25   |
| canary_error_rate > 2%       | +25   |
| error_budget_remaining < 20% | +10   |

Decision thresholds:

* 0–39 → ALLOW
* 40–59 → PAUSE
* 60+ → BLOCK

---

# 14. Data Preparation

* Use synthetic CSV data for initial loading.
* Replace missing numeric values with median values.
* Remove impossible values (e.g., availability > 100).
* Apply moving-average smoothing to noisy metrics.

---

# 15. Edge and Failure Cases

## Case 1: Missing Metric

Expected behavior: Use statistical imputation and show data-quality warning.

## Case 2: Temporary Error Spike

Expected behavior: Use smoothed values before alert generation.

## Case 3: Delayed Canary Result

Expected behavior: Set release state to **PAUSE**.

## Case 4: Backend Unavailable

Expected behavior: Store event in browser localStorage and retry synchronization.

---

# 16. Security and Privacy

* No customer personal data is stored.
* User identifiers are anonymized where applicable.
* Access is controlled by role and organization.
* Supabase Row Level Security (RLS) can be enabled for organization isolation.
* All demo data is synthetic.

---

# 17. Evaluation Plan

## Dataset

100 synthetic deployment records.

## Experiment

Run the risk engine against known harmful releases.

## Metrics

* Harmful releases blocked
* False positives
* False negatives
* Precision
* Recall
* Stop rate before broad exposure

Example:

| Metric                   | Value |
| ------------------------ | ----- |
| Total releases           | 100   |
| Harmful releases         | 20    |
| Harmful releases blocked | 17    |
| Stop rate                | 85%   |

---

# 18. UI Screens

* Login / role selection
* Release dashboard
* Risk detail page
* Evidence report page
* Organization-specific view
* Audit history page

---

# 19. Deliverables

* Flask source code
* HTML/CSS/JS frontend
* Supabase PostgreSQL schema
* Synthetic dataset
* README with setup instructions
* Test cases
* Evaluation report
* Demo video

---

# 20. Future Enhancements

* GitHub Actions or Jenkins integration
* Real-time WebSocket monitoring
* Machine-learning anomaly detection
* Automated rollback trigger
* Email or Slack notifications
* Digital signatures for audit evidence

---

# 21. Conclusion

This project delivers a practical, auditable, and privacy-preserving pre-release monitoring system for regulated enterprises. By combining deployment signals, health metrics, error budgets, and canary validation, the system helps organizations identify risky releases before broad customer exposure while maintaining evidence suitable for compliance and audit review.
