// dashboard.js - Handles fetching and rendering for the Dashboard page

let charts = {}; // Store chart instances to destroy/update them

document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    
    // Listen for global refresh
    document.addEventListener('dashboard:refresh', initDashboard);
});

async function initDashboard() {
    try {
        setLoadingState(true);
        const res = await fetch('/api/dashboard');
        const data = await res.json();
        
        renderKPIs(data.metrics);
        renderCharts(data.charts);
        
        setLoadingState(false);
    } catch (e) {
        console.error("Failed to load dashboard data", e);
        setLoadingState(false);
    }
}

function setLoadingState(isLoading) {
    const kpiEls = ['kpi-critical', 'kpi-unassigned', 'kpi-missing', 'kpi-agents'];
    
    if (isLoading) {
        kpiEls.forEach(id => {
            const el = document.getElementById(id);
            if(el) {
                el.innerHTML = '<div class="h-8 w-24 skeleton bg-[#2A2E37]"></div>';
            }
        });
    }
}

function renderKPIs(metrics) {
    const formatNumber = num => new Intl.NumberFormat().format(num);
    
    document.getElementById('kpi-critical').textContent = formatNumber(metrics.critical_alerts);
    document.getElementById('kpi-unassigned').textContent = formatNumber(metrics.unassigned_alerts);
    document.getElementById('kpi-missing').textContent = formatNumber(metrics.assets_missing);
    document.getElementById('kpi-agents').textContent = formatNumber(metrics.agents_requiring_attention);
}

function renderCharts(chartData) {
    // Shared Chart.js defaults
    Chart.defaults.color = '#94A3B8';
    Chart.defaults.font.family = 'Inter, sans-serif';
    
    renderDonutChart(chartData.classification);
    renderLineChart(chartData.risk_scores);
    renderBarChart(chartData.agents_attention);
}

function renderDonutChart(data) {
    const ctx = document.getElementById('donutChart');
    if (!ctx) return;
    
    if (charts.donut) charts.donut.destroy();
    
    document.getElementById('donut-total').textContent = data.total;

    charts.donut = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.data,
                backgroundColor: [
                    '#10B981', // Hacktool
                    '#6366F1', // Virus
                    '#F59E0B', // Spyware
                    '#F97316', // Malware
                    '#EF4444'  // Phishing
                ],
                borderWidth: 0,
                cutout: '75%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(28, 31, 38, 0.9)',
                    titleColor: '#E2E8F0',
                    bodyColor: '#E2E8F0',
                    borderColor: 'rgba(42, 46, 55, 0.8)',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            return ` ${context.label}: ${context.raw}%`;
                        }
                    }
                }
            }
        }
    });
}

function renderLineChart(data) {
    const ctx = document.getElementById('lineChart');
    if (!ctx) return;
    
    if (charts.line) charts.line.destroy();

    const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(239, 68, 68, 0.5)'); // Critical Red
    gradient.addColorStop(1, 'rgba(239, 68, 68, 0.0)');

    charts.line = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Risk Score',
                data: data.data,
                borderColor: '#EF4444',
                backgroundColor: gradient,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#0F1115',
                pointBorderColor: '#EF4444',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(28, 31, 38, 0.9)',
                    borderColor: 'rgba(42, 46, 55, 0.8)',
                    borderWidth: 1,
                    padding: 10
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    border: { display: false }
                },
                x: {
                    grid: { display: false },
                    border: { display: false }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index',
            },
        }
    });
}

function renderBarChart(data) {
    const ctx = document.getElementById('barChart');
    if (!ctx) return;
    
    if (charts.bar) charts.bar.destroy();

    charts.bar = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.data,
                backgroundColor: [
                    '#6366F1', // Pending Deprecation
                    '#10B981', // Reboot
                    '#F59E0B', // Extended
                    '#EF4444'  // NE CF
                ],
                borderRadius: 4,
                barThickness: 'flex',
                maxBarThickness: 40
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(28, 31, 38, 0.9)',
                    borderColor: 'rgba(42, 46, 55, 0.8)',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    display: false, // hide y axis to match the design style
                    beginAtZero: true
                },
                x: {
                    grid: { display: false },
                    border: { display: false },
                    ticks: {
                        color: '#94A3B8',
                        font: { size: 10 }
                    }
                }
            }
        }
    });
}
