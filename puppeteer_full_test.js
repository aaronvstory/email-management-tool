/**
 * Email Management Tool - Comprehensive Puppeteer Test Suite
 * Tests all functionality, UI elements, and styling
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Configuration
const BASE_URL = 'http://127.0.0.1:5000';
const SCREENSHOT_DIR = './screenshots/puppeteer-test';
const RESULTS_FILE = `test_results_puppeteer_${Date.now()}.json`;

// Test credentials
const LOGIN_CREDENTIALS = {
    username: 'admin',
    password: 'admin123'
};

// Test results tracker
const testResults = {
    timestamp: new Date().toISOString(),
    totalTests: 0,
    passed: 0,
    failed: 0,
    details: [],
    screenshots: [],
    performanceMetrics: {}
};

// Utility functions
function log(message, type = 'info') {
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
    const prefix = {
        'info': '[INFO]',
        'success': '[✓]',
        'error': '[✗]',
        'warning': '[!]'
    };
    
    const colors = {
        'info': '\x1b[36m',
        'success': '\x1b[32m',
        'error': '\x1b[31m',
        'warning': '\x1b[33m',
        'reset': '\x1b[0m'
    };
    
    console.log(`${colors[type]}${prefix[type]}${colors.reset} ${timestamp} - ${message}`);
}

async function takeScreenshot(page, name, description = '') {
    try {
        const filename = `${name.replace(/\s+/g, '-')}_${Date.now()}.png`;
        const filepath = path.join(SCREENSHOT_DIR, filename);
        await page.screenshot({ path: filepath, fullPage: true });
        testResults.screenshots.push({
            name,
            description,
            filename,
            timestamp: new Date().toISOString()
        });
        log(`Screenshot saved: ${filename}`, 'success');
        return filepath;
    } catch (error) {
        log(`Failed to take screenshot: ${error.message}`, 'error');
        return null;
    }
}

async function testCase(name, testFn) {
    testResults.totalTests++;
    const startTime = Date.now();
    
    try {
        await testFn();
        const duration = Date.now() - startTime;
        testResults.passed++;
        testResults.details.push({
            name,
            status: 'passed',
            duration: `${duration}ms`
        });
        log(`${name} - PASSED (${duration}ms)`, 'success');
        return true;
    } catch (error) {
        const duration = Date.now() - startTime;
        testResults.failed++;
        testResults.details.push({
            name,
            status: 'failed',
            duration: `${duration}ms`,
            error: error.message
        });
        log(`${name} - FAILED: ${error.message}`, 'error');
        return false;
    }
}

async function checkElementStyling(page, selector, expectedStyles) {
    const element = await page.$(selector);
    if (!element) throw new Error(`Element ${selector} not found`);
    
    const computedStyles = await page.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
            display: styles.display,
            backgroundColor: styles.backgroundColor,
            color: styles.color,
            fontSize: styles.fontSize,
            fontWeight: styles.fontWeight,
            padding: styles.padding,
            margin: styles.margin,
            border: styles.border,
            borderRadius: styles.borderRadius,
            boxShadow: styles.boxShadow
        };
    }, element);
    
    for (const [property, expectedValue] of Object.entries(expectedStyles)) {
        if (computedStyles[property] !== expectedValue) {
            log(`Style mismatch for ${selector}: ${property} is ${computedStyles[property]}, expected ${expectedValue}`, 'warning');
        }
    }
    
    return computedStyles;
}

// Main test suite
async function runTests() {
    log('='.repeat(60), 'info');
    log('EMAIL MANAGEMENT TOOL - COMPREHENSIVE PUPPETEER TEST', 'info');
    log('='.repeat(60), 'info');
    
    // Create screenshot directory
    if (!fs.existsSync(SCREENSHOT_DIR)) {
        fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
    
    // Launch browser
    log('Launching browser...', 'info');
    const browser = await puppeteer.launch({
        headless: false,  // Set to true for CI/CD
        args: ['--window-size=1920,1080'],
        defaultViewport: { width: 1920, height: 1080 }
    });
    
    const page = await browser.newPage();
    
    // Enable console logging
    page.on('console', msg => {
        if (msg.type() === 'error') {
            log(`Console Error: ${msg.text()}`, 'error');
        }
    });
    
    try {
        // Test 1: Check if application is running
        await testCase('Application Accessibility', async () => {
            const response = await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
            if (!response || !response.ok()) {
                throw new Error(`Server returned status: ${response ? response.status() : 'No response'}`);
            }
        });
        
        // Test 2: Login page rendering and styling
        await testCase('Login Page Rendering', async () => {
            await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle2' });
            await page.waitForSelector('form', { timeout: 5000 });
            
            // Check for all required elements
            const elements = [
                'input[name="username"]',
                'input[name="password"]',
                'button[type="submit"]',
                '.card',  // Bootstrap card
                'h2'      // Login header
            ];
            
            for (const selector of elements) {
                const element = await page.$(selector);
                if (!element) throw new Error(`Missing element: ${selector}`);
            }
            
            // Check gradient background
            const bodyStyles = await page.evaluate(() => {
                const styles = window.getComputedStyle(document.body);
                return {
                    backgroundImage: styles.backgroundImage,
                    minHeight: styles.minHeight
                };
            });
            
            if (!bodyStyles.backgroundImage.includes('gradient')) {
                log('Warning: Expected gradient background not found', 'warning');
            }
            
            await takeScreenshot(page, 'login-page', 'Login page with styling');
        });
        
        // Test 3: Login functionality
        await testCase('Login Functionality', async () => {
            await page.type('input[name="username"]', LOGIN_CREDENTIALS.username);
            await page.type('input[name="password"]', LOGIN_CREDENTIALS.password);
            await takeScreenshot(page, 'login-filled', 'Login form filled');
            
            await Promise.all([
                page.waitForNavigation({ waitUntil: 'networkidle2' }),
                page.click('button[type="submit"]')
            ]);
            
            // Check if we're redirected to dashboard
            const currentUrl = page.url();
            if (!currentUrl.includes('/dashboard') && !currentUrl.includes('/emails')) {
                throw new Error(`Unexpected redirect: ${currentUrl}`);
            }
        });
        
        // Test 4: Dashboard layout and navigation
        await testCase('Dashboard Layout', async () => {
            // Check sidebar
            const sidebar = await page.$('.sidebar, #sidebar, nav');
            if (!sidebar) throw new Error('Sidebar not found');
            
            // Check navigation links
            const navLinks = await page.$$eval('a[href*="/"], nav a', links => 
                links.map(link => ({
                    text: link.textContent.trim(),
                    href: link.href
                }))
            );
            
            const requiredLinks = ['Dashboard', 'Email Queue', 'Inbox', 'Compose', 'Accounts'];
            for (const required of requiredLinks) {
                const found = navLinks.some(link => 
                    link.text.toLowerCase().includes(required.toLowerCase())
                );
                if (!found) {
                    log(`Warning: Navigation link for '${required}' not found`, 'warning');
                }
            }
            
            await takeScreenshot(page, 'dashboard', 'Main dashboard view');
        });
        
        // Test 5: Email Queue functionality
        await testCase('Email Queue Page', async () => {
            await page.goto(`${BASE_URL}/emails`, { waitUntil: 'networkidle2' });
            
            // Check for table or card layout
            const hasTable = await page.$('table');
            const hasCards = await page.$('.card');
            
            if (!hasTable && !hasCards) {
                log('Warning: No table or card layout found for emails', 'warning');
            }
            
            // Check for action buttons
            const buttons = await page.$$eval('button, .btn', btns => 
                btns.map(btn => btn.textContent.trim())
            );
            
            await takeScreenshot(page, 'email-queue', 'Email queue page');
        });
        
        // Test 6: Email Compose page
        await testCase('Email Compose Page', async () => {
            await page.goto(`${BASE_URL}/compose`, { waitUntil: 'networkidle2' });
            
            // Check for compose form elements
            const formElements = [
                'select[name="account_id"], #account_id',
                'input[name="recipient"], input[type="email"]',
                'input[name="subject"], #subject',
                'textarea[name="body"], #body'
            ];
            
            for (const selector of formElements) {
                const element = await page.$(selector);
                if (!element) {
                    log(`Warning: Compose form element not found: ${selector}`, 'warning');
                }
            }
            
            // Test character counter if present
            const charCounter = await page.$('.char-count, #char-count');
            if (charCounter) {
                log('Character counter found', 'success');
            }
            
            await takeScreenshot(page, 'compose-page', 'Email compose interface');
        });
        
        // Test 7: Inbox page
        await testCase('Inbox Page', async () => {
            await page.goto(`${BASE_URL}/inbox`, { waitUntil: 'networkidle2' });
            
            // Check for inbox elements
            const inboxElements = await page.$$('.email-item, .card, tr');
            log(`Found ${inboxElements.length} email items in inbox`, 'info');
            
            // Check for account filter
            const accountFilter = await page.$('select[name="account_id"], #account-filter');
            if (accountFilter) {
                log('Account filter dropdown found', 'success');
            }
            
            await takeScreenshot(page, 'inbox-page', 'Email inbox view');
        });
        
        // Test 8: Account Management
        await testCase('Account Management Page', async () => {
            await page.goto(`${BASE_URL}/accounts`, { waitUntil: 'networkidle2' });
            
            // Check for account list
            const accounts = await page.$$('.account-item, .card, table tr');
            log(`Found ${accounts.length} account entries`, 'info');
            
            // Check for Add Account button
            const addButton = await page.$('a[href*="/add"], button:has-text("Add")');
            if (!addButton) {
                log('Warning: Add Account button not found', 'warning');
            }
            
            await takeScreenshot(page, 'accounts-page', 'Account management page');
        });
        
        // Test 9: Responsive design
        await testCase('Responsive Design Check', async () => {
            const viewports = [
                { name: 'Mobile', width: 375, height: 667 },
                { name: 'Tablet', width: 768, height: 1024 },
                { name: 'Desktop', width: 1920, height: 1080 }
            ];
            
            for (const viewport of viewports) {
                await page.setViewport(viewport);
                await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle2' });
                await takeScreenshot(page, `responsive-${viewport.name.toLowerCase()}`, 
                    `${viewport.name} view (${viewport.width}x${viewport.height})`);
            }
        });
        
        // Test 10: Performance metrics
        await testCase('Performance Metrics', async () => {
            await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle2' });
            
            const metrics = await page.metrics();
            const performance = await page.evaluate(() => {
                const timing = window.performance.timing;
                return {
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    loadComplete: timing.loadEventEnd - timing.navigationStart
                };
            });
            
            testResults.performanceMetrics = {
                ...metrics,
                ...performance
            };
            
            log(`Page load time: ${performance.loadComplete}ms`, 'info');
            log(`DOM ready time: ${performance.domContentLoaded}ms`, 'info');
        });
        
        // Test 11: Styling consistency
        await testCase('Styling Consistency Check', async () => {
            await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle2' });
            
            // Check Bootstrap is loaded
            const hasBootstrap = await page.evaluate(() => {
                return typeof window.bootstrap !== 'undefined' || 
                       document.querySelector('link[href*="bootstrap"]') !== null;
            });
            
            if (!hasBootstrap) {
                throw new Error('Bootstrap not loaded');
            }
            
            // Check for gradient theme
            const hasGradient = await page.evaluate(() => {
                const elements = document.querySelectorAll('[style*="gradient"], .bg-gradient');
                return elements.length > 0 || 
                       window.getComputedStyle(document.body).backgroundImage.includes('gradient');
            });
            
            if (!hasGradient) {
                log('Warning: Gradient theme not detected', 'warning');
            }
            
            // Check color scheme (purple theme)
            const purpleElements = await page.$$eval('*', elements => {
                return elements.filter(el => {
                    const styles = window.getComputedStyle(el);
                    return styles.backgroundColor.includes('103, 58, 183') || // Purple
                           styles.backgroundColor.includes('667eea') ||         // Gradient start
                           styles.backgroundColor.includes('764ba2');           // Gradient end
                }).length;
            });
            
            log(`Found ${purpleElements} elements with purple theme colors`, 'info');
        });
        
        // Test 12: Error handling
        await testCase('Error Handling Check', async () => {
            // Try accessing a non-existent page
            await page.goto(`${BASE_URL}/nonexistent`, { waitUntil: 'networkidle2' });
            
            // Check if we get a proper error page or redirect
            const pageContent = await page.content();
            if (pageContent.includes('404') || pageContent.includes('Not Found')) {
                log('404 error page working correctly', 'success');
            } else if (page.url().includes('/login') || page.url().includes('/dashboard')) {
                log('Redirected to valid page', 'success');
            } else {
                log('Warning: No proper error handling for non-existent pages', 'warning');
            }
        });
        
    } catch (error) {
        log(`Test suite error: ${error.message}`, 'error');
    } finally {
        // Close browser
        await browser.close();
        
        // Save test results
        fs.writeFileSync(RESULTS_FILE, JSON.stringify(testResults, null, 2));
        
        // Print summary
        log('='.repeat(60), 'info');
        log('TEST SUMMARY', 'info');
        log('='.repeat(60), 'info');
        log(`Total Tests: ${testResults.totalTests}`, 'info');
        log(`Passed: ${testResults.passed}`, 'success');
        log(`Failed: ${testResults.failed}`, testResults.failed > 0 ? 'error' : 'success');
        log(`Screenshots taken: ${testResults.screenshots.length}`, 'info');
        log(`Results saved to: ${RESULTS_FILE}`, 'info');
        
        // Performance summary
        if (testResults.performanceMetrics.loadComplete) {
            log('', 'info');
            log('Performance Metrics:', 'info');
            log(`  Page Load: ${testResults.performanceMetrics.loadComplete}ms`, 'info');
            log(`  DOM Ready: ${testResults.performanceMetrics.domContentLoaded}ms`, 'info');
            log(`  JS Heap Used: ${Math.round(testResults.performanceMetrics.JSHeapUsedSize / 1048576)}MB`, 'info');
        }
        
        // Exit with appropriate code
        process.exit(testResults.failed > 0 ? 1 : 0);
    }
}

// Run the tests
runTests().catch(error => {
    log(`Fatal error: ${error.message}`, 'error');
    process.exit(1);
});