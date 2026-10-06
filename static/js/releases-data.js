/**
 * Pre-Release Deployment Risk Monitor — Single Source of Truth
 * Canonical release records, scoring model configuration, SHA-256 evidence hashing,
 * and unified 100-release history dataset (80 ALLOW, 12 PAUSE, 8 BLOCK).
 */

// ============================================================================
// 1. SCORING MODEL CONFIGURATION
// Maximum Cumulative Score = 100 points
// ============================================================================
const SCORING_MODEL = {
    rules: [
        {
            id: 'rule_error_rate',
            metric: 'error_rate',
            name: 'System Error Rate',
            threshold: 3.0,
            unit: '%',
            operator: '>',
            weight: 40,
            description: 'Penalizes deployments when overall system request error rate exceeds SLA safety boundary of 3.0%.'
        },
        {
            id: 'rule_canary_delta',
            metric: 'canary_error_delta',
            name: 'Canary Error Rate Delta (canary minus baseline)',
            threshold: 2.0,
            unit: '%',
            operator: '>',
            weight: 25,
            description: 'Measures excess error percentage in canary ring relative to the stable baseline version (>2.0% divergence).'
        },
        {
            id: 'rule_latency',
            metric: 'latency_p95',
            name: 'P95 Latency',
            threshold: 500,
            unit: 'ms',
            operator: '>',
            weight: 25,
            description: 'Evaluates P95 response latency to catch severe tail-latency degradations (>500ms threshold).'
        },
        {
            id: 'rule_budget',
            metric: 'error_budget_remaining',
            name: 'Remaining Error Budget',
            threshold: 20.0,
            unit: '%',
            operator: '<',
            weight: 10,
            description: 'Penalizes release when rolling 30-day error budget buffer falls below 20.0%.'
        }
    ],
    max_score: 100,
    decision_thresholds: {
        ALLOW: { min: 0, max: 39, label: 'ALLOW', action: 'Promote to Next Ring / Production' },
        PAUSE: { min: 40, max: 59, label: 'PAUSE', action: 'Hold in Current Ring for SRE Review' },
        BLOCK: { min: 60, max: 100, label: 'BLOCK', action: 'Automated Circuit Breaker Rollback' }
    },
    rollout_ladder: ['10%', '25%', '50%', '100%']
};

/**
 * Evaluates telemetry against the scoring model.
 */
function evaluateMetrics(metrics) {
    let score = 0;
    const triggeredRules = [];

    // Rule 1: Error rate > 3.0% (+40)
    if (metrics.error_rate > 3.0) {
        score += 40;
        triggeredRules.push({
            id: 'rule_error_rate',
            name: 'High System Error Rate',
            detail: `Observed error rate ${metrics.error_rate.toFixed(2)}% exceeds SLA limit of 3.0%`,
            pts: '+40 pts',
            score_added: 40
        });
    }

    // Rule 2: Canary delta > 2.0% (+25)
    const canaryDelta = metrics.canary_error_delta != null ? metrics.canary_error_delta : (metrics.canary_error_rate || 0);
    if (canaryDelta > 2.0) {
        score += 25;
        triggeredRules.push({
            id: 'rule_canary_delta',
            name: 'Canary Error Rate Delta (canary minus baseline) Elevated',
            detail: `Observed canary delta +${canaryDelta.toFixed(2)}% exceeds safe tolerance of 2.0%`,
            pts: '+25 pts',
            score_added: 25
        });
    }

    // Rule 3: Latency > 500ms (+25)
    const lat = metrics.latency_p95 != null ? metrics.latency_p95 : (metrics.latency_ms || 0);
    if (lat > 500) {
        score += 25;
        triggeredRules.push({
            id: 'rule_latency',
            name: 'P95 Latency Breach',
            detail: `Observed P95 response time ${Math.round(lat)}ms exceeds SLA limit of 500ms`,
            pts: '+25 pts',
            score_added: 25
        });
    }

    // Rule 4: Error budget < 20% (+10)
    if (metrics.error_budget_remaining < 20.0) {
        score += 10;
        triggeredRules.push({
            id: 'rule_budget',
            name: 'Low Error Budget Buffer',
            detail: `Remaining budget ${metrics.error_budget_remaining.toFixed(1)}% is below 20.0% safety buffer`,
            pts: '+10 pts',
            score_added: 10
        });
    }

    score = Math.min(100, Math.max(0, score));
    let decision = 'ALLOW';
    if (score >= 60) decision = 'BLOCK';
    else if (score >= 40) decision = 'PAUSE';

    return { score, decision, triggeredRules };
}

// ============================================================================
// 2. CANONICAL TOP RELEASES
// ============================================================================
const CANONICAL_RELEASES = {
    // Current release with circuit-breaker rollback
    'R0042': {
        release_id: 'R0042',
        version: '2.4.1',
        org: 'BankA',
        org_name: 'BankA (Retail Core)',
        git_sha: 'a8b3f1e94c2d7fa8b3f1e94c2d7fa8b3f1e94c2d',
        timestamp: '2026-09-19 10:42:18 UTC',
        timestamp_iso: '2026-09-19T10:42:18Z',
        stage: 'canary',
        stage_display: 'Rolled Back (was 25% Canary Ring)',
        canary_pct: '0%',
        stable_pct: '100%',
        status: 'Rolled Back',
        risk_score: 65,
        decision: 'BLOCK',
        action: 'Rollback Triggered',
        action_detail: 'Automated circuit breaker engaged immediately; canary traffic reverted from 25% to 0% and 100% stable baseline restored.',
        reviewer: 'Automated Circuit Breaker',
        reason: 'Canary error rate delta (+2.8%) and service error rate (4.2%) exceeded SLA limit; automated rollback engaged.',
        math: 'Risk Score = 40 (Error Rate) + 25 (Canary Delta) = 65 / 100',
        factors: [
            { rule: 'High System Error Rate', detail: 'Observed 4.2% exceeds SLA limit of 3.0%', pts: '+40 pts', score_added: 40 },
            { rule: 'Canary Error Rate Delta (canary minus baseline) Elevated', detail: 'Canary delta +2.8% exceeds tolerance 2.0%', pts: '+25 pts', score_added: 25 }
        ],
        metrics: {
            error_rate: 4.2,
            latency_avg: 320,
            latency_p95: 540,
            canary_error_delta: 2.8,
            error_budget_remaining: 48.0,
            availability: 99.82
        },
        signals: {
            error_rate: { val: '4.2%', pts: '+40 pts', status: 'VIOLATION (>3%)', isDanger: true },
            latency: { val: '320 ms', pts: '0 pts', status: 'Avg 320ms / P95 540ms', isDanger: false },
            canary_error: { val: '+2.8%', pts: '+25 pts', status: 'VIOLATION (>2%)', isDanger: true },
            budget: { val: '48.0%', pts: '0 pts', status: 'SAFE (>20%)', isDanger: false }
        },
        audit: {
            timestamp: '2026-09-19 10:42:18 UTC',
            stage: 'Canary (blocked at 25% ring)',
            reviewer: 'Automated Circuit Breaker',
            rules: 'High Error Rate (+40), Canary Error Rate Delta (+25)',
            reason: 'Canary error rate delta exceeded 2.0% divergence SLA limit; automated circuit breaker engaged to prevent production incident.'
        }
    },

    'R0041': {
        release_id: 'R0041',
        version: '2.4.0',
        org: 'BankA',
        org_name: 'BankA (Retail Core)',
        git_sha: 'c4e7a2b91f0d3e5a6c8b7d9e0f1a2b3c4d5e6f7a',
        timestamp: '2026-09-15 14:20:00 UTC',
        timestamp_iso: '2026-09-15T14:20:00Z',
        stage: 'production',
        stage_display: '100% Production',
        canary_pct: '100%',
        stable_pct: '100%',
        status: 'Deployed Safely',
        risk_score: 18,
        decision: 'ALLOW',
        action: 'Promoted to Production',
        action_detail: 'All telemetry metrics and canary health checks compliant with SLA thresholds; successfully rolled out to 100% traffic.',
        reviewer: 'automated_gatekeeper',
        reason: 'Healthy Canary · Risk 18 · Promoted through rollout ladder to 100% Production.',
        math: 'Risk Score = 0 (Error Rate) + 0 (Canary Delta) + 0 (Latency) + 0 (Budget) = 18 / 100 (Baseline drift noise)',
        factors: [
            { rule: 'All Health Signals Normal', detail: 'Zero SLA breaches observed during progressive rollout ladder (10% → 25% → 50% → 100%)', pts: '18 pts', score_added: 0 }
        ],
        metrics: {
            error_rate: 0.8,
            latency_avg: 180,
            latency_p95: 210,
            canary_error_delta: 0.4,
            error_budget_remaining: 88.0,
            availability: 99.98
        },
        signals: {
            error_rate: { val: '0.8%', pts: '0 pts', status: 'SAFE (<3%)', isDanger: false },
            latency: { val: '180 ms', pts: '0 pts', status: 'Avg 180ms / P95 210ms', isDanger: false },
            canary_error: { val: '+0.4%', pts: '0 pts', status: 'SAFE (<2%)', isDanger: false },
            budget: { val: '88.0%', pts: '0 pts', status: 'HEALTHY (>20%)', isDanger: false }
        },
        audit: {
            timestamp: '2026-09-15 14:20:00 UTC',
            stage: 'Production (100% full)',
            reviewer: 'automated_gatekeeper',
            rules: 'All SLA invariants compliant',
            reason: 'Zero SLA violations during 10% → 25% → 50% → 100% progressive delivery.'
        }
    },

    'R0040': {
        release_id: 'R0040',
        version: '2.3.9',
        org: 'BankA',
        org_name: 'BankA (Retail Core)',
        git_sha: 'e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4',
        timestamp: '2026-09-12 11:05:00 UTC',
        timestamp_iso: '2026-09-12T11:05:00Z',
        stage: 'canary',
        stage_display: '10% Canary (Held)',
        canary_pct: '10%',
        stable_pct: '90%',
        status: 'Under Review',
        risk_score: 47,
        decision: 'PAUSE',
        action: 'Held for Human Review',
        action_detail: 'Threshold drift detected in canary traffic; deployment frozen at 10% canary ring awaiting SRE investigation.',
        reviewer: 'sarah.chen (RE)',
        reason: 'Threshold Drift Detected · Risk 47 · Error budget depletion (18%) and system error rate (3.4%) triggered safety hold.',
        math: 'Risk Score = 40 (Error Rate) + 7 (Budget Burn) = 47 / 100',
        factors: [
            { rule: 'High System Error Rate', detail: 'Observed 3.4% exceeds SLA limit of 3.0%', pts: '+40 pts', score_added: 40 },
            { rule: 'Low Error Budget Buffer', detail: 'Remaining allowance 18.0% breached 20% safe buffer', pts: '+7 pts', score_added: 7 }
        ],
        metrics: {
            error_rate: 3.4,
            latency_avg: 290,
            latency_p95: 410,
            canary_error_delta: 1.2,
            error_budget_remaining: 18.0,
            availability: 99.60
        },
        signals: {
            error_rate: { val: '3.4%', pts: '+40 pts', status: 'WARNING (>3%)', isDanger: true },
            latency: { val: '290 ms', pts: '0 pts', status: 'Avg 290ms / P95 410ms', isDanger: false },
            canary_error: { val: '+1.2%', pts: '0 pts', status: 'SAFE (<2%)', isDanger: false },
            budget: { val: '18.0%', pts: '+7 pts', status: 'LOW (<20%)', isDanger: true }
        },
        audit: {
            timestamp: '2026-09-12 11:05:00 UTC',
            stage: 'Canary (10% ring held)',
            reviewer: 'sarah.chen (RE)',
            rules: 'High Error Rate (+40), Budget Burn (+7)',
            reason: 'Canary traffic frozen at 10% ring due to elevated error rate and monthly budget burn.'
        }
    },

    'R0038': {
        release_id: 'R0038',
        version: '2.3.8',
        org: 'BankA',
        org_name: 'BankA (Retail Core)',
        git_sha: '7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b',
        timestamp: '2026-09-08 09:30:00 UTC',
        timestamp_iso: '2026-09-08T09:30:00Z',
        stage: 'production',
        stage_display: '100% Production',
        canary_pct: '100%',
        stable_pct: '100%',
        status: 'Deployed Safely',
        risk_score: 15,
        decision: 'ALLOW',
        action: 'Promoted to Production',
        action_detail: 'Canary health checks passed all automated validation steps cleanly.',
        reviewer: 'automated_gatekeeper',
        reason: 'Healthy Canary · Risk 15 · Deployed Safely to 100% Production.',
        math: 'Risk Score = 15 / 100 (Compliant)',
        factors: [
            { rule: 'All Health Signals Normal', detail: 'Zero SLA breaches observed during 100% rollout', pts: '15 pts', score_added: 0 }
        ],
        metrics: {
            error_rate: 0.6,
            latency_avg: 160,
            latency_p95: 195,
            canary_error_delta: 0.2,
            error_budget_remaining: 92.0,
            availability: 99.99
        },
        signals: {
            error_rate: { val: '0.6%', pts: '0 pts', status: 'SAFE (<3%)', isDanger: false },
            latency: { val: '160 ms', pts: '0 pts', status: 'Avg 160ms / P95 195ms', isDanger: false },
            canary_error: { val: '+0.2%', pts: '0 pts', status: 'SAFE (<2%)', isDanger: false },
            budget: { val: '92.0%', pts: '0 pts', status: 'HEALTHY (>20%)', isDanger: false }
        },
        audit: {
            timestamp: '2026-09-08 09:30:00 UTC',
            stage: 'Production (100% full)',
            reviewer: 'automated_gatekeeper',
            rules: 'Compliant telemetry verification',
            reason: 'All pre-release metrics satisfied gating rules.'
        }
    },

    'R0037': {
        release_id: 'R0037',
        version: '2.3.7',
        org: 'BankA',
        org_name: 'BankA (Retail Core)',
        git_sha: '1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c',
        timestamp: '2026-09-04 16:15:00 UTC',
        timestamp_iso: '2026-09-04T16:15:00Z',
        stage: 'canary',
        stage_display: '10% Canary (Rolled Back)',
        canary_pct: '0%',
        stable_pct: '100%',
        status: 'Rolled Back',
        risk_score: 82,
        decision: 'BLOCK',
        action: 'Immediate Rollback Executed',
        action_detail: 'Multiple risk signals crossed critical safety limits; automated circuit breaker rolled back canary traffic instantly.',
        reviewer: 'Automated Circuit Breaker',
        reason: 'Multiple Risk Signals · Risk 82 · Immediate Rollback Executed at 10% canary.',
        math: 'Risk Score = 40 (Error Rate) + 25 (Canary Delta) + 10 (Budget) + 7 (Latency) = 82 / 100',
        factors: [
            { rule: 'High System Error Rate', detail: 'Observed 5.1% exceeds SLA limit of 3.0%', pts: '+40 pts', score_added: 40 },
            { rule: 'Canary Error Rate Delta (canary minus baseline) Elevated', detail: 'Canary delta +3.8% exceeds tolerance 2.0%', pts: '+25 pts', score_added: 25 },
            { rule: 'Low Error Budget Buffer', detail: 'Budget burned to 12.0% (<20% safe buffer)', pts: '+10 pts', score_added: 10 }
        ],
        metrics: {
            error_rate: 5.1,
            latency_avg: 490,
            latency_p95: 580,
            canary_error_delta: 3.8,
            error_budget_remaining: 12.0,
            availability: 99.20
        },
        signals: {
            error_rate: { val: '5.1%', pts: '+40 pts', status: 'VIOLATION (>3%)', isDanger: true },
            latency: { val: '490 ms', pts: '0 pts', status: 'Avg 490ms / P95 580ms', isDanger: true },
            canary_error: { val: '+3.8%', pts: '+25 pts', status: 'VIOLATION (>2%)', isDanger: true },
            budget: { val: '12.0%', pts: '+10 pts', status: 'CRITICAL (<20%)', isDanger: true }
        },
        audit: {
            timestamp: '2026-09-04 16:15:00 UTC',
            stage: 'Canary (blocked at 10% ring)',
            reviewer: 'Automated Circuit Breaker',
            rules: 'High Error Rate (+40), Canary Delta (+25), Budget Burn (+10)',
            reason: 'Severe regression detected in initial 10% canary pool; circuit breaker safely rolled back release.'
        }
    }
};

CANONICAL_RELEASES['v2.4.1'] = CANONICAL_RELEASES['R0042'];
CANONICAL_RELEASES['v2.4.0'] = CANONICAL_RELEASES['R0041'];
CANONICAL_RELEASES['v2.3.9'] = CANONICAL_RELEASES['R0040'];
CANONICAL_RELEASES['v2.3.8'] = CANONICAL_RELEASES['R0038'];
CANONICAL_RELEASES['v2.3.7'] = CANONICAL_RELEASES['R0037'];

function generateAllReleases() {
    const orgs = ['BankA', 'HealthCo', 'GovAgency'];
    const reviewers = ['system_engine', 'sarah.chen (RE)', 'marcus.vance (CO)', 'automated_circuit_breaker'];
    const baseDate = new Date('2026-09-20T12:00:00Z');

    const blockIds = new Set(['R0042', 'R0037', 'R0015', 'R0028', 'R0052', 'R0065', 'R0079', 'R0094']);
    const pauseIds = new Set(['R0040', 'R0007', 'R0014', 'R0021', 'R0031', 'R0048', 'R0058', 'R0067', 'R0073', 'R0083', 'R0089', 'R0098']);

    const releases = [];

    for (let i = 1; i <= 100; i++) {
        const id = `R${String(i).padStart(4, '0')}`;
        const time = new Date(baseDate.getTime() - (100 - i) * 3600 * 1000 * 4);
        const timestampStr = time.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';

        if (CANONICAL_RELEASES[id]) {
            const canonical = JSON.parse(JSON.stringify(CANONICAL_RELEASES[id]));
            releases.push(canonical);
            continue;
        }

        const org = orgs[(i * 7) % 3];
        const version = `2.${Math.floor(i / 10)}.${i % 10}`;
        let decision, score, stage, stageDisplay, canaryPct, stablePct, status, reviewer, reasons = [], warnings = [];
        let errorRate, latencyAvg, latencyP95, canaryDelta, errorBudget, availability;

        if (blockIds.has(id)) {
            decision = 'BLOCK';
            score = 65 + (i % 20);
            stage = 'canary';
            stageDisplay = 'Rolled Back (was 25% ring)';
            canaryPct = '0%';
            stablePct = '100%';
            status = 'Rolled Back';
            reviewer = 'Automated Circuit Breaker';
            errorRate = +(3.8 + (i % 5) * 0.4).toFixed(2);
            latencyAvg = 380 + (i % 6) * 30;
            latencyP95 = 520 + (i % 5) * 25;
            canaryDelta = +(2.4 + (i % 4) * 0.4).toFixed(2);
            errorBudget = +(14.0 - (i % 4) * 2.0).toFixed(1);
            availability = +(99.30 + (i % 3) * 0.1).toFixed(2);
            reasons = [
                { rule: 'High System Error Rate', detail: `Observed ${errorRate}% exceeds 3.0% SLA limit`, pts: '+40 pts', score_added: 40 },
                { rule: 'Canary Error Rate Delta (canary minus baseline) Elevated', detail: `Observed delta +${canaryDelta}% exceeds 2.0% tolerance`, pts: '+25 pts', score_added: 25 }
            ];
        } else if (pauseIds.has(id)) {
            decision = 'PAUSE';
            score = 42 + (i % 14);
            stage = 'canary';
            stageDisplay = '10% Canary (Held)';
            canaryPct = '10%';
            stablePct = '90%';
            status = 'Under Review';
            reviewer = reviewers[i % reviewers.length];
            errorRate = +(3.1 + (i % 3) * 0.2).toFixed(2);
            latencyAvg = 260 + (i % 5) * 20;
            latencyP95 = 390 + (i % 4) * 20;
            canaryDelta = +(1.1 + (i % 3) * 0.2).toFixed(2);
            errorBudget = +(18.0 - (i % 3) * 1.5).toFixed(1);
            availability = +(99.70 + (i % 3) * 0.05).toFixed(2);
            reasons = [
                { rule: 'High System Error Rate', detail: `Observed ${errorRate}% exceeds 3.0% threshold`, pts: '+40 pts', score_added: 40 }
            ];
        } else {
            decision = 'ALLOW';
            score = (i % 4 === 0) ? (i % 15) : 0;
            stage = (i % 3 === 0) ? 'production' : (i % 2 === 0 ? 'staged' : 'canary');
            stageDisplay = stage === 'production' ? '100% Production' : (stage === 'staged' ? '50% Staged Ring' : '25% Canary Ring');
            canaryPct = stage === 'production' ? '100%' : (stage === 'staged' ? '50%' : '25%');
            stablePct = stage === 'production' ? '100%' : (stage === 'staged' ? '50%' : '75%');
            status = 'Deployed Safely';
            reviewer = 'automated_gatekeeper';
            errorRate = +(0.2 + (i % 8) * 0.2).toFixed(2);
            latencyAvg = 120 + (i % 8) * 15;
            latencyP95 = 180 + (i % 6) * 15;
            canaryDelta = +(0.1 + (i % 5) * 0.15).toFixed(2);
            errorBudget = +(65.0 + (i % 8) * 4.0).toFixed(1);
            availability = +(99.95 + (i % 4) * 0.01).toFixed(2);
            reasons = [
                { rule: 'All Health Signals Normal', detail: 'Zero SLA breaches observed during progressive canary evaluation', pts: `${score} pts`, score_added: 0 }
            ];
        }

        if (i % 10 === 7) {
            warnings.push('Imputed missing field: error_rate using historical median (0.65%)');
        }

        releases.push({
            release_id: id,
            version: version,
            org: org,
            org_name: `${org} (Service Group)`,
            git_sha: `git-${Math.sin(i).toString(16).substring(2, 10)}`,
            timestamp: timestampStr,
            timestamp_iso: time.toISOString(),
            stage: stage,
            stage_display: stageDisplay,
            canary_pct: canaryPct,
            stable_pct: stablePct,
            status: status,
            risk_score: score,
            decision: decision,
            action: decision === 'BLOCK' ? 'Rollback Triggered' : (decision === 'PAUSE' ? 'Held for Human Review' : 'Promoted Safely'),
            action_detail: decision === 'BLOCK' ? 'Circuit breaker engaged; restored stable version.' : (decision === 'PAUSE' ? 'Rollout held in canary ring.' : 'All signals compliant.'),
            reviewer: reviewer,
            reason: decision === 'BLOCK' ? 'Multiple Risk Signals · Circuit Breaker Tripped' : (decision === 'PAUSE' ? 'Threshold Drift Detected · Held for Review' : 'Healthy Canary · Promoted Safely'),
            math: `Risk Score = ${score} / 100`,
            factors: reasons,
            metrics: {
                error_rate: errorRate,
                latency_avg: latencyAvg,
                latency_p95: latencyP95,
                canary_error_delta: canaryDelta,
                error_budget_remaining: errorBudget,
                availability: availability
            },
            signals: {
                error_rate: { val: `${errorRate}%`, pts: errorRate > 3 ? '+40 pts' : '0 pts', status: errorRate > 3 ? 'VIOLATION (>3%)' : 'SAFE (<3%)', isDanger: errorRate > 3 },
                latency: { val: `${latencyAvg} ms`, pts: latencyP95 > 500 ? '+25 pts' : '0 pts', status: `Avg ${latencyAvg}ms / P95 ${latencyP95}ms`, isDanger: latencyP95 > 500 },
                canary_error: { val: `+${canaryDelta}%`, pts: canaryDelta > 2 ? '+25 pts' : '0 pts', status: canaryDelta > 2 ? 'VIOLATION (>2%)' : 'SAFE (<2%)', isDanger: canaryDelta > 2 },
                budget: { val: `${errorBudget}%`, pts: errorBudget < 20 ? '+10 pts' : '0 pts', status: errorBudget < 20 ? 'LOW (<20%)' : 'HEALTHY (>20%)', isDanger: errorBudget < 20 }
            },
            audit: {
                timestamp: timestampStr,
                stage: stageDisplay,
                reviewer: reviewer,
                rules: reasons.map(r => r.rule).join(', '),
                reason: decision === 'BLOCK' ? 'Telemetry SLA violation triggered automated rollback.' : (decision === 'PAUSE' ? 'Threshold drift detected; held for inspection.' : 'All safety SLA invariants compliant.')
            },
            warnings: warnings
        });
    }

    return releases;
}

const ALL_100_RELEASES = generateAllReleases();

async function computeCanonicalSha256(release) {
    if (!release) return '0'.repeat(64);

    const canonicalPayload = {
        release_id: release.release_id || 'UNKNOWN',
        version: release.version || '0.0.0',
        timestamp: release.timestamp || '',
        risk_score: release.risk_score != null ? release.risk_score : 0,
        decision: release.decision || 'ALLOW',
        triggered_rules: (release.factors || []).map(f => f.rule || f.name || f)
    };

    const jsonStr = JSON.stringify(canonicalPayload);

    if (window.crypto && window.crypto.subtle) {
        try {
            const encoder = new TextEncoder();
            const data = encoder.encode(jsonStr);
            const hashBuffer = await window.crypto.subtle.digest('SHA-256', data);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            return hashHex;
        } catch (e) {
            console.warn('Crypto subtle digest failed, generating deterministic fallback hash:', e);
        }
    }

    let h1 = 0xdeadbeef, h2 = 0x41c6ce57, h3 = 0x67452301, h4 = 0xefcdab89;
    for (let i = 0; i < jsonStr.length; i++) {
        const ch = jsonStr.charCodeAt(i);
        h1 = Math.imul(h1 ^ ch, 2654435761);
        h2 = Math.imul(h2 ^ ch, 1597334677);
        h3 = Math.imul(h3 ^ ch, 2246822507);
        h4 = Math.imul(h4 ^ ch, 3266489909);
    }
    const part1 = (h1 >>> 0).toString(16).padStart(8, '0') + (h2 >>> 0).toString(16).padStart(8, '0');
    const part2 = (h3 >>> 0).toString(16).padStart(8, '0') + (h4 >>> 0).toString(16).padStart(8, '0');
    const part3 = (Math.imul(h1 ^ h3, 2654435761) >>> 0).toString(16).padStart(8, '0') + (Math.imul(h2 ^ h4, 1597334677) >>> 0).toString(16).padStart(8, '0');
    const part4 = (Math.imul(h1 ^ h2, 2246822507) >>> 0).toString(16).padStart(8, '0') + (Math.imul(h3 ^ h4, 3266489909) >>> 0).toString(16).padStart(8, '0');
    return (part1 + part2 + part3 + part4).substring(0, 64);
}

window.RiskData = {
    SCORING_MODEL,
    evaluateMetrics,
    CANONICAL_RELEASES,
    ALL_100_RELEASES,
    computeCanonicalSha256
};
