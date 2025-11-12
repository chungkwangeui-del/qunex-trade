/**
 * WebSocket Client for Real-time Market Data
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Toast notifications for connection status
 * - Event-driven architecture
 */

class MarketDataSocket {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        this.subscribedTickers = new Set();
        this.callbacks = {};
    }

    connect() {
        console.log('[WebSocket] Connecting...');

        this.socket = io({
            transports: ['websocket', 'polling'],
            upgrade: true,
            reconnection: true,
            reconnectionDelay: this.reconnectDelay,
            reconnectionAttempts: this.maxReconnectAttempts,
        });

        this._setupEventHandlers();
    }

    _setupEventHandlers() {
        this.socket.on('connect', () => {
            console.log('[WebSocket] Connected');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this._showToast('Connected to live market data', 'success');

            // Resubscribe to tickers
            this.subscribedTickers.forEach(ticker => {
                this._subscribeToTicker(ticker);
            });
        });

        this.socket.on('disconnect', (reason) => {
            console.log('[WebSocket] Disconnected:', reason);
            this._showToast('Disconnected from live data', 'warning');
        });

        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log(`[WebSocket] Reconnection attempt ${attemptNumber}`);
            this._showToast(`Reconnecting... (attempt ${attemptNumber})`, 'info');
        });

        this.socket.on('reconnect_error', (error) => {
            console.error('[WebSocket] Reconnection error:', error);
        });

        this.socket.on('reconnect_failed', () => {
            console.error('[WebSocket] Reconnection failed');
            this._showToast('Failed to reconnect. Please refresh the page.', 'error');
        });

        this.socket.on('connection_established', (data) => {
            console.log('[WebSocket] Connection established:', data);
        });

        this.socket.on('error', (data) => {
            console.error('[WebSocket] Error:', data.message);
            this._showToast(`Error: ${data.message}`, 'error');
        });

        this.socket.on('subscribed', (data) => {
            console.log('[WebSocket] Subscribed to:', data.ticker);
        });

        this.socket.on('unsubscribed', (data) => {
            console.log('[WebSocket] Unsubscribed from:', data.ticker);
        });

        this.socket.on('market_update', (data) => {
            console.log('[WebSocket] Market update:', data);
            this._handleMarketUpdate(data);
        });
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

        this._subscribeToTicker(ticker);
    }

    unsubscribe(ticker) {
        if (!ticker) return;

        ticker = ticker.toUpperCase();
        this.subscribedTickers.delete(ticker);
        delete this.callbacks[ticker];

        if (this.socket && this.socket.connected) {
            this.socket.emit('unsubscribe_ticker', { ticker });
        }
    }

    _subscribeToTicker(ticker) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('subscribe_ticker', { ticker });
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
                    console.error('[WebSocket] Callback error:', error);
                }
            });
        }
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
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
    }
}

// Add CSS animations
if (!document.getElementById('socket-animations')) {
    const style = document.createElement('style');
    style.id = 'socket-animations';
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

// Global instance
const marketSocket = new MarketDataSocket();

// Auto-connect when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        marketSocket.connect();
    });
} else {
    marketSocket.connect();
}

// Export for use in other scripts
window.marketSocket = marketSocket;
