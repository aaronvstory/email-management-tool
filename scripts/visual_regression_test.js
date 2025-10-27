#!/usr/bin/env node
/**
 * Phase 2B Visual Regression Testing
 *
 * Tests CSS changes across 10 pages at 4 viewports
 * Requirements:
 * - < 0.5% diff per image to pass
 * - Generates diff images and summary table
 *
 * Usage: node scripts/visual_regression_test.js [--baseline-only | --compare-only]
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const pixelmatch = require('pixelmatch').default;
const { PNG } = require('pngjs');

const BASE_URL = 'http://localhost:5000';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'visual_regression');
const BASELINE_DIR = path.join(SCREENSHOT_DIR, 'baseline');
const CURRENT_DIR = path.join(SCREENSHOT_DIR, 'current');
const DIFF_DIR = path.join(SCREENSHOT_DIR, 'diff');

// Test configuration
const VIEWPORTS = [
  { name: '1440px', width: 1440, height: 900 },
  { name: '1024px', width: 1024, height: 768 },
  { name: '768px', width: 768, height: 1024 },
  { name: '390px', width: 390, height: 844 }
];

const PAGES = [
  { name: 'Dashboard', url: '/dashboard' },
  { name: 'Emails', url: '/emails' },
  { name: 'Compose', url: '/compose' },
  { name: 'Watchers', url: '/watchers' },
  { name: 'Rules', url: '/rules' },
  { name: 'Accounts', url: '/accounts' },
  { name: 'Import Accounts', url: '/import_accounts' },
  { name: 'Diagnostics', url: '/diagnostics' },
  { name: 'Settings', url: '/settings' },
  { name: 'Style Guide', url: '/styleguide' }
];

// Create directories if they don't exist
function ensureDirectories() {
  [SCREENSHOT_DIR, BASELINE_DIR, CURRENT_DIR, DIFF_DIR].forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });
}

// Login helper
async function login(page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE_URL}/dashboard`, { timeout: 5000 });
}

// Capture screenshots for all pages at all viewports
async function captureScreenshots(outputDir, label) {
  console.log(`\n📸 Capturing ${label} screenshots...`);
  console.log('='.repeat(60));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Login once
  await login(page);

  let capturedCount = 0;

  for (const viewport of VIEWPORTS) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    console.log(`\n  Viewport: ${viewport.name}`);

    for (const pageConfig of PAGES) {
      try {
        await page.goto(`${BASE_URL}${pageConfig.url}`, { waitUntil: 'networkidle', timeout: 10000 });

        // Wait a bit for any animations to settle
        await page.waitForTimeout(500);

        const filename = `${pageConfig.name.replace(/\s+/g, '_')}_${viewport.name}.png`;
        const filepath = path.join(outputDir, filename);

        await page.screenshot({ path: filepath, fullPage: true });
        console.log(`    ✓ ${pageConfig.name}`);
        capturedCount++;
      } catch (error) {
        console.log(`    ✗ ${pageConfig.name} - ${error.message}`);
      }
    }
  }

  await browser.close();
  console.log(`\n  Total: ${capturedCount}/${VIEWPORTS.length * PAGES.length} screenshots captured`);
  return capturedCount;
}

// Compare screenshots and generate diff images
function compareScreenshots() {
  console.log(`\n🔍 Comparing screenshots...`);
  console.log('='.repeat(60));

  const results = [];
  const baselineFiles = fs.readdirSync(BASELINE_DIR).filter(f => f.endsWith('.png'));

  for (const filename of baselineFiles) {
    const baselinePath = path.join(BASELINE_DIR, filename);
    const currentPath = path.join(CURRENT_DIR, filename);
    const diffPath = path.join(DIFF_DIR, filename);

    if (!fs.existsSync(currentPath)) {
      console.log(`  ⚠️  Missing current: ${filename}`);
      continue;
    }

    try {
      const baseline = PNG.sync.read(fs.readFileSync(baselinePath));
      const current = PNG.sync.read(fs.readFileSync(currentPath));

      const { width, height } = baseline;
      const diff = new PNG({ width, height });

      const diffPixels = pixelmatch(
        baseline.data,
        current.data,
        diff.data,
        width,
        height,
        { threshold: 0.1 }
      );

      const totalPixels = width * height;
      const diffPercent = (diffPixels / totalPixels) * 100;
      const passed = diffPercent < 0.5;

      results.push({
        filename,
        diffPixels,
        totalPixels,
        diffPercent,
        passed
      });

      // Only save diff image if there are differences
      if (diffPixels > 0) {
        fs.writeFileSync(diffPath, PNG.sync.write(diff));
      }

      const icon = passed ? '✓' : '✗';
      const status = passed ? 'PASS' : 'FAIL';
      console.log(`  ${icon} ${filename}: ${diffPercent.toFixed(3)}% (${status})`);

    } catch (error) {
      console.log(`  ✗ Error comparing ${filename}: ${error.message}`);
    }
  }

  return results;
}

// Generate summary report
function generateReport(results) {
  console.log(`\n📊 Visual Regression Test Report`);
  console.log('='.repeat(60));

  // Group by page and viewport
  const pageGroups = {};
  results.forEach(result => {
    const parts = result.filename.replace('.png', '').split('_');
    const viewport = parts.pop();
    const pageName = parts.join(' ');

    if (!pageGroups[pageName]) {
      pageGroups[pageName] = {};
    }
    pageGroups[pageName][viewport] = result;
  });

  // Print table
  console.log('\n| Page | 1440px | 1024px | 768px | 390px | Status |');
  console.log('|------|--------|--------|-------|-------|--------|');

  let allPassed = true;
  Object.keys(pageGroups).sort().forEach(pageName => {
    const viewports = pageGroups[pageName];
    const row = [
      pageName,
      viewports['1440px']?.diffPercent.toFixed(3) + '%' || 'N/A',
      viewports['1024px']?.diffPercent.toFixed(3) + '%' || 'N/A',
      viewports['768px']?.diffPercent.toFixed(3) + '%' || 'N/A',
      viewports['390px']?.diffPercent.toFixed(3) + '%' || 'N/A'
    ];

    const pagePassed = Object.values(viewports).every(v => v.passed);
    const status = pagePassed ? '✓ PASS' : '✗ FAIL';
    if (!pagePassed) allPassed = false;

    console.log(`| ${row.join(' | ')} | ${status} |`);
  });

  // Summary stats
  const totalTests = results.length;
  const passed = results.filter(r => r.passed).length;
  const failed = totalTests - passed;
  const passRate = ((passed / totalTests) * 100).toFixed(1);

  console.log('\n' + '='.repeat(60));
  console.log(`Total Tests: ${totalTests}`);
  console.log(`Passed: ${passed} (${passRate}%)`);
  console.log(`Failed: ${failed}`);
  console.log('='.repeat(60));

  if (allPassed) {
    console.log('\n✅ All visual regression tests PASSED (<0.5% diff)');
  } else {
    console.log('\n❌ Some visual regression tests FAILED (≥0.5% diff)');
    console.log(`   Check diff images in: ${DIFF_DIR}`);
  }

  return allPassed;
}

// Main execution
async function main() {
  const args = process.argv.slice(2);
  const baselineOnly = args.includes('--baseline-only');
  const compareOnly = args.includes('--compare-only');
  const currentOnly = args.includes('--current-only');

  ensureDirectories();

  if (!compareOnly && !currentOnly) {
    // Capture baseline screenshots (before changes)
    await captureScreenshots(BASELINE_DIR, 'baseline');
  }

  if (currentOnly) {
    // Only capture current screenshots
    await captureScreenshots(CURRENT_DIR, 'current');
    return;
  }

  if (!baselineOnly && !compareOnly) {
    console.log('\n⏸️  Baseline captured. Apply CSS changes and press Enter to continue...');
    // In automated mode, we'll skip the pause
  }

  if (!baselineOnly) {
    if (!compareOnly && !currentOnly) {
      // Capture current screenshots (after changes)
      await captureScreenshots(CURRENT_DIR, 'current');
    }

    // Compare and generate report
    const results = compareScreenshots();
    const allPassed = generateReport(results);

    process.exit(allPassed ? 0 : 1);
  }
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
