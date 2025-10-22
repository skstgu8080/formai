/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

class DashboardApp {
    constructor() {
        this.profileSelect = document.getElementById('profile-select');
        this.urlScopeRadios = document.querySelectorAll('input[name="url-scope"]');
        this.urlAmountInput = document.getElementById('url-amount-input');
        this.urlGroupSelect = document.getElementById('url-group-select');
        this.modeSelect = document.getElementById('mode-select');
        this.llmModelSelect = document.getElementById('llm-model-select');
        this.startButton = document.querySelector('.start-automation');
        this.stopButton = document.querySelector('.stop-automation');
        this.analyzeFormBtn = document.getElementById('analyze-form-btn');
        this.generateMappingBtn = document.getElementById('generate-mapping-btn');
        this.logsContainer = document.querySelector('.logs-container');

        this.websocket = null;
        this.isAutomationRunning = false;
        this.currentPage = 'dashboard';

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadProfiles();
        this.loadUrlGroups();
        this.loadAIModels();
        this.connectWebSocket();
        this.setupThemeToggle();
        this.setupMobileMenu();
        // Simple navigation - no SPA complexity
    }

    setupEventListeners() {
        this.urlScopeRadios.forEach(radio => {
            radio.addEventListener('change', this.handleUrlScopeChange.bind(this));
        });

        this.startButton?.addEventListener('click', this.startAutomation.bind(this));
        this.stopButton?.addEventListener('click', this.stopAutomation.bind(this));
        this.analyzeFormBtn?.addEventListener('click', this.analyzeForm.bind(this));
        this.generateMappingBtn?.addEventListener('click', this.generateMapping.bind(this));

        document.addEventListener('DOMContentLoaded', () => {
            this.handleUrlScopeChange();
            this.loadLLMModelPreference();
        });
    }

    handleUrlScopeChange() {
        const amountContainer = document.getElementById('url-amount-input-container');
        const groupContainer = document.getElementById('url-group-select-container');
        const amountRadio = document.getElementById('url-scope-amount');
        const groupRadio = document.getElementById('url-scope-group');

        if (amountContainer) {
            amountContainer.classList.toggle('hidden', !amountRadio?.checked);
        }
        if (groupContainer) {
            groupContainer.classList.toggle('hidden', !groupRadio?.checked);
        }
    }

    async loadProfiles() {
        if (!this.profileSelect) return;

        try {
            this.profileSelect.innerHTML = '<option value="">Loading profiles...</option>';

            const response = await fetch('/api/profiles');
            if (response.ok) {
                const profiles = await response.json();
                if (profiles && profiles.length > 0) {
                    this.populateProfiles(profiles);
                } else {
                    this.profileSelect.innerHTML = '<option value="">No profiles available</option>';
                }
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Failed to load profiles:', error);
            this.profileSelect.innerHTML = '<option value="">Error loading profiles</option>';
            this.addLog('warning', `Failed to load profiles: ${error.message}`);
        }
    }

    populateProfiles(profiles) {
        if (!this.profileSelect) return;

        this.profileSelect.innerHTML = '';
        profiles.forEach(profile => {
            const option = document.createElement('option');
            option.value = profile.id;
            option.textContent = profile.name;
            this.profileSelect.appendChild(option);
        });
    }

    async loadUrlGroups() {
        if (!this.urlGroupSelect) return;

        try {
            this.urlGroupSelect.innerHTML = '<option value="">Loading groups...</option>';

            const response = await fetch('/api/url-groups');
            if (response.ok) {
                const groups = await response.json();
                if (groups && groups.length > 0) {
                    this.populateUrlGroups(groups);
                } else {
                    this.urlGroupSelect.innerHTML = '<option value="">No groups available</option>';
                }
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Failed to load URL groups:', error);
            this.urlGroupSelect.innerHTML = '<option value="">Error loading groups</option>';
            this.addLog('warning', `Failed to load URL groups: ${error.message}`);
        }
    }

    async loadAIModels() {
        if (!this.llmModelSelect) return;

        try {
            // Load from Models.json via static file serving
            const response = await fetch('/static/Models.json');
            if (response.ok) {
                const modelsData = await response.json();
                if (modelsData && modelsData.models && modelsData.models.length > 0) {
                    this.populateAIModels(modelsData.models, modelsData.default_dropdown_model);
                } else {
                    console.warn('No models found in Models.json');
                }
            } else {
                console.warn('Could not load Models.json, using hardcoded models');
            }
        } catch (error) {
            console.error('Failed to load AI models:', error);
            // Keep the hardcoded options as fallback
        }
    }

    populateAIModels(models, defaultModel) {
        if (!this.llmModelSelect) return;

        // Clear existing options
        this.llmModelSelect.innerHTML = '';

        // Add models from the configuration
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = `${model.name} - ${model.description}`;
            this.llmModelSelect.appendChild(option);
        });

        // Set default model
        if (defaultModel) {
            this.llmModelSelect.value = defaultModel;
        }

        // Load saved preference from localStorage (overrides default)
        const savedModel = localStorage.getItem('formai-llm-model');
        if (savedModel) {
            this.llmModelSelect.value = savedModel;
        }
    }

    populateUrlGroups(groups) {
        if (!this.urlGroupSelect) return;

        this.urlGroupSelect.innerHTML = '';
        groups.forEach(group => {
            const option = document.createElement('option');
            option.value = group.id;
            option.textContent = group.name;
            this.urlGroupSelect.appendChild(option);
        });
    }

    async startAutomation() {
        if (this.isAutomationRunning) return;

        const config = this.getAutomationConfig();
        console.log('Sending automation config:', config);

        try {
            this.updateButtonStates(true);

            const response = await fetch('/api/automation/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                this.isAutomationRunning = true;
                this.addLog('info', 'Automation started successfully');
            } else {
                const error = await response.json();
                this.addLog('error', `Failed to start automation: ${error.message}`);
                this.updateButtonStates(false);
            }
        } catch (error) {
            console.error('Failed to start automation:', error);
            this.addLog('error', `Error starting automation: ${error.message}`);
            this.updateButtonStates(false);
        }
    }

    async stopAutomation() {
        if (!this.isAutomationRunning) return;

        try {
            const response = await fetch('/api/automation/stop', {
                method: 'POST'
            });

            if (response.ok) {
                this.isAutomationRunning = false;
                this.updateButtonStates(false);
                this.addLog('info', 'Automation stopped');
            } else {
                const error = await response.json();
                this.addLog('error', `Failed to stop automation: ${error.message}`);
            }
        } catch (error) {
            console.error('Failed to stop automation:', error);
            this.addLog('error', `Error stopping automation: ${error.message}`);
        }
    }

    getAutomationConfig() {
        const targetUrl = document.getElementById('target-url')?.value;

        // Get URL - use target URL input or default to RoboForm test page
        let url = targetUrl && targetUrl.trim() !== ''
            ? targetUrl.trim()
            : 'https://www.roboform.com/filling-test-all-fields';

        // Map mode to use_stealth (headless uses stealth, visible doesn't for debugging)
        const mode = this.modeSelect?.value || 'Visible (Debug)';
        const use_stealth = mode === 'Headless (Fast)';

        console.log('Sending config - URL:', url, 'Stealth:', use_stealth);

        return {
            profile_id: this.profileSelect?.value,
            url: url,
            use_stealth: use_stealth
        };
    }

    updateButtonStates(running) {
        if (this.startButton) {
            this.startButton.disabled = running;
            this.startButton.classList.toggle('opacity-50', running);
        }

        if (this.stopButton) {
            this.stopButton.disabled = !running;
            this.stopButton.classList.toggle('opacity-50', !running);
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
        };

        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        this.websocket.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'log':
                this.addLog(data.level, data.message, data.timestamp);
                break;
            case 'automation_status':
                this.isAutomationRunning = data.running;
                this.updateButtonStates(data.running);
                break;
            case 'profile_updated':
                this.loadProfiles();
                break;
            case 'url_groups_updated':
                this.loadUrlGroups();
                break;
        }
    }

    addLog(level, message, timestamp = null) {
        if (!this.logsContainer) return;

        const time = timestamp || new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = 'flex items-start text-xs font-mono mb-1';

        const icon = this.getLogIcon(level);
        const colorClass = this.getLogColorClass(level);

        logEntry.innerHTML = `
            <span class="text-gray-400 dark:text-gray-500 mr-2">[${time}]</span>
            <span class="mr-2">${icon}</span>
            <span class="${colorClass}">${this.escapeHtml(message)}</span>
        `;

        this.logsContainer.appendChild(logEntry);
        this.logsContainer.scrollTop = this.logsContainer.scrollHeight;

        if (this.logsContainer.children.length > 1000) {
            this.logsContainer.removeChild(this.logsContainer.firstChild);
        }
    }

    getLogIcon(level) {
        switch (level) {
            case 'success':
                return '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-blue-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" /></svg>';
            case 'error':
            case 'fail':
                return '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-red-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>';
            case 'warning':
                return '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-yellow-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.21 3.03-1.742 3.03H4.42c-1.532 0-2.492-1.696-1.742-3.03l5.58-9.92zM10 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" /></svg>';
            default:
                return '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-blue-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" /></svg>';
        }
    }

    getLogColorClass(level) {
        switch (level) {
            case 'success':
                return 'text-blue-800 dark:text-blue-300';
            case 'error':
            case 'fail':
                return 'text-red-800 dark:text-red-300';
            case 'warning':
                return 'text-yellow-800 dark:text-yellow-300';
            default:
                return 'text-gray-800 dark:text-gray-300';
        }
    }

    updateConnectionStatus(connected) {
        const statusElements = document.querySelectorAll('.connection-status');
        statusElements.forEach(element => {
            const indicator = element.querySelector('.status-indicator');
            const text = element.querySelector('.status-text');

            if (indicator) {
                indicator.className = connected
                    ? 'relative flex h-2 w-2 status-indicator'
                    : 'relative flex h-2 w-2 status-indicator';

                indicator.innerHTML = connected
                    ? '<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>'
                    : '<span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>';
            }

            if (text) {
                text.textContent = connected ? 'Connected' : 'Disconnected';
            }

            element.className = connected
                ? 'flex items-center gap-2 bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-400 px-3 py-1.5 rounded-full connection-status'
                : 'flex items-center gap-2 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-400 px-3 py-1.5 rounded-full connection-status';
        });
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        const html = document.documentElement;

        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            html.classList.toggle('dark', savedTheme === 'dark');
            this.updateThemeToggleIcon(savedTheme === 'dark');
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            html.classList.add('dark');
            this.updateThemeToggleIcon(true);
        }

        themeToggle?.addEventListener('click', () => {
            const isDark = html.classList.toggle('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            this.updateThemeToggleIcon(isDark);
        });
    }

    updateThemeToggleIcon(isDark) {
        const themeToggle = document.getElementById('theme-toggle');
        if (!themeToggle) return;

        const sunIcon = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>';
        const moonIcon = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>';

        themeToggle.innerHTML = isDark ? sunIcon : moonIcon;
    }

    setupMobileMenu() {
        const mobileMenuBtn = document.getElementById('mobile-menu-btn');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');

        mobileMenuBtn?.addEventListener('click', () => {
            sidebar?.classList.toggle('-translate-x-full');
            overlay?.classList.toggle('hidden');
        });

        overlay?.addEventListener('click', () => {
            sidebar?.classList.add('-translate-x-full');
            overlay?.classList.add('hidden');
        });

        // Fix sidebar visibility on window resize
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                if (window.innerWidth >= 768) {
                    // Desktop view - ensure sidebar is visible
                    sidebar?.classList.remove('-translate-x-full');
                    overlay?.classList.add('hidden');
                } else {
                    // Mobile view - hide sidebar by default
                    sidebar?.classList.add('-translate-x-full');
                    overlay?.classList.add('hidden');
                }
            }, 100);
        });

        // Initial check on page load
        if (window.innerWidth >= 768) {
            sidebar?.classList.remove('-translate-x-full');
            overlay?.classList.add('hidden');
        } else {
            sidebar?.classList.add('-translate-x-full');
            overlay?.classList.add('hidden');
        }
    }




    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // LLM Model preference management
    loadLLMModelPreference() {
        if (!this.llmModelSelect) return;

        const savedModel = localStorage.getItem('formai-llm-model');
        if (savedModel) {
            this.llmModelSelect.value = savedModel;
        }

        this.llmModelSelect?.addEventListener('change', () => {
            localStorage.setItem('formai-llm-model', this.llmModelSelect.value);
        });
    }

    // AI functionality
    async analyzeForm() {
        if (!this.analyzeFormBtn) return;

        this.analyzeFormBtn.disabled = true;
        this.analyzeFormBtn.innerHTML = 'Analyzing...';

        try {
            const model = this.llmModelSelect?.value || 'anthropic/claude-3.5-sonnet';

            // For demo, we'll analyze a sample form
            const sampleFormHtml = '<form><input name="email" type="email"><input name="password" type="password"><button type="submit">Login</button></form>';
            const sampleUrl = 'https://example.com/login';

            const response = await fetch('/api/ai/analyze-form', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    form_html: sampleFormHtml,
                    url: sampleUrl,
                    model: model
                })
            });

            const result = await response.json();

            if (result.success) {
                this.addLog('success', `AI Form Analysis: ${result.result.substring(0, 100)}...`);
                this.showAIResult('Form Analysis Result', result.result);
            } else {
                this.addLog('error', `AI Analysis failed: ${result.error}`);
            }
        } catch (error) {
            console.error('Failed to analyze form:', error);
            this.addLog('error', `Error analyzing form: ${error.message}`);
        } finally {
            this.analyzeFormBtn.disabled = false;
            this.analyzeFormBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><path d="M9 11H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2h-4"/><polyline points="9,11 12,14 15,11"/><line x1="12" y1="14" x2="12" y2="3"/></svg>AI Analyze Forms';
        }
    }

    async generateMapping() {
        if (!this.generateMappingBtn) return;

        this.generateMappingBtn.disabled = true;
        this.generateMappingBtn.innerHTML = 'Generating...';

        try {
            const model = this.llmModelSelect?.value || 'anthropic/claude-3.5-sonnet';

            // For demo, we'll generate mapping for a sample form
            const sampleFormHtml = '<form><input name="firstName" placeholder="First Name"><input name="lastName" placeholder="Last Name"><input name="email" type="email"><select name="country"><option>USA</option><option>Canada</option></select></form>';

            const response = await fetch('/api/ai/generate-mapping', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    form_html: sampleFormHtml,
                    model: model
                })
            });

            const result = await response.json();

            if (result.success) {
                this.addLog('success', `AI Mapping Generated: ${result.result.substring(0, 100)}...`);
                this.showAIResult('Field Mapping Result', result.result);
            } else {
                this.addLog('error', `AI Mapping failed: ${result.error}`);
            }
        } catch (error) {
            console.error('Failed to generate mapping:', error);
            this.addLog('error', `Error generating mapping: ${error.message}`);
        } finally {
            this.generateMappingBtn.disabled = false;
            this.generateMappingBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/></svg>Generate Mappings';
        }
    }

    showAIResult(title, content) {
        // Create a simple modal-like display for AI results
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 1000; display: flex;
            align-items: center; justify-content: center;
        `;

        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: white; padding: 2rem; border-radius: 8px;
            max-width: 80%; max-height: 80%; overflow: auto;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        `;

        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="margin: 0; color: #333;">${title}</h3>
                <button style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">&times;</button>
            </div>
            <pre style="background: #f5f5f5; padding: 1rem; border-radius: 4px; overflow: auto; white-space: pre-wrap;">${this.escapeHtml(content)}</pre>
        `;

        modal.appendChild(modalContent);
        document.body.appendChild(modal);

        // Close modal when clicking the X or outside
        const closeBtn = modalContent.querySelector('button');
        closeBtn.addEventListener('click', () => document.body.removeChild(modal));
        modal.addEventListener('click', (e) => {
            if (e.target === modal) document.body.removeChild(modal);
        });
    }

    // No complex SPA routing - just simple HTML navigation

    async loadPage(href) {
        const mainContent = document.getElementById('main-content');

        try {
            const response = await fetch(href);
            if (response.ok) {
                const html = await response.text();
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                const newMainContent = tempDiv.querySelector('#main-content');

                if (newMainContent && mainContent) {
                    mainContent.innerHTML = newMainContent.innerHTML;
                    this.initializePageContent(href);
                }
            }
        } catch (error) {
            console.error('Failed to load page:', error);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new DashboardApp();
});