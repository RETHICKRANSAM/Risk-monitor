/**
 * Offline Queue — localStorage-based event queue for offline resilience.
 * Stores API requests when the backend is unavailable and retries on reconnect (FR-8).
 */

const OfflineQueue = {
    STORAGE_KEY: 'risk_monitor_offline_queue',

    /**
     * Get all queued events from localStorage.
     */
    getAll() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            return data ? JSON.parse(data) : [];
        } catch (e) {
            console.error('OfflineQueue: Failed to read queue', e);
            return [];
        }
    },

    /**
     * Save the queue back to localStorage.
     */
    save(queue) {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(queue));
        } catch (e) {
            console.error('OfflineQueue: Failed to save queue', e);
        }
    },

    /**
     * Add an event to the offline queue.
     */
    add(event) {
        const queue = this.getAll();
        queue.push({
            ...event,
            id: Date.now() + '_' + Math.random().toString(36).substr(2, 9),
            timestamp: new Date().toISOString(),
            retries: 0,
        });
        this.save(queue);
        this.updateUI();
        console.log('OfflineQueue: Event queued', event);
    },

    /**
     * Remove an event from the queue.
     */
    remove(eventId) {
        const queue = this.getAll().filter(e => e.id !== eventId);
        this.save(queue);
        this.updateUI();
    },

    /**
     * Get the count of queued events.
     */
    count() {
        return this.getAll().length;
    },

    /**
     * Attempt to sync all queued events with the server.
     */
    async sync() {
        const queue = this.getAll();
        if (queue.length === 0) return;

        console.log(`OfflineQueue: Syncing ${queue.length} queued events...`);
        const remaining = [];

        for (const event of queue) {
            try {
                const options = {
                    method: event.method || 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                };

                if (event.data) {
                    options.body = JSON.stringify(event.data);
                }

                const response = await fetch(event.url, options);

                if (response.ok) {
                    console.log(`OfflineQueue: Synced event ${event.id}`);
                } else if (response.status >= 500) {
                    // Server error — retry later
                    event.retries = (event.retries || 0) + 1;
                    if (event.retries < 5) {
                        remaining.push(event);
                    }
                }
                // 4xx errors are client errors — discard
            } catch (e) {
                // Network still unavailable — keep in queue
                event.retries = (event.retries || 0) + 1;
                if (event.retries < 10) {
                    remaining.push(event);
                }
            }
        }

        this.save(remaining);
        this.updateUI();

        if (remaining.length === 0) {
            console.log('OfflineQueue: All events synced!');
            if (typeof showToast === 'function') {
                showToast(`Synced ${queue.length} offline events`, 'success');
            }
        } else {
            console.log(`OfflineQueue: ${remaining.length} events still pending`);
        }
    },

    /**
     * Update the offline banner UI.
     */
    updateUI() {
        if (typeof updateOfflineBanner === 'function') {
            updateOfflineBanner();
        }
    },

    /**
     * Clear the entire queue.
     */
    clear() {
        this.save([]);
        this.updateUI();
    }
};

// Auto-sync when coming back online
window.addEventListener('online', () => {
    setTimeout(() => OfflineQueue.sync(), 1000);
});

// Periodic sync attempt every 30 seconds
setInterval(() => {
    if (navigator.onLine && OfflineQueue.count() > 0) {
        OfflineQueue.sync();
    }
}, 30000);
