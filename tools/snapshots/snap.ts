import { chromium, BrowserContext, Page } from 'playwright';
import fs from 'fs';
import path from 'path';

type PageDef = { name: string; path: string; ready?: string };

const BASE_URL = process.env.SNAP_BASE_URL || 'http://localhost:5000';
const OUT_DIR  = process.env.SNAP_OUT_DIR  || 'snapshots';
const VP_LIST  = (process.env.SNAP_VIEWPORTS || '1440x900,390x844')
  .split(',')
  .map(v => {
    const [w, h] = v.toLowerCase().split('x').map(Number);
    return { label: `${w}x${h}`, width: w, height: h };
  });

const STATE_FILE = process.env.SNAP_STATE_FILE || 'tools/snapshots/state.json';
const PAGES_FILE = process.env.SNAP_PAGES_FILE || 'tools/snapshots/pages.json';

const LOGIN_PATH = process.env.SNAP_LOGIN_PATH;            // e.g. "/login"
const LOGIN_USER_SELECTOR = process.env.SNAP_USER_SEL;     // e.g. "#email"
const LOGIN_PASS_SELECTOR = process.env.SNAP_PASS_SEL;     // e.g. "#password"
const LOGIN_SUBMIT_SELECTOR = process.env.SNAP_SUBMIT_SEL; // e.g. "button[type=submit]"
const LOGIN_USERNAME = process.env.SNAP_USERNAME;
const LOGIN_PASSWORD = process.env.SNAP_PASSWORD;

const MAX_RETRIES = Number(process.env.SNAP_RETRIES || 2);
const TIMEOUT = Number(process.env.SNAP_TIMEOUT_MS || 20000);

function nowStamp() {
  const d = new Date();
  const pad = (n:number)=>String(n).padStart(2,'0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

async function ensureDir(dir: string) {
  await fs.promises.mkdir(dir, { recursive: true });
}

async function loginAndSaveState(): Promise<void> {
  if (!LOGIN_PATH || !LOGIN_USER_SELECTOR || !LOGIN_PASS_SELECTOR || !LOGIN_SUBMIT_SELECTOR) {
    throw new Error('Login env vars not set; provide SNAP_LOGIN_PATH, SNAP_USER_SEL, SNAP_PASS_SEL, SNAP_SUBMIT_SEL.');
  }
  if (!LOGIN_USERNAME || !LOGIN_PASSWORD) {
    throw new Error('Provide SNAP_USERNAME and SNAP_PASSWORD to perform login.');
  }

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(TIMEOUT);

  await page.goto(new URL(LOGIN_PATH, BASE_URL).toString(), { waitUntil: 'networkidle' });
  await page.fill(LOGIN_USER_SELECTOR, LOGIN_USERNAME);
  await page.fill(LOGIN_PASS_SELECTOR, LOGIN_PASSWORD);
  await Promise.all([
    page.click(LOGIN_SUBMIT_SELECTOR),
    page.waitForLoadState('networkidle')
  ]);

  // Optionally verify a post-login element (set SNAP_POSTLOGIN_SEL)
  const POSTLOGIN = process.env.SNAP_POSTLOGIN_SEL;
  if (POSTLOGIN) await page.waitForSelector(POSTLOGIN, { timeout: TIMEOUT });

  await context.storageState({ path: STATE_FILE });
  await browser.close();
  console.log(`Saved storage state -> ${STATE_FILE}`);
}

async function makeContext(): Promise<BrowserContext> {
  const args: any = {};
  if (fs.existsSync(STATE_FILE)) args.storageState = STATE_FILE;
  const browser = await chromium.launch();
  return browser.newContext(args);
}

async function snapPage(context: BrowserContext, def: PageDef, outRoot: string) {
  for (const vp of VP_LIST) {
    const outDir = path.join(outRoot, vp.label);
    await ensureDir(outDir);

    const page: Page = await context.newPage();
    await page.setViewportSize({ width: vp.width, height: vp.height });
    page.setDefaultTimeout(TIMEOUT);

    // Reduce visual noise
    await page.addInitScript(() => {
      // Freeze animations/transitions
      const css = `
        *, *::before, *::after { transition: none !important; animation: none !important; caret-color: transparent !important; }
      `;
      const style = document.createElement('style');
      style.textContent = css;
      document.head.appendChild(style);
    });

    let attempt = 0, ok = false, lastErr: any = null;

    while (attempt <= MAX_RETRIES && !ok) {
      try {
        const url = new URL(def.path, BASE_URL).toString();
        await page.goto(url, { waitUntil: 'networkidle' });
        if (def.ready) await page.waitForSelector(def.ready, { timeout: TIMEOUT });

        // Give any badges/counters a moment to settle
        await page.waitForTimeout(300);

        const stamp = new Date().toISOString().slice(0,19).replace(/[:T]/g,'');
        const fname = `${stamp}_${def.name}.png`;
        const fpath = path.join(outDir, fname);

        await page.screenshot({ path: fpath, fullPage: true });
        console.log(`✅ ${vp.label} ${def.name} -> ${fpath}`);
        ok = true;
      } catch (e) {
        lastErr = e;
        attempt += 1;
        if (attempt <= MAX_RETRIES) {
          console.warn(`Retry ${attempt}/${MAX_RETRIES} for ${def.name} at ${vp.label}…`);
          await page.waitForTimeout(500);
        }
      }
    }

    await page.close();
    if (!ok) {
      console.error(`❌ Failed to capture ${def.name} @ ${vp.label}`, lastErr);
    }
  }
}

async function main() {
  const args = process.argv.slice(2);
  const doUpdateState = args.includes('--update-state');

  if (doUpdateState) {
    await loginAndSaveState();
  }

  const pages: PageDef[] = JSON.parse(await fs.promises.readFile(PAGES_FILE, 'utf8'));
  const outRoot = path.join(OUT_DIR, nowStamp());
  await ensureDir(outRoot);

  const context = await makeContext();
  try {
    for (const def of pages) {
      await snapPage(context, def, outRoot);
    }
  } finally {
    await context.browser()?.close();
  }

  console.log(`All done. Folder: ${outRoot}`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
