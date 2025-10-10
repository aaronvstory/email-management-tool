# Email Management Tool Style Guide

## 📋 Table of Contents
1. [Design Philosophy](#design-philosophy)
2. [Color System](#color-system)
3. [Typography](#typography)
4. [Spacing & Layout](#spacing--layout)
5. [Components](#components)
6. [Animation & Transitions](#animation--transitions)
7. [Responsive Design](#responsive-design)
8. [Dark Theme Principles](#dark-theme-principles)
9. [CSS Architecture](#css-architecture)
10. [Implementation Examples](#implementation-examples)

---

## 🎨 Design Philosophy

### Core Principles
- **Dark-First Design**: Built specifically for dark environments with reduced eye strain
- **Gradient-Rich**: Multi-layer gradients for depth and visual interest
- **High Contrast**: Clear visual hierarchy with strategic contrast ratios
- **Micro-Interactions**: Subtle animations and transitions for engagement
- **Consistent Sizing**: All similar components maintain identical dimensions
- **Full-Width Layouts**: Maximize screen real estate usage

### Visual Identity
- **Style**: Modern, professional, security-focused
- **Mood**: Sophisticated, reliable, cutting-edge
- **Personality**: Powerful yet approachable, serious but not intimidating

---

## 🎨 Color System

### Primary Colors

```css
/* Core Brand Colors */
--primary-color: #dc2626;        /* Bright red - primary actions */
--secondary-color: #991b1b;       /* Dark red - secondary elements */
--accent-gradient: linear-gradient(135deg, #dc2626 0%, #991b1b 50%, #7f1d1d 100%);

/* Background Colors */
--dark-bg: #0a0a0a;               /* Deepest background */
--card-bg: #1a1a1a;               /* Card/panel background */
--panel-alt: #242424;             /* Alternative panel background */
--bg-gradient: radial-gradient(circle at 20% 20%, #1a1a1a 0%, #121212 35%, #0d0d0d 70%, #0a0a0a 100%);

/* Text Colors */
--text-light: #ffffff;            /* Primary text */
--text-dim: #9ca3af;              /* Secondary/muted text */
--text-muted: #6b7280;            /* Disabled/placeholder text */
```

### Semantic Colors

```css
/* Status Colors */
--success-color: #10b981;         /* Success states */
--danger-color: #dc2626;          /* Error/danger states */
--warning-color: #f59e0b;         /* Warning states */
--info-color: #3b82f6;            /* Information */

/* Status Backgrounds (with opacity) */
--success-bg: rgba(34,197,94,0.1);
--danger-bg: rgba(239,68,68,0.1);
--warning-bg: rgba(251,191,36,0.1);
--info-bg: rgba(59,130,246,0.1);
```

### Gradient System

```css
/* Card Gradients */
--grad-card: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 60%, #242424 100%);

/* Accent Gradients */
--grad-accent: linear-gradient(135deg, #dc2626 0%, #991b1b 50%, #7f1d1d 100%);

/* Hover State Gradients */
--grad-hover: linear-gradient(90deg, rgba(220,38,38,.25), rgba(153,27,27,.15));
```

---

## ✍️ Typography

### Font Stack

```css
/* Primary Font Family */
--font-sans: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;

/* Monospace Font (for code/technical) */
--font-mono: 'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace;
```

### Type Scale

```css
/* Headings - Compact for Space Efficiency */
h1 { font-size: 1.8rem; margin-bottom: 15px; }    /* 28.8px */
h2 { font-size: 1.5rem; margin-bottom: 12px; }    /* 24px */
h3 { font-size: 1.3rem; margin-bottom: 10px; }    /* 20.8px */
h4 { font-size: 1.15rem; margin-bottom: 8px; }    /* 18.4px */
h5 { font-size: 1.05rem; margin-bottom: 8px; }    /* 16.8px */
h6 { font-size: 0.95rem; margin-bottom: 6px; }    /* 15.2px */

/* Body Text */
body { font-size: 1rem; line-height: 1.6; }       /* 16px base */
.small-text { font-size: 0.875rem; }              /* 14px */
.tiny-text { font-size: 0.75rem; }                /* 12px */
```

### Font Weights

```css
/* Weight Scale */
--weight-regular: 400;
--weight-medium: 500;
--weight-semibold: 600;
--weight-bold: 700;
```

### Text Styling

```css
/* Letter Spacing for Headers */
.text-uppercase {
    text-transform: uppercase;
    letter-spacing: 1.4px;
}

/* Stat Numbers */
.stat-number {
    font-size: 2.5rem;
    font-weight: 700;
    background: var(--grad-accent);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
```

---

## 📐 Spacing & Layout

### Spacing System

```css
/* Base Unit: 8px */
--space-xs: 4px;      /* 0.5x */
--space-sm: 8px;      /* 1x */
--space-md: 15px;     /* ~2x */
--space-lg: 25px;     /* ~3x */
--space-xl: 35px;     /* ~4.5x */
--space-2xl: 50px;    /* ~6x */

/* Margin Classes */
.mb-0 { margin-bottom: 0; }
.mb-1 { margin-bottom: 8px; }
.mb-2 { margin-bottom: 15px; }
.mb-3 { margin-bottom: 25px; }
.mb-4 { margin-bottom: 35px; }
.mb-5 { margin-bottom: 50px; }
```

### Container System

```css
/* Full Width Containers */
.container {
    max-width: 100%;
    width: 100%;
    padding: 20px 30px;
}

/* Content Areas */
.main-content {
    padding: 30px;
    width: 100%;
}

/* Sidebar */
.sidebar {
    width: 250px;
    min-height: 100vh;
    padding: 20px 14px;
}
```

### Grid System

```css
/* Responsive Grid */
.stats-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

/* Card Grid */
.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
    gap: 20px;
}
```

---

## 🧩 Components

### Buttons

#### Standard Button Dimensions
```css
/* All buttons maintain consistent height */
.btn {
    height: 42px;
    padding: 8px 20px;
    font-size: 15px;
    font-weight: 500;
    border-radius: 6px;
    min-width: 100px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

/* Size Variants */
.btn-sm { height: 34px; padding: 5px 15px; font-size: 14px; }
.btn-lg { height: 50px; padding: 12px 30px; font-size: 18px; }
.btn-icon-only { width: 42px; min-width: 42px; padding: 8px; }
```

#### Button Styles
```css
/* Primary Button */
.btn-primary {
    background: linear-gradient(135deg, #dc2626 0%, #991b1b 50%, #7f1d1d 100%);
    color: white;
    border: none;
    box-shadow: 0 2px 10px -2px rgba(220,38,38,0.5);
}

/* Secondary Button */
.btn-secondary {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    color: #ffffff;
}

/* Ghost Button */
.btn-ghost {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    color: #ffffff;
}
```

### Cards

```css
/* Base Card */
.card {
    background: linear-gradient(145deg, #1a1a1a 0%, #1f1f1f 60%, #242424 100%);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 15px;
    padding: 0;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px -1px rgba(0,0,0,0.6);
}

/* Card Sections */
.card-header {
    padding: 12px 20px;
    background: rgba(220,38,38,0.1);
    border-bottom: 1px solid rgba(255,255,255,0.06);
}

.card-body {
    padding: 15px 20px;
}

/* Stat Card */
.stat-card {
    background: var(--grad-card);
    border-radius: 20px;
    padding: 25px;
    box-shadow: var(--shadow-elev-1);
    transition: transform 0.3s ease;
}

.stat-card:hover {
    transform: translateY(-5px);
    box-shadow: var(--shadow-elev-2);
}
```

### Forms

#### Input Fields
```css
.form-control {
    background: #2a2a2a;
    border: 1px solid #3a3a3a;
    color: #ffffff;
    padding: 10px 15px;
    border-radius: 4px;
    margin-bottom: 15px;
}

.form-control:focus {
    background: #333333;
    border-color: #4a4a4a;
    box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.2);
}

.form-control::placeholder {
    color: #888888;
}
```

#### Labels
```css
.form-label {
    color: #ffffff;
    font-weight: 600;
    margin-bottom: 8px;
}
```

### Tables

```css
.table-modern {
    background: #1a1a1a;
    border-radius: 15px;
    overflow: hidden;
    box-shadow: var(--shadow-elev-1);
}

.table-modern thead {
    background: var(--grad-accent);
    color: white;
}

.table-modern th {
    padding: 15px;
    font-weight: 600;
}

.table-modern td {
    padding: 20px 15px;
    background: #242424;
    color: #ffffff;
}

.table-modern tbody tr:hover {
    background: rgba(220,38,38,0.08);
    box-shadow: 0 0 0 1px rgba(220,38,38,0.2);
}
```

### Badges

```css
.badge {
    border-radius: 4px;  /* Rectangular, not pill-shaped */
    padding: 4px 10px;
    font-weight: 500;
    font-size: 0.875rem;
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: #ffffff;
}

/* Status Badges */
.badge-pending { background: #fff3cd; color: #856404; }
.badge-approved { background: #d4edda; color: #155724; }
.badge-rejected { background: #f8d7da; color: #721c24; }
.badge-sent { background: #cce5ff; color: #004085; }
```

### Modals

```css
.modal-content {
    background: var(--grad-card);
    border: 1px solid rgba(255,255,255,0.06);
    color: #ffffff;
}

.modal-header {
    background: var(--grad-accent);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    color: #ffffff;
}

.modal-dialog {
    max-width: 90%;
    width: 800px;
}

.modal-dialog-lg {
    max-width: 90%;
    width: 1200px;
}
```

### Navigation

```css
/* Sidebar Navigation */
.nav-link {
    color: #9ca3af;
    padding: 12px 20px;
    margin: 5px 10px;
    border-radius: 10px;
    transition: all 0.3s ease;
}

.nav-link:hover {
    background: rgba(220, 38, 38, 0.15);
    color: white;
    transform: translateX(5px);
}

.nav-link.active {
    background: var(--grad-hover);
    color: white;
    border-left: 3px solid var(--primary-color);
}
```

---

## ⚡ Animation & Transitions

### Standard Transition
```css
--transition: 140ms cubic-bezier(0.4, 0.2, 0.2, 1);
```

### Hover Effects
```css
/* Lift Effect */
.hover-lift:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.75);
}

/* Glow Effect */
.hover-glow:hover {
    box-shadow: 0 0 20px rgba(220,38,38,0.5);
}

/* Brightness Effect */
.hover-bright:hover {
    filter: brightness(1.1);
}
```

### Animation Keyframes
```css
/* Pulse Animation */
@keyframes pulse {
    0% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.2); opacity: 0.7; }
    100% { transform: scale(1); opacity: 1; }
}

/* Fade In */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Slide In */
@keyframes slideIn {
    from { transform: translateX(-100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
```

---

## 📱 Responsive Design

### Breakpoints
```css
/* Mobile First Approach */
--breakpoint-sm: 640px;
--breakpoint-md: 768px;
--breakpoint-lg: 1024px;
--breakpoint-xl: 1280px;
```

### Responsive Patterns
```css
/* Tablet and Below */
@media (max-width: 1100px) {
    .split-layout { grid-template-columns: 1fr; }
    .sidebar { width: 220px; }
}

/* Mobile */
@media (max-width: 840px) {
    .sidebar {
        position: fixed;
        transform: translateX(-100%);
        z-index: 40;
    }
    .sidebar.open {
        transform: translateX(0);
    }
}
```

---

## 🌙 Dark Theme Principles

### Depth & Layering
1. **Base Layer**: `#0a0a0a` - Deepest background
2. **Primary Layer**: `#1a1a1a` - Cards and panels
3. **Secondary Layer**: `#242424` - Table rows, alternate backgrounds
4. **Elevated Layer**: `#2a2a2a` - Form inputs
5. **Hover Layer**: `rgba(220,38,38,0.08)` - Interactive states

### Border System
```css
/* Subtle Borders */
--border-default: 1px solid rgba(255,255,255,0.06);
--border-strong: 1px solid rgba(255,255,255,0.12);
--border-accent: 1px solid rgba(220,38,38,0.3);
```

### Shadow System
```css
/* Elevation Shadows */
--shadow-elev-1: 0 2px 4px -1px rgba(0,0,0,0.6), 0 1px 2px rgba(0,0,0,0.4);
--shadow-elev-2: 0 4px 12px -2px rgba(0,0,0,0.75), 0 2px 6px rgba(0,0,0,0.5);
--shadow-focus: 0 0 0 2px rgba(220,38,38,0.5);
```

### Contrast Ratios
- **Primary Text on Dark**: 15:1 (#ffffff on #1a1a1a)
- **Secondary Text on Dark**: 7:1 (#9ca3af on #1a1a1a)
- **Minimum Interactive**: 4.5:1 (WCAG AA compliant)

---

## 🏗️ CSS Architecture

### Naming Convention
```css
/* BEM-inspired with modifications */
.component-name {}           /* Block */
.component-name__element {}  /* Element */
.component-name--modifier {} /* Modifier */

/* Utility Classes */
.u-text-center {}
.u-margin-top-20 {}
```

### CSS Variables Organization
```css
:root {
    /* Colors */
    --color-*

    /* Typography */
    --font-*
    --weight-*

    /* Spacing */
    --space-*

    /* Borders */
    --border-*
    --radius-*

    /* Shadows */
    --shadow-*

    /* Animations */
    --transition-*
}
```

### File Structure
```
static/
├── css/
│   ├── theme-dark.css      # Dark theme variables
│   ├── components.css      # Component styles
│   ├── layout.css          # Layout utilities
│   └── animations.css      # Animation keyframes
```

---

## 💻 Implementation Examples

### Creating a New Card Component
```html
<div class="stat-card">
    <div class="stat-label">TOTAL EMAILS</div>
    <div class="stat-number">1,234</div>
    <div class="stat-delta">+12% from last week</div>
</div>
```

### Creating a Primary Button
```html
<button class="btn btn-primary">
    <i class="bi bi-send"></i>
    Send Email
</button>
```

### Creating a Form Input
```html
<div class="form-group">
    <label class="form-label">Email Address</label>
    <input type="email" class="form-control" placeholder="user@example.com">
    <small class="form-text">We'll never share your email</small>
</div>
```

### Creating a Data Table
```html
<div class="table-modern">
    <table class="table">
        <thead>
            <tr>
                <th>Sender</th>
                <th>Subject</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>john@example.com</td>
                <td>Important Update</td>
                <td><span class="badge badge-pending">PENDING</span></td>
            </tr>
        </tbody>
    </table>
</div>
```

---

## 📝 Best Practices

### Do's
✅ Use CSS variables for all colors and measurements
✅ Maintain consistent spacing using the 8px grid system
✅ Apply transitions to all interactive elements
✅ Use gradients sparingly for emphasis
✅ Ensure text contrast meets WCAG AA standards
✅ Test components in both light and dark environments

### Don'ts
❌ Mix different border radius values arbitrarily
❌ Use pure black (#000000) - use #0a0a0a instead
❌ Apply shadows without considering the light source
❌ Create buttons with inconsistent heights
❌ Use pill-shaped badges - keep them rectangular
❌ Override the full-width container system

---

## 🔄 Version History

- **v2.1** (Current): Unified dark theme with gradient system
- **v2.0**: Introduction of modular CSS architecture
- **v1.0**: Initial Bootstrap-based implementation

---

## 📚 Resources

- [Bootstrap 5.3 Documentation](https://getbootstrap.com/docs/5.3/)
- [Bootstrap Icons](https://icons.getbootstrap.com/)
- [Font Awesome 6.5](https://fontawesome.com/)
- [Inter Font](https://fonts.google.com/specimen/Inter)
- [CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)

---

**Last Updated**: September 30, 2025
**Maintained By**: Email Management Tool Development Team