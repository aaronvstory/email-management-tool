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
let toastStylesApplied = false;

function normalizeToastMessage(raw) {
    if (raw === null || raw === undefined) {
        return '';
    }

    let value = raw;
    if (value instanceof Error) {
        value = value.message || String(value);
    }

    if (typeof value === 'object') {
        try {
            value = JSON.stringify(value, null, 2);
        } catch (_) {
            value = String(value);
        }
    }

    const stringValue = String(value);
    const escaped = stringValue
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    return escaped.replace(/\r?\n/g, '<br>');
}

function ensureToastStyles() {
    if (toastStylesApplied) return;

    let styleBlock = document.getElementById('toast-animations');
    if (!styleBlock) {
        styleBlock = document.createElement('style');
        styleBlock.id = 'toast-animations';
        document.head.appendChild(styleBlock);
    }

    styleBlock.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(25%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .toast-container .toast {
            margin-bottom: 12px;
        }

        .toast-compact {
            position: relative;
            background: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 55%, #242424 100%);
            background-color: var(--toast-bg, rgba(26,26,26,0.94));
            border: 1px solid var(--toast-border-color, #dc2626);
            border-radius: 12px;
            box-shadow: 0 12px 24px rgba(0,0,0,0.55);
            color: #f9fafb;
            min-width: 240px;
            max-width: 400px;
            width: max-content;
            padding: 0;
            overflow: hidden;
            backdrop-filter: blur(14px);
            animation: slideInRight 0.25s ease-out;
        }

        @media (max-width: 576px) {
            .toast-compact {
                width: calc(100vw - 32px);
                max-width: calc(100vw - 32px);
            }
        }

        .toast-compact .toast-inner {
            display: flex;
            align-items: flex-start;
            gap: 14px;
            padding: 14px 18px;
            flex-wrap: nowrap;
            position: relative;
        }

        .toast-compact .toast-icon {
            font-size: 1.1rem;
            color: var(--toast-icon-color, #dc2626);
            margin-top: 2px;
            flex-shrink: 0;
        }

        .toast-compact .toast-message {
            font-size: 0.95rem;
            line-height: 1.5;
            white-space: normal;
            word-break: break-word;
            overflow-wrap: anywhere;
            margin: 0;
            color: inherit;
            max-height: var(--toast-max-height, 220px);
            overflow-y: auto;
            padding-right: 4px;
        }

        .toast-compact .toast-message::-webkit-scrollbar {
            width: 6px;
        }

        .toast-compact .toast-message::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.15);
            border-radius: 8px;
        }

        .toast-compact .toast-message::-webkit-scrollbar-thumb:hover {
            background: rgba(255,255,255,0.25);
        }

        .toast-compact .toast-close {
            position: absolute;
            top: 10px;
            right: 12px;
            transform: scale(0.9);
            opacity: 0.85;
        }

        .toast-compact .toast-close:hover {
            opacity: 1;
        }

        .toast-compact .toast-close:focus {
            outline: none;
            box-shadow: none;
        }

        .toast-compact.toast-confirm {
            border-color: var(--toast-border-color, #f59e0b);
        }

        .toast-compact.toast-confirm .toast-inner {
            flex-direction: column;
            gap: 16px;
            padding: 18px;
        }

        .toast-compact.toast-confirm .toast-header {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            background: transparent;
            border: 0;
            padding: 0;
            margin: 0;
        }

        .toast-compact.toast-confirm .toast-header .toast-message {
            font-weight: 600;
            font-size: 1rem;
        }

        .toast-compact.toast-confirm .toast-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            flex-wrap: wrap;
        }

        .toast-compact.toast-confirm .toast-actions .btn {
            height: 36px;
            padding: 6px 18px;
            min-width: 96px;
            border-radius: 8px;
            font-weight: 600;
        }

        .toast-compact.toast-confirm .toast-actions .btn-secondary {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            color: #f3f4f6;
        }

        .toast-compact.toast-confirm .toast-actions .btn-secondary:hover {
            background: rgba(255,255,255,0.12);
            color: #ffffff;
        }

        .toast-compact.toast-confirm .toast-actions .btn-primary-modern {
            background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
            border: none;
        }
    `;

    toastStylesApplied = true;
}

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
    ensureToastStyles();

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
    const normalizedMessage = normalizeToastMessage(message);

    // Create toast element with dark theme styling
    const toastEl = document.createElement('div');
    toastEl.className = 'toast toast-compact';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.style.setProperty('--toast-border-color', config.border);
    toastEl.style.setProperty('--toast-icon-color', config.iconColor);
    toastEl.style.setProperty('--toast-bg', config.bg);

    toastEl.innerHTML = `
        <div class="toast-inner">
            <i class="toast-icon bi ${config.icon}"></i>
            <div class="toast-message toast-body flex-grow-1">${normalizedMessage}</div>
            <button type="button" class="btn-close btn-close-white toast-close" data-bs-dismiss="toast" aria-label="Close"></button>
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
    ensureToastStyles();

    const toastEl = document.createElement('div');
    toastEl.className = 'toast toast-compact toast-confirm';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    // Critical action styling (darker with prominent border)
    toastEl.style.setProperty('--toast-border-color', '#f59e0b');
    toastEl.style.setProperty('--toast-icon-color', '#f59e0b');
    toastEl.style.setProperty('--toast-bg', 'rgba(251,191,36,0.12)');

    const normalizedMessage = normalizeToastMessage(message);

    toastEl.innerHTML = `
        <div class="toast-inner">
            <div class="toast-header">
                <i class="toast-icon bi bi-exclamation-triangle-fill"></i>
                <div class="toast-message flex-grow-1">${normalizedMessage}</div>
            </div>
            <div class="toast-actions">
                <button type="button" class="btn btn-sm btn-secondary toast-cancel" data-bs-dismiss="toast">Cancel</button>
                <button type="button" class="btn btn-sm btn-primary-modern toast-confirm-cta">Confirm</button>
            </div>
        </div>
    `;

    toastContainer.appendChild(toastEl);

    const bsToast = new bootstrap.Toast(toastEl, {
        autohide: false  // Must manually close
    });

    // Handle confirm button
    const confirmBtn = toastEl.querySelector('.toast-confirm-cta');
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
