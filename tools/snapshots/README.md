# Screenshot Snapshot Tool

Automated screenshot capture for all application pages using Playwright. Generates date-stamped, multi-viewport snapshots with optional authentication state, element-only captures, and one-command workflows.

## 🚀 Quick Start (One Command)

**Boot → Snap → Open Folder:**
```bash
.\manage.ps1 boot-snap-open
```

Or use the batch file:
```batch
start.bat
```

This will:
1. Start the Flask application
2. Wait for it to be ready
3. Capture all pages at multiple viewports
4. Open the screenshots folder automatically

## 📦 Installation

### 1. Install Dependencies

```bash
npm install
npm run snap:install
```

This installs Playwright Chromium browser with system dependencies.

### 2. Configure Authentication (One Time)

Copy the template and fill in your credentials:

```bash
cp .snap.env.example .snap.env
```

Edit `.snap.env`:
```ini
SNAP_BASE_URL=http://localhost:5000
SNAP_LOGIN_PATH=/login
SNAP_USER_SEL=#email
SNAP_PASS_SEL=#password
SNAP_SUBMIT_SEL=button[type=submit]
SNAP_USERNAME=admin
SNAP_PASSWORD=admin123
```

**Save authentication state** (run once):
```bash
npm run snap:update-state
```

This creates `tools/snapshots/state.json` which subsequent runs will reuse.

⚠️ **Security**: `.snap.env` and `state.json` are gitignored. Never commit credentials!

## 🎯 Usage Workflows

### Basic Workflows

**Capture all pages** (headless):
```bash
.\manage.ps1 snap
```

**Capture with browser visible** (headful):
```bash
.\manage.ps1 snap -Headful
```

**Capture specific pages only**:
```bash
.\manage.ps1 snap -Pages "dashboard,emails,watchers"
```

**Element-only screenshots**:
```bash
.\manage.ps1 snap -Elements ".page-header,.email-table"
```

**Combine filters**:
```bash
.\manage.ps1 snap -Pages "dashboard" -Elements ".page-header,.stats-grid" -Headful
```

### Advanced Workflows

**Boot + Snap + Open**:
```bash
.\manage.ps1 boot-snap-open
# OR
start.bat
```

**Just start the server**:
```bash
.\manage.ps1 start
```

**Snap + Open folder** (assumes server already running):
```bash
.\manage.ps1 snap-open
```

### Direct npm Scripts

**Headless capture**:
```bash
npm run snap
```

**Headful capture**:
```bash
npm run snap:headful
```

**Custom base URL**:
```bash
npm run snap -- --base-url http://localhost:8000
```

**With CLI flags**:
```bash
npm run snap -- --pages dashboard,emails --elements .page-header
```

## 📂 Output Structure

```
snapshots/
  2025-10-30_143012/           # Date-stamped batch
    1440x900/                   # Viewport size
      dashboard.png             # Full-page screenshot
      emails.png
      watchers.png
      ...
    390x844/                    # Mobile viewport
      dashboard.png
      ...
```

### Element-Only Output

When using `--elements`:
```
snapshots/
  2025-10-30_143012/
    1440x900/
      dashboard__element__page-header.png
      dashboard__element__email-table.png
      emails__element__page-header.png
      ...
```

## ⚙️ Configuration

### Pages Configuration (`pages.json`)

Define routes and their ready selectors:

```json
[
  { 
    "key": "dashboard", 
    "url": "/dashboard", 
    "ready": "#dashboard-page",
    "elements": [".page-header", ".email-table", ".stats-grid"]
  },
  {
    "key": "emails",
    "url": "/emails-unified",
    "ready": "#emails-page",
    "elements": [".page-header", ".email-table"]
  }
]
```

**Fields:**
- `key` - Unique page identifier (used in filenames and `--pages` filter)
- `url` - Route path (must start with `/`)
- `ready` - CSS selector to wait for (ensures page is fully loaded)
- `elements` - Optional array of CSS selectors for element-only captures

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SNAP_BASE_URL` | `http://localhost:5000` | Application base URL |
| `SNAP_LOGIN_PATH` | `/login` | Login route |
| `SNAP_USER_SEL` | `#email` | Username input selector |
| `SNAP_PASS_SEL` | `#password` | Password input selector |
| `SNAP_SUBMIT_SEL` | `button[type=submit]` | Submit button selector |
| `SNAP_USERNAME` | - | Login username |
| `SNAP_PASSWORD` | - | Login password |
| `SNAP_VIEWPORTS` | `1440x900,390x844` | Comma-separated viewport sizes (WxH) |
| `SNAP_OUT_DIR` | `snapshots` | Output directory |
| `SNAP_STATE_FILE` | `tools/snapshots/state.json` | Auth state file |
| `SNAP_RETRIES` | `2` | Retry attempts per page |
| `SNAP_TIMEOUT_MS` | `20000` | Page load timeout (ms) |

### CLI Flags

`snap.ts` supports the following flags:

```bash
ts-node tools/snapshots/snap.ts [flags]
```

**Flags:**
- `--update-state` - Save new authentication state and exit
- `--headful` - Show browser during capture (default: headless)
- `--base-url <url>` - Override base URL
- `--out <dir>` - Output directory (default: `snapshots`)
- `--pages <keys>` - Comma-separated page keys to capture
- `--elements <selectors>` - Comma-separated CSS selectors for element-only captures
- `--login <path>` - Login route path
- `--user-sel <selector>` - Username input selector
- `--pass-sel <selector>` - Password input selector
- `--submit-sel <selector>` - Submit button selector
- `--username <user>` - Login username
- `--password <pass>` - Login password
- `--state <path>` - Auth state file path

**Examples:**
```bash
# Element-only: capture headers and tables only
ts-node tools/snapshots/snap.ts --elements ".page-header,.email-table"

# Specific pages with custom viewports
SNAP_VIEWPORTS="1920x1080,768x1024" ts-node tools/snapshots/snap.ts --pages "dashboard,emails"

# Headful mode for debugging
ts-node tools/snapshots/snap.ts --headful

# Custom base URL
ts-node tools/snapshots/snap.ts --base-url "http://192.168.1.100:5000"
```

## 🔧 PowerShell Helpers

### manage.ps1

Central management script with menu-driven interface:

```powershell
.\manage.ps1 [task] [options]
```

**Tasks:**
- `menu` - Show interactive menu (default)
- `start` - Start Flask server only
- `snap` - Capture screenshots only
- `snap-open` - Capture + open folder
- `boot-snap-open` - Boot → snap → open

**Options:**
- `-BaseUrl <url>` - Base URL (default: `http://localhost:5000`)
- `-Headful` - Show browser during capture
- `-Pages <keys>` - Comma-separated page keys
- `-Elements <selectors>` - Comma-separated CSS selectors

**Examples:**
```powershell
# Show menu
.\manage.ps1

# Start server
.\manage.ps1 start

# Capture with browser visible
.\manage.ps1 snap -Headful

# Capture specific pages
.\manage.ps1 snap -Pages "dashboard,emails"

# Element-only capture
.\manage.ps1 snap -Elements ".page-header,.stats-grid"

# Full workflow
.\manage.ps1 boot-snap-open
```

### snap.ps1

Direct screenshot wrapper (called by manage.ps1):

```powershell
.\tools\snapshots\snap.ps1 [options]
```

**Options:**
- `-BaseUrl <url>` - Base URL
- `-Headful` - Show browser
- `-Out <dir>` - Output directory
- `-Pages <keys>` - Page filter
- `-Elements <selectors>` - Element filter

## 🎨 Element-Only Screenshots

Capture specific UI components instead of full pages:

**Predeclared Elements** (in `pages.json`):
```bash
# Capture headers and tables from all pages
.\manage.ps1 snap -Elements ".page-header,.email-table"
```

**Ad-hoc Selectors**:
```bash
# Any CSS selector works
.\manage.ps1 snap -Elements "#dashboard-stats,.action-menu"
```

**Page-Specific Elements**:
```bash
# Only dashboard, only specific elements
.\manage.ps1 snap -Pages "dashboard" -Elements ".stats-grid,.email-table"
```

**Output naming**: `{page-key}__element__{sanitized-selector}.png`

Example: `dashboard__element__page-header.png`

## 🔄 CI/CD Integration

### GitHub Actions

Example workflow (`.github/workflows/snapshots.yml`):

```yaml
name: UI Snapshots
on:
  workflow_dispatch: {}
  push:
    branches: [main, master]
    paths:
      - 'static/**'
      - 'templates/**'

jobs:
  snapshots:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      
      - name: Install dependencies
        run: |
          npm install
          npm run snap:install
          pip install -r requirements.txt
      
      - name: Start application
        run: |
          Start-Process python -ArgumentList "simple_app.py" -NoNewWindow
          Start-Sleep -Seconds 10
        shell: pwsh
      
      - name: Create .snap.env
        run: |
          @"
          SNAP_BASE_URL=http://localhost:5000
          SNAP_USERNAME=${{ secrets.SNAP_USERNAME }}
          SNAP_PASSWORD=${{ secrets.SNAP_PASSWORD }}
          "@ | Out-File -FilePath .snap.env -Encoding utf8
        shell: pwsh
      
      - name: Update auth state
        run: npm run snap:update-state
        env:
          SNAP_BASE_URL: http://localhost:5000
      
      - name: Capture snapshots
        run: npm run snap
      
      - uses: actions/upload-artifact@v4
        with:
          name: ui-snapshots
          path: snapshots/**
          retention-days: 30
```

### Visual Regression Testing

Integrate with visual diff tools:

**Percy:**
```bash
npm install --save-dev @percy/cli
npx percy snapshot snapshots/
```

**Chromatic:**
```bash
npx chromatic --project-token=<token> --snapshots-dir=snapshots/
```

**BackstopJS:**
```json
{
  "viewports": [
    { "label": "desktop", "width": 1440, "height": 900 },
    { "label": "mobile", "width": 390, "height": 844 }
  ],
  "scenarios": [
    {
      "label": "Dashboard",
      "url": "http://localhost:5000/dashboard",
      "readySelector": "#dashboard-page"
    }
  ]
}
```

## 🛠️ Troubleshooting

### "Login env vars not set"
→ Create `.snap.env` from `.snap.env.example` and fill in credentials
→ Or run `npm run snap:update-state` with env vars set

### "Failed to capture [page]"
→ Check `ready` selector in `pages.json` exists on page
→ Increase timeout: `SNAP_TIMEOUT_MS=30000 npm run snap`
→ Verify application is running at `SNAP_BASE_URL`
→ Try headful mode for debugging: `.\manage.ps1 snap -Headful`

### "Timeout waiting for selector"
→ Ensure `ready` selector is present after page load
→ Check browser console for JavaScript errors (use `-Headful`)
→ Verify authentication state is valid: `npm run snap:update-state`

### Screenshots are blank/partial
→ Increase wait timeout or adjust `ready` selector
→ Check for lazy-loaded content
→ Use `freezeAnimations()` is working (animations disabled in captures)

### Port 5000 already in use
→ Change base URL: `.\manage.ps1 snap -BaseUrl http://localhost:8000`
→ Or kill existing process: `taskkill /F /IM python.exe`

### Element screenshots failing
→ Verify element selector exists and is visible
→ Use `--headful` to inspect page state
→ Check element hasn't been removed by CSS (display: none)
→ Try full-page capture first to verify page loads correctly

## 📊 Performance Tips

**Faster captures**:
- Use `--pages` to capture only changed pages
- Use `chromium` only (already default): `npm run snap:install chromium`
- Reduce viewports: `SNAP_VIEWPORTS="1440x900" npm run snap`

**Element-only captures are faster** than full-page:
```bash
# Fast: Only capture specific components
.\manage.ps1 snap -Elements ".page-header,.email-table"

# Slower: Full-page screenshots
.\manage.ps1 snap
```

**Parallel execution** (requires manual setup):
```bash
# Capture different pages simultaneously
Start-Job { npm run snap -- --pages "dashboard,emails" }
Start-Job { npm run snap -- --pages "watchers,rules" }
Get-Job | Wait-Job | Receive-Job
```

## 🔐 Security Best Practices

1. **Never commit credentials**:
   - `.snap.env` is gitignored
   - `state.json` is gitignored
   - Use GitHub Secrets in CI/CD

2. **Rotate credentials regularly**:
   ```bash
   # Update .snap.env with new password
   npm run snap:update-state
   ```

3. **Use test accounts only**:
   - Don't use production credentials for screenshots
   - Create dedicated `screenshot-bot` account with read-only access

4. **Review screenshots before sharing**:
   - Check for sensitive data in captures
   - Use element-only mode to avoid capturing full pages with PII

## 📚 Integration with PR Workflow

### Standard Workflow

1. Make UI changes
2. Start app: `python simple_app.py`
3. Capture screenshots: `.\manage.ps1 snap`
4. Compare with previous captures (manual or automated)
5. Attach to PR for review

### One-Command Workflow

```bash
# After making changes
.\manage.ps1 boot-snap-open

# Screenshots automatically captured and folder opened
# Attach latest folder to PR
```

### Automated PR Comments

Use GitHub Actions + Percy/Chromatic to automatically post visual diffs as PR comments.

## 🎓 Advanced Topics

### Custom Viewports

Add mobile, tablet, and desktop breakpoints:

```bash
$env:SNAP_VIEWPORTS="1920x1080,1440x900,1280x800,1024x768,768x1024,390x844,375x667"
npm run snap
```

### Custom Animation Freeze

Edit `snap.ts` `freezeAnimations()` function to customize:

```typescript
async function freezeAnimations(page: Page) {
  await page.addStyleTag({
    content: `
      * { transition: none !important; animation: none !important; }
      .spinner { display: none !important; }
      [data-loading="true"] { opacity: 1 !important; }
    `
  });
}
```

### Pre-Capture Scripts

Run custom JavaScript before capturing:

```typescript
// In snap.ts, before screenshot
await page.evaluate(() => {
  // Hide cookie banners
  document.querySelectorAll('[data-cookie-banner]').forEach(el => el.remove());
  // Scroll to top
  window.scrollTo(0, 0);
});
```

## 📝 File Structure

```
tools/snapshots/
├── snap.ts               # Main Playwright engine (134 lines)
├── snap.ps1              # PowerShell wrapper (13 lines)
├── pages.json            # Route configuration (57 lines)
├── state.json            # Auth state (gitignored)
└── README.md             # This file

Root:
├── manage.ps1            # Central management script (125 lines)
├── start.bat             # One-command launcher (7 lines)
├── .snap.env             # Credentials (gitignored)
└── .snap.env.example     # Template (32 lines)
```

## 📄 License

Integrated with Email Management Tool project. See root LICENSE file.

---

**Quick Reference Card:**

```bash
# Installation
npm install && npm run snap:install

# One-time auth
cp .snap.env.example .snap.env
# Edit .snap.env with credentials
npm run snap:update-state

# Quick workflows
.\manage.ps1 boot-snap-open    # Full workflow
.\manage.ps1 snap              # Just capture
.\manage.ps1 snap -Headful     # Debug mode
start.bat                      # Batch file

# Filters
.\manage.ps1 snap -Pages "dashboard,emails"
.\manage.ps1 snap -Elements ".page-header,.email-table"

# CI/CD
npm run snap                   # Headless capture
npm run snap:headful           # Show browser
```
