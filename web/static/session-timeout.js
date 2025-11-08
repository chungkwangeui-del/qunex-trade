/**
 * Session Timeout Warning System
 * Warns users before session expires and auto-logs out
 */

class SessionTimeout {
    constructor(options = {}) {
        this.sessionDuration = options.sessionDuration || 7 * 24 * 60 * 60 * 1000; // 7 days default
        this.warningTime = options.warningTime || 5 * 60 * 1000; // Warn 5 minutes before
        this.checkInterval = options.checkInterval || 60 * 1000; // Check every minute
        this.logoutUrl = options.logoutUrl || '/auth/logout';

        this.lastActivity = Date.now();
        this.warningShown = false;
        this.warningModal = null;

        this.init();
    }

    init() {
        // Track user activity
        this.trackActivity();

        // Start checking for timeout
        setInterval(() => this.checkTimeout(), this.checkInterval);

        // Create warning modal
        this.createWarningModal();
    }

    trackActivity() {
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];

        events.forEach(event => {
            document.addEventListener(event, () => {
                this.lastActivity = Date.now();

                // Hide warning if user becomes active again
                if (this.warningShown) {
                    this.hideWarning();
                }
            }, true);
        });
    }

    checkTimeout() {
        const now = Date.now();
        const inactiveDuration = now - this.lastActivity;
        const timeUntilTimeout = this.sessionDuration - inactiveDuration;

        // Show warning
        if (timeUntilTimeout <= this.warningTime && timeUntilTimeout > 0 && !this.warningShown) {
            this.showWarning(Math.floor(timeUntilTimeout / 1000));
        }

        // Auto logout
        if (timeUntilTimeout <= 0) {
            this.logout();
        }
    }

    createWarningModal() {
        const modal = document.createElement('div');
        modal.id = 'session-timeout-modal';
        modal.className = 'session-modal';
        modal.innerHTML = `
            <div class="session-modal-backdrop"></div>
            <div class="session-modal-content">
                <div class="session-modal-header">
                    <div class="warning-icon">⏰</div>
                    <h3>Session Expiring Soon</h3>
                </div>
                <div class="session-modal-body">
                    <p>Your session will expire in <strong id="session-countdown">5:00</strong></p>
                    <p class="session-subtitle">Click "Stay Logged In" to continue your session</p>
                </div>
                <div class="session-modal-actions">
                    <button class="btn-secondary" onclick="sessionManager.logout()">Logout</button>
                    <button class="btn-primary" onclick="sessionManager.extendSession()">Stay Logged In</button>
                </div>
            </div>
        `;

        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .session-modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: 10000;
            }

            .session-modal.show {
                display: block;
                animation: fadeIn 0.3s ease;
            }

            .session-modal-backdrop {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.7);
                backdrop-filter: blur(5px);
            }

            .session-modal-content {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: var(--bg-card, #131829);
                border: 1px solid var(--border, rgba(0, 217, 255, 0.15));
                border-radius: 20px;
                padding: 40px;
                max-width: 500px;
                width: 90%;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                animation: slideInUp 0.3s ease;
            }

            @keyframes slideInUp {
                from {
                    opacity: 0;
                    transform: translate(-50%, -40%);
                }
                to {
                    opacity: 1;
                    transform: translate(-50%, -50%);
                }
            }

            .session-modal-header {
                text-align: center;
                margin-bottom: 25px;
            }

            .warning-icon {
                font-size: 3em;
                margin-bottom: 15px;
                animation: pulse 2s ease-in-out infinite;
            }

            .session-modal-header h3 {
                font-size: 1.8em;
                color: var(--text-primary, #ffffff);
                margin: 0;
            }

            .session-modal-body {
                text-align: center;
                margin-bottom: 30px;
            }

            .session-modal-body p {
                font-size: 1.1em;
                color: var(--text-secondary, #8b92b0);
                margin: 10px 0;
            }

            .session-modal-body strong {
                color: var(--primary, #00d9ff);
                font-size: 1.3em;
                font-weight: 700;
            }

            .session-subtitle {
                font-size: 0.95em !important;
                margin-top: 20px !important;
            }

            .session-modal-actions {
                display: flex;
                gap: 15px;
                justify-content: center;
            }

            .session-modal-actions button {
                padding: 12px 30px;
                border-radius: 10px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                border: none;
                font-size: 1em;
            }

            .btn-primary {
                background: linear-gradient(135deg, var(--primary, #00d9ff) 0%, var(--secondary, #7c3aed) 100%);
                color: white;
            }

            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 30px rgba(0, 217, 255, 0.4);
            }

            .btn-secondary {
                background: transparent;
                color: var(--text-secondary, #8b92b0);
                border: 1px solid var(--border, rgba(0, 217, 255, 0.15));
            }

            .btn-secondary:hover {
                border-color: var(--primary, #00d9ff);
                color: var(--primary, #00d9ff);
            }

            @media (max-width: 480px) {
                .session-modal-content {
                    padding: 30px 20px;
                }

                .session-modal-actions {
                    flex-direction: column;
                }

                .session-modal-actions button {
                    width: 100%;
                }
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(modal);

        this.warningModal = modal;
    }

    showWarning(secondsLeft) {
        this.warningShown = true;
        this.warningModal.classList.add('show');

        // Update countdown every second
        const countdown = this.warningModal.querySelector('#session-countdown');
        const updateCountdown = () => {
            const minutes = Math.floor(secondsLeft / 60);
            const seconds = secondsLeft % 60;
            countdown.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

            if (secondsLeft > 0) {
                secondsLeft--;
                setTimeout(updateCountdown, 1000);
            }
        };
        updateCountdown();
    }

    hideWarning() {
        this.warningShown = false;
        this.warningModal.classList.remove('show');
    }

    extendSession() {
        // Reset last activity
        this.lastActivity = Date.now();
        this.hideWarning();

        // Make a ping request to server to extend session
        fetch('/auth/ping', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        }).catch(err => {
            // Session extend failed - silent fail
        });

        if (window.showToast) {
            showToast('Session extended successfully', 'success');
        }
    }

    logout() {
        // Show logout message
        if (window.showToast) {
            showToast('Session expired. Logging out...', 'info');
        }

        // Redirect to logout
        setTimeout(() => {
            window.location.href = this.logoutUrl;
        }, 1500);
    }
}

// Initialize session timeout manager (only for authenticated users)
let sessionManager;

document.addEventListener('DOMContentLoaded', function() {
    // Check if user is authenticated (presence of logout link)
    const isAuthenticated = document.querySelector('a[href*="logout"]') !== null;

    if (isAuthenticated) {
        sessionManager = new SessionTimeout({
            sessionDuration: 7 * 24 * 60 * 60 * 1000, // 7 days
            warningTime: 5 * 60 * 1000, // Warn 5 minutes before
            checkInterval: 60 * 1000, // Check every minute
            logoutUrl: '/auth/logout'
        });

        // Make it globally accessible
        window.sessionManager = sessionManager;
    }
});
