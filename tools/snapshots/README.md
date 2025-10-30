# Screenshot Snapshot Tool

Automated screenshot capture for all application pages using Playwright. Generates date-stamped, multi-viewport snapshots with optional authentication state.

## Quick Start

### 1. Install Dependencies

```bash
npm install
npm run snap:install
```

This installs Playwright browsers with system dependencies.

### 2. Configure Login (Optional)

If your application requires authentication, create a storage state file once:

**Windows PowerShell:**
```powershell
$env:SNAP_BASE_URL = "http://localhost:5000"
$env:SNAP_LOGIN_PATH = "/login"
$env:SNAP_USER_SEL = "#email"
$env:SNAP_PASS_SEL = "#password"
$env:SNAP_SUBMIT_SEL = "button[type=submit]"
$env:SNAP_POSTLOGIN_SEL = "#sidebar"
$env:SNAP_USERNAME = "admin"
$env:SNAP_PASSWORD = "admin123"
npm run snap:update-state
```

**Linux/macOS:**
```bash
export SNAP_BASE_URL="http://localhost:5000"
export SNAP_LOGIN_PATH="/login"
export SNAP_USER_SEL="#email"
export SNAP_PASS_SEL="#password"
export SNAP_SUBMIT_SEL="button[type=submit]"
export SNAP_POSTLOGIN_SEL="#sidebar"
export SNAP_USERNAME="admin"
export SNAP_PASSWORD="admin123"
npm run snap:update-state
```

This creates `tools/snapshots/state.json` with your authenticated session. Subsequent runs reuse this state.

### 3. Capture Screenshots

**Using npm:**
```bash
npm run snap
```

**Using PowerShell helper:**
```powershell
.\tools\snapshots\snap.ps1
```

**Custom base URL:**
```bash
$env:SNAP_BASE_URL = "http://localhost:8000"
npm run snap
```

## Output Structure

```
snapshots/
  2025-10-30_143012/
    1440x900/
      20251030143012_dashboard.png
      20251030143013_emails.png
      20251030143014_watchers.png
      ...
    390x844/
      20251030143015_dashboard.png
      ...
```

Each run creates a timestamped folder with viewport subdirectories.

## Configuration

### Pages (`pages.json`)

Define routes to snapshot:

```json
[
  { "name": "dashboard", "path": "/dashboard", "ready": "#dashboard-page" },
  { "name": "emails", "path": "/emails-unified", "ready": "#emails-page" }
]
```

**Fields:**
- `name` - Filename prefix (alphanumeric, hyphens)
- `path` - Route path (must start with `/`)
- `ready` - CSS selector to wait for (ensures page is fully loaded)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SNAP_BASE_URL` | `http://localhost:5000` | Application base URL |
| `SNAP_OUT_DIR` | `snapshots` | Output directory (relative to repo root) |
| `SNAP_VIEWPORTS` | `1440x900,390x844` | Comma-separated viewport sizes (WxH) |
| `SNAP_STATE_FILE` | `tools/snapshots/state.json` | Authentication state file |
| `SNAP_PAGES_FILE` | `tools/snapshots/pages.json` | Pages configuration |
| `SNAP_TIMEOUT_MS` | `20000` | Page load timeout (milliseconds) |
| `SNAP_RETRIES` | `2` | Retry attempts per page |

**Login-specific:**
- `SNAP_LOGIN_PATH` - Login route (e.g., `/login`)
- `SNAP_USER_SEL` - Username input selector
- `SNAP_PASS_SEL` - Password input selector
- `SNAP_SUBMIT_SEL` - Submit button selector
- `SNAP_POSTLOGIN_SEL` - Post-login element to verify success
- `SNAP_USERNAME` - Username credential
- `SNAP_PASSWORD` - Password credential

## Advanced Usage

### Custom Viewports

```bash
$env:SNAP_VIEWPORTS = "1920x1080,1280x800,768x1024,390x844"
npm run snap
```

### Capture Specific Pages

Edit `tools/snapshots/pages.json` and remove unwanted pages, then run:

```bash
npm run snap
```

### CI/CD Integration

Example GitHub Actions workflow (`.github/workflows/snapshots.yml`):

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
    runs-on: ubuntu-latest
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
          python simple_app.py &
          sleep 5
      
      - name: Capture snapshots
        env:
          SNAP_BASE_URL: http://localhost:5000
        run: npm run snap
      
      - uses: actions/upload-artifact@v4
        with:
          name: ui-snapshots
          path: snapshots/**
          retention-days: 30
```

## Features

- **Multi-viewport**: Test responsive layouts automatically
- **Authentication state**: Login once, reuse for all pages
- **Retry logic**: Handles transient failures gracefully
- **Full-page screenshots**: Captures entire scrollable content
- **Ready selectors**: Waits for page to fully render
- **Animation freeze**: Disables transitions for consistent captures
- **Date-stamped output**: Organized folders for easy comparison

## Troubleshooting

**"Login env vars not set"**
→ Ensure all `SNAP_LOGIN_*` variables are set when using `--update-state`

**"Failed to capture [page]"**
→ Check `ready` selector in `pages.json` exists on page
→ Increase `SNAP_TIMEOUT_MS` for slow-loading pages
→ Verify application is running at `SNAP_BASE_URL`

**"Timeout waiting for selector"**
→ Ensure `ready` selector is present after page load
→ Check browser console for JavaScript errors
→ Verify authentication state is valid (re-run `snap:update-state`)

**Screenshots are blank/partial**
→ Increase wait timeout or adjust `ready` selector
→ Check for lazy-loaded content (add explicit waits in `snap.ts`)

## File Structure

```
tools/snapshots/
├── snap.ts          # Main screenshot engine
├── snap.ps1         # PowerShell helper (Windows)
├── pages.json       # Route configuration
├── state.json       # Authentication state (gitignored)
└── README.md        # This file
```

## Integration with PR Workflow

After making UI changes:

1. Start application: `python simple_app.py`
2. Capture snapshots: `npm run snap`
3. Compare with previous snapshots (manual or automated diff tool)
4. Attach screenshots to PR for review

**Recommended tools for visual diff:**
- [Percy](https://percy.io/)
- [Chromatic](https://www.chromatic.com/)
- [BackstopJS](https://github.com/garris/BackstopJS)
- Manual: Use image diff tools like ImageMagick `compare`

## License

Integrated with Email Management Tool project. See root LICENSE file.
