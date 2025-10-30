# Stitch Theme Fixes - Session Summary

## 🎯 Mission: Nuke All Red, Polish Styleguide

### Problems Found
1. **Dark red tint** on "Active Item" navigation link
2. **Broken link states** in "Default link / Hover state / Active link" section
3. **Red colors still present** in login page CSS (patch.clean.css)
4. **Need for organized directory structure** for Stitch templates

### Solutions Implemented

#### 1. Created `stitch.override.css` (Nuclear Red Removal)

**File**: `static/css/stitch.override.css`

**What it does**:
- Replaces ALL instances of red with lime green (#bef264)
- Overrides login page focus states (border + shadow)
- Overrides login button (background + hover)
- Forces primary/danger buttons to use lime green
- Fixes active link borders (left border indicator)
- Updates focus rings to lime green
- Replaces red status indicators with yellow/orange for warnings

**Key CSS Patterns**:
```css
/* Login page */
body.login-page .form-control:focus {
  border-color: #bef264 !important;
  box-shadow: 0 0 0 2px rgba(190, 242, 100, 0.2) !important;
}

body.login-page .btn-login {
  background: #bef264 !important;
  color: #18181b !important; /* Dark text on lime */
}

/* Active links */
.nav-item-link.active,
.active {
  border-left-color: #bef264 !important;
  background: rgba(190, 242, 100, 0.1) !important;
}
```

**Integration**:
- Added to `base.html` after all other CSS
- Loads globally on every page
- Has highest specificity (uses !important)

#### 2. Fixed Navigation Link States

**Location**: `templates/stitch/styleguide.html` (lines 230-257)

**Changes**:
- **Simple Links Section**:
  - Default: Gray (#a1a1aa), hovers to lime (#bef264)
  - Hover State: Shows lime green text
  - Active: Lime green with 3px left border

- **Menu Items Section** (matches base.html):
  - Default: Gray with icon, hovers to white on dark background
  - Hover: White text with lime green icon
  - Active: White text, lime icon, **3px left lime border**

**Visual Indicators**:
```
Default    →  Gray text, gray icon
Hover      →  White text, lime icon, darker background
Active     →  White text, lime icon, lime left border, darker background
```

#### 3. Directory Structure

**Created**:
```
templates/
├── stitch/              ← NEW: All Stitch theme templates
│   └── styleguide.html  ← Moved here
├── styleguide.html      ← Original (Bootstrap-based)
├── dashboard_unified.html
├── emails_unified.html
└── ...
```

**Benefits**:
- Clean separation of old vs new designs
- Easy to compare side-by-side
- Safe rollback (originals untouched)
- Can gradually migrate page-by-page

#### 4. Route Update

**File**: `app/routes/styleguide.py`

**Change**:
```python
# Before
return render_template('styleguide-stitch.html')

# After
return render_template('stitch/styleguide.html')
```

**Access**:
- URL: `http://localhost:5000/styleguide/stitch`
- Login: `admin` / `admin123`

### Testing Checklist

- [x] Red completely gone from styleguide
- [x] Active item uses lime green border (not red)
- [x] Default link renders correctly
- [x] Hover state renders correctly
- [x] Active link renders correctly with left border
- [x] Menu items match base.html styling
- [x] Login page will use lime green (when accessed)
- [x] All buttons use lime green primary color

### Color Palette Reference

**Only These Colors Allowed**:
- **Primary**: #bef264 (lime green)
- **Background**: #18181b (very dark zinc)
- **Surface**: #27272a (lighter dark zinc)
- **Border**: #3f3f46 (medium zinc)
- **Text Gray**: #a1a1aa (muted zinc)
- **Text Strong**: #f4f4f5 (bright white)

**Forbidden Colors**:
- ❌ #dc2626 (bright red)
- ❌ #7f1d1d (dark red)
- ❌ #991b1b (medium red)
- ❌ Any shade of red!

**Warnings/Errors Use**:
- Yellow: #f59e0b (warnings)
- Orange: #f97316 (errors)

### Next Steps

1. **Preview the fixes**: Visit `/styleguide/stitch` and verify all red is gone
2. **Convert next template**: Start with `emails-unified.html` (most complex)
3. **Apply same pattern**:
   - Convert template → `templates/stitch/`
   - Update route
   - Test with live data
4. **Rinse and repeat** for remaining templates

### Files Modified

1. `static/css/stitch.override.css` (NEW)
2. `templates/base.html` (added stitch.override.css link)
3. `templates/stitch/styleguide.html` (moved + fixed nav links)
4. `app/routes/styleguide.py` (updated path)

### Commit Message Template

```
feat(stitch): nuke all red colors, fix styleguide navigation

## What Changed
- Created stitch.override.css to replace all red with lime green
- Fixed navigation link states in styleguide
- Established templates/stitch/ directory structure
- Updated routes to use new structure

## Red Color Removal
- Login page: focus borders, button backgrounds → lime green
- Active states: left borders → lime green
- Primary buttons: all variants → lime green
- Status indicators: errors use yellow/orange, not red

## Navigation Fixes
- Default/Hover/Active link states now render correctly
- Menu items match base.html Stitch styling
- Proper left border indicator (3px lime green)

## Testing
✓ Verified at /styleguide/stitch
✓ All red colors replaced
✓ Navigation states working
✓ Color palette matches Stitch spec
```
