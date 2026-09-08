-- ============================================================
-- Pre-Release Risk Monitor — Database Schema
-- Target: Supabase PostgreSQL
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. Organizations
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE
);

-- ============================================================
-- 2. Users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN (
                      'release_engineer',
                      'compliance_officer',
                      'sre',
                      'external_partner',
                      'auditor'
                  )),
    org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_users_role   ON users(role);

-- ============================================================
-- 3. Releases
-- ============================================================
CREATE TABLE IF NOT EXISTS releases (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    release_id  TEXT NOT NULL,
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    version     TEXT NOT NULL,
    stage       TEXT NOT NULL DEFAULT 'canary' CHECK (stage IN ('canary', 'staged', 'production')),
    deployed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_releases_org_id     ON releases(org_id);
CREATE INDEX IF NOT EXISTS idx_releases_release_id ON releases(release_id);

-- ============================================================
-- 4. Deployment Metrics
-- ============================================================
CREATE TABLE IF NOT EXISTS deployment_metrics (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    release_id             UUID NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    error_rate             NUMERIC(6,3),
    latency_ms             INTEGER,
    availability           NUMERIC(6,3),
    error_budget_remaining NUMERIC(6,3),
    canary_error_rate      NUMERIC(6,3),
    canary_latency_delta   INTEGER,
    cpu_usage              NUMERIC(5,2),
    memory_usage           NUMERIC(5,2),
    created_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_release_id ON deployment_metrics(release_id);

-- ============================================================
-- 5. Risk Decisions
-- ============================================================
CREATE TABLE IF NOT EXISTS risk_decisions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    release_id  UUID NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    risk_score  INTEGER NOT NULL,
    decision    TEXT NOT NULL CHECK (decision IN ('ALLOW', 'PAUSE', 'BLOCK')),
    reasons     TEXT,
    reviewer    TEXT,
    decided_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_release_id ON risk_decisions(release_id);
CREATE INDEX IF NOT EXISTS idx_decisions_decision   ON risk_decisions(decision);

-- ============================================================
-- Seed Organizations
-- ============================================================
INSERT INTO organizations (name) VALUES
    ('BankA'),
    ('HealthCo'),
    ('GovAgency')
ON CONFLICT (name) DO NOTHING;
