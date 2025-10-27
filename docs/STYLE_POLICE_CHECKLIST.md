# Style Police Checklist for PRs

**Version**: 1.0
**Last Updated**: October 27, 2025
**Applies To**: All UI changes, CSS modifications, and template updates

---

## Purpose

This checklist ensures all UI changes maintain consistency with our design system and visual standards. Use this for:
- Pull request reviews
- Self-review before committing UI changes
- Design system compliance validation

---

## 1. Design System Token Usage

### ✅ Required: Use Design Tokens, Never Hardcode

**CSS Variables** (from `design-system.css`):

```css
/* ✅ CORRECT - Use design tokens */
.my-component {
  background: var(--surface-elevated);
  border: 1px solid var(--border-subtle);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  color: var(--text-primary);
}

/* ❌ WRONG - Hardcoded values */
.my-component {
  background: #1e1e1e;
  border: 1px solid rgba(255,255,255,0.1);
  padding: 16px;
  border-radius: 8px;
  color: #ffffff;
}
```

**Checklist**:
- [ ] All colors use `--text-*`, `--surface-*`, or `--accent-*` variables
- [ ] All spacing uses `--space-*` variables (1-8 scale)
- [ ] All border-radius uses `--radius-*` variables (sm, md, lg)
- [ ] All shadows use `--shadow-*` variables (sm, md, lg)
- [ ] All transitions use `--transition-*` variables (fast, base, slow)

---

## 2. Layout Patterns

### Section Rhythm
**Rule**: 24px outer margin, 16px inner padding, 24px bottom margin

```html
<!-- ✅ CORRECT -->
<section class="section">
  <h2>Section Title</h2>
  <div class="content">
    <!-- Content -->
  </div>
</section>

<!-- ❌ WRONG - Custom spacing -->
<div style="margin: 30px 0; padding: 20px;">
  <h2>Section Title</h2>
</div>
```

**Checklist**:
- [ ] Use `.section` class for all major page sections
- [ ] No inline `margin` or `padding` styles
- [ ] Consistent 24px outer / 16px inner rhythm maintained

### Grid Layouts
**Rule**: Use design system grid classes, avoid custom grids

```html
<!-- ✅ CORRECT - Design system grid -->
<div class="stats-grid stats-5">
  <div class="stat-card-modern">...</div>
  <div class="stat-card-modern">...</div>
  <div class="stat-card-modern">...</div>
  <div class="stat-card-modern">...</div>
  <div class="stat-card-modern">...</div>
</div>

<!-- ❌ WRONG - Custom grid -->
<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px;">
  <div class="card">...</div>
</div>
```

**Available Grid Classes**:
- `.stats-grid` - Base grid container
- `.stats-3` - 3-column stat cards
- `.stats-5` - 5-column stat cards (responsive)

**Checklist**:
- [ ] Use `.stats-grid` for stat card layouts
- [ ] Add `.stats-3` or `.stats-5` for column count
- [ ] No custom `display: grid` or `grid-template-columns` in components

---

## 3. Component Standards

### Hero Cards
**Rule**: Use `.hero-card` for prominent page headers

```html
<!-- ✅ CORRECT -->
<div class="hero-card">
  <h1>Page Title</h1>
  <div class="hero-badges">
    <span class="badge-primary">Badge 1</span>
    <span class="badge-secondary">Badge 2</span>
  </div>
</div>
```

**Checklist**:
- [ ] Page title is in `.hero-card` if prominent header needed
- [ ] Badges use `.hero-badges` container
- [ ] Hero card uses design system classes only

### Stat Cards
**Rule**: Use `.stat-card-modern` for all statistics

```html
<!-- ✅ CORRECT -->
<div class="stat-card-modern">
  <div class="stat-value">403</div>
  <div class="stat-label">Total Emails</div>
</div>

<!-- Add state classes for emphasis -->
<div class="stat-card-modern held">...</div>
<div class="stat-card-modern released">...</div>
```

**Available State Classes**:
- `.held` - Orange accent (warning)
- `.released` - Green accent (success)
- `.rejected` - Red accent (danger)

**Checklist**:
- [ ] Use `.stat-card-modern` for all stat displays
- [ ] Value in `.stat-value`, label in `.stat-label`
- [ ] State classes (held/released/rejected) used appropriately

### Form Controls
**Rule**: Use `.input-modern` for all inputs

```html
<!-- ✅ CORRECT -->
<input type="text" class="input-modern" placeholder="Enter email...">
<select class="input-modern">
  <option>Option 1</option>
</select>

<!-- ❌ WRONG - Bootstrap form-control -->
<input type="text" class="form-control" placeholder="Enter email...">
```

**Checklist**:
- [ ] All `<input>` elements use `.input-modern`
- [ ] All `<select>` elements use `.input-modern`
- [ ] All `<textarea>` elements use `.input-modern`
- [ ] No Bootstrap `.form-control` class used

### Buttons
**Rule**: Use design system button classes

```html
<!-- ✅ CORRECT -->
<button class="btn btn-primary">Primary Action</button>
<button class="btn btn-secondary">Secondary Action</button>
<button class="btn btn-ghost">Tertiary Action</button>

<!-- ❌ WRONG - Custom button styles -->
<button style="background: blue; color: white;">Action</button>
```

**Checklist**:
- [ ] All buttons have `.btn` base class
- [ ] Primary actions use `.btn-primary`
- [ ] Secondary actions use `.btn-secondary`
- [ ] Tertiary actions use `.btn-ghost`
- [ ] Destructive actions use `.btn-danger`

---

## 4. CSS Architecture Rules

### !important Usage
**Rule**: NEVER use `!important` except in documented allowlist

```css
/* ❌ WRONG - Never add new !important */
.my-component {
  color: white !important;
  padding: 16px !important;
}

/* ✅ CORRECT - Use specificity and cascade */
.my-component {
  color: var(--text-primary);
  padding: var(--space-4);
}
```

**Why**: We spent an entire day (Oct 27, 2025) removing 106 `!important` declarations. Adding more creates specificity wars and unmaintainable CSS.

**Checklist**:
- [ ] Zero new `!important` declarations added
- [ ] If override needed, use scoping (e.g., `body.page-name .component`)
- [ ] Verify with: `python scripts/count_important.py static/css/main.css`

### @layer Architecture
**Rule**: All new CSS must be in appropriate @layer

```css
/* ✅ CORRECT - Use @layer */
@layer components {
  .my-new-component {
    background: var(--surface-elevated);
  }
}

/* ❌ WRONG - Global scope */
.my-new-component {
  background: var(--surface-elevated);
}
```

**Layer Priority**: `reset < base < components < utilities`

**Checklist**:
- [ ] New CSS rules wrapped in `@layer components`
- [ ] Utility classes in `@layer utilities` if truly universal
- [ ] No CSS in global scope (outside layers)

### Specificity Limit
**Rule**: Keep specificity ≤ 0,3,0 (no more than 3 classes)

```css
/* ✅ CORRECT - Specificity 0,2,0 */
.hero-card .hero-badges {
  display: flex;
}

/* ⚠️ WARNING - Specificity 0,4,0 (avoid) */
.section .hero-card .hero-badges .badge-primary {
  color: blue;
}

/* ❌ WRONG - Specificity 0,0,1 + ID (never use) */
#my-unique-id {
  color: red;
}
```

**Checklist**:
- [ ] Selectors have ≤ 3 classes deep
- [ ] No ID selectors used
- [ ] No element selectors combined with classes (e.g., avoid `div.card`)

---

## 5. Responsive Design

### Breakpoints
**Rule**: Use design system breakpoints

```css
/* ✅ CORRECT - Design system breakpoints */
@media (max-width: 768px) {
  .stats-grid.stats-5 {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 390px) {
  .stats-grid.stats-5 {
    grid-template-columns: 1fr;
  }
}
```

**Standard Breakpoints**:
- Desktop: ≥1024px
- Tablet: 768px - 1023px
- Mobile: <768px
- Small Mobile: <390px

**Checklist**:
- [ ] Components tested at 1440px, 1024px, 768px, 390px
- [ ] No horizontal scroll at any breakpoint
- [ ] Touch targets ≥44px on mobile
- [ ] Text readable without zoom

### Stat Card Responsiveness
**Rule**: Follow 3-2-1 pattern

```
≥1024px: 5 columns (or 3 for stats-3)
768-1023px: 2 columns
<768px: 1 column (stacked)
```

**Checklist**:
- [ ] `.stats-5` shows 5 columns at desktop
- [ ] `.stats-5` shows 2 columns at tablet
- [ ] `.stats-5` shows 1 column at mobile
- [ ] Cards maintain consistent height across rows

---

## 6. Dark Theme Compliance

### Background Attachment
**Rule**: Always use `background-attachment: fixed` on body

```css
/* ✅ CORRECT - Fixed background */
body {
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
  background-attachment: fixed;
}

/* ❌ WRONG - Scroll background (causes white flashes) */
body {
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
}
```

**Why**: Prevents white screen flashes when scrolling on dark theme.

**Checklist**:
- [ ] `background-attachment: fixed` present on body/html
- [ ] No pure white backgrounds anywhere
- [ ] All loading states use dark backgrounds

### Color Contrast
**Rule**: Maintain WCAG AA contrast ratios

**Minimum Ratios**:
- Normal text: 4.5:1
- Large text (18px+): 3:1
- Interactive elements: 3:1

**Checklist**:
- [ ] Text on backgrounds meets 4.5:1 contrast
- [ ] Buttons/links meet 3:1 contrast
- [ ] Disabled states clearly distinguishable
- [ ] No low-opacity text on low-opacity backgrounds

---

## 7. Toast Notifications

### Never Use Browser Alerts
**Rule**: Use Bootstrap 5 toasts, never `alert()` or `confirm()`

```javascript
// ✅ CORRECT - Bootstrap toast
if (window.showSuccess) {
  window.showSuccess('Operation completed successfully');
}

// ❌ WRONG - Browser alert
alert('Operation completed successfully');
```

**Available Functions** (from `static/js/app.js`):
- `window.showSuccess(message)`
- `window.showError(message)`
- `window.showWarning(message)`
- `window.showInfo(message)`

**Checklist**:
- [ ] No `alert()`, `confirm()`, or `prompt()` calls
- [ ] Success messages use `window.showSuccess()`
- [ ] Error messages use `window.showError()`
- [ ] Warnings use `window.showWarning()`

### Confirmation Prompts
**Rule**: Only confirm destructive actions

```javascript
// ✅ CORRECT - Confirm destructive action
if (confirm('Are you sure you want to delete this account? This cannot be undone.')) {
  deleteAccount();
}

// ❌ WRONG - Confirm non-destructive action
if (confirm('Do you want to view this email?')) {
  viewEmail();
}
```

**Checklist**:
- [ ] Confirmations only for DELETE, DISCARD, REMOVE
- [ ] Confirmation text describes consequence
- [ ] Non-destructive actions proceed without confirmation

---

## 8. Visual Regression Testing

### Before Committing UI Changes
**Rule**: Run visual regression tests at 4 viewports

```bash
# 1. Capture baseline (before changes)
node scripts/visual_regression_test.js --baseline-only

# 2. Make your changes

# 3. Capture current (after changes)
node scripts/visual_regression_test.js --current-only

# 4. Compare and verify
node scripts/visual_regression_test.js --compare-only
```

**Pass Criteria**:
- Total tests passing: ≥95% (38/40 minimum)
- Maximum pixel diff per test: <0.5%
- Zero regressions on unchanged pages

**Checklist**:
- [ ] Baseline screenshots captured before changes
- [ ] Current screenshots captured after changes
- [ ] Comparison report shows ≤0.5% diff
- [ ] All 10 pages tested: Dashboard, Emails, Compose, Watchers, Rules, Accounts, Import Accounts, Diagnostics, Settings, Style Guide
- [ ] All 4 viewports tested: 1440px, 1024px, 768px, 390px

### Critical Regression Checks

**7-Point Validation** (from Phase 2B):
1. ✅ Sidebar fixed at desktop; .main aligns sections
2. ✅ Stat cards: 3-up ≥1024, 2-up 768-1023, 1-up <768
3. ✅ Search inputs match chip height; chips evenly spaced
4. ✅ Pills (HELD/POLLING/etc.) match contrast/padding
5. ✅ Section rhythm: 24px outer, 16px inner, 24px bottom
6. ✅ One border token across containers
7. ✅ No new !important added

**Checklist**:
- [ ] All 7 regression criteria verified
- [ ] No layout shifts at any viewport
- [ ] No color inconsistencies
- [ ] No spacing irregularities

---

## 9. Documentation Requirements

### CSS Changes Must Document
**Rule**: Large CSS changes require proof document

```markdown
# [Feature Name] - Proof of Success

## Summary
- Before: [metrics]
- After: [metrics]
- Visual diff: [results]

## Verification
[Screenshots, test results, validation commands]

## Files Modified
- [file 1]
- [file 2]
```

**Required for**:
- New design system components
- !important removal batches
- Major layout refactors
- Breaking CSS changes

**Checklist**:
- [ ] Summary document created in `docs/`
- [ ] Before/after metrics included
- [ ] Visual regression results attached
- [ ] Validation commands documented

### Commit Messages
**Rule**: Use conventional commit format

```bash
# ✅ CORRECT - Descriptive conventional commit
feat(ui): Add 5-stat dashboard layout with hero card

- Rebuild stats section with 5 stat cards
- Add hero card with title and status badges
- Apply design system tokens throughout
- Update responsive breakpoints for stats-5 grid

# ❌ WRONG - Vague message
Update dashboard
```

**Format**: `<type>(<scope>): <description>`

**Types**: feat, fix, refactor, style, docs, test, chore

**Checklist**:
- [ ] Commit message follows conventional format
- [ ] Type and scope present
- [ ] Description is clear and specific
- [ ] Body explains "why" not just "what"

---

## 10. PR Review Criteria

### Self-Review Before Submitting

**File Check**:
- [ ] Only intended files modified
- [ ] No debugging code left (console.log, debugger, etc.)
- [ ] No commented-out code blocks
- [ ] No TODO comments without JIRA ticket

**Code Quality**:
- [ ] All design tokens used (no hardcoded values)
- [ ] No new `!important` declarations
- [ ] All CSS in appropriate @layer
- [ ] Specificity ≤ 0,3,0

**Testing**:
- [ ] Visual regression tests passing
- [ ] All 10 pages checked in browser
- [ ] All 4 viewports tested (1440px, 1024px, 768px, 390px)
- [ ] Flask test suite passing: `python -m pytest tests/ -v`

**Documentation**:
- [ ] README updated if needed
- [ ] STYLEGUIDE.md updated if new patterns added
- [ ] Proof document created if major change
- [ ] IMPLEMENTATION_HISTORY.md updated if significant feature

### Reviewer Checklist

**Visual Review**:
- [ ] Screenshots show no regressions
- [ ] Design system tokens used consistently
- [ ] Responsive behavior correct at all breakpoints
- [ ] Dark theme maintained (no white flashes)

**Code Review**:
- [ ] Zero `!important` added
- [ ] CSS in @layer wrappers
- [ ] Design tokens used (no hardcoded colors/spacing)
- [ ] Toast notifications used (no alerts)

**Testing Review**:
- [ ] Visual regression report attached
- [ ] All tests passing
- [ ] No increase in !important count

**Documentation Review**:
- [ ] Commit messages clear
- [ ] Proof document complete (if required)
- [ ] Changes aligned with STYLEGUIDE.md

---

## Quick Validation Commands

```bash
# Count !important (must not increase)
python scripts/count_important.py static/css/main.css

# Run visual regression tests
node scripts/visual_regression_test.js --compare-only

# Run test suite
python -m pytest tests/ -v

# Check Flask health
curl http://localhost:5000/healthz

# Lint CSS (if configured)
npx stylelint "static/css/**/*.css"
```

---

## Common Violations & Fixes

### ❌ Violation: Hardcoded Colors
```css
/* WRONG */
.card { background: #1e1e1e; }

/* FIXED */
.card { background: var(--surface-elevated); }
```

### ❌ Violation: Custom Spacing
```css
/* WRONG */
.section { padding: 20px; margin-bottom: 30px; }

/* FIXED */
.section { padding: var(--space-5); margin-bottom: var(--space-6); }
```

### ❌ Violation: !important Added
```css
/* WRONG */
.override { color: white !important; }

/* FIXED */
body.page-name .override { color: var(--text-primary); }
```

### ❌ Violation: Browser Alert
```javascript
// WRONG
alert('Email sent successfully');

// FIXED
if (window.showSuccess) window.showSuccess('Email sent successfully');
```

### ❌ Violation: Inline Styles
```html
<!-- WRONG -->
<div style="margin: 20px; padding: 10px;">Content</div>

<!-- FIXED -->
<div class="section">Content</div>
```

---

## Enforcement

### PR Blocking Conditions
PRs will be blocked if:
1. ❌ New `!important` declarations added
2. ❌ Visual regression tests not run
3. ❌ Hardcoded colors/spacing present
4. ❌ No documentation for major changes
5. ❌ Test suite failing

### Warning Conditions
PRs will receive review comments for:
1. ⚠️ Specificity >0,3,0
2. ⚠️ Missing design tokens in some places
3. ⚠️ Incomplete responsive testing
4. ⚠️ Commit messages not following convention

---

## Contact & Questions

If you're unsure about any style decision:
1. Check `docs/STYLEGUIDE.md` for detailed patterns
2. Reference `static/css/design-system.css` for available tokens
3. Review recent commits for examples
4. Ask in PR comments before committing

---

**Version History**:
- v1.0 (Oct 27, 2025) - Initial checklist based on Phase 2B Batch 1 and dashboard rebuild

**Related Docs**:
- [docs/STYLEGUIDE.md](STYLEGUIDE.md) - Detailed UI patterns and examples
- [docs/CSS_PHASE2B_BATCH1_SUMMARY.md](CSS_PHASE2B_BATCH1_SUMMARY.md) - !important removal project
- [static/css/design-system.css](../static/css/design-system.css) - Design token reference
- [scripts/visual_regression_test.js](../scripts/visual_regression_test.js) - Visual testing tool
