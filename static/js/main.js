// main.js - Core UI functionality and navigation

document.addEventListener('DOMContentLoaded', () => {
    initMobileMenu();
    initGlobalRefresh();
    fetchAlertsBadge();
});

function initMobileMenu() {
    const btn = document.getElementById('mobile-menu-btn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (!btn || !sidebar || !overlay) return;

    function toggleMenu() {
        const isOpen = !sidebar.classList.contains('-translate-x-full');
        if (isOpen) {
            sidebar.classList.add('-translate-x-full');
            overlay.classList.add('opacity-0');
            setTimeout(() => overlay.classList.add('hidden'), 300);
        } else {
            sidebar.classList.remove('-translate-x-full');
            overlay.classList.remove('hidden');
            setTimeout(() => overlay.classList.remove('opacity-0'), 10);
        }
    }

    btn.addEventListener('click', toggleMenu);
    overlay.addEventListener('click', toggleMenu);
}

function initGlobalRefresh() {
    const refreshBtn = document.getElementById('global-refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            refreshBtn.classList.add('animate-spin', 'text-soc-accent');
            
            // Dispatch a custom event so individual pages can hook into the refresh
            document.dispatchEvent(new Event('dashboard:refresh'));

            setTimeout(() => {
                refreshBtn.classList.remove('animate-spin', 'text-soc-accent');
            }, 1000);
        });
    }
}

async function fetchAlertsBadge() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        const badge = document.getElementById('sidebar-alert-badge');
        
        if (badge && data.metrics) {
            badge.textContent = data.metrics.critical_alerts > 999 ? '999+' : data.metrics.critical_alerts;
        }
    } catch (e) {
        console.error('Failed to fetch badge count', e);
    }
}

async function logout() {
    try {
        const res = await fetch('/api/logout', { method: 'POST' });
        const data = await res.json();
        if (data.redirect) {
            window.location.href = data.redirect;
        }
    } catch (e) {
        window.location.href = '/';
    }
}
