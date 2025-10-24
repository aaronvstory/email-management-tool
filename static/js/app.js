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
            // Build new Headers to avoid mutating possibly read-only objects
            const hdrs = new Headers(options && options.headers ? options.headers : undefined);
            hdrs.set('X-CSRFToken', csrfToken);
            const opts = Object.assign({}, options, { headers: hdrs });
            try { console.debug('[CSRF] Added token to request:', method, url); } catch (_) {}
            return originalFetch(url, opts);
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

    return escaped
        .replace(/\r?\n/g, '<br>')
        .replace(/\s{2,}/g, match => '&nbsp;'.repeat(match.length));
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
            background: var(--surface-highest);
            background-color: var(--toast-bg, rgba(26,26,26,0.94));
            border: 1px solid var(--toast-border-color, #dc2626);
            border-radius: 12px;
            box-shadow: 0 12px 24px rgba(0,0,0,0.55);
            color: #f9fafb;
            min-width: 240px;
            max-width: 400px;
            width: max-content;
            padding: 0;
            overflow: visible;
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
            align-items: center;
            gap: 12px;
            padding: 14px 44px 14px 18px;
            flex-wrap: nowrap;
        }

        .toast-compact .toast-icon {
            font-size: 1.1rem;
            color: var(--toast-icon-color, #dc2626);
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
        }

        .toast-compact .toast-message {
            font-size: 0.95rem;
            line-height: 1.5;
            white-space: normal;
            word-break: break-word;
            overflow-wrap: anywhere;
            margin: 0;
            color: #f9fafb !important;
            max-height: var(--toast-max-height, 220px);
            overflow-y: auto;
            padding-right: 4px;
            flex: 1;
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

        /* Removed close button entirely to prevent overlap issues */
        .toast-compact > .btn-close { display: none !important; }
        .toast-compact .btn-close { display: none !important; }

        .toast-compact.toast-confirm {
            border-color: var(--toast-border-color, #f59e0b);
        }

        .toast-compact.toast-confirm .toast-inner {
            flex-direction: column;
            align-items: stretch;
            gap: 16px;
            padding: 20px 20px 18px 20px;
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
            color: #f9fafb !important;
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
            background: rgba(220,38,38,0.18);
            border: 1px solid rgba(220,38,38,0.35);
            color: #fef2f2;
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
            <span class="toast-icon bi ${config.icon}" aria-hidden="true"></span>
            <div class="toast-message toast-body">${normalizedMessage}</div>
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
// Attachments module
// ============================================================================

(function attachModuleNamespace() {
    const flags = window.ATTACHMENTS_FLAGS || {};
    const cache = new Map();

    const defaultEscape = (value) => {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };
    const escapeHtml = window.MailOps && typeof window.MailOps.escapeHtml === 'function'
        ? window.MailOps.escapeHtml
        : defaultEscape;

    function isEnabled() {
        return !!flags.ui;
    }

    function formatSize(bytes) {
        const size = Number(bytes || 0);
        if (!size) return '';
        const units = ['B', 'KB', 'MB', 'GB'];
        let idx = 0;
        let value = size;
        while (value >= 1024 && idx < units.length - 1) {
            value /= 1024;
            idx += 1;
        }
        return `${value.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`;
    }

    function toggleElement(el, show) {
        if (!el) return;
        el.classList.toggle('hidden', !show);
    }

    function applyError(container, message) {
        if (container) container.classList.add('attachments-error');
        if (window.showError) window.showError(message);
    }

    async function fetchAttachments(emailId) {
        if (cache.has(emailId)) {
            return cache.get(emailId);
        }

        const response = await fetch(`/api/email/${emailId}/attachments`);
        let data = null;
        try {
            data = await response.json();
        } catch (_) {
            data = null;
        }
        if (!response.ok || !data || data.ok === false) {
            const reason = (data && (data.error || data.reason)) || `HTTP ${response.status}`;
            throw new Error(reason);
        }
        cache.set(emailId, data);
        return data;
    }

    function renderList(options, attachments) {
        const listEl = options.listElement;
        const emptyEl = options.emptyElement;
        if (!listEl) return;

        if (!attachments || attachments.length === 0) {
            listEl.innerHTML = '';
            toggleElement(emptyEl, true);
            return;
        }

        const rows = attachments.map(att => {
            const badge = att.is_staged ? '<span class="attachment-pill">Staged</span>' : '';
            const sizeLabel = formatSize(att.size);
            const sizeHtml = sizeLabel ? `<span class="attachment-size">${escapeHtml(sizeLabel)}</span>` : '';
            return `
                <div class="attachment-item-row">
                    <div class="attachment-meta">
                        <i class="bi bi-paperclip"></i>
                        <span class="attachment-name">${escapeHtml(att.filename || 'attachment')}</span>
                        ${badge}
                        ${sizeHtml}
                    </div>
                    <div class="attachment-actions">
                        <button type="button" class="btn btn-ghost btn-sm" onclick="window.MailAttach.download(${att.id})">
                            <i class="bi bi-download"></i> Download
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        listEl.innerHTML = rows;
        toggleElement(emptyEl, false);
    }

    async function render(options = {}) {
        const emailId = options.emailId;
        const container = options.container || null;
        const skeletonEl = options.skeletonElement || null;
        if (!emailId || !isEnabled()) {
            if (container) container.classList.add('hidden');
            return;
        }
        if (container) {
            container.classList.remove('hidden');
            container.classList.remove('attachments-error');
        }
        if (skeletonEl) skeletonEl.classList.remove('hidden');
        toggleElement(options.emptyElement, false);

        try {
            const payload = await fetchAttachments(emailId);
            renderList(options, payload.attachments || []);
        } catch (error) {
            applyError(container, `Failed to load attachments: ${error.message}`);
        } finally {
            if (skeletonEl) skeletonEl.classList.add('hidden');
        }
    }

    function download(attachmentId) {
        if (!attachmentId) return;
        window.location.href = `/api/attachment/${attachmentId}/download`;
    }

    window.MailAttach = {
        render,
        download,
        _fetch: fetchAttachments,
    };
})();

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

// ============================================================================
// Formatting & HTML helpers
// ============================================================================
window.MailOps = window.MailOps || {};

(function(util) {
  util.escapeHtml = function(value) {
    if (value === null || value === undefined) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  };

  util.normalizeTimestamp = function(value) {
    if (!value) return null;
    const raw = typeof value === 'string' ? value.trim() : value;
    if (typeof raw === 'string' && raw.length && raw.includes(' ') && !raw.includes('T')) {
      return raw.replace(' ', 'T');
    }
    return raw;
  };

  util.formatTimestamp = function(ts, options) {
    if (!ts) return '—';
    const normalized = util.normalizeTimestamp(ts);
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return ts;
    const formatterOptions = options || { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true };
    return date.toLocaleString('en-US', formatterOptions);
  };

  util.renderTimeCell = function(ts, fallback = '—') {
    if (!ts) return fallback;
    const normalized = util.normalizeTimestamp(ts) || ts;
    return `<span class="time-cell" data-ts="${util.escapeHtml(normalized)}">${util.escapeHtml(String(ts))}</span>`;
  };

  util.applyTimeFormatting = function(root) {
    const scope = root || document;
    scope.querySelectorAll('.time-cell').forEach(node => {
      const ts = node.dataset.ts || node.textContent;
      if (!ts) {
        node.textContent = '—';
        return;
      }
      node.dataset.ts = ts;
      node.textContent = util.formatTimestamp(ts);
    });
  };
})(window.MailOps);

