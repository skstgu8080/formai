/**
 * Puppeteer Replay - EXACT Chrome DevTools replay
 * Uses @puppeteer/replay library (same as Chrome DevTools)
 */

const { createRunner, PuppeteerRunnerExtension } = require('@puppeteer/replay');
const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');

class ProfileValueExtension extends PuppeteerRunnerExtension {
    /**
     * Custom extension to replace values with profile data
     */
    constructor(browser, page, options) {
        super(browser, page, options);
        this.profileValues = options?.profileValues || {};
        this.stepDelay = options?.stepDelay || 1000;
        this.randomVariation = options?.randomVariation || 500;
    }

    /**
     * Add human-like delay with random variation
     */
    async humanDelay(baseDelay = null) {
        const delay = baseDelay || this.stepDelay;
        const variation = Math.random() * this.randomVariation - (this.randomVariation / 2);
        const totalDelay = Math.max(100, delay + variation);
        await new Promise(resolve => setTimeout(resolve, totalDelay));
    }

    async beforeAllSteps(flow) {
        await super.beforeAllSteps(flow);
        console.log(`[Puppeteer Replay] Starting replay: ${flow.title}`);
        console.log(`[Puppeteer Replay] Total steps: ${flow.steps.length}`);
        console.log(`[Puppeteer Replay] Profile values:`, JSON.stringify(this.profileValues, null, 2));

        // Attempt to close common popups/overlays
        await this.closeCommonPopups();
    }

    async closeCommonPopups() {
        /**
         * Try to close common popup/overlay patterns (cookie banners, newsletter signups, etc.)
         */
        const page = this.page;

        try {
            // Common selectors for close buttons
            const closeSelectors = [
                'button[aria-label*="close" i]',
                'button[aria-label*="dismiss" i]',
                '.modal-close',
                '.popup-close',
                '.close-modal',
                '.close-button',
                '[class*="close"][class*="button"]',
                'button.close',
                'a.close',
                '[data-dismiss="modal"]',
                '[data-close]',
                '.cookie-banner button',
                '.cookie-consent button',
                '#onetrust-accept-btn-handler',
                '.privacy-banner button'
            ];

            for (const selector of closeSelectors) {
                try {
                    const elements = await page.$$(selector);
                    for (const element of elements) {
                        const isVisible = await element.isVisible();
                        if (isVisible) {
                            await element.click();
                            console.log(`[Popup Closed] Closed popup using selector: ${selector}`);
                            await page.waitForTimeout(500);
                        }
                    }
                } catch (err) {
                    // Selector not found or click failed, continue
                }
            }
        } catch (err) {
            // Ignore errors - some pages may not have popups
        }
    }

    async beforeEachStep(step, flow) {
        await super.beforeEachStep(step, flow);

        // Replace value with profile data if available
        if (step.type === 'change' && step.selectors) {
            const selector = this.getFieldIdentifier(step.selectors);

            if (this.profileValues[selector]) {
                const originalValue = step.value;
                step.value = this.profileValues[selector];
                console.log(`[Value Replaced] ${selector}: "${originalValue}" → "${step.value}"`);
            }
        }
    }

    async afterEachStep(step, flow) {
        await super.afterEachStep(step, flow);
        console.log(`[Step Complete] ${step.type} ${this.getStepDescription(step)}`);

        // Add human-like delay after each action
        let delayTime = this.stepDelay;

        // Different delays for different action types
        if (step.type === 'navigate') {
            delayTime = 2000;
        } else if (step.type === 'click') {
            delayTime = 800;
        } else if (step.type === 'change') {
            delayTime = 1200;
        } else if (step.type === 'keyDown' || step.type === 'keyUp') {
            delayTime = 300;
        } else if (step.type === 'setViewport') {
            delayTime = 200;
        }

        await this.humanDelay(delayTime);
    }

    async afterAllSteps(flow) {
        await super.afterAllSteps(flow);
        console.log(`[Puppeteer Replay] Replay completed successfully`);
    }

    getFieldIdentifier(selectors) {
        if (!selectors || !selectors.length) return '';

        for (const selectorGroup of selectors) {
            for (const selector of selectorGroup) {
                if (selector.startsWith('#')) return selector;
                if (selector.startsWith('aria/')) return selector;
            }
        }

        return selectors[0][0] || '';
    }

    getStepDescription(step) {
        if (step.type === 'navigate') return step.url;
        if (step.type === 'click' || step.type === 'change') {
            const selector = this.getFieldIdentifier(step.selectors);
            return selector;
        }
        return '';
    }
}

async function replayRecording(recordingPath, profileValues = {}, options = {}) {
    const {
        headless = false,
        timeout = 30000,
        slowMo = 0,
        stepDelay = 1000,
        randomVariation = 500,
        autoClose = false,
        closeDelay = 2000
    } = options;

    let browser;
    let page;

    try {
        // Read recording file
        const recordingContent = await fs.readFile(recordingPath, 'utf-8');
        const recording = JSON.parse(recordingContent);

        console.log(`\n${'='.repeat(60)}`);
        console.log('Puppeteer Replay - EXACT Chrome DevTools Replay');
        console.log(`${'='.repeat(60)}`);
        console.log(`Recording: ${recording.title}`);
        console.log(`Steps: ${recording.steps.length}`);
        console.log(`Headless: ${headless}`);
        console.log(`Step Delay: ${stepDelay}ms ± ${randomVariation}ms`);
        console.log(`Auto-close: ${autoClose} ${autoClose ? `(after ${closeDelay}ms)` : ''}`);
        console.log(`${'='.repeat(60)}\n`);

        // Launch browser (same settings as Chrome DevTools)
        browser = await puppeteer.launch({
            headless: headless ? 'new' : false,
            defaultViewport: null,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled'
            ],
            slowMo: slowMo
        });

        page = await browser.newPage();

        // Set default timeout
        page.setDefaultTimeout(timeout);

        // Auto-dismiss dialogs/popups (alerts, confirms, prompts)
        page.on('dialog', async dialog => {
            console.log(`[Dialog Detected] Type: ${dialog.type()}, Message: ${dialog.message()}`);
            await dialog.dismiss();
            console.log('[Dialog Dismissed] Automatically dismissed popup');
        });

        // Create runner with our custom extension
        const runner = await createRunner(recording, new ProfileValueExtension(browser, page, {
            profileValues: profileValues,
            stepDelay: stepDelay,
            randomVariation: randomVariation
        }));

        // Run the replay - EXACTLY what Chrome DevTools does
        await runner.run();

        console.log('\n✓ Replay completed successfully!\n');

        // Auto-close or keep browser open
        if (autoClose) {
            console.log(`[Auto-close] Waiting ${closeDelay}ms before closing browser...`);
            await new Promise(resolve => setTimeout(resolve, closeDelay));
            await browser.close();
            console.log('[Auto-close] Browser closed');
        } else {
            console.log('[Manual] Browser will remain open - close manually when done');
            // Keep browser open for a moment to see results
            await new Promise(resolve => setTimeout(resolve, 2000));
        }

        return {
            success: true,
            message: 'Replay completed successfully'
        };

    } catch (error) {
        console.error('\n✗ Replay failed:', error.message);
        console.error(error.stack);

        // Auto-close on error if enabled
        if (autoClose && browser) {
            try {
                await browser.close();
                console.log('[Auto-close] Browser closed after error');
            } catch (closeErr) {
                console.error('[Auto-close] Failed to close browser:', closeErr.message);
            }
        }

        return {
            success: false,
            error: error.message,
            stack: error.stack
        };

    } finally {
        // Only close if not already closed by auto-close
        if (!autoClose && browser) {
            await browser.close();
        }
    }
}

/**
 * Replace values in recording with profile data (pre-processing)
 */
function replaceValuesInRecording(recording, profileMappings) {
    const modifiedRecording = JSON.parse(JSON.stringify(recording));

    for (const step of modifiedRecording.steps) {
        if (step.type === 'change' && step.selectors) {
            // Find matching profile mapping
            for (const mapping of profileMappings) {
                if (matchesSelector(step.selectors, mapping.selector)) {
                    step.value = mapping.value;
                    console.log(`[Pre-processing] ${mapping.selector}: "${step.value}"`);
                    break;
                }
            }
        }
    }

    return modifiedRecording;
}

function matchesSelector(selectors, targetSelector) {
    for (const selectorGroup of selectors) {
        for (const selector of selectorGroup) {
            if (selector === targetSelector) return true;
            if (selector.includes(targetSelector)) return true;
            if (targetSelector.includes(selector)) return true;
        }
    }
    return false;
}

// CLI usage
if (require.main === module) {
    const args = process.argv.slice(2);

    if (args.length === 0) {
        console.log('Usage: node puppeteer_replay.js <recording.json> [profile-values.json] [options]');
        console.log('');
        console.log('Options:');
        console.log('  --headless         Run in headless mode');
        console.log('  --timeout N        Set timeout in milliseconds (default: 30000)');
        console.log('  --slowmo N         Slow down operations by N milliseconds');
        console.log('  --stepdelay N      Delay between steps in milliseconds (default: 1000)');
        console.log('  --variation N      Random delay variation in milliseconds (default: 500)');
        console.log('  --autoclose        Automatically close browser after replay completes');
        console.log('  --closedelay N     Delay before auto-closing browser in milliseconds (default: 2000)');
        console.log('');
        console.log('Example:');
        console.log('  node puppeteer_replay.js recording.json profile.json --headless --stepdelay 1500 --autoclose');
        process.exit(1);
    }

    const recordingPath = args[0];
    const profilePath = args[1] && !args[1].startsWith('--') ? args[1] : null;

    const options = {
        headless: args.includes('--headless'),
        timeout: parseInt(args.find(arg => arg.startsWith('--timeout'))?.split('=')[1]) || 30000,
        slowMo: parseInt(args.find(arg => arg.startsWith('--slowmo'))?.split('=')[1]) || 0,
        stepDelay: parseInt(args.find(arg => arg.startsWith('--stepdelay'))?.split('=')[1]) || 1000,
        randomVariation: parseInt(args.find(arg => arg.startsWith('--variation'))?.split('=')[1]) || 500,
        autoClose: args.includes('--autoclose'),
        closeDelay: parseInt(args.find(arg => arg.startsWith('--closedelay'))?.split('=')[1]) || 2000
    };

    // Main async function
    (async () => {
        try {
            // Load profile values if provided
            let profileValues = {};
            if (profilePath) {
                try {
                    const content = await fs.readFile(profilePath, 'utf-8');
                    profileValues = JSON.parse(content);
                    console.log(`[Profile Values] Loaded ${Object.keys(profileValues).length} values from ${profilePath}`);
                } catch (err) {
                    console.warn('Could not load profile values:', err.message);
                }
            }

            // Run replay
            const result = await replayRecording(recordingPath, profileValues, options);

            if (result.success) {
                process.exit(0);
            } else {
                console.error('Replay failed:', result.error);
                process.exit(1);
            }
        } catch (err) {
            console.error('Fatal error:', err);
            process.exit(1);
        }
    })();
}

module.exports = { replayRecording, replaceValuesInRecording, ProfileValueExtension };
