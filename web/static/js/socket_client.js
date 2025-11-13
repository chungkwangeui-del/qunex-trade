/**
 * AJAX Polling Client for Market Data
 *
 * Replaces WebSocket with polling for compatibility with Render free tier.
 * Features:
 * - Automatic polling every 15 seconds
 * - Toast notifications for status
 * - Event-driven architecture (maintains API compatibility)
 */

class MarketDataPoller {
    constructor() {
        this.pollInterval = null;
        this.pollFrequency = 15000; // 15 seconds
        this.subscribedTickers = new Set();
        this.callbacks = {};
        this.isPolling = false;
    }

    connect() {
        console.log('[Polling] Starting market data polling...');

        if (!this.isPolling) {
            this.isPolling = true;
            this._startPolling();
            this._showToast('Connected to market data', 'success');
        }
    }

    _startPolling() {
        // Clear any existing interval
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }

        // Start polling immediately
        this._poll();

        // Then poll every 15 seconds
        this.pollInterval = setInterval(() => {
            this._poll();
        }, this.pollFrequency);
    }

    async _poll() {
        if (this.subscribedTickers.size === 0) {
            return; // Nothing to poll
        }

        const tickers = Array.from(this.subscribedTickers);

        try {
            const response = await fetch('/api/market-data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this._getCSRFToken()
                },
                body: JSON.stringify({ tickers })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success && data.data) {
                // Process each ticker's data
                Object.entries(data.data).forEach(([ticker, tickerData]) => {
                    this._handleMarketUpdate({ ticker, ...tickerData });
                });
            }
        } catch (error) {
            console.error('[Polling] Error fetching market data:', error);
            // Don't show toast for every error to avoid spam
        }
    }

    subscribe(ticker, callback) {
        if (!ticker) return;

        ticker = ticker.toUpperCase();
        this.subscribedTickers.add(ticker);

        if (callback) {
            if (!this.callbacks[ticker]) {
                this.callbacks[ticker] = [];
            }
            this.callbacks[ticker].push(callback);
        }

        // Start polling if not already started
        if (!this.isPolling) {
            this.connect();
        } else {
            // Trigger immediate poll for new subscription
            this._poll();
        }

        console.log('[Polling] Subscribed to:', ticker);
    }

    unsubscribe(ticker) {
        if (!ticker) return;

        ticker = ticker.toUpperCase();
        this.subscribedTickers.delete(ticker);
        delete this.callbacks[ticker];

        console.log('[Polling] Unsubscribed from:', ticker);

        // Stop polling if no more subscriptions
        if (this.subscribedTickers.size === 0) {
            this._stopPolling();
        }
    }

    _stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
            this.isPolling = false;
            console.log('[Polling] Stopped polling');
        }
    }

    _handleMarketUpdate(data) {
        const ticker = data.ticker || data.sym;
        if (!ticker) return;

        const callbacks = this.callbacks[ticker.toUpperCase()];
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error('[Polling] Callback error:', error);
                }
            });
        }
    }

    _getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }

    _showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(toast);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                if (toast.parentNode) {
                    document.body.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }

    disconnect() {
        this._stopPolling();
        this.subscribedTickers.clear();
        this.callbacks = {};
        this._showToast('Disconnected from market data', 'warning');
    }
}

// Add CSS animations
if (!document.getElementById('polling-animations')) {
    const style = document.createElement('style');
    style.id = 'polling-animations';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

// Global instance (maintains backward compatibility)
const marketSocket = new MarketDataPoller();

// Auto-connect when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Don't auto-connect, wait for subscriptions
        console.log('[Polling] Market data poller ready');
    });
} else {
    console.log('[Polling] Market data poller ready');
}

// Export for use in other scripts
window.marketSocket = marketSocket;
