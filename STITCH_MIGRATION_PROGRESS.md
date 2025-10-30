# Stitch Theme Migration Progress

## ✅ UPDATE: Styleguide Fixed & Ready!

### Fixes Applied (Latest)

1. **RED COLOR COMPLETELY NUKED** 🎯
   - Created `static/css/stitch.override.css`
   - Replaces ALL red (#dc2626, #7f1d1d) with lime green (#bef264)
   - Overrides login page, buttons, borders, active states
   - Added to base.html (loads globally)

2. **Navigation Links Section Fixed**
   - "Default Link", "Hover State", "Active Link" now properly styled
   - Uses exact colors from Stitch palette
   - Left border indicator on active items (lime green)
   - Matches base.html sidebar styling

3. **Directory Structure Established**
   - Created `templates/stitch/` directory
   - Moved styleguide to `templates/stitch/styleguide.html`
   - All future Stitch templates go here
   - Original templates remain untouched

4. **Route Updated**
   - Route: `/styleguide/stitch` → `templates/stitch/styleguide.html`
   - Ready to preview immediately

## ✅ Completed: Styleguide Conversion

### What Was Done

1. **Created Conversion Script** (`scripts/convert_styleguide.py`)
   - Automatically adds `tw-` prefix to all Tailwind classes
   - Preserves custom classes (btn, input-modern, etc.)
   - Converts standalone HTML to Flask template structure

2. **Converted Styleguide Template**
   - Source: `templates/new/styleguide.html` (standalone Tailwind)
   - Output: `templates/styleguide-stitch.html` (Flask + Jinja2)
   - All Tailwind classes now have `tw-` prefix
   - Extends `base.html` (includes sidebar, navigation)

3. **Added Flask Route**
   - Route: `/styleguide/stitch`
   - File: `app/routes/styleguide.py`
   - Requires login (like all other pages)

### How to Preview

```bash
# Start the app
python simple_app.py

# Visit in browser
http://localhost:5000/styleguide/stitch
```

Login with: `admin` / `admin123`

### What's Different from Dashboard

The converted styleguide:
- ✅ Uses same Tailwind config from `base.html`
- ✅ Uses same lime green (`#bef264`) color scheme
- ✅ Has sidebar navigation (from `base.html`)
- ✅ All Tailwind classes properly prefixed with `tw-`
- ✅ Material Symbols icons (same as dashboard)

## 🔄 Next Steps

### Remaining Templates to Convert

1. **emails-unified.html** (Priority: High)
   - Needs dynamic data from Flask (email list)
   - Table components with status badges
   - Search/filter functionality

2. **accounts.html** (Priority: High)
   - Grid/list toggle view
   - Account status indicators
   - SMTP/IMAP configuration display

3. **watchers.html** (Priority: Medium)
   - IMAP watcher status cards
   - Connection health indicators

4. **compose-email.html** (Priority: Low)
   - Form with validation
   - Rich text editor area

### Conversion Strategy

For each template:
1. Run conversion script with template-specific customizations
2. Replace hardcoded data with Jinja2 variables (`{{ variable }}`)
3. Add Flask route (or update existing route)
4. Test with real data from the database
5. Fix any styling issues

### Quick Conversion Command

```python
# Adapt for each template
python scripts/convert_template.py --input templates/new/TEMPLATE.html --output templates/TEMPLATE-stitch.html
```

## 📋 Migration Checklist

- [x] Styleguide converted
- [x] Route added for styleguide
- [ ] Emails-unified converted
- [ ] Accounts converted
- [ ] Watchers converted
- [ ] Compose converted
- [ ] All templates tested with live data
- [ ] Screenshot comparison (before/after)
- [ ] Mobile responsive check
- [ ] Browser compatibility test

## 🎯 Final Goal

Replace old Bootstrap templates with Stitch (Tailwind) versions:
- All pages use consistent lime green theme
- Sharp corners (no/minimal border-radius)
- Material Symbols icons throughout
- Clean, modern Tailwind utility classes

## Notes

- Dashboard already uses Stitch theme (done ✓)
- Base.html has Tailwind configured with `tw-` prefix
- New templates don't need `<head>` sections (base.html handles it)
- Custom classes (btn, panel, input-modern) work alongside Tailwind
