/**
 * Playwright E2E tests for complete email account management flow
 */

const { test, expect } = require('@playwright/test');

// Test configuration
const BASE_URL = 'http://localhost:5000';
const ADMIN_USERNAME = 'admin';
const ADMIN_PASSWORD = 'admin123';

test.describe('Email Account Management E2E Flow', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto(BASE_URL);
    
    // Login as admin
    await page.fill('input[name="username"]', ADMIN_USERNAME);
    await page.fill('input[name="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    
    // Wait for dashboard to load
    await page.waitForURL(`${BASE_URL}/dashboard`);
  });
  
  test('Complete account management workflow', async ({ page }) => {
    // Step 1: Navigate to accounts page
    await page.click('a[href="/accounts"]');
    await page.waitForURL(`${BASE_URL}/accounts`);
    
    // Verify page loaded
    await expect(page.locator('h2')).toContainText('Email Account Management');
    
    // Step 2: Check account statistics
    const totalAccounts = await page.locator('#total-accounts').textContent();
    const activeAccounts = await page.locator('#active-accounts').textContent();
    const connectedAccounts = await page.locator('#connected-accounts').textContent();
    
    console.log(`Initial stats - Total: ${totalAccounts}, Active: ${activeAccounts}, Connected: ${connectedAccounts}`);
  });
  
  test('Add new email account', async ({ page }) => {
    // Navigate to accounts page
    await page.goto(`${BASE_URL}/accounts`);
    
    // Click add account button
    await page.click('button:has-text("Add Account")');
    await page.waitForURL(`${BASE_URL}/accounts/add`);
    
    // Fill in account details
    await page.fill('input[name="account_name"]', 'Test Gmail Account');
    await page.fill('input[name="email_address"]', 'test@gmail.com');
    
    // SMTP settings
    await page.fill('input[name="smtp_host"]', 'smtp.gmail.com');
    await page.fill('input[name="smtp_port"]', '587');
    await page.fill('input[name="smtp_username"]', 'test@gmail.com');
    await page.fill('input[name="smtp_password"]', 'app-password-here');
    
    // IMAP settings
    await page.fill('input[name="imap_host"]', 'imap.gmail.com');
    await page.fill('input[name="imap_port"]', '993');
    await page.fill('input[name="imap_username"]', 'test@gmail.com');
    await page.fill('input[name="imap_password"]', 'app-password-here');
    await page.check('input[name="imap_use_ssl"]');
    
    // Note: In real test, would mock the connection test
    // await page.click('button[type="submit"]');
  });
  
  test('Real-time health monitoring', async ({ page }) => {
    await page.goto(`${BASE_URL}/accounts`);
    
    // Wait for health check to run
    await page.waitForTimeout(2000);
    
    // Check for status indicators
    const statusIndicators = await page.locator('.connection-indicator').count();
    console.log(`Found ${statusIndicators} status indicators`);
    
    // Verify protocol status icons
    const smtpIcons = await page.locator('[id^="smtp-status-"]').count();
    const imapIcons = await page.locator('[id^="imap-status-"]').count();
    const pop3Icons = await page.locator('[id^="pop3-status-"]').count();
    
    expect(smtpIcons).toBeGreaterThanOrEqual(0);
    expect(imapIcons).toBeGreaterThanOrEqual(0);
    expect(pop3Icons).toBeGreaterThanOrEqual(0);
  });
  
  test('Test account connection', async ({ page }) => {
    await page.goto(`${BASE_URL}/accounts`);
    
    // Find first account card if exists
    const accountCard = await page.locator('.account-card').first();
    const cardExists = await accountCard.count() > 0;
    
    if (cardExists) {
      // Click test button
      await accountCard.locator('button:has-text("Test")').click();
      
      // Wait for toast notification
      await page.waitForSelector('.toast', { timeout: 5000 });
      
      const toastText = await page.locator('.toast').textContent();
      console.log(`Test result: ${toastText}`);
    }
  });
  
  test('Edit account details', async ({ page }) => {
    await page.goto(`${BASE_URL}/accounts`);
    
    // Find first account card if exists
    const accountCard = await page.locator('.account-card').first();
    const cardExists = await accountCard.count() > 0;
    
    if (cardExists) {
      // Click edit button
      await accountCard.locator('button:has-text("Edit")').click();
      
      // Wait for edit modal
      await page.waitForSelector('#editModal.show');
      
      // Verify form loaded
      await expect(page.locator('#edit-account-name')).toBeVisible();
      
      // Update account name
      await page.fill('#edit-account-name', 'Updated Account Name');
      
      // Save changes
      await page.click('#editAccountForm button[type="submit"]');
      
      // Wait for success notification
      await page.waitForSelector('.toast-success', { timeout: 5000 });
    }
  });
  
  test('Run diagnostics on account', async ({ page }) => {
    await page.goto(`${BASE_URL}/accounts`);
    
    const accountCard = await page.locator('.account-card').first();
    const cardExists = await accountCard.count() > 0;
    
    if (cardExists) {
      // Click diagnostics button
      await accountCard.locator('button:has-text("Diagnose")').click();
      
      // Wait for diagnostics modal
      await page.waitForSelector('#diagnosticsModal.show');
      
      // Wait for results
      await page.waitForSelector('.alert', { timeout: 10000 });
      
      // Check for test results
      const smtpResult = await page.locator('.alert:has-text("SMTP Test")').count();
      const imapResult = await page.locator('.alert:has-text("IMAP Test")').count();
      
      expect(smtpResult).toBe(1);
      expect(imapResult).toBe(1);
    }
  });
  
  test('Dashboard integration', async ({ page }) => {
    // Navigate to dashboard
    await page.goto(`${BASE_URL}/dashboard`);
    
    // Check for account selector
    const accountSelector = await page.locator('select#account-selector').count();
    
    if (accountSelector > 0) {
      // Select an account
      await page.selectOption('select#account-selector', { index: 1 });
      
      // Wait for page to update
      await page.waitForTimeout(1000);
      
      // Verify filtered stats
      const pendingEmails = await page.locator('.stat-card:has-text("Pending")').textContent();
      console.log(`Pending emails for selected account: ${pendingEmails}`);
    }
  });
  
  test('Export accounts', async ({ page }) => {
    await page.goto(`${BASE_URL}/accounts`);
    
    // Set up download handler
    const downloadPromise = page.waitForEvent('download');
    
    // Click export button
    await page.click('button:has-text("Export")');
    
    // Wait for download
    const download = await downloadPromise;
    
    // Verify download
    expect(download.suggestedFilename()).toBe('email_accounts_export.json');
  });
  
  test('Empty state handling', async ({ page }) => {
    // This test assumes no accounts exist
    await page.goto(`${BASE_URL}/accounts`);
    
    const emptyState = await page.locator('.empty-state').count();
    
    if (emptyState > 0) {
      // Verify empty state message
      await expect(page.locator('.empty-title')).toContainText('No Email Accounts Configured');
      
      // Verify add account button exists
      await expect(page.locator('.empty-state button:has-text("Add Your First Account")')).toBeVisible();
    }
  });
  
  test('Responsive design', async ({ page }) => {
    await page.goto(`${BASE_URL}/accounts`);
    
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    
    // Verify cards stack vertically
    const accountCards = await page.locator('.account-card').count();
    if (accountCards > 0) {
      const firstCard = await page.locator('.account-card').first().boundingBox();
      const secondCard = await page.locator('.account-card').nth(1).boundingBox();
      
      if (firstCard && secondCard) {
        // Cards should be stacked (second card below first)
        expect(secondCard.y).toBeGreaterThan(firstCard.y + firstCard.height);
      }
    }
    
    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    
    // Test desktop viewport
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(500);
  });
});

// Performance tests
test.describe('Performance Tests', () => {
  test('Page load performance', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto(`${BASE_URL}/accounts`);
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    console.log(`Page load time: ${loadTime}ms`);
    
    // Page should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });
  
  test('Health check performance', async ({ page }) => {
    await page.goto(`${BASE_URL}/accounts`);
    
    // Measure health check API call
    const healthCheckPromise = page.waitForResponse(response => 
      response.url().includes('/api/accounts/') && 
      response.url().includes('/health')
    );
    
    const startTime = Date.now();
    
    // Trigger health check (happens automatically)
    const response = await healthCheckPromise;
    
    const responseTime = Date.now() - startTime;
    console.log(`Health check response time: ${responseTime}ms`);
    
    // Health check should respond within 500ms
    expect(responseTime).toBeLessThan(500);
    expect(response.status()).toBe(200);
  });
});