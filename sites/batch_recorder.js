const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const SITES_FILE = 'sites.md';
const RECORDINGS_DIR = 'recordings';
const INDEX_FILE = path.join(RECORDINGS_DIR, 'recordings_index.json');

async function getSites() {
  const content = fs.readFileSync(SITES_FILE, 'utf8');
  return content.split('\n')
    .map(line => line.replace(/^\d+→/, '').trim())
    .filter(line => line.startsWith('http'));
}

function generateId() {
  return crypto.randomUUID().split('-').slice(0, 2).join('-');
}

async function recordSite(browser, url, index) {
  // Normalize URL to avoid duplicates with minor variations (trailing slashes, etc.)
  const normalizedUrl = url.trim().replace(/\/$/, '');
  
  // Skip if already in index
  const alreadyRecorded = Object.values(index.recordings || {}).some(r => {
    const existingUrl = (r.url || '').trim().replace(/\/$/, '');
    return existingUrl === normalizedUrl;
  });
  if (alreadyRecorded) {
    console.log(`Skipping already recorded site: ${url}`);
    return null;
  }

  console.log(`Recording site: ${url}`);
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();

  try {
    // Shorter timeout and use load event instead of networkidle for speed
    await page.goto(url, { waitUntil: 'load', timeout: 30000 });
    const title = await page.title();
    
    // Find all input and select elements
    const inputs = await page.$$eval('input, select, textarea', (elements) => {
      return elements.map(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0 || getComputedStyle(el).display === 'none') {
          return null;
        }
        
        // Get label text
        let label = '';
        if (el.id) {
          const labelEl = document.querySelector(`label[for="${el.id}"]`);
          if (labelEl) label = labelEl.innerText.trim();
        }
        if (!label) {
          const parentLabel = el.closest('label');
          if (parentLabel) label = parentLabel.innerText.trim();
        }
        
        return {
          tagName: el.tagName.toLowerCase(),
          type: el.type,
          name: el.name,
          id: el.id,
          placeholder: el.placeholder || '',
          label: label || el.ariaLabel || '',
          value: el.value,
          rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
        };
      }).filter(x => x !== null);
    });

    const recordingId = generateId();
    const timestamp = new Date().toISOString();
    const date = timestamp.split('T')[0];

    const recording = {
      recording_id: recordingId,
      recording_name: title || url,
      url: url,
      original_url: url,
      created_date: date,
      created_timestamp: timestamp,
      total_fields: inputs.length,
      steps: [
        {
          type: 'setViewport',
          width: 1280,
          height: 800,
          deviceScaleFactor: 1,
          isMobile: false,
          hasTouch: false,
          isLandscape: false
        },
        {
          type: 'navigate',
          url: url,
          assertedEvents: [
            {
              type: 'navigation',
              url: url,
              title: title
            }
          ]
        }
      ]
    };

    for (const input of inputs) {
      let profileKey = 'text';
      let value = '{{text}}';
      
      const labelLower = (input.label || '').toLowerCase();
      const nameLower = (input.name || '').toLowerCase();
      const idLower = (input.id || '').toLowerCase();
      const placeholderLower = (input.placeholder || '').toLowerCase();
      const typeLower = (input.type || '').toLowerCase();

      if (labelLower.includes('email') || nameLower.includes('email') || typeLower === 'email') {
        profileKey = 'email';
        value = '{{email}}';
      } else if (labelLower.includes('password') || nameLower.includes('password') || typeLower === 'password') {
        profileKey = 'password';
        value = '{{password}}';
      } else if (labelLower.includes('first name') || nameLower.includes('firstname') || nameLower.includes('first_name')) {
        profileKey = 'firstName';
        value = '{{firstName}}';
      } else if (labelLower.includes('last name') || nameLower.includes('lastname') || nameLower.includes('last_name')) {
        profileKey = 'lastName';
        value = '{{lastName}}';
      } else if (labelLower.includes('phone') || nameLower.includes('phone') || typeLower === 'tel') {
        profileKey = 'phone';
        value = '{{phone}}';
      } else if (labelLower.includes('zip') || labelLower.includes('postal') || nameLower.includes('zip') || nameLower.includes('postal')) {
        profileKey = 'zipCode';
        value = '{{zipCode}}';
      } else if (labelLower.includes('city') || nameLower.includes('city')) {
        profileKey = 'city';
        value = '{{city}}';
      } else if (labelLower.includes('address') || nameLower.includes('address')) {
        profileKey = 'address';
        value = '{{address}}';
      }

      const selectors = [];
      if (input.id) selectors.push([`#${input.id}`]);
      if (input.name) selectors.push([`[name="${input.name}"]`]);
      if (input.label) selectors.push([`aria/${input.label}`]);

      if (input.type === 'checkbox' || input.type === 'radio') {
        recording.steps.push({
          type: 'click',
          selectors: selectors,
          target: 'main',
          offsetX: 5,
          offsetY: 5,
          _fieldInfo: {
            name: input.name,
            type: input.type,
            label: input.label,
            profile_key: profileKey
          }
        });
      } else {
        recording.steps.push({
          type: 'change',
          selectors: selectors,
          value: value,
          target: 'main',
          _fieldInfo: {
            name: input.name,
            type: input.type,
            label: input.label,
            profile_key: profileKey
          }
        });
      }
    }

    // Add a click on the submit button if found
    const submitButton = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
      const submit = buttons.find(b => {
        const text = (b.innerText || b.value || '').toLowerCase();
        return text.includes('sign up') || text.includes('register') || text.includes('create') || text.includes('submit');
      });
      if (submit) {
        const rect = submit.getBoundingClientRect();
        return {
          id: submit.id,
          name: submit.name,
          label: submit.innerText || submit.value || '',
          rect: { x: rect.x, y: rect.y }
        };
      }
      return null;
    });

    if (submitButton) {
      const selectors = [];
      if (submitButton.id) selectors.push([`#${submitButton.id}`]);
      if (submitButton.name) selectors.push([`[name="${submitButton.name}"]`]);
      if (submitButton.label) selectors.push([`aria/${submitButton.label}`]);
      
      recording.steps.push({
        type: 'click',
        selectors: selectors,
        target: 'main',
        offsetX: 5,
        offsetY: 5,
        _isSubmit: true
      });
    }

    const filePath = path.join(RECORDINGS_DIR, `${recordingId}.json`);
    fs.writeFileSync(filePath, JSON.stringify(recording, null, 2));
    console.log(`Saved recording to ${filePath}`);

    return {
      id: recordingId,
      name: title || url,
      url: url,
      date: date,
      timestamp: timestamp,
      fields: inputs.length,
      file: `recordings/${recordingId}.json`
    };

  } catch (error) {
    console.error(`Error recording ${url}: ${error.message}`);
    return null;
  } finally {
    await context.close();
  }
}

async function main() {
  const sites = await getSites();
  const browser = await chromium.launch({ headless: true });
  
  let index = {};
  if (fs.existsSync(INDEX_FILE)) {
    index = JSON.parse(fs.readFileSync(INDEX_FILE, 'utf8'));
  }
  if (!index.recordings) index.recordings = {};

  // Process sites in batches of 10 to be faster but not overload
  const batchSize = 10;
  for (let i = 0; i < sites.length; i += batchSize) {
    const batch = sites.slice(i, i + batchSize);
    const results = await Promise.all(batch.map(url => recordSite(browser, url, index)));
    
    for (const result of results) {
      if (result) {
        index.recordings[result.id] = {
          recording_id: result.id,
          recording_name: result.name,
          url: result.url,
          created_date: result.date,
          created_timestamp: result.timestamp,
          total_fields: result.fields,
          import_source: 'playwright_batch_recorder',
          file_path: result.file,
          success_rate: 'pending',
          description: `Auto-recorded from ${result.url}`,
          tags: []
        };
      }
    }
    
    // Save index after each batch
    fs.writeFileSync(INDEX_FILE, JSON.stringify(index, null, 2));
    console.log(`Processed batch ${i / batchSize + 1} of ${Math.ceil(sites.length / batchSize)}`);
  }

  await browser.close();
  console.log('All sites processed!');
}

main().catch(console.error);
