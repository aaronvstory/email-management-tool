### **Implementation Plan: Unifying Email Styling in `templates/emails_unified.html`**

**Goal:** Replicate the visual design, spacing, typography, color scheme, and interactive behavior of `stitch-dashboard/email_management/email-management.html` in `templates/emails_unified.html` without disrupting existing logic, templating directives, or data bindings.

**Phase 1: Global Styling & Assets Integration**

1.  **Update `templates/base.html` (or `emails_unified.html` header):**
    *   **Action:** Add Google Fonts `<link>` tags for `Roboto` and `Material Symbols Outlined`.
    *   **Action:** Ensure the `html` tag has the `class="dark"` attribute for consistent dark mode application.
    *   **Action:** Modify the `body` tag to include `font-display bg-background-light dark:bg-background-dark text-slate-300 dark:text-slate-300 antialiased` classes (or their custom CSS equivalents).

2.  **Create/Update `static/css/unified.css` (or `main.css`):**
    *   **Action:** Define CSS variables for the custom colors and font family identified from the Tailwind config in `email-management.html`.
        *   `--primary: #bef264;`
        *   `--background-dark: #18181b;`
        *   `--surface-dark: #27272a;`
        *   `--zinc-700: #3f3f46;`
        *   `--zinc-800: #27272a;`
        *   `--zinc-900: #18181b;`
        *   `--zinc-300: #d4d4d8;`
        *   `--zinc-400: #a1a1aa;`
        *   `--white: #ffffff;`
        *   `--font-display: 'Roboto', sans-serif;`
    *   **Action:** Implement the `material-symbols-outlined` font-variation-settings:
        ```css
        .material-symbols-outlined {
            font-variation-settings:
            'FILL' 0,
            'wght' 400,
            'GRAD' 0,
            'opsz' 20;
        }
        ```
    *   **Action:** Create utility classes that mimic essential Tailwind classes (e.g., `bg-surface-dark`, `border-zinc-700`, `text-zinc-400`, `focus:ring-primary`, `hover:bg-lime-400`, `transition-colors`, `shadow-sm`, `rounded-full`, `border-2`, `border-transparent`, `duration-200`, `ease-in-out`, `focus:outline-none`, `focus:ring-2`, `focus:ring-offset-2`, `dark:focus:ring-offset-surface-dark`).
    *   **Action:** Override default Bootstrap styles for form elements, buttons, tables, and modals to align with the new design system.

**Phase 2: HTML Structure & Class Adjustments in `templates/emails_unified.html`**

1.  **Main Content Area:**
    *   **Action:** Wrap the entire content block (inside `{% block content %}`) with a `div` having classes `flex-1 flex flex-col overflow-y-auto` to match the dashboard's main content layout.

2.  **Header/Title Section (Email Management):**
    *   **Action:** Update the outer `div.panel-card` to `div` with classes `flex flex-col md:flex-row md:items-center md:justify-between gap-4`.
    *   **Action:** Modify the `panel-title` to `h1` with classes `text-3xl font-bold text-white flex items-center gap-3`.
    *   **Action:** Replace `<i class="bi bi-envelope-fill"></i>` with `<span class="material-symbols-outlined text-3xl text-primary">inbox</span>`.
    *   **Action:** Update the `panel-body p` to `p` with classes `mt-1 text-zinc-400`.
    *   **Action:** Restyle the "Compose" button (`btn btn-secondary btn-sm`) to `button` with classes `flex-shrink-0 bg-primary text-zinc-900 font-semibold py-2 px-4 shadow-sm hover:bg-lime-400 transition-colors flex items-center gap-2`. Replace `<i class="bi bi-pencil-square"></i>` with `<span class="material-symbols-outlined text-lg">edit_square</span>`.

3.  **Account Selector with Fetch Controls:**
    *   **Action:** Update the `div.account-selector.selector-card` to `div` with classes `bg-surface-dark p-6 border border-zinc-700`.
    *   **Action:** Modify the inner structure to `div` with classes `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 items-end`.
    *   **Action:** Update labels (`form-label`) to `label` with classes `block text-sm font-medium text-zinc-300 mb-1`.
    *   **Action:** Update `select.form-select` and `input.form-control` to include classes `w-full border-zinc-600 bg-zinc-800 text-zinc-200 focus:ring-primary focus:border-primary`.
    *   **Action:** Restyle "Fetch" button (`btn btn-primary btn-sm`) to `button` with classes `bg-primary text-zinc-900 font-semibold py-2 px-4 shadow-sm hover:bg-lime-400 transition-colors flex items-center gap-2`. Replace `<i class="bi bi-cloud-download"></i>` with `<span class="material-symbols-outlined text-lg">cloud_download</span>`.
    *   **Action:** Restyle "More" button (`btn btn-secondary btn-sm`) to `button` with classes `bg-zinc-700 text-zinc-200 font-semibold py-2 px-4 hover:bg-zinc-600 transition-colors flex items-center gap-2`. Replace `<i class="bi bi-plus-circle"></i>` with `<span class="material-symbols-outlined text-lg">add</span>`.

4.  **Unified Email Panel (Tabs, Search, Auto-Refresh):**
    *   **Action:** Update the outer `div.panel` to `div` with classes `bg-surface-dark border border-zinc-700`.
    *   **Action:** Modify the `panel-header` to `div` with classes `p-4 md:p-6 border-b border-zinc-700 flex items-center justify-between`.
    *   **Action:** Update `panel-title` to `h2` with classes `text-xl font-semibold text-white`. Replace `<i class="bi bi-inboxes"></i>` with `<span class="material-symbols-outlined text-3xl text-primary">inbox</span>`.
    *   **Action:** Restyle "Refresh" button (`btn btn-secondary btn-sm`) to `button` with classes `text-zinc-400 hover:text-primary font-semibold text-sm flex items-center gap-2`. Replace `<i class="bi bi-arrow-clockwise"></i>` with `<span class="material-symbols-outlined text-lg">refresh</span>`.
    *   **Action:** Replace `div.status-tabs` with `div` having classes `px-4 md:px-6 border-b border-zinc-700`. Inside, replace the `button.status-tab` elements with `a` tags (or `button` if functionality requires) using classes:
        *   Active: `shrink-0 border-b-2 border-primary text-primary px-1 py-3 text-sm font-semibold flex items-center gap-2`
        *   Inactive: `shrink-0 border-b-2 border-transparent text-zinc-400 hover:border-zinc-500 hover:text-zinc-200 px-1 py-3 text-sm font-medium flex items-center gap-2`
        *   Replace `i.bi` icons with `span.material-symbols-outlined`.
        *   Update `span.badge` to `span` with classes `bg-primary/10 text-primary text-xs font-bold px-2 py-0.5` (active) or `bg-zinc-800 text-zinc-300 text-xs font-bold px-2 py-0.5` (inactive).
    *   **Action:** Update `div.filters-bar` to `div` with classes `p-4 md:p-6`. Inside, update `div.filter-control` to `div` with classes `flex flex-col sm:flex-row gap-4 items-center`.
    *   **Action:** For the search input, update `div.input-with-icon.emails-search` to `div` with classes `relative w-full`. Replace `i.bi.bi-search.input-icon` with `span.material-symbols-outlined.absolute.left-3.top-1/2.-translate-y-1/2.text-zinc-500`. Update `input.form-control` to `input` with classes `w-full pl-10 pr-4 py-2 border-zinc-600 bg-zinc-800 text-zinc-200 focus:ring-primary focus:border-primary`.
    *   **Action:** For auto-refresh, update `div.filter-control.compact-switch` to `div` with classes `flex items-center gap-2 flex-shrink-0`. Replace `label.form-switch` with `label` with classes `text-sm font-medium text-zinc-400` and the toggle button with `button` having classes `bg-zinc-700 relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 dark:focus:ring-offset-surface-dark`.

5.  **Email Table:**
    *   **Action:** Update `div.table-responsive-modern` to `div` with classes `overflow-x-auto`.
    *   **Action:** Update `table.table-modern.email-table` to `table` with classes `w-full text-sm`.
    *   **Action:** Update `thead` to `thead` with classes `bg-zinc-800`.
    *   **Action:** Update `th` elements to include classes `p-4 font-semibold text-left text-zinc-400 uppercase tracking-wider`. The checkbox `th` should have `p-4 w-4`.
    *   **Action:** Update `tbody` to `tbody` with classes `divide-y divide-zinc-700`.
    *   **Action:** Update `tr` elements to include `hover:bg-zinc-800/50`.
    *   **Action:** Update checkboxes (`form-check-input`) to `input` with classes `border-zinc-600 text-primary focus:ring-primary/50 bg-zinc-700`.
    *   **Action:** Adjust `td` elements for padding and text colors (`text-zinc-400`, `font-medium text-zinc-200`, `font-semibold text-white`, `text-primary hover:underline`).
    *   **Action:** Update status badges (`status-badge`) to `span` with classes `inline-flex items-center text-xs font-semibold px-2.5 py-1 bg-yellow-500/20 text-yellow-300` (for HELD) and `bg-blue-500/20 text-blue-300` (for POLLING).
    *   **Action:** Update action buttons (`action-btn`) to `button` with classes `p-2 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200`. Replace `i.bi` icons with `span.material-symbols-outlined`.

6.  **Modals (Edit Email, Attachments Summary, Batch Progress):**
    *   **Action:** For all modals, ensure the `modal-dialog` has `modal-lg modal-unified` and the `modal-content` is styled with `bg-surface-dark border border-zinc-700` (via custom CSS).
    *   **Action:** Update `modal-title` to `h5` with `text-white`. Replace `i.bi` icons with `span.material-symbols-outlined`.
    *   **Action:** Update form labels (`form-label fw-bold`) to `label` with classes `block text-sm font-medium text-zinc-300 mb-1`.
    *   **Action:** Update form inputs (`form-control`, `form-control-plaintext`, `textarea`) to include classes `w-full border-zinc-600 bg-zinc-800 text-zinc-200 focus:ring-primary focus:border-primary`.
    *   **Action:** Restyle modal footer buttons to match the new button palette (`btn btn-secondary`, `btn btn-primary`, `btn btn-success`, `btn btn-ghost`).
    *   **Action:** Update the `alert alert-info alert-modern` to a `div` with classes `alert alert-info alert-modern` (or custom CSS equivalent for dark theme).
    *   **Action:** For the attachment summary cards (`summary-count-card`), apply styling similar to `stat-card-modern` or a simple `bg-surface-dark p-4 border border-zinc-700` with appropriate text colors.