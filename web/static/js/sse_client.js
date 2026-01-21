/**
 * Server-Sent Events (SSE) Client for Real-Time Market Data
 * 
 * Provides true real-time updates with automatic reconnection.
 * Falls back to polling if SSE is not supported.
 * 
 * Usage:
 *   const client = new MarketSSEClient();
 *   client.subscribe(['AAPL', 'MSFT'], (data) => {
 *     console.log('Price update:', data);
 *   });
 */

class MarketSSEClient {
    constructor(options = {}) {
        this.baseUrl = options.baseUrl || '';
        this.reconnectDelay = options.reconnectDelay || 3000;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
        
        this.eventSource = null;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.subscribedTickers = new Set();
        this.callbacks = new Map(); // ticker -> Set of callbacks
        this.globalCallbacks = new Set();
        
        // Check SSE support
        this.sseSupported = typeof EventSource !== 'undefined';
        
        if (!this.sseSupported) {
            console.warn('[SSE] EventSource not supported, falling back to polling');
        }
    }

    /**
     * Subscribe to price updates for specific tickers
     * @param {string[]} tickers - Array of ticker symbols
     * @param {function} callback - Callback function for price updates
     */
    subscribe(tickers, callback) {
        if (!Array.isArray(tickers)) {
            tickers = [tickers];
        }

        tickers.forEach(ticker => {
            ticker = ticker.toUpperCase();
            this.subscribedTickers.add(ticker);
            
            if (!this.callbacks.has(ticker)) {
                this.callbacks.set(ticker, new Set());
            }
            if (callback) {
                this.callbacks.get(ticker).add(callback);
            }
        });

        // Reconnect with new tickers
        this._reconnect();
        
        console.log('[SSE] Subscribed to:', tickers.join(', '));
    }

    /**
     * Subscribe to all price updates
     * @param {function} callback - Callback for all updates
     */
    subscribeAll(callback) {
        this.globalCallbacks.add(callback);
    }

    /**
     * Unsubscribe from specific tickers
     * @param {string[]} tickers - Tickers to unsubscribe from
     * @param {function} callback - Optional specific callback to remove
     */
    unsubscribe(tickers, callback) {
        if (!Array.isArray(tickers)) {
            tickers = [tickers];
        }

        tickers.forEach(ticker => {
            ticker = ticker.toUpperCase();
            
            if (callback && this.callbacks.has(ticker)) {
                this.callbacks.get(ticker).delete(callback);
                if (this.callbacks.get(ticker).size === 0) {
                    this.callbacks.delete(ticker);
                    this.subscribedTickers.delete(ticker);
                }
            } else {
                this.callbacks.delete(ticker);
                this.subscribedTickers.delete(ticker);
            }
        });

        // Reconnect with updated tickers
        if (this.subscribedTickers.size > 0) {
            this._reconnect();
        } else {
            this.disconnect();
        }
    }

    /**
     * Connect to SSE stream
     */
    connect() {
        if (!this.sseSupported) {
            this._fallbackPolling();
            return;
        }

        if (this.subscribedTickers.size === 0) {
            console.log('[SSE] No tickers to subscribe to');
            return;
        }

        const tickers = Array.from(this.subscribedTickers).join(',');
        const url = `${this.baseUrl}/api/sse/prices?tickers=${encodeURIComponent(tickers)}`;

        this._createEventSource(url);
    }

    /**
     * Connect to watchlist stream (requires authentication)
     */
    connectWatchlist() {
        if (!this.sseSupported) {
            this._fallbackPolling();
            return;
        }

        const url = `${this.baseUrl}/api/sse/watchlist`;
        this._createEventSource(url);
    }

    /**
     * Connect to market pulse stream
     */
    connectMarketPulse() {
        if (!this.sseSupported) {
            this._fallbackPolling();
            return;
        }

        const url = `${this.baseUrl}/api/sse/market-pulse`;
        this._createEventSource(url);
    }

    /**
     * Create EventSource connection
     * @private
     */
    _createEventSource(url) {
        // Close existing connection
        if (this.eventSource) {
            this.eventSource.close();
        }

        console.log('[SSE] Connecting to:', url);
        this.eventSource = new EventSource(url);

        this.eventSource.onopen = () => {
            console.log('[SSE] Connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this._showToast('Real-time data connected', 'success');
        };

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this._handleMessage(data);
            } catch (e) {
                console.error('[SSE] Parse error:', e);
            }
        };

        this.eventSource.addEventListener('connected', (event) => {
            const data = JSON.parse(event.data);
            console.log('[SSE] Stream connected:', data);
        });

        this.eventSource.addEventListener('price_update', (event) => {
            const data = JSON.parse(event.data);
            this._handleMessage(data);
        });

        this.eventSource.addEventListener('heartbeat', () => {
            console.debug('[SSE] Heartbeat received');
        });

        this.eventSource.onerror = (error) => {
            console.error('[SSE] Connection error:', error);
            this.isConnected = false;
            
            if (this.eventSource.readyState === EventSource.CLOSED) {
                this._handleDisconnect();
            }
        };
    }

    /**
     * Handle incoming message
     * @private
     */
    _handleMessage(data) {
        if (!data) return;

        const ticker = data.ticker;
        
        // Call ticker-specific callbacks
        if (ticker && this.callbacks.has(ticker)) {
            this.callbacks.get(ticker).forEach(callback => {
                try {
                    callback(data);
                } catch (e) {
                    console.error('[SSE] Callback error:', e);
                }
            });
        }

        // Call global callbacks
        this.globalCallbacks.forEach(callback => {
            try {
                callback(data);
            } catch (e) {
                console.error('[SSE] Global callback error:', e);
            }
        });

        // Dispatch custom event for other listeners
        window.dispatchEvent(new CustomEvent('market-update', { detail: data }));
    }

    /**
     * Handle disconnection with reconnect logic
     * @private
     */
    _handleDisconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.min(this.reconnectAttempts, 5);
            
            console.log(`[SSE] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            this._showToast(`Reconnecting... (${this.reconnectAttempts})`, 'warning');
            
            setTimeout(() => this.connect(), delay);
        } else {
            console.error('[SSE] Max reconnection attempts reached');
            this._showToast('Connection lost. Please refresh.', 'error');
        }
    }

    /**
     * Reconnect with current subscriptions
     * @private
     */
    _reconnect() {
        if (this.subscribedTickers.size > 0) {
            this.connect();
        }
    }

    /**
     * Disconnect from SSE stream
     */
    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.isConnected = false;
        console.log('[SSE] Disconnected');
    }

    /**
     * Fallback to polling for browsers without SSE support
     * @private
     */
    _fallbackPolling() {
        console.log('[SSE] Using polling fallback');
        
        // Use existing MarketDataPoller if available
        if (window.marketSocket) {
            Array.from(this.subscribedTickers).forEach(ticker => {
                this.callbacks.get(ticker)?.forEach(callback => {
                    window.marketSocket.subscribe(ticker, callback);
                });
            });
            window.marketSocket.connect();
        }
    }

    /**
     * Show toast notification
     * @private
     */
    _showToast(message, type = 'info') {
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };

        const toast = document.createElement('div');
        toast.className = `sse-toast sse-toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: ${colors[type] || colors.info};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            font-size: 14px;
            font-weight: 500;
            animation: sseSlideIn 0.3s ease-out;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'sseSlideOut 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * Get connection status
     */
    getStatus() {
        return {
            connected: this.isConnected,
            sseSupported: this.sseSupported,
            subscribedTickers: Array.from(this.subscribedTickers),
            reconnectAttempts: this.reconnectAttempts
        };
    }
}

// Add CSS animations
if (!document.getElementById('sse-animations')) {
    const style = document.createElement('style');
    style.id = 'sse-animations';
    style.textContent = `
        @keyframes sseSlideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes sseSlideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        /* Price flash animations */
        .price-flash-up {
            animation: flashGreen 0.5s ease-out;
        }
        .price-flash-down {
            animation: flashRed 0.5s ease-out;
        }
        @keyframes flashGreen {
            0% { background-color: rgba(16, 185, 129, 0.3); }
            100% { background-color: transparent; }
        }
        @keyframes flashRed {
            0% { background-color: rgba(239, 68, 68, 0.3); }
            100% { background-color: transparent; }
        }
    `;
    document.head.appendChild(style);
}

// Create global instance
window.marketSSE = new MarketSSEClient();

// Helper function for quick subscriptions
window.subscribeToTicker = function(ticker, callback) {
    window.marketSSE.subscribe([ticker], callback);
};

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MarketSSEClient;
}

