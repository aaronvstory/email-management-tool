// tools/snapshots/snap.ts
import { chromium, type Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

type View = { width: number; height: number; label: string };

const arg = (name: string, d?: string): string | undefined => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? (process.argv[i + 1] ?? 'true') : d;
};
const flag = (name: string) => process.argv.includes(`--${name}`);

const BASE_URL = arg('base-url', process.env.SNAP_BASE_URL || 'http://localhost:5000')!;
const OUT_DIR = arg('out', 'snapshots')!;
const HEADFUL = flag('headful');
const UPDATE_STATE = flag('update-state');
const STATE_PATH = arg('state', path.join(__dirname, 'state.json'))!;

const LOGIN_PATH = arg('login', process.env.SNAP_LOGIN_PATH || '/login');
const USER_SEL = arg('user-sel', process.env.SNAP_USER_SEL || '#email');
const PASS_SEL = arg('pass-sel', process.env.SNAP_PASS_SEL || '#password');
const SUBMIT_SEL = arg('submit-sel', process.env.SNAP_SUBMIT_SEL || 'button[type=submit]');
const USERNAME = arg('username', process.env.SNAP_USERNAME);
const PASSWORD = arg('password', process.env.SNAP_PASSWORD);

// Optional: capture only a subset of pages by key, comma-separated
const PAGES_FILTER = (arg('pages') || '').split(',').filter(Boolean);

// Optional: element-only screenshots: css selector or key from pages.json
const ELEMENTS = (arg('elements') || '').split(',').filter(Boolean);

const views: View[] = [
  { width: 1440, height: 900, label: '1440x900' },
  { width: 390, height: 844, label: '390x844' }
];

type PageConf = { key: string; url: string; ready?: string; elements?: string[] };
const pages: PageConf[] = JSON.parse(
  fs.readFileSync(path.join(__dirname, 'pages.json'), 'utf8')
);

const stamp = () => {
  const d = new Date();
  const pad = (n: number) => `${n}`.padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
};

async function loginIfNeeded(page: Page) {
  if (!USERNAME || !PASSWORD) return;
  await page.goto(`${BASE_URL}${LOGIN_PATH}`, { waitUntil: 'domcontentloaded' });
  await page.fill(USER_SEL!, USERNAME);
  await page.fill(PASS_SEL!, PASSWORD);
  await page.click(SUBMIT_SEL!);
  await page.waitForLoadState('networkidle');
}

async function freezeAnimations(page: Page) {
  await page.addStyleTag({
    content: `
      * { transition: none !important; animation: none !important; }
      .blinking, [data-animated="true"] { animation: none !important; }
    `
  });
}

(async () => {
  const browser = await chromium.launch({ headless: !HEADFUL });
  const context = await browser.newContext({
    storageState: fs.existsSync(STATE_PATH) ? STATE_PATH : undefined
  });
  const page = await context.newPage();

  // Update/save login state
  if (UPDATE_STATE) {
    await loginIfNeeded(page);
    await context.storageState({ path: STATE_PATH });
    await browser.close();
    console.log(`Auth state saved → ${STATE_PATH}`);
    process.exit(0);
  }

  const batchDir = path.join(process.cwd(), OUT_DIR, stamp());
  fs.mkdirSync(batchDir, { recursive: true });

  const targetPages = PAGES_FILTER.length
    ? pages.filter(p => PAGES_FILTER.includes(p.key))
    : pages;

  for (const view of views) {
    await page.setViewportSize({ width: view.width, height: view.height });
    const viewDir = path.join(batchDir, view.label);
    fs.mkdirSync(viewDir, { recursive: true });

    for (const conf of targetPages) {
      const url = `${BASE_URL}${conf.url}`;
      for (let attempt = 1; attempt <= 2; attempt++) {
        try {
          await page.goto(url, { waitUntil: 'domcontentloaded' });
          await freezeAnimations(page);
          if (conf.ready) await page.waitForSelector(conf.ready, { timeout: 15000 });

          // Element-only mode (if --elements is set)
          if (ELEMENTS.length) {
            const list = conf.elements || [];
            for (const sel of ELEMENTS) {
              const selector = list.find(e => e === sel) || sel; // allow ad-hoc or predeclared
              const loc = page.locator(selector).first();
              await loc.waitFor({ state: 'visible', timeout: 5000 });
              const out = path.join(viewDir, `${conf.key}__element__${selector.replace(/[^\w-]+/g, '_')}.png`);
              await loc.screenshot({ path: out });
              console.log(`✓ element ${selector} → ${out}`);
            }
          } else {
            const out = path.join(viewDir, `${conf.key}.png`);
            await page.screenshot({ path: out, fullPage: true });
            console.log(`✓ page ${conf.key} → ${out}`);
          }
          break;
        } catch (e) {
          if (attempt === 2) console.error(`✗ ${conf.key} failed:`, e);
          else await page.waitForTimeout(1200);
        }
      }
    }
  }

  console.log(`Done → ${batchDir}`);
  await browser.close();
})();
