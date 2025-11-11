# Future Feature Plans - FormAI

## AI-Powered Form Field Discovery

### Overview

**Goal:** Before recording, users can enter a URL and have AI automatically scrape and analyze all form fields, providing a complete JSON schema with intelligent field mappings.

**User Flow:**
1. User goes to Recorder page
2. Clicks "Discover Form" button
3. Enters target URL in modal
4. Backend launches headless browser → scrapes form → AI analyzes fields
5. Frontend displays interactive field table with:
   - Discovered fields with AI-suggested mappings
   - Profile validation (which fields can be auto-filled)
   - Confidence scores
   - Export to JSON button

---

## Implementation Plan

### Phase 1: Backend Discovery Engine

#### File: `tools/form_field_discoverer.py` (NEW)

```python
"""
AI-Powered Form Field Discovery
Scrapes forms and uses AI to analyze field purposes
"""

class FormFieldDiscoverer:
    """
    Discover and analyze form fields from a URL using Puppeteer + AI
    """

    def __init__(self, ai_provider='ollama'):
        """
        Args:
            ai_provider: 'ollama' (local) or 'openrouter' (cloud)
        """
        self.ai_provider = ai_provider
        self.ollama_analyzer = AIRecordingAnalyzer()  # Existing
        self.puppeteer_script = Path(__file__).parent / "puppeteer_discover.js"

    async def discover_fields(self, url: str, profile: Dict = None) -> Dict:
        """
        Main discovery method

        Process:
        1. Launch Puppeteer (headless)
        2. Navigate to URL
        3. Extract all form fields (inputs, selects, textareas)
        4. Get attributes, labels, validation rules
        5. Run AI analysis for field purpose detection
        6. Validate against profile if provided
        7. Return structured JSON

        Args:
            url: Target form URL
            profile: Optional profile dict for validation

        Returns:
            {
                "discovery_id": "uuid",
                "url": "https://...",
                "total_fields": 8,
                "fields": [...],
                "profile_validation": {...}
            }
        """
        pass

    async def _scrape_with_puppeteer(self, url: str) -> List[Dict]:
        """Call puppeteer_discover.js to scrape form fields"""
        pass

    async def _analyze_with_ai(self, fields: List[Dict]) -> List[Dict]:
        """Use AI to determine field purposes and mappings"""
        pass

    def _validate_against_profile(self, fields: List[Dict], profile: Dict) -> Dict:
        """Check which fields can be filled from profile"""
        pass
```

---

#### File: `tools/puppeteer_discover.js` (NEW)

```javascript
/**
 * Puppeteer Form Field Scraper
 * Extracts all form fields from a page
 */

async function discoverFormFields(url) {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox']
    });

    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'networkidle0' });

    // Extract all form elements
    const fields = await page.evaluate(() => {
        const formElements = [];

        // Find all inputs, selects, textareas
        document.querySelectorAll('input, select, textarea').forEach((el, index) => {
            // Get label
            const label = findLabelFor(el);

            // Build field object
            formElements.push({
                field_index: index,
                element_type: el.tagName.toLowerCase(),
                input_type: el.type || null,
                selector: generateSelector(el),
                alternative_selectors: generateAlternativeSelectors(el),
                attributes: {
                    name: el.name || null,
                    id: el.id || null,
                    type: el.type || null,
                    placeholder: el.placeholder || null,
                    required: el.required || false,
                    pattern: el.pattern || null,
                    minlength: el.minLength || null,
                    maxlength: el.maxLength || null
                },
                label_text: label,
                options: el.tagName === 'SELECT' ? getSelectOptions(el) : null
            });
        });

        return formElements;
    });

    await browser.close();
    return fields;
}

// Helper functions for selector generation, label detection, etc.
```

**CLI Usage:**
```bash
node puppeteer_discover.js <url>
# Outputs JSON to stdout
```

---

### Phase 2: Backend API Integration

#### Modify: `formai_server.py`

**Add Pydantic Model:**
```python
class DiscoverFormRequest(BaseModel):
    url: str
    ai_provider: Optional[str] = 'ollama'  # or 'openrouter'
    profile_id: Optional[str] = None
```

**Add Endpoint:**
```python
@app.post("/api/forms/discover")
async def discover_form_fields(request: DiscoverFormRequest):
    """
    Discover form fields from URL with AI analysis

    Body:
    {
        "url": "https://example.com/signup",
        "ai_provider": "ollama",
        "profile_id": "optional-uuid"
    }

    Returns:
    {
        "success": true,
        "discovery_id": "uuid",
        "discovery": {
            "url": "...",
            "total_fields": 8,
            "fields": [...],
            "profile_validation": {...}
        }
    }
    """
    try:
        # Get AI provider from request or settings
        ai_provider = request.ai_provider or os.getenv('AI_PROVIDER', 'ollama')

        # Create discoverer
        discoverer = FormFieldDiscoverer(ai_provider=ai_provider)

        # Get profile if provided
        profile = None
        if request.profile_id:
            profile_path = PROFILES_DIR / f"{request.profile_id}.json"
            if profile_path.exists():
                with open(profile_path) as f:
                    profile = json.load(f)

        # Run discovery
        discovery = await discoverer.discover_fields(request.url, profile)

        # Save discovery for later retrieval
        discovery_id = str(uuid.uuid4())
        discovery_path = Path("discoveries") / f"{discovery_id}.json"
        discovery_path.parent.mkdir(exist_ok=True)

        with open(discovery_path, 'w') as f:
            json.dump(discovery, f, indent=2)

        return {
            "success": True,
            "discovery_id": discovery_id,
            "discovery": discovery
        }

    except Exception as e:
        logger.error(f"Form discovery failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/forms/discovery/{discovery_id}")
async def get_discovery(discovery_id: str):
    """Retrieve saved discovery by ID"""
    discovery_path = Path("discoveries") / f"{discovery_id}.json"

    if not discovery_path.exists():
        raise HTTPException(status_code=404, detail="Discovery not found")

    with open(discovery_path) as f:
        discovery = json.load(f)

    return discovery
```

---

### Phase 3: Frontend UI

#### Modify: `web/recorder.html`

**Add Button:**
```html
<!-- Add next to "Import Chrome Recording" button -->
<div class="button-group">
    <button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md"
            onclick="openImportModal()">
        Import Chrome Recording
    </button>

    <!-- NEW BUTTON -->
    <button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md"
            onclick="openDiscoverFormModal()">
        🔍 Discover Form Fields
    </button>
</div>
```

**Add Modal:**
```html
<!-- Discovery Modal -->
<div id="discoverFormModal" class="modal" style="display:none">
    <div class="modal-content">
        <span class="close" onclick="closeDiscoverFormModal()">&times;</span>

        <h2>Discover Form Fields</h2>
        <p>Enter a form URL to automatically discover and analyze all fields</p>

        <div class="form-group">
            <label>Form URL:</label>
            <input type="url"
                   id="discoverUrl"
                   placeholder="https://example.com/signup"
                   class="w-full px-3 py-2 border rounded-md">
        </div>

        <div class="form-group">
            <label>AI Provider:</label>
            <select id="aiProvider" class="w-full px-3 py-2 border rounded-md">
                <option value="ollama">Ollama (Local AI - Free)</option>
                <option value="openrouter">OpenRouter (Cloud AI)</option>
            </select>
        </div>

        <div class="form-group">
            <label>Validate Against Profile (Optional):</label>
            <select id="validateProfile" class="w-full px-3 py-2 border rounded-md">
                <option value="">-- No Profile Validation --</option>
                <!-- Populated dynamically -->
            </select>
        </div>

        <div class="button-group">
            <button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md"
                    onclick="startFormDiscovery()">
                🚀 Start Discovery
            </button>
            <button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md"
                    onclick="closeDiscoverFormModal()">
                Cancel
            </button>
        </div>

        <!-- Loading State -->
        <div id="discoveryLoading" style="display:none">
            <div class="spinner"></div>
            <p>Analyzing form fields with AI...</p>
        </div>
    </div>
</div>

<!-- Discovery Results Modal -->
<div id="discoveryResultsModal" class="modal" style="display:none">
    <div class="modal-content" style="max-width: 1200px">
        <span class="close" onclick="closeDiscoveryResults()">&times;</span>

        <h2>Discovered Form Fields</h2>
        <p id="discoveryUrl" class="text-sm text-gray-600"></p>

        <div class="stats-bar">
            <span>Total Fields: <strong id="totalFields">0</strong></span>
            <span>Fillable: <strong id="fillableFields">0</strong></span>
            <span>Missing: <strong id="missingFields">0</strong></span>
        </div>

        <!-- Interactive Fields Table -->
        <div class="table-container">
            <table id="discoveredFieldsTable" class="w-full">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Field Type</th>
                        <th>Label</th>
                        <th>Selector</th>
                        <th>AI Mapping</th>
                        <th>Confidence</th>
                        <th>Profile Value</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Dynamic content -->
                </tbody>
            </table>
        </div>

        <!-- Export Buttons -->
        <div class="button-group">
            <button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md"
                    onclick="exportDiscoveryJSON()">
                📥 Export JSON
            </button>
            <button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md"
                    onclick="createRecordingFromDiscovery()">
                🎬 Create Recording Template
            </button>
            <button class="bg-secondary hover:bg-secondary/90 text-secondary-foreground px-4 py-2 rounded-md"
                    onclick="closeDiscoveryResults()">
                Close
            </button>
        </div>
    </div>
</div>
```

---

#### File: `static/js/form-discovery.js` (NEW)

```javascript
/**
 * Form Discovery Frontend Module
 */

let currentDiscovery = null;

async function startFormDiscovery() {
    const url = document.getElementById('discoverUrl').value;
    const aiProvider = document.getElementById('aiProvider').value;
    const profileId = document.getElementById('validateProfile').value;

    if (!url) {
        alert('Please enter a URL');
        return;
    }

    // Show loading
    document.getElementById('discoveryLoading').style.display = 'block';

    try {
        const response = await fetch('/api/forms/discover', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                url: url,
                ai_provider: aiProvider,
                profile_id: profileId || null
            })
        });

        const result = await response.json();

        if (result.success) {
            currentDiscovery = result.discovery;
            displayDiscoveredFields(result.discovery);
            closeDiscoverFormModal();
        } else {
            throw new Error(result.error || 'Discovery failed');
        }

    } catch (error) {
        console.error('Discovery error:', error);
        alert('Failed to discover form fields: ' + error.message);
    } finally {
        document.getElementById('discoveryLoading').style.display = 'none';
    }
}

function displayDiscoveredFields(discovery) {
    // Open results modal
    document.getElementById('discoveryResultsModal').style.display = 'block';

    // Set header info
    document.getElementById('discoveryUrl').textContent = discovery.url;
    document.getElementById('totalFields').textContent = discovery.total_fields;

    if (discovery.profile_validation) {
        document.getElementById('fillableFields').textContent =
            discovery.profile_validation.fillable_fields || 0;
        document.getElementById('missingFields').textContent =
            discovery.profile_validation.missing_fields?.length || 0;
    }

    // Build table
    const tbody = document.querySelector('#discoveredFieldsTable tbody');
    tbody.innerHTML = '';

    discovery.fields.forEach((field, index) => {
        const row = document.createElement('tr');

        // Confidence color
        const confidence = field.ai_analysis?.confidence || 0;
        const confidenceColor = confidence > 0.8 ? 'green' : confidence > 0.5 ? 'orange' : 'red';

        // Profile value indicator
        const hasValue = field.profile_validation?.has_value || false;
        const valueIcon = hasValue ? '✅' : '❌';
        const valuePreview = field.profile_validation?.value_preview || 'N/A';

        row.innerHTML = `
            <td>${index + 1}</td>
            <td><code>${field.input_type || field.element_type}</code></td>
            <td>${field.label_text || '<em>No label</em>'}</td>
            <td><code class="text-xs">${field.selector}</code></td>
            <td>${field.ai_analysis?.profile_mapping || 'unknown'}</td>
            <td><span style="color: ${confidenceColor}">${(confidence * 100).toFixed(0)}%</span></td>
            <td>${valueIcon} ${valuePreview}</td>
            <td>
                <button onclick="editFieldMapping(${index})" class="text-blue-500 hover:underline">
                    Edit
                </button>
            </td>
        `;

        tbody.appendChild(row);
    });
}

function exportDiscoveryJSON() {
    if (!currentDiscovery) return;

    const json = JSON.stringify(currentDiscovery, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `form-discovery-${Date.now()}.json`;
    a.click();

    URL.revokeObjectURL(url);
}

function createRecordingFromDiscovery() {
    // Future: Generate Chrome DevTools recording format from discovery
    alert('Feature coming soon: Auto-generate recording from discovered fields');
}

function editFieldMapping(fieldIndex) {
    // Future: Allow user to manually adjust AI mapping
    alert('Feature coming soon: Edit field mapping');
}

function closeDiscoverFormModal() {
    document.getElementById('discoverFormModal').style.display = 'none';
}

function openDiscoverFormModal() {
    document.getElementById('discoverFormModal').style.display = 'block';
    loadProfilesForValidation();
}

function closeDiscoveryResults() {
    document.getElementById('discoveryResultsModal').style.display = 'none';
}

async function loadProfilesForValidation() {
    try {
        const response = await fetch('/api/profiles');
        const profiles = await response.json();

        const select = document.getElementById('validateProfile');
        select.innerHTML = '<option value="">-- No Profile Validation --</option>';

        profiles.forEach(profile => {
            const option = document.createElement('option');
            option.value = profile.id;
            option.textContent = `${profile.first_name} ${profile.last_name}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load profiles:', error);
    }
}
```

---

### Phase 4: Settings Integration

#### Modify: `web/settings.html`

```html
<!-- Add to settings page -->
<div class="setting-section">
    <h3 class="text-lg font-semibold mb-4">Form Discovery Settings</h3>

    <div class="form-group">
        <label class="block mb-2">
            <strong>AI Provider for Form Analysis:</strong>
        </label>
        <select id="aiProvider"
                class="w-full px-3 py-2 border rounded-md"
                onchange="saveSettings()">
            <option value="ollama">Ollama (Local, Free)</option>
            <option value="openrouter">OpenRouter (Cloud, Free Models Available)</option>
        </select>
        <p class="text-sm text-gray-600 mt-1">
            Ollama runs AI models locally on your machine. OpenRouter uses cloud AI (requires API key).
        </p>
    </div>

    <div id="openrouterSettings" style="display:none">
        <div class="form-group mt-4">
            <label class="block mb-2">
                <strong>OpenRouter API Key:</strong>
            </label>
            <input type="password"
                   id="openrouterKey"
                   class="w-full px-3 py-2 border rounded-md"
                   placeholder="sk-or-v1-..."
                   onchange="saveSettings()">
            <p class="text-sm text-gray-600 mt-1">
                Get your free API key at <a href="https://openrouter.ai" target="_blank" class="text-blue-500">openrouter.ai</a>
            </p>
        </div>
    </div>
</div>
```

---

## JSON Schema Structure

### Discovery Output Format

```json
{
  "discovery_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com/signup",
  "discovered_at": "2025-01-11T10:30:00Z",
  "page_title": "Sign Up - Example Site",
  "ai_provider": "ollama",
  "ai_model": "llama3.2",
  "total_fields": 8,
  "form_analysis": {
    "form_type": "user_registration",
    "ai_confidence": 0.92,
    "suggested_profile_completion": 0.85,
    "detected_sections": ["personal_info", "account_details", "preferences"]
  },
  "profile_validation": {
    "profile_id": "profile-uuid",
    "profile_name": "John Doe",
    "fillable_fields": 6,
    "missing_fields": ["company", "job_title"],
    "completion_percentage": 0.75
  },
  "fields": [
    {
      "field_index": 0,
      "element_type": "input",
      "input_type": "email",
      "selector": "#email",
      "alternative_selectors": [
        "input[name='email']",
        "input[type='email']"
      ],
      "attributes": {
        "name": "email",
        "id": "email",
        "type": "email",
        "placeholder": "Enter your email",
        "required": true,
        "autocomplete": "email"
      },
      "label_text": "Email Address",
      "ai_analysis": {
        "field_purpose": "email",
        "profile_mapping": "email",
        "confidence": 0.95,
        "reasoning": "Email input with clear email-related attributes and label"
      },
      "profile_validation": {
        "has_value": true,
        "value_preview": "john.d***@example.com",
        "value_type": "email"
      }
    },
    {
      "field_index": 1,
      "element_type": "input",
      "input_type": "text",
      "selector": "#firstName",
      "alternative_selectors": [
        "input[name='firstName']"
      ],
      "attributes": {
        "name": "firstName",
        "id": "firstName",
        "type": "text",
        "placeholder": "First name",
        "required": true,
        "maxlength": 50
      },
      "label_text": "First Name",
      "ai_analysis": {
        "field_purpose": "first_name",
        "profile_mapping": "first_name",
        "confidence": 0.98,
        "reasoning": "Clear first name field with matching label and attributes"
      },
      "profile_validation": {
        "has_value": true,
        "value_preview": "John",
        "value_type": "string"
      }
    },
    {
      "field_index": 2,
      "element_type": "select",
      "input_type": null,
      "selector": "#country",
      "alternative_selectors": [
        "select[name='country']"
      ],
      "attributes": {
        "name": "country",
        "id": "country",
        "required": true
      },
      "label_text": "Country",
      "options": [
        {"value": "US", "text": "United States"},
        {"value": "CA", "text": "Canada"},
        {"value": "UK", "text": "United Kingdom"}
      ],
      "ai_analysis": {
        "field_purpose": "country",
        "profile_mapping": "country",
        "confidence": 0.90,
        "reasoning": "Country selector with standard country codes"
      },
      "profile_validation": {
        "has_value": true,
        "value_preview": "United States",
        "value_type": "string"
      }
    }
  ]
}
```

---

## Implementation Phases

### Phase 1: Core Backend (Week 1)
- [ ] Create `form_field_discoverer.py`
- [ ] Create `puppeteer_discover.js`
- [ ] Add `/api/forms/discover` endpoint
- [ ] Test with simple forms (Google Forms, Typeform)

### Phase 2: AI Integration (Week 2)
- [ ] Integrate Ollama analyzer
- [ ] Add OpenRouter API support
- [ ] Test AI accuracy on various form types
- [ ] Tune AI prompts for better field detection

### Phase 3: Frontend UI (Week 3)
- [ ] Add "Discover Form" button to recorder.html
- [ ] Create discovery modal
- [ ] Create `form-discovery.js` module
- [ ] Build interactive field table

### Phase 4: Profile Validation (Week 4)
- [ ] Add profile comparison logic
- [ ] Show fillable vs missing fields
- [ ] Display completion percentage
- [ ] Add visual indicators

### Phase 5: Export & Polish (Week 5)
- [ ] JSON export functionality
- [ ] Error handling for failed discoveries
- [ ] Loading states and progress indicators
- [ ] Documentation and user guide

---

## Benefits

1. **Time Savings**: Users understand form structure before recording
2. **AI Intelligence**: Automatically maps fields to profile data
3. **Profile Awareness**: See which fields can be auto-filled
4. **Documentation**: Export JSON schemas for documentation
5. **Error Prevention**: Identify required fields and validation rules upfront
6. **Flexibility**: Works with any public form URL
7. **Privacy**: Runs locally with Ollama (no data sent to cloud)

---

## Technical Considerations

### Challenges
- **Dynamic Forms**: Forms that load fields via JavaScript after page load
- **Multi-Step Forms**: Forms split across multiple pages
- **Authentication**: Forms behind login walls (not supported initially)
- **CAPTCHA**: Forms with CAPTCHA protection
- **Rate Limiting**: Sites that block automated scraping

### Solutions
- Use Puppeteer's `waitUntil: 'networkidle0'` for dynamic content
- Add delay options for slow-loading forms
- MVP focuses on public forms only
- Handle errors gracefully with clear messages
- Add retry logic with exponential backoff

---

## Future Enhancements

1. **Auto-Generate Recordings**: Convert discovery JSON to Chrome DevTools recording format
2. **Multi-Page Forms**: Detect and follow "Next" buttons
3. **Smart Form Detection**: Automatically find forms on landing pages
4. **Confidence Tuning**: Allow users to adjust AI confidence thresholds
5. **Field Editing**: Interactive UI to correct AI mappings
6. **Batch Discovery**: Discover multiple forms at once
7. **Version Tracking**: Track form changes over time
8. **API Integration**: REST API for programmatic form discovery

---

## Dependencies

**Existing:**
- Puppeteer (already installed)
- OpenRouter API integration (already implemented)
- Ollama AI analyzer (already implemented)
- FastAPI backend (already running)

**New:**
- None! Uses existing infrastructure

---

## Estimated Effort

- **Backend**: 2-3 days
- **Frontend UI**: 2-3 days
- **AI Integration**: 1-2 days
- **Testing & Polish**: 2-3 days
- **Total**: ~1-2 weeks

---

## Success Metrics

1. Successfully discovers 95%+ of form fields on standard forms
2. AI mapping accuracy >85% for common fields (email, name, phone)
3. Profile validation correctly identifies fillable fields
4. User can export usable JSON schema
5. Discovery completes in <10 seconds for typical forms

---

## Notes

- This feature complements (not replaces) Chrome DevTools recording
- Focus on simple public forms initially
- AI accuracy will improve with usage and feedback
- Consider adding user feedback loop to improve AI prompts
