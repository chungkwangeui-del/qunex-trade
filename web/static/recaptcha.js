/**
 * Google reCAPTCHA v3 Integration
 * Invisible CAPTCHA for better UX
 */

// Configuration
const RECAPTCHA_SITE_KEY = '6LfGavErAAAAAON0YoDr5u_h7ueMDZcNyLMlOH69'; // Qunex Trade reCAPTCHA v3
const RECAPTCHA_TIMEOUT_MS = 5000; // 5 second timeout for reCAPTCHA

// Track if reCAPTCHA loaded successfully
let recaptchaLoaded = false;
let recaptchaLoadFailed = false;

// Initialize reCAPTCHA on page load
function initRecaptcha() {
    // Load reCAPTCHA script if not already loaded
    if (!window.grecaptcha) {
        const script = document.createElement('script');
        script.src = `https://www.google.com/recaptcha/api.js?render=${RECAPTCHA_SITE_KEY}`;
        script.async = true;
        script.defer = true;

        // Mark as loaded when script loads successfully
        script.onload = () => {
            recaptchaLoaded = true;
        };

        // Mark as failed if script fails to load
        script.onerror = () => {
            recaptchaLoadFailed = true;
            console.warn('reCAPTCHA failed to load - forms will submit without verification');
        };

        document.head.appendChild(script);

        // Set a timeout - if reCAPTCHA doesn't load in time, allow forms to work
        setTimeout(() => {
            if (!recaptchaLoaded && !recaptchaLoadFailed) {
                recaptchaLoadFailed = true;
                console.warn('reCAPTCHA load timeout - forms will submit without verification');
            }
        }, RECAPTCHA_TIMEOUT_MS);
    }
}

// Execute reCAPTCHA for a specific action
async function executeRecaptcha(action) {
    // If reCAPTCHA failed to load, return special token to indicate bypass
    if (recaptchaLoadFailed) {
        return 'RECAPTCHA_BYPASS_CLIENT_LOAD_FAILED';
    }

    try {
        // Wait for grecaptcha with timeout
        await new Promise((resolve, reject) => {
            const startTime = Date.now();
            const checkRecaptcha = setInterval(() => {
                if (window.grecaptcha && window.grecaptcha.ready) {
                    clearInterval(checkRecaptcha);
                    resolve();
                } else if (Date.now() - startTime > RECAPTCHA_TIMEOUT_MS) {
                    clearInterval(checkRecaptcha);
                    reject(new Error('reCAPTCHA timeout'));
                }
            }, 100);
        });

        // Execute reCAPTCHA with timeout
        const token = await Promise.race([
            new Promise((resolve) => {
                grecaptcha.ready(() => {
                    grecaptcha.execute(RECAPTCHA_SITE_KEY, { action: action })
                        .then(resolve)
                        .catch(() => resolve('RECAPTCHA_BYPASS_EXECUTE_FAILED'));
                });
            }),
            new Promise((resolve) => {
                setTimeout(() => resolve('RECAPTCHA_BYPASS_TIMEOUT'), RECAPTCHA_TIMEOUT_MS);
            })
        ]);

        return token;
    } catch (error) {
        // reCAPTCHA error - return bypass token
        console.warn('reCAPTCHA error:', error.message);
        return 'RECAPTCHA_BYPASS_ERROR';
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
        submitBtn.innerHTML = '<span class="spinner"></span> Signing in...';

        // Get reCAPTCHA token (will return bypass token if reCAPTCHA unavailable)
        const token = await executeRecaptcha('login');

        // Add token to form (always - even bypass tokens)
        let tokenInput = this.querySelector('input[name="recaptcha_token"]');
        if (!tokenInput) {
            tokenInput = document.createElement('input');
            tokenInput.type = 'hidden';
            tokenInput.name = 'recaptcha_token';
            this.appendChild(tokenInput);
        }
        tokenInput.value = token || 'RECAPTCHA_BYPASS_NO_TOKEN';

        // Submit form
        this.submit();
    });
}

// Add reCAPTCHA to signup form
function protectSignupForm() {
    const signupForm = document.querySelector('form[action*="signup"]');
    if (!signupForm) return;

    signupForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Client-side validation first
        const password = this.querySelector('#password')?.value;
        const confirmPassword = this.querySelector('#confirm_password')?.value;

        if (password && confirmPassword && password !== confirmPassword) {
            alert('Passwords do not match!');
            return;
        }

        if (password && password.length < 8) {
            alert('Password must be at least 8 characters long!');
            return;
        }

        // Show loading state
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Creating account...';

        // Get reCAPTCHA token (will return bypass token if reCAPTCHA unavailable)
        const token = await executeRecaptcha('signup');

        // Add token to form (always - even bypass tokens)
        let tokenInput = this.querySelector('input[name="recaptcha_token"]');
        if (!tokenInput) {
            tokenInput = document.createElement('input');
            tokenInput.type = 'hidden';
            tokenInput.name = 'recaptcha_token';
            this.appendChild(tokenInput);
        }
        tokenInput.value = token || 'RECAPTCHA_BYPASS_NO_TOKEN';

        // Submit form
        this.submit();
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
        submitBtn.innerHTML = '<span class="spinner"></span> Sending...';

        // Get reCAPTCHA token (will return bypass token if reCAPTCHA unavailable)
        const token = await executeRecaptcha('forgot_password');

        // Add token to form (always - even bypass tokens)
        let tokenInput = this.querySelector('input[name="recaptcha_token"]');
        if (!tokenInput) {
            tokenInput = document.createElement('input');
            tokenInput.type = 'hidden';
            tokenInput.name = 'recaptcha_token';
            this.appendChild(tokenInput);
        }
        tokenInput.value = token || 'RECAPTCHA_BYPASS_NO_TOKEN';

        // Submit form
        this.submit();
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
