/**
 * Light/Dark Mode Toggle
 * Qunex Trade - Theme Switcher
 * IMPORTANT: This script must be loaded in <head> with defer attribute
 */

// Apply theme IMMEDIATELY to prevent flash (inline in head)
(function() {
    const theme = localStorage.getItem('theme') || 'dark';
    if (theme === 'light') {
        document.documentElement.classList.add('light-mode');
    }
})();

// Main theme toggle functionality (runs when script loads)
(function() {
    'use strict';

    // Get saved theme or default to dark
    const getCurrentTheme = () => localStorage.getItem('theme') || 'dark';

    // Apply theme to document
    const applyTheme = (theme) => {
        if (theme === 'light') {
            document.documentElement.classList.add('light-mode');
            document.body.classList.add('light-mode');
        } else {
            document.documentElement.classList.remove('light-mode');
            document.body.classList.remove('light-mode');
        }

        // Update toggle button icon if it exists
        updateToggleButton(theme);
    };

    // Update toggle button appearance
    const updateToggleButton = (theme) => {
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.textContent = theme === 'light' ? '🌙' : '☀️';
            toggleBtn.setAttribute('aria-label', theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode');
        }
    };

    // Toggle theme
    const toggleTheme = () => {
        const currentTheme = getCurrentTheme();
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    };

    // Setup toggle button when DOM is ready
    const setupToggleButton = () => {
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
            updateToggleButton(getCurrentTheme());
        }
    };

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            applyTheme(getCurrentTheme());
            setupToggleButton();
        });
    } else {
        applyTheme(getCurrentTheme());
        setupToggleButton();
    }

    // Expose toggle function globally
    window.toggleTheme = toggleTheme;
})();
