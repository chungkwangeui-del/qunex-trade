/**
 * Google reCAPTCHA v3 Integration
 * Invisible CAPTCHA for better UX
 */

// Configuration
const RECAPTCHA_SITE_KEY = '6LfGavErAAAAAON0YoDr5u_h7ueMDZcNyLMlOH69'; // Qunex Trade reCAPTCHA v3

// Initialize reCAPTCHA on page load
function initRecaptcha() {
    // Load reCAPTCHA script if not already loaded
    if (!window.grecaptcha) {
        const script = document.createElement('script');
        script.src = `https://www.google.com/recaptcha/api.js?render=${RECAPTCHA_SITE_KEY}`;
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
    }
}

// Execute reCAPTCHA for a specific action
async function executeRecaptcha(action) {
    try {
        await new Promise((resolve) => {
            // Wait for grecaptcha to be ready
            const checkRecaptcha = setInterval(() => {
                if (window.grecaptcha && window.grecaptcha.ready) {
                    clearInterval(checkRecaptcha);
                    resolve();
                }
            }, 100);
        });

        // Execute reCAPTCHA
        const token = await new Promise((resolve) => {
            grecaptcha.ready(() => {
                grecaptcha.execute(RECAPTCHA_SITE_KEY, { action: action })
                    .then(resolve);
            });
        });

        return token;
    } catch (error) {
        // reCAPTCHA error - failed to execute
        return null;
    }
}

// Add reCAPTCHA to login form
function protectLoginForm() {
    const loginForm = document.querySelector('form[action*="login"]');
    if (!loginForm) return;

    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Show loading state
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Verifying...';

        try {
            // Get reCAPTCHA token
            const token = await executeRecaptcha('login');

            if (!token) {
                throw new Error('reCAPTCHA verification failed');
            }

            // Add token to form
            let tokenInput = this.querySelector('input[name="recaptcha_token"]');
            if (!tokenInput) {
                tokenInput = document.createElement('input');
                tokenInput.type = 'hidden';
                tokenInput.name = 'recaptcha_token';
                this.appendChild(tokenInput);
            }
            tokenInput.value = token;

            // Submit form
            this.submit();
        } catch (error) {
            if (window.showToast) {
                showToast('Security verification failed. Please try again.', 'error');
            } else {
                alert('Security verification failed. Please try again.');
            }
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
}

// Add reCAPTCHA to signup form
function protectSignupForm() {
    const signupForm = document.querySelector('form[action*="signup"]');
    if (!signupForm) return;

    signupForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Show loading state
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Verifying...';

        try {
            // Get reCAPTCHA token
            const token = await executeRecaptcha('signup');

            if (!token) {
                throw new Error('reCAPTCHA verification failed');
            }

            // Add token to form
            let tokenInput = this.querySelector('input[name="recaptcha_token"]');
            if (!tokenInput) {
                tokenInput = document.createElement('input');
                tokenInput.type = 'hidden';
                tokenInput.name = 'recaptcha_token';
                this.appendChild(tokenInput);
            }
            tokenInput.value = token;

            // Submit form
            this.submit();
        } catch (error) {
            if (window.showToast) {
                showToast('Security verification failed. Please try again.', 'error');
            } else {
                alert('Security verification failed. Please try again.');
            }
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
}

// Add reCAPTCHA to forgot password form
function protectForgotPasswordForm() {
    const forgotForm = document.querySelector('form[action*="forgot-password"]');
    if (!forgotForm) return;

    forgotForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Verifying...';

        try {
            const token = await executeRecaptcha('forgot_password');

            if (!token) {
                throw new Error('reCAPTCHA verification failed');
            }

            let tokenInput = this.querySelector('input[name="recaptcha_token"]');
            if (!tokenInput) {
                tokenInput = document.createElement('input');
                tokenInput.type = 'hidden';
                tokenInput.name = 'recaptcha_token';
                this.appendChild(tokenInput);
            }
            tokenInput.value = token;

            this.submit();
        } catch (error) {
            if (window.showToast) {
                showToast('Security verification failed. Please try again.', 'error');
            } else {
                alert('Security verification failed. Please try again.');
            }
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if on a page with forms
    if (document.querySelector('form')) {
        initRecaptcha();

        // Wait a bit for reCAPTCHA to load
        setTimeout(() => {
            protectLoginForm();
            protectSignupForm();
            protectForgotPasswordForm();
        }, 1000);
    }
});

// Add reCAPTCHA badge styling
const style = document.createElement('style');
style.textContent = `
    .grecaptcha-badge {
        visibility: visible !important;
        opacity: 0.5;
        transition: opacity 0.3s;
    }

    .grecaptcha-badge:hover {
        opacity: 1;
    }
`;
document.head.appendChild(style);
