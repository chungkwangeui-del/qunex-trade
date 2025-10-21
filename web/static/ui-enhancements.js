/**
 * UI Enhancements - Loading States & Dark Mode
 */

// ========================================
// Loading State for Buttons
// ========================================

function setButtonLoading(button, isLoading, originalText = null) {
    if (isLoading) {
        button.dataset.originalText = button.innerHTML;
        button.disabled = true;
        button.style.position = 'relative';
        button.innerHTML = `
            <span style="opacity: 0.6;">${originalText || button.dataset.originalText}</span>
            <span class="spinner" style="
                position: absolute;
                right: 15px;
                top: 50%;
                transform: translateY(-50%);
            "></span>
        `;
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || originalText;
    }
}

// Add loading spinner CSS
const spinnerStyle = document.createElement('style');
spinnerStyle.textContent = `
    .spinner {
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-top: 2px solid white;
        border-radius: 50%;
        width: 16px;
        height: 16px;
        animation: spin 0.8s linear infinite;
        display: inline-block;
    }

    @keyframes spin {
        0% { transform: translateY(-50%) rotate(0deg); }
        100% { transform: translateY(-50%) rotate(360deg); }
    }

    .btn:disabled {
        opacity: 0.7;
        cursor: not-allowed;
    }
`;
document.head.appendChild(spinnerStyle);

// Auto-apply loading state to forms
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton && !submitButton.disabled) {
                setButtonLoading(submitButton, true);
            }
        });
    });
});


// ========================================
// Dark Mode Toggle
// ========================================

function initDarkMode() {
    // Check saved preference or system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = savedTheme === 'dark' || (!savedTheme && prefersDark);

    if (isDark) {
        document.documentElement.classList.add('dark-mode');
    }

    // Create dark mode toggle button
    createDarkModeToggle();
}

function createDarkModeToggle() {
    const toggle = document.createElement('button');
    toggle.id = 'dark-mode-toggle';
    toggle.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path class="sun" d="M10 3a1 1 0 011 1v1a1 1 0 11-2 0V4a1 1 0 011-1zm0 10a3 3 0 100-6 3 3 0 000 6zm0 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM3 10a1 1 0 011-1h1a1 1 0 110 2H4a1 1 0 01-1-1zm12 0a1 1 0 011-1h1a1 1 0 110 2h-1a1 1 0 01-1-1zM5.05 5.05a1 1 0 011.414 0l.707.707a1 1 0 11-1.414 1.414l-.707-.707a1 1 0 010-1.414zm9.9 9.9a1 1 0 011.414 0l.707.707a1 1 0 11-1.414 1.414l-.707-.707a1 1 0 010-1.414zm0-9.9a1 1 0 010 1.414l-.707.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM5.05 14.95a1 1 0 010 1.414l-.707.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0z" />
            <path class="moon" d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" style="display:none;"/>
        </svg>
    `;
    toggle.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        width: 50px;
        height: 50px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s;
        z-index: 1000;
        color: white;
    `;

    toggle.addEventListener('mouseenter', () => {
        toggle.style.transform = 'scale(1.1)';
        toggle.style.background = 'rgba(255, 255, 255, 0.2)';
    });

    toggle.addEventListener('mouseleave', () => {
        toggle.style.transform = 'scale(1)';
        toggle.style.background = 'rgba(255, 255, 255, 0.1)';
    });

    toggle.addEventListener('click', toggleDarkMode);

    document.body.appendChild(toggle);
    updateDarkModeIcon();
}

function toggleDarkMode() {
    const isDark = document.documentElement.classList.toggle('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateDarkModeIcon();
    showToast(isDark ? 'Dark mode enabled' : 'Light mode enabled', 'info');
}

function updateDarkModeIcon() {
    const isDark = document.documentElement.classList.contains('dark-mode');
    const sun = document.querySelector('#dark-mode-toggle .sun');
    const moon = document.querySelector('#dark-mode-toggle .moon');

    if (sun && moon) {
        sun.style.display = isDark ? 'none' : 'block';
        moon.style.display = isDark ? 'block' : 'none';
    }
}

// Dark mode CSS
const darkModeStyle = document.createElement('style');
darkModeStyle.textContent = `
    :root {
        --bg-dark: #0a0e27;
        --bg-card: #131829;
        --text-primary: #ffffff;
        --text-secondary: #8b92b0;
        --primary: #00d9ff;
        --secondary: #7c3aed;
        --border: rgba(0, 217, 255, 0.15);
    }

    .dark-mode {
        --bg-dark: #e8edf2;
        --bg-card: #f7f9fb;
        --text-primary: #2d3748;
        --text-secondary: #4a5568;
        --border: rgba(0, 0, 0, 0.08);
    }

    .dark-mode body {
        background: var(--bg-dark);
        color: var(--text-primary);
    }

    .dark-mode .card {
        background: var(--bg-card);
        border-color: var(--border);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    }

    .dark-mode input {
        background: var(--bg-dark);
        color: var(--text-primary);
        border-color: var(--border);
    }

    .dark-mode label {
        color: var(--text-secondary);
    }

    .dark-mode .subtitle {
        color: var(--text-secondary);
    }

    .dark-mode::before {
        opacity: 0.3;
    }

    /* Smooth transition */
    body, .card, input, label {
        transition: background 0.3s, color 0.3s, border-color 0.3s;
    }
`;
document.head.appendChild(darkModeStyle);

// Initialize on page load
document.addEventListener('DOMContentLoaded', initDarkMode);
