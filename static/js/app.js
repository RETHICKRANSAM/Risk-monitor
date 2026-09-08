/**
 * Pre-Release Risk Monitor — Core Application JavaScript
 * API client, auth management, toasts, and shared utilities.
 */

// ============================================================
// API Client
// ============================================================
const API = {
    baseUrl: '',

    async request(method, url, data = null) {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include', // Send session cookies
        };

        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(this.baseUrl + url, options);
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `HTTP ${response.status}`);
            }

            return result;
        } catch (err) {
            if (err.name === 'TypeError' && err.message.includes('fetch')) {
                // Network error — queue the event if it's a POST
                if (method === 'POST' && data) {
                    OfflineQueue.add({ method, url, data });
                    showToast('Offline: Event queued for later sync', 'warning');
                }
                throw new Error('Network unavailable');
            }
            throw err;
        }
    },

    get(url) { return this.request('GET', url); },
    post(url, data) { return this.request('POST', url, data); },
    put(url, data) { return this.request('PUT', url, data); },
    delete(url) { return this.request('DELETE', url); },
};


// ============================================================
// Auth Helpers
// ============================================================
async function requireAuth() {
    try {
        const user = await API.get('/api/me');
        if (!user.user_id) {
            window.location.href = '/';
        }
        return user;
    } catch (e) {
        window.location.href = '/';
    }
}

async function loadUserInfo() {
    try {
        const user = await API.get('/api/me');

        const avatarEl = document.getElementById('userAvatar');
        const nameEl = document.getElementById('userName');
        const roleEl = document.getElementById('userRole');

        if (avatarEl) avatarEl.textContent = (user.name || '?')[0].toUpperCase();
        if (nameEl) nameEl.textContent = user.name || user.username;
        if (roleEl) roleEl.textContent = formatRole(user.role);

        // Show/hide nav items based on role
        const auditNav = document.getElementById('nav-audit');
        if (auditNav && user.permissions) {
            if (!user.permissions.can_view_audit) {
                auditNav.style.display = 'none';
            }
        }

        return user;
    } catch (e) {
        // Silently fail
    }
}

function formatRole(role) {
    if (!role) return '—';
    return role.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}


// ============================================================
// Toast Notifications
// ============================================================
function showToast(message, type = 'success', duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}


// ============================================================
// Offline Status
// ============================================================
function updateOfflineBanner() {
    const banner = document.getElementById('offlineBanner');
    const countEl = document.getElementById('queueCount');
    if (!banner || !countEl) return;

    const count = OfflineQueue.count();
    countEl.textContent = count;

    if (count > 0 || !navigator.onLine) {
        banner.classList.add('visible');
    } else {
        banner.classList.remove('visible');
    }
}

// Listen for online/offline events
window.addEventListener('online', () => {
    showToast('Back online! Syncing queued events...', 'success');
    OfflineQueue.sync();
    updateOfflineBanner();
});

window.addEventListener('offline', () => {
    showToast('You are offline. Events will be queued.', 'warning');
    updateOfflineBanner();
});

// Check offline status on load
document.addEventListener('DOMContentLoaded', updateOfflineBanner);


// ============================================================
// Utility Functions
// ============================================================
function formatDate(isoString) {
    if (!isoString) return '—';
    return new Date(isoString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
