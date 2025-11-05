/**
 * Light/Dark Mode Toggle
 * Qunex Trade - Theme Switcher
 */

// Theme toggle functionality
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

    // Apply theme on page load (before content paints to avoid flash)
    applyTheme(getCurrentTheme());

    // Setup toggle button when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupToggleButton);
    } else {
        setupToggleButton();
    }

    function setupToggleButton() {
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
            applyTheme(getCurrentTheme()); // Update button appearance
        }
    }

    // Expose toggle function globally
    window.toggleTheme = toggleTheme;
})();
