const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const PROFILE_FILE = 'profile.json';
const RECORDINGS_DIR = 'recordings';
const INDEX_FILE = path.join(RECORDINGS_DIR, 'recordings_index.json');

async function runRecording(browser, recordingPath, profile) {
  const recording = JSON.parse(fs.readFileSync(recordingPath, 'utf8'));
  console.log(`\n--- Running recording: ${recording.recording_name} ---`);
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();

  try {
    for (const step of recording.steps) {
      console.log(`Step: ${step.type} ${step.selectors ? `on ${step.selectors[0][0]}` : ''}`);
      
      switch (step.type) {
        case 'setViewport':
          await page.setViewportSize({ width: step.width, height: step.height });
          break;
          
        case 'navigate':
          await page.goto(step.url, { waitUntil: 'load', timeout: 30000 });
          break;
          
        case 'change':
          if (step.selectors && step.selectors.length > 0) {
            let value = step.value;
            // Replace placeholders like {{email}} with profile data
            if (value && value.startsWith('{{') && value.endsWith('}}')) {
              const key = value.substring(2, value.length - 2);
              value = profile[key] || profile['text'] || '';
            }
            
            // Try each selector until one works
            let success = false;
            for (const selectorGroup of step.selectors) {
              let selector = selectorGroup[0];
              // Handle Playwright aria selectors
              if (selector.startsWith('aria/')) {
                selector = `role=${selector.split('/')[1]}`;
                // This is a simplification, but good for common labels
              }
              
              try {
                // If it's still an aria/ selector, we need to use page.getByLabel or similar
                let element;
                if (selectorGroup[0].startsWith('aria/')) {
                   const label = selectorGroup[0].split('/')[1];
                   try {
                     element = page.getByLabel(label, { exact: false }).first();
                     await element.waitFor({ timeout: 2000 });
                     await element.fill(value);
                   } catch (e) {
                     // Try regular fill if getByLabel fails
                     await page.fill(selector, value, { timeout: 2000 });
                   }
                 } else if (selector.startsWith('xpath/')) {
                   const xpath = selector.split('xpath/')[1];
                   await page.fill(`xpath=${xpath}`, value, { timeout: 2000 });
                 } else {
                   await page.fill(selector, value, { timeout: 5000 });
                 }
                success = true;
                break;
              } catch (e) {
                // Try next selector
              }
            }
            if (!success) console.log(`  Warning: Could not find element for step change`);
          }
          break;
          
        case 'click':
          if (step.selectors && step.selectors.length > 0) {
            let success = false;
            for (const selectorGroup of step.selectors) {
              const selector = selectorGroup[0];
              try {
                if (selector.startsWith('aria/')) {
                   const label = selector.split('/')[1];
                   try {
                     const element = page.getByLabel(label, { exact: false }).first();
                     await element.click({ timeout: 2000 });
                   } catch (e) {
                     try {
                       const button = page.getByRole('button', { name: label, exact: false }).first();
                       await button.click({ timeout: 2000 });
                     } catch (e2) {
                       try {
                         const text = page.getByText(label, { exact: false }).first();
                         await text.click({ timeout: 2000 });
                       } catch (e3) {
                         // Last resort, try the selector directly
                         await page.click(selector, { timeout: 2000 });
                       }
                     }
                   }
                 } else if (selector.startsWith('xpath/')) {
                   const xpath = selector.split('xpath/')[1];
                   await page.click(`xpath=${xpath}`, { timeout: 2000 });
                 } else {
                   await page.click(selector, { timeout: 5000 });
                 }
                success = true;
                break;
              } catch (e) {
                // Try next selector
              }
            }
            if (!success) console.log(`  Warning: Could not find element for step click`);
          }
          break;
      }
    }
    
    // Wait a bit to see the result
    await page.waitForTimeout(3000);
    console.log(`Successfully completed recording: ${recording.recording_name}`);
    return true;
  } catch (error) {
    console.error(`Error running recording ${recording.recording_name}: ${error.message}`);
    return false;
  } finally {
    await page.close();
    await context.close();
  }
}

async function main() {
  const profile = JSON.parse(fs.readFileSync(PROFILE_FILE, 'utf8'));
  const index = JSON.parse(fs.readFileSync(INDEX_FILE, 'utf8'));
  const browser = await chromium.launch({ headless: false }); // Show browser so user can see it working

  // Get all recording IDs that have fields (skip the empty ones)
  const recordingIds = Object.keys(index.recordings).filter(id => {
    return index.recordings[id].total_fields > 0;
  });

  console.log(`Found ${recordingIds.length} recordings with fields to run.`);

  // For safety and visibility, we'll run them sequentially
  for (const id of recordingIds) {
    const recordingPath = path.join(RECORDINGS_DIR, `${id}.json`);
    if (fs.existsSync(recordingPath)) {
      const success = await runRecording(browser, recordingPath, profile);
      // You can add logic here to update the index with the success/failure result
    }
  }

  await browser.close();
  console.log('\nAll recordings finished execution.');
}

main().catch(console.error);
