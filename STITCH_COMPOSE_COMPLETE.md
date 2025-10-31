# Stitch Compose Template - Conversion Complete

## ✅ Status: Ready for Testing

The compose email template has been successfully converted from standalone Stitch HTML to a fully functional Flask template.

### What Was Done

#### 1. Improved Conversion Script

**File**: `scripts/convert_styleguide.py`

**Enhancements**:
- ✅ Now accepts template name as command-line argument
- ✅ Handles multiple content container patterns:
  - `<main class="flex-1"` (compose)
  - `<div class="max-w-7xl"` (styleguide)
  - `<div class="max-w-4xl"` (compose)
- ✅ Dynamic title generation from template name
- ✅ Dynamic ID generation for wrapper div
- ✅ Proper error handling when content markers not found

**Usage**:
```bash
python scripts/convert_styleguide.py <template-name>

# Examples:
python scripts/convert_styleguide.py compose-email
python scripts/convert_styleguide.py emails-unified
python scripts/convert_styleguide.py accounts
```

#### 2. Converted Compose Template

**Source**: `templates/new/compose-email.html` (standalone Stitch HTML)
**Output**: `templates/stitch/compose-email.html` (Flask + Jinja2)

**Conversion Results**:
- ✅ All Tailwind classes prefixed with `tw-`
- ✅ Custom classes preserved (btn, input-modern, etc.)
- ✅ Stripped `<head>` section (base.html provides it)
- ✅ Stripped sidebar (base.html provides it)
- ✅ Wrapped in `{% extends "base.html" %}` structure
- ✅ Form wrapped with POST action
- ✅ Dynamic accounts dropdown from database
- ✅ Proper form field names match backend expectations
- ✅ Required attributes on necessary fields
- ✅ Proper button types (submit vs button)

**Form Integration**:
```html
<form method="POST" action="{{ url_for('compose.compose_email') }}" ...>
  <select name="from_account" required>
    {% for account in accounts %}
    <option value="{{ account['id'] }}">{{ account['account_name'] }} ...</option>
    {% endfor %}
  </select>

  <input name="to" type="email" required />
  <input name="cc" type="email" />
  <input name="subject" type="text" required />
  <textarea name="body" required></textarea>

  <button type="submit">Send Email</button>
</form>
```

#### 3. Added Preview Route

**File**: `app/routes/compose.py`

**New Route**:
```python
@compose_bp.route('/compose/stitch')
@login_required
def compose_stitch():
    """Preview the new Stitch theme compose page (Tailwind-based)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all active email accounts for FROM dropdown
    accounts = cursor.execute("""
        SELECT id, account_name, email_address
        FROM email_accounts
        WHERE is_active = 1
        ORDER BY account_name
    """).fetchall()

    conn.close()
    return render_template('stitch/compose-email.html', accounts=accounts)
```

**Access Point**: http://localhost:5000/compose/stitch

### How to Test

1. **Start the app** (if not already running):
   ```bash
   python simple_app.py
   ```

2. **Navigate to preview**:
   ```
   http://localhost:5000/compose/stitch
   ```

3. **Verify**:
   - ✓ Page loads without errors
   - ✓ Lime green theme (#bef264) applied
   - ✓ Sharp corners (no border-radius)
   - ✓ Accounts dropdown populated from database
   - ✓ All form fields render correctly
   - ✓ "Send Email" button has lime green background
   - ✓ Form submission works (redirects to inbox on success)
   - ✓ Toast notifications appear (not browser alerts)

### What's Different from Styleguide

**Compose template advantages**:
- ✓ Simpler layout (single form, fewer sections)
- ✓ Less CSS conflicts (fewer custom components)
- ✓ Fully functional form integration
- ✓ Real database integration (accounts dropdown)
- ✓ Should have fewer CSS override issues than styleguide

### Next Steps

1. **Test the compose page** at `/compose/stitch`:
   - Fill out form with real account
   - Test actual email sending
   - Verify error handling

2. **Compare with original**:
   - Side-by-side: `file:///C:/claude/Stitch/compose-email/compose-email.html`
   - Check for any major styling differences
   - Note any CSS conflicts that need fixing

3. **If compose looks good**, use it as the cleaner reference for:
   - Converting emails-unified.html (high priority)
   - Converting accounts.html
   - Converting other remaining templates

4. **Address link styling** (NEW REQUEST):
   - Check `C:\claude\Stitch\emails-link\emails-link.html` for link styling patterns
   - Apply consistent link styling to:
     - Styleguide link examples
     - Navigation menu (base.html)
     - All other templates
   - Behavior needed:
     - Active/clicked: lime green tint + left border (3px lime green)
     - Hovered: gray overlay
     - Default: gray text

### Files Modified

1. `scripts/convert_styleguide.py` (enhanced for multiple templates)
2. `templates/stitch/compose-email.html` (created, fully integrated)
3. `app/routes/compose.py` (added /compose/stitch route)

### Color Palette (Reference)

**Primary Colors**:
- Primary: #bef264 (lime green) - buttons, active states, accents
- Background: #18181b (very dark zinc)
- Surface: #27272a (panels, cards)
- Border: #3f3f46 (dividers, borders)
- Text Muted: #a1a1aa (labels, hints)
- Text Strong: #f4f4f5 (headings, important text)

**Forbidden**:
- ❌ Any shade of red
- ❌ Rounded corners (border-radius should be 0px or minimal)

### Remaining Templates to Convert

1. **emails-unified.html** (HIGH PRIORITY) - Complex table with badges/status
2. **accounts.html** (HIGH PRIORITY) - Grid view, account status cards
3. **watchers.html** (MEDIUM) - IMAP watcher status
4. **All others** - Lower priority

### Lessons Learned

1. **Conversion script flexibility**: Need to handle multiple content container patterns
2. **Template integration**: Must integrate Flask/Jinja2 variables for dynamic data
3. **Form structure**: Need proper form wrapping and field naming
4. **CSS conflicts**: Simpler templates (like compose) may have fewer conflicts than complex ones (like styleguide)

### Expected Result

When you visit `/compose/stitch`, you should see a clean, modern compose form with:
- Lime green "Send Email" button
- Sharp corners everywhere
- Dark zinc background (#18181b)
- All form fields styled consistently
- Material Symbols icons
- No red colors anywhere
- Proper dropdown with actual database accounts

**Quality Check**: Compare with `/compose` (original) to verify all functionality preserved while gaining the modern Stitch styling.
