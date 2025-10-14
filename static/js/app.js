/**
 * Email Management Tool - Global JavaScript Utilities
 * Modern toast notification system using Bootstrap 5.3
 * CSRF protection for all AJAX requests
 * Follows STYLEGUIDE.md dark theme principles
 */

// ============================================================================
// CSRF Protection - Global Fetch Wrapper
// ============================================================================

/**
 * Get CSRF token from meta tag
 */
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : null;
}

/**
 * Wrap native fetch to automatically include CSRF token for same-origin requests
 */
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    // Only add CSRF for same-origin requests and non-GET/HEAD methods
    const isSameOrigin = !url.startsWith('http') || url.startsWith(window.location.origin);
    const method = (options.method || 'GET').toUpperCase();
    const needsCSRF = isSameOrigin && !['GET', 'HEAD', 'OPTIONS'].includes(method);

    if (needsCSRF) {
        const csrfToken = getCSRFToken();
        if (!csrfToken) {
            console.warn('[CSRF] Token meta tag not found - request may fail:', method, url);
        } else {
            options.headers = options.headers || {};
            if (options.headers instanceof Headers) {
                options.headers.set('X-CSRFToken', csrfToken);
            } else if (typeof options.headers === 'object') {
                options.headers['X-CSRFToken'] = csrfToken;
            }
            try { console.debug('[CSRF] Added token to request:', method, url); } catch (_) {}
        }
    }

    return originalFetch(url, options);
};

// ============================================================================
// Toast Notification System
// ============================================================================

// Toast container - auto-created on first use
let toastContainer = null;

/**
 * Initialize toast container with dark theme styling
 */
function initToastContainer() {
    if (toastContainer) return;

    toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
    toastContainer.style.zIndex = '9999';
    document.body.appendChild(toastContainer);
}

/**
 * Show toast notification with modern dark theme styling
 *
 * @param {string} message - Toast message content
 * @param {string} type - Toast type: 'success', 'error', 'warning', 'info', or 'primary'
 * @param {number} duration - Auto-hide duration in milliseconds (default: 4000, 0 = no auto-hide)
 *
 * @example
 * showToast('Email fetched successfully!', 'success');
 * showToast('Failed to connect to server', 'error');
 * showToast('Are you sure?', 'warning', 0); // No auto-hide
 */
function showToast(message, type = 'info', duration = 4000) {
    initToastContainer();

    // Map types to Bootstrap/theme colors
    const typeConfig = {
        success: {
            bg: 'rgba(34,197,94,0.15)',
            border: '#10b981',
            icon: 'bi-check-circle-fill',
            iconColor: '#10b981'
        },
        error: {
            bg: 'rgba(239,68,68,0.15)',
            border: '#dc2626',
            icon: 'bi-x-circle-fill',
            iconColor: '#dc2626'
        },
        warning: {
            bg: 'rgba(251,191,36,0.15)',
            border: '#f59e0b',
            icon: 'bi-exclamation-triangle-fill',
            iconColor: '#f59e0b'
        },
        info: {
            bg: 'rgba(59,130,246,0.15)',
            border: '#3b82f6',
            icon: 'bi-info-circle-fill',
            iconColor: '#3b82f6'
        },
        primary: {
            bg: 'rgba(220,38,38,0.15)',
            border: '#dc2626',
            icon: 'bi-envelope-fill',
            iconColor: '#dc2626'
        }
    };

    const config = typeConfig[type] || typeConfig.info;

    // Create toast element with dark theme styling
    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    // Dark theme styling following STYLEGUIDE.md
    toastEl.style.cssText = `
        background: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 60%, #242424 100%);
        border: 2px solid ${config.border};
        border-radius: 10px;
        box-shadow: 0 8px 18px rgba(0,0,0,0.55);
        color: #ffffff;
        min-width: 220px;
        max-width: 420px;
        padding: 0;
        overflow: hidden;
        backdrop-filter: blur(10px);
        animation: slideInRight 0.25s ease-out;
    `;

    toastEl.innerHTML = `
        <div class="d-flex" style="align-items:flex-start; column-gap:12px; padding:12px 16px;">
            <i class="bi ${config.icon}" style="font-size: 1.15rem; color: ${config.iconColor}; margin-top:2px;"></i>
            <div class="toast-body flex-grow-1" style="color: #ffffff; font-weight: 500; font-size: 0.92rem; line-height: 1.35; white-space: normal; word-break: break-word;">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close" style="margin-left: 8px; transform: scale(0.85); opacity: 0.75;"></button>
        </div>
    `;

    toastContainer.appendChild(toastEl);

    // Initialize Bootstrap toast
    const bsToast = new bootstrap.Toast(toastEl, {
        autohide: duration > 0,
        delay: duration
    });

    // Show toast
    bsToast.show();

    // Remove from DOM after hidden
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });

    return bsToast;
}

/**
 * Show success toast (green theme)
 */
function showSuccess(message, duration = 4000) {
    return showToast(message, 'success', duration);
}

/**
 * Show error toast (red theme)
 */
function showError(message, duration = 5000) {
    return showToast(message, 'error', duration);
}

/**
 * Show warning toast (orange theme)
 */
function showWarning(message, duration = 5000) {
    return showToast(message, 'warning', duration);
}

/**
 * Show info toast (blue theme)
 */
function showInfo(message, duration = 4000) {
    return showToast(message, 'info', duration);
}

/**
 * Confirm action with toast (requires manual close for critical actions)
 * Returns a Promise that resolves when user interacts
 *
 * @param {string} message - Confirmation message
 * @param {function} onConfirm - Callback when confirmed
 * @param {function} onCancel - Callback when cancelled (optional)
 *
 * @example
 * confirmToast('Delete this email?', () => {
 *     // User confirmed
 *     deleteEmail(id);
 * });
 */
function confirmToast(message, onConfirm, onCancel = null) {
    initToastContainer();

    const toastEl = document.createElement('div');
    toastEl.className = 'toast';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    // Critical action styling (darker with prominent border)
    toastEl.style.cssText = `
        background: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 60%, #242424 100%);
        border: 2px solid #f59e0b;
        border-radius: 10px;
        box-shadow: 0 8px 18px rgba(0,0,0,0.55);
        color: #ffffff;
        min-width: 260px;
        max-width: 420px;
        padding: 0;
        backdrop-filter: blur(10px);
    `;

    toastEl.innerHTML = `
        <div style="padding:14px 16px 12px;">
            <div class="d-flex" style="align-items:flex-start; column-gap:10px; margin-bottom:12px;">
                <i class="bi bi-exclamation-triangle-fill" style="font-size: 1.15rem; color: #f59e0b; margin-top:2px;"></i>
                <div class="flex-grow-1" style="color: #ffffff; font-weight: 600; line-height:1.4;">
                    ${message}
                </div>
            </div>
            <div class="d-flex justify-content-end" style="column-gap:8px;">
                <button class="btn btn-sm btn-secondary toast-cancel" data-bs-dismiss="toast" style="min-width: 80px; height: 32px; padding: 4px 14px;">
                    Cancel
                </button>
                <button class="btn btn-sm btn-primary-modern toast-confirm" style="min-width: 80px; height: 32px; padding: 4px 14px; background: linear-gradient(135deg,#dc2626 0%,#991b1b 50%,#7f1d1d 100%); color: white; border: none;">
                    Confirm
                </button>
            </div>
        </div>
    `;

    toastContainer.appendChild(toastEl);

    const bsToast = new bootstrap.Toast(toastEl, {
        autohide: false  // Must manually close
    });

    // Handle confirm button
    const confirmBtn = toastEl.querySelector('.toast-confirm');
    confirmBtn.addEventListener('click', () => {
        if (onConfirm) onConfirm();
        bsToast.hide();
    });

    // Handle cancel button
    const cancelBtn = toastEl.querySelector('.toast-cancel');
    if (onCancel) {
        cancelBtn.addEventListener('click', () => {
            onCancel();
        });
    }

    // Remove from DOM after hidden
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });

    bsToast.show();
    return bsToast;
}

// Add slideInRight animation
if (!document.getElementById('toast-animations')) {
    const style = document.createElement('style');
    style.id = 'toast-animations';
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .toast-container .toast {
            margin-bottom: 10px;
        }
    `;
    document.head.appendChild(style);
}

// Export for global use
window.showToast = showToast;
window.showSuccess = showSuccess;
window.showError = showError;
window.showWarning = showWarning;
window.showInfo = showInfo;
window.confirmToast = confirmToast;

// ============================================================================
// HTTP helper utilities
// ============================================================================

async function parseResponseBody(response) {
    const cloned = response.clone();
    const contentType = (response.headers.get('content-type') || '').toLowerCase();
    if (contentType.includes('application/json')) {
        try {
            const data = await cloned.json();
            return { format: 'json', body: data };
        } catch (_) {
            // fall through to text
        }
    }
    try {
        const data = await cloned.json();
        return { format: 'json', body: data };
    } catch (_) {
        try {
            const text = await response.text();
            return { format: 'text', body: text };
        } catch (_) {
            return { format: 'text', body: '' };
        }
    }
}

function extractErrorMessage(payload, fallback) {
    if (!payload && payload !== 0) {
        return fallback;
    }
    if (typeof payload === 'string') {
        const trimmed = payload.trim();
        return trimmed || fallback;
    }
    if (typeof payload === 'object') {
        const candidates = ['error', 'reason', 'message', 'detail', 'info', 'statusText'];
        for (const key of candidates) {
            if (payload[key]) {
                const val = String(payload[key]).trim();
                if (val) return val;
            }
        }
        if (payload.body && typeof payload.body === 'string') {
            const val = payload.body.trim();
            if (val) return val;
        }
        if (payload.raw) {
            const val = String(payload.raw).trim();
            if (val) return val;
        }
    }
    return fallback;
}

window.parseResponseBody = parseResponseBody;
window.extractErrorMessage = extractErrorMessage;
