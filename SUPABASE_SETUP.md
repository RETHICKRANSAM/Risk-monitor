# Supabase Integration & Setup Guide

## 📌 Project Overview
This guide covers the integration between the **Pre-Release Risk Monitor for Regulated Enterprise Deployments** and **Supabase (PostgreSQL)**.

---

## 🔑 Obtaining Your Live Supabase Credentials

### Step 1: Go to Supabase Dashboard
1. Visit: [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Log in and select (or create) your project.

### Step 2: Get API Keys & Project URL
1. Click on **Project Settings** (gear icon in the sidebar) ➔ **API**.
2. Find the **Project URL**:
   - Format: `https://<YOUR-PROJECT-ID>.supabase.co`
3. Find the **Project API keys**:
   - Copy the **`anon` / `public`** key (starts with `eyJhbGciOi...`).
   - *(Note: Do NOT use the `service_role` key for regular application traffic).*

### Step 3: Configure `.env`
Update your local `.env` file with your active credentials:

```env
# Supabase API Configuration
SUPABASE_URL=https://<YOUR-PROJECT-ID>.supabase.co
SUPABASE_KEY=eyJhbGciOi... (your full anon key here)

# Direct PostgreSQL Connection URI (from Project Settings -> Database)
# DATABASE_URL=postgresql://postgres:<YOUR_PASSWORD>@db.<YOUR-PROJECT-ID>.supabase.co:5432/postgres?sslmode=require
DATABASE_URL=sqlite:///local_fallback.db
```

---

## 🧪 Testing Connection & Diagnostics

Run the built-in diagnostic test:

```powershell
python test_supabase_connection.py
```

The test validates:
1. Environment variables exist in `.env`.
2. URL format and HTTPS protocol.
3. Hostname DNS resolution.
4. TCP/TLS connectivity on port 443.
5. Supabase client initialization.
6. Safe query execution using the `anon` key against the `organizations` table.

---

## 🗄️ Database Schema & Migrations

The single source of truth for the database schema is [`database/schema.sql`](database/schema.sql).

### Applying the Schema to Supabase:
1. Open your project in the [Supabase Dashboard](https://supabase.com/dashboard).
2. Click on **SQL Editor** in the left sidebar.
3. Click **New query**.
4. Copy and paste the contents of [`database/schema.sql`](database/schema.sql).
5. Click **Run**.

### Core Tables Created:
* **`organizations`**: Multi-tenant organizations (`BankA`, `HealthCo`, `GovAgency`).
* **`users`**: Role-based access control (`release_engineer`, `compliance_officer`, `sre`, `auditor`).
* **`releases`**: Deployment records, versions, and rollout stages.
* **`deployment_metrics`**: Telemetry data (error rate, latency, canary delta, error budget).
* **`risk_decisions`**: Gating outcomes (`ALLOW`, `PAUSE`, `BLOCK`) with audit trails.

---

## 📝 Code Examples (Pre-Release Risk Monitor)

### Querying Organizations
```python
from supabase_client import get_supabase_client

supabase = get_supabase_client()
response = supabase.table("organizations").select("*").execute()
organizations = response.data
```

### Querying Recent Releases
```python
from supabase_client import get_supabase_client

supabase = get_supabase_client()
response = (
    supabase.table("releases")
    .select("release_id, version, stage, deployed_at")
    .order("deployed_at", desc=True)
    .limit(10)
    .execute()
)
releases = response.data
```

### Inserting a Risk Decision
```python
from supabase_client import insert_data

record = insert_data(
    "risk_decisions",
    {
        "release_id": release_uuid,
        "risk_score": 25,
        "decision": "ALLOW",
        "reasons": "Canary delta stable; error budget > 90%",
        "reviewer": "system_auto",
    },
)
```

---

## 🆘 Troubleshooting Common Issues

### 1. `[Errno 11001] getaddrinfo failed` (DNS Resolution Error)
* **Root Cause**: The hostname configured in `SUPABASE_URL` does not exist on the public internet.
* **Why it happens**:
  - Free-tier Supabase projects are automatically paused after 7 days of inactivity.
  - The project was deleted or replaced with a new one.
* **Fix**:
  1. Go to [supabase.com/dashboard](https://supabase.com/dashboard).
  2. If the project is paused, click **Restore project** / **Unpause**.
  3. If you created a new project, copy the new Project URL from **Settings → API** and update `SUPABASE_URL` in `.env`.

### 2. `Authentication rejected (HTTP 401)`
* **Root Cause**: The `SUPABASE_KEY` does not match the project in `SUPABASE_URL`.
* **Fix**: Copy the **`anon` / `public`** key from the active project's **Settings → API** page.

### 3. `relation "organizations" does not exist` (PGRST200)
* **Root Cause**: Connection is successful, but the tables have not been created yet.
* **Fix**: Run [`database/schema.sql`](database/schema.sql) in the Supabase SQL Editor.
