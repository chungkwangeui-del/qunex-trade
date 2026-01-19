/**
 * Qunex Trade - Real-Time Price Streaming Client
 * 
 * Provides real-time price updates via polling with smooth animations
 * Uses the /api/realtime endpoints for price data
 */

class RealtimePriceClient {
    constructor(options = {}) {
        this.pollInterval = options.pollInterval || 5000;
        this.tickers = new Set();
        this.lastPrices = {};
        this.callbacks = new Map();
        this.isRunning = false;
        this.pollTimer = null;
        this.marketStatus = 'unknown';
    }

    /**
     * Subscribe to price updates for a ticker
     * @param {string} ticker - Stock ticker symbol
     * @param {Function} callback - Called with price data on update
     */
    subscribe(ticker, callback) {
        ticker = ticker.toUpperCase();
        this.tickers.add(ticker);
        
        if (!this.callbacks.has(ticker)) {
            this.callbacks.set(ticker, new Set());
        }
        this.callbacks.get(ticker).add(callback);

        // Start polling if not already running
        if (!this.isRunning && this.tickers.size > 0) {
            this.start();
        }

        // Return unsubscribe function
        return () => this.unsubscribe(ticker, callback);
    }

    /**
     * Unsubscribe from price updates
     */
    unsubscribe(ticker, callback) {
        ticker = ticker.toUpperCase();
        
        if (this.callbacks.has(ticker)) {
            this.callbacks.get(ticker).delete(callback);
            
            if (this.callbacks.get(ticker).size === 0) {
                this.callbacks.delete(ticker);
                this.tickers.delete(ticker);
            }
        }

        // Stop polling if no subscribers
        if (this.tickers.size === 0) {
            this.stop();
        }
    }

    /**
     * Subscribe to multiple tickers at once
     */
    subscribeMany(tickers, callback) {
        const unsubscribes = tickers.map(t => this.subscribe(t, callback));
        return () => unsubscribes.forEach(fn => fn());
    }

    /**
     * Start the price polling
     */
    start() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.poll();
        
        console.log('[RealtimePrices] Started polling for:', Array.from(this.tickers));
    }

    /**
     * Stop the price polling
     */
    stop() {
        this.isRunning = false;
        
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
            this.pollTimer = null;
        }
        
        console.log('[RealtimePrices] Stopped polling');
    }

    /**
     * Perform a single poll for prices
     */
    async poll() {
        if (!this.isRunning || this.tickers.size === 0) return;

        try {
            const response = await fetch('/api/realtime/prices', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tickers: Array.from(this.tickers),
                    last_prices: this.lastPrices
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                // Process price updates
                this.processPrices(data.prices);
                
                // Process price changes
                if (data.changes && data.changes.length > 0) {
                    this.processChanges(data.changes);
                }
            }

        } catch (error) {
            console.warn('[RealtimePrices] Poll error:', error.message);
        }

        // Schedule next poll
        if (this.isRunning) {
            this.pollTimer = setTimeout(() => this.poll(), this.pollInterval);
        }
    }

    /**
     * Process price data
     */
    processPrices(prices) {
        for (const [ticker, data] of Object.entries(prices)) {
            if (data.error) continue;

            // Store as last known price
            this.lastPrices[ticker] = data;

            // Notify subscribers
            const callbacks = this.callbacks.get(ticker);
            if (callbacks) {
                callbacks.forEach(cb => {
                    try {
                        cb(data);
                    } catch (e) {
                        console.error('[RealtimePrices] Callback error:', e);
                    }
                });
            }
        }
    }

    /**
     * Process price changes and trigger animations
     */
    processChanges(changes) {
        for (const change of changes) {
            const ticker = change.ticker;
            const direction = change.direction;

            // Dispatch custom event for UI to react
            document.dispatchEvent(new CustomEvent('price-change', {
                detail: {
                    ticker,
                    oldPrice: change.old_price,
                    newPrice: change.new_price,
                    change: change.change,
                    changePct: change.change_pct,
                    direction
                }
            }));

            // Animate price elements
            this.animatePriceChange(ticker, direction);
        }
    }

    /**
     * Animate price change in the UI
     */
    animatePriceChange(ticker, direction) {
        // Find all elements displaying this ticker's price
        const elements = document.querySelectorAll(`[data-ticker="${ticker}"]`);
        
        elements.forEach(el => {
            // Add flash animation class
            el.classList.remove('price-up', 'price-down');
            void el.offsetWidth; // Force reflow
            el.classList.add(direction === 'up' ? 'price-up' : 'price-down');

            // Remove class after animation
            setTimeout(() => {
                el.classList.remove('price-up', 'price-down');
            }, 800);
        });
    }

    /**
     * Get current price for a ticker (from cache)
     */
    getPrice(ticker) {
        return this.lastPrices[ticker.toUpperCase()] || null;
    }

    /**
     * Check market status
     */
    async checkMarketStatus() {
        try {
            const response = await fetch('/api/realtime/market-pulse');
            const data = await response.json();
            
            if (data.success) {
                this.marketStatus = data.market_status;
                return data;
            }
        } catch (error) {
            console.warn('[RealtimePrices] Market status error:', error);
        }
        return null;
    }
}

/**
 * Price display helper - formats and updates price elements
 */
class PriceDisplay {
    constructor(element, options = {}) {
        this.element = element;
        this.ticker = options.ticker;
        this.format = options.format || 'currency';
        this.showChange = options.showChange !== false;
        this.lastPrice = null;

        if (this.ticker) {
            this.element.setAttribute('data-ticker', this.ticker);
        }
    }

    /**
     * Update the display with new price data
     */
    update(data) {
        if (!data || !data.price) return;

        const price = data.price;
        const change = data.change_percent || 0;
        const direction = this.lastPrice ? (price > this.lastPrice ? 'up' : price < this.lastPrice ? 'down' : null) : null;

        // Format price
        let formattedPrice;
        if (this.format === 'currency') {
            formattedPrice = '$' + price.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        } else {
            formattedPrice = price.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }

        // Update element
        if (this.element.querySelector('.price-value')) {
            this.element.querySelector('.price-value').textContent = formattedPrice;
        } else {
            this.element.textContent = formattedPrice;
        }

        // Update change display
        if (this.showChange && this.element.querySelector('.price-change')) {
            const changeEl = this.element.querySelector('.price-change');
            const sign = change >= 0 ? '+' : '';
            changeEl.textContent = `${sign}${change.toFixed(2)}%`;
            changeEl.className = 'price-change ' + (change >= 0 ? 'positive' : 'negative');
        }

        // Trigger animation
        if (direction) {
            this.element.classList.remove('price-up', 'price-down');
            void this.element.offsetWidth;
            this.element.classList.add(direction === 'up' ? 'price-up' : 'price-down');
            
            setTimeout(() => {
                this.element.classList.remove('price-up', 'price-down');
            }, 800);
        }

        this.lastPrice = price;
    }
}

// Global instance
window.realtimePrices = new RealtimePriceClient();
window.PriceDisplay = PriceDisplay;

// Auto-start if there are data-realtime-ticker elements on page
document.addEventListener('DOMContentLoaded', () => {
    const realtimeElements = document.querySelectorAll('[data-realtime-ticker]');
    
    if (realtimeElements.length > 0) {
        const displays = new Map();

        realtimeElements.forEach(el => {
            const ticker = el.dataset.realtimeTicker;
            const display = new PriceDisplay(el, { ticker });
            displays.set(ticker, display);

            window.realtimePrices.subscribe(ticker, (data) => {
                display.update(data);
            });
        });

        console.log(`[RealtimePrices] Auto-subscribed to ${realtimeElements.length} tickers`);
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { RealtimePriceClient, PriceDisplay };
}

