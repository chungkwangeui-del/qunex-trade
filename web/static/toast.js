/**
 * Toast Notification System
 * Usage: showToast('Message', 'success|error|info|warning')
 */

function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
        `;
        document.body.appendChild(container);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    // Toast colors
    const colors = {
        success: { bg: 'rgba(0, 255, 136, 0.15)', border: '#00ff88', icon: '✓' },
        error: { bg: 'rgba(255, 0, 110, 0.15)', border: '#ff006e', icon: '✕' },
        info: { bg: 'rgba(0, 217, 255, 0.15)', border: '#00d9ff', icon: 'ℹ' },
        warning: { bg: 'rgba(255, 193, 7, 0.15)', border: '#ffc107', icon: '⚠' }
    };

    const color = colors[type] || colors.info;

    toast.style.cssText = `
        background: ${color.bg};
        border-left: 4px solid ${color.border};
        border-radius: 8px;
        padding: 16px 20px;
        min-width: 300px;
        max-width: 400px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        display: flex;
        align-items: center;
        gap: 12px;
        animation: slideIn 0.3s ease-out;
        backdrop-filter: blur(10px);
        color: white;
        font-family: 'Space Grotesk', sans-serif;
    `;

    toast.innerHTML = `
        <span style="font-size: 20px; flex-shrink: 0;">${color.icon}</span>
        <span style="flex: 1; font-size: 14px; line-height: 1.5;">${message}</span>
        <button onclick="this.parentElement.remove()" style="
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            padding: 0;
            margin: 0;
            opacity: 0.7;
            transition: opacity 0.2s;
        " onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'">×</button>
    `;

    // Add animation
    const style = document.createElement('style');
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
    if (!document.querySelector('#toast-animations')) {
        style.id = 'toast-animations';
        document.head.appendChild(style);
    }

    container.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Convert Flask flash messages to toasts on page load
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(function(alert) {
        const message = alert.textContent.trim();
        let type = 'info';

        if (alert.classList.contains('alert-success')) type = 'success';
        else if (alert.classList.contains('alert-error')) type = 'error';
        else if (alert.classList.contains('alert-warning')) type = 'warning';

        showToast(message, type);
        alert.remove(); // Remove the old flash message
    });
});
