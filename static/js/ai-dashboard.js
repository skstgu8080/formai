/**
 * AI Dashboard - Control panel for FormAI AI Agent
 * Uses Ollama for AI-powered form filling
 */

class AIDashboard {
    constructor() {
        // UI Elements
        this.profileSelect = document.getElementById('profile-select');
        this.siteCountSelect = document.getElementById('site-count-select');
        this.modeSelect = document.getElementById('mode-select');
        this.startButton = document.getElementById('start-ai-agent');
        this.stopButton = document.getElementById('stop-ai-agent');
        this.logsContainer = document.getElementById('logs-container');
        this.progressContainer = document.getElementById('progress-container');
        this.progressBar = document.getElementById('progress-bar');
        this.progressLabel = document.getElementById('progress-label');
        this.progressPercent = document.getElementById('progress-percent');
        this.agentStatusBadge = document.getElementById('agent-status-badge');
        this.activityLog = document.getElementById('activity-log');

        // State
        this.isRunning = false;
        this.websocket = null;
        this.sites = [];
        this.profiles = [];

        // Initialize
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.setupTheme();
        await this.loadProfiles();
        await this.loadSites();
        await this.checkOllamaStatus();
        await this.loadAIMemoryStats();
        this.connectWebSocket();
    }

    setupEventListeners() {
        this.startButton?.addEventListener('click', () => this.startAIAgent());
        this.stopButton?.addEventListener('click', () => this.stopAIAgent());
        document.getElementById('clear-activity')?.addEventListener('click', () => this.clearActivity());
    }

    setupTheme() {
        const themeToggle = document.getElementById('theme-toggle');
        const html = document.documentElement;

        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            html.classList.toggle('dark', savedTheme === 'dark');
        }
        this.updateThemeIcon(html.classList.contains('dark'));

        themeToggle?.addEventListener('click', () => {
            const isDark = html.classList.toggle('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            this.updateThemeIcon(isDark);
        });
    }

    updateThemeIcon(isDark) {
        const toggle = document.getElementById('theme-toggle');
        if (!toggle) return;
        toggle.innerHTML = isDark
            ? '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>'
            : '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>';
    }

    async loadProfiles() {
        try {
            const response = await fetch('/api/profiles');
            if (response.ok) {
                this.profiles = await response.json();
                this.populateProfileSelect();
                this.updateMetric('total-profiles-count', this.profiles.length);
            }
        } catch (error) {
            console.error('Failed to load profiles:', error);
            this.addLog('error', 'Failed to load profiles');
        }
    }

    populateProfileSelect() {
        if (!this.profileSelect) return;
        this.profileSelect.innerHTML = '';

        if (this.profiles.length === 0) {
            this.profileSelect.innerHTML = '<option value="">No profiles - Create one first</option>';
            return;
        }

        this.profiles.forEach(profile => {
            const option = document.createElement('option');
            option.value = profile.id;
            option.textContent = profile.name || profile.firstName || profile.id;
            this.profileSelect.appendChild(option);
        });
    }

    async loadSites() {
        try {
            const response = await fetch('/api/sites');
            if (response.ok) {
                const data = await response.json();
                // Sites are objects with url property - extract URLs
                const siteObjects = data.sites || [];
                this.sites = siteObjects.map(s => s.url).filter(url => url);
                this.updateMetric('total-sites-count', this.sites.length);
                document.getElementById('sites-info').textContent = `${this.sites.length} sites available`;
                document.getElementById('sites-db-info').textContent = `${this.sites.length} URLs loaded`;
            }
        } catch (error) {
            console.error('Failed to load sites:', error);
            document.getElementById('sites-info').textContent = 'Failed to load sites';
        }
    }

    async checkOllamaStatus() {
        const indicator = document.getElementById('ollama-indicator');
        const text = document.getElementById('ollama-text');
        const badge = document.getElementById('ollama-badge');
        const model = document.getElementById('ollama-model');
        const icon = document.getElementById('ollama-status-icon');

        try {
            const response = await fetch('/api/ai-agent/status');
            if (response.ok) {
                const status = await response.json();

                if (status.ollama_available) {
                    indicator?.classList.remove('bg-gray-400', 'bg-red-500');
                    indicator?.classList.add('bg-green-500');
                    text.textContent = 'Ollama Ready';
                    badge.textContent = 'Online';
                    badge.className = 'px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400';
                    model.textContent = status.model || 'llama3.2';
                    icon.className = 'p-2 bg-green-100 dark:bg-green-900/30 rounded-lg';
                    icon.querySelector('svg')?.classList.remove('text-gray-500');
                    icon.querySelector('svg')?.classList.add('text-green-600');
                } else {
                    indicator?.classList.remove('bg-gray-400', 'bg-green-500');
                    indicator?.classList.add('bg-red-500');
                    text.textContent = 'Ollama Offline';
                    badge.textContent = 'Offline';
                    badge.className = 'px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400';
                    model.textContent = 'Not connected';
                    icon.className = 'p-2 bg-red-100 dark:bg-red-900/30 rounded-lg';
                }
            }
        } catch (error) {
            console.error('Failed to check Ollama status:', error);
            indicator?.classList.remove('bg-gray-400', 'bg-green-500');
            indicator?.classList.add('bg-red-500');
            text.textContent = 'Ollama Error';
            badge.textContent = 'Error';
            badge.className = 'px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-600';
        }
    }

    async loadAIMemoryStats() {
        try {
            const response = await fetch('/api/ai-agent/memory/stats');
            if (response.ok) {
                const stats = await response.json();
                this.updateMetric('fields-learned-count', stats.total_field_mappings || 0);

                // Calculate success rate
                if (stats.total_actions > 0) {
                    const rate = ((stats.successful_actions / stats.total_actions) * 100).toFixed(1);
                    this.updateMetric('success-rate-percent', `${rate}%`);
                }
            }
        } catch (error) {
            console.debug('AI memory stats not available:', error);
        }
    }

    async startAIAgent() {
        if (this.isRunning) return;

        const profileId = this.profileSelect?.value;
        if (!profileId) {
            this.addLog('error', 'Please select a profile first');
            return;
        }

        // Check Ollama status first
        try {
            const statusResp = await fetch('/api/ai-agent/status');
            const status = await statusResp.json();
            if (!status.ollama_available) {
                this.addLog('error', 'Ollama is not running. Please start Ollama first.');
                this.addLog('info', 'Install: https://ollama.ai and run: ollama run llama3.2');
                return;
            }
        } catch (e) {
            this.addLog('error', 'Cannot check AI agent status');
            return;
        }

        // Get site count - blank/empty means all sites
        const siteCountValue = this.siteCountSelect?.value?.trim();
        let siteCount = (!siteCountValue || siteCountValue === '') ? this.sites.length : parseInt(siteCountValue);
        if (isNaN(siteCount) || siteCount <= 0) siteCount = this.sites.length;
        siteCount = Math.min(siteCount, this.sites.length);

        if (this.sites.length === 0) {
            this.addLog('error', 'No sites available to fill');
            return;
        }

        // Get selected sites
        const selectedSites = this.sites.slice(0, siteCount);
        const headless = this.modeSelect?.value === 'headless';

        this.isRunning = true;
        this.updateButtonStates(true);
        this.setAgentStatus('Running', 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400');
        this.showProgress(true);

        this.clearLogs();
        this.addLog('info', `Starting AI Agent with ${siteCount} sites...`);
        this.addLog('info', `Profile: ${this.profiles.find(p => p.id === profileId)?.name || profileId}`);
        this.addLog('info', `Mode: ${headless ? 'Headless (Fast)' : 'Visible (Watch AI)'}`);

        try {
            const response = await fetch('/api/ai-agent/fill-batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    urls: selectedSites,
                    profile_id: profileId,
                    headless: headless
                })
            });

            if (response.ok) {
                const result = await response.json();
                this.addLog('success', `AI Agent started! Task ID: ${result.task_id}`);
                this.addActivityLog('AI Agent started', `Processing ${siteCount} sites`, 'info');
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to start AI agent');
            }
        } catch (error) {
            console.error('Failed to start AI agent:', error);
            this.addLog('error', `Failed to start: ${error.message}`);
            this.isRunning = false;
            this.updateButtonStates(false);
            this.setAgentStatus('Error', 'bg-red-100 text-red-600');
            this.showProgress(false);
        }
    }

    async stopAIAgent() {
        if (!this.isRunning) return;

        try {
            const response = await fetch('/api/ai-agent/stop', {
                method: 'POST'
            });

            if (response.ok) {
                this.addLog('info', 'Stopping AI Agent...');
                this.isRunning = false;
                this.updateButtonStates(false);
                this.setAgentStatus('Stopped', 'bg-yellow-100 text-yellow-600');
            }
        } catch (error) {
            console.error('Failed to stop AI agent:', error);
            this.addLog('error', `Failed to stop: ${error.message}`);
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('WebSocket connected');
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
            console.log('WebSocket disconnected, reconnecting...');
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'ai_agent_progress':
                // Handle progress updates from server
                const info = data.data || {};
                const progress = info.progress || {};

                if (info.type === 'site_start') {
                    this.addLog('info', `[${info.current}/${info.total}] Starting: ${this.truncateUrl(info.site)}`);
                    this.updateProgress(info.current, info.total, `Site ${info.current}/${info.total}`);
                } else if (info.type === 'site_complete') {
                    const result = info.result || {};
                    if (result.success) {
                        this.addLog('success', `[${info.current}/${info.total}] Completed: ${result.fields_filled || 0} fields`);
                    } else {
                        this.addLog('warning', `[${info.current}/${info.total}] Failed: ${result.error || 'Unknown'}`);
                    }
                    this.updateProgress(progress.completed || 0, progress.total || 1, `${progress.completed}/${progress.total} sites`);
                } else if (info.type === 'action') {
                    const action = info.action || {};
                    if (action.tool === 'fill') {
                        this.addLog('info', `  Filling: ${action.profile_field || action.selector}`);
                    } else if (action.tool === 'click') {
                        this.addLog('info', `  Clicking: ${action.selector}`);
                    } else if (action.tool === 'submit') {
                        this.addLog('info', `  Submitting form...`);
                    } else if (action.tool === 'done') {
                        this.addLog('success', `  Form completed!`);
                    } else if (action.tool !== 'skip') {
                        this.addLog('info', `  Action: ${action.tool}`);
                    }
                }
                break;

            case 'ai_agent_batch_complete':
                const result = data.data || {};
                this.addLog('success', `AI Agent finished!`);
                this.addLog('info', `Successful: ${result.successful || 0}/${result.total_sites || 0} sites`);
                this.addLog('info', `Fields filled: ${result.total_fields_filled || 0}`);
                this.isRunning = false;
                this.updateButtonStates(false);
                this.setAgentStatus('Complete', 'bg-green-100 text-green-600');
                this.showProgress(false);
                this.addActivityLog('AI Agent finished', `${result.successful}/${result.total_sites} sites successful`,
                    result.successful === result.total_sites ? 'success' : 'warning');
                this.loadAIMemoryStats();
                break;

            case 'ai_agent_error':
                const error = data.data?.error || data.error || 'Unknown error';
                this.addLog('error', `Error: ${error}`);
                this.isRunning = false;
                this.updateButtonStates(false);
                this.setAgentStatus('Error', 'bg-red-100 text-red-600');
                this.showProgress(false);
                break;

            case 'ai_agent_missing_fields':
                // Self-learning: notify user about fields that need profile data
                const missingData = data.data || {};
                const missingCount = missingData.missing_count || 0;
                if (missingCount > 0) {
                    this.addLog('warning', `Missing profile data for ${missingCount} fields:`);
                    const missingFields = missingData.missing_fields || [];
                    missingFields.slice(0, 5).forEach(f => {
                        const label = f.labels?.[0] || f.selector;
                        this.addLog('warning', `  - Add "${f.suggested_key}" to profile (${label})`);
                    });
                    // Show notification to user
                    this.showMissingFieldsNotification(missingFields);
                }
                break;

            case 'ai_agent_missing_field':
                // Single missing field notification
                const fieldInfo = data.data || {};
                this.addLog('warning', `Missing: Add "${fieldInfo.suggested_key}" to profile for ${fieldInfo.selector}`);
                break;

            case 'log':
                this.addLog(data.level || 'info', data.message);
                break;
        }
    }

    showMissingFieldsNotification(missingFields) {
        // Create a notification panel if it doesn't exist
        let panel = document.getElementById('missing-fields-panel');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'missing-fields-panel';
            panel.className = 'fixed bottom-4 right-4 max-w-sm bg-yellow-50 dark:bg-yellow-900/50 border border-yellow-200 dark:border-yellow-700 rounded-lg shadow-lg p-4 z-50';
            document.body.appendChild(panel);
        }

        // Update content
        const fieldsList = missingFields.slice(0, 5).map(f => {
            const label = f.labels?.[0] || f.selector;
            return `<li class="text-sm text-yellow-800 dark:text-yellow-200">Add <strong>${this.escapeHtml(f.suggested_key)}</strong> to profile</li>`;
        }).join('');

        panel.innerHTML = `
            <div class="flex items-start space-x-3">
                <div class="flex-shrink-0">
                    <svg class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                    </svg>
                </div>
                <div class="flex-1">
                    <h3 class="text-sm font-medium text-yellow-800 dark:text-yellow-200">Profile Fields Missing</h3>
                    <p class="text-xs text-yellow-700 dark:text-yellow-300 mt-1">Add these fields to fill all forms:</p>
                    <ul class="mt-2 space-y-1 list-disc list-inside">
                        ${fieldsList}
                    </ul>
                    <div class="mt-3 flex space-x-2">
                        <a href="/profiles" class="text-xs px-2 py-1 bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200 rounded hover:bg-yellow-300">
                            Edit Profile
                        </a>
                        <button onclick="document.getElementById('missing-fields-panel').remove()" class="text-xs px-2 py-1 text-yellow-700 dark:text-yellow-300 hover:underline">
                            Dismiss
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Auto-dismiss after 30 seconds
        setTimeout(() => {
            panel?.remove();
        }, 30000);
    }

    // UI Helper Methods

    addLog(level, message) {
        if (!this.logsContainer) return;

        // Remove placeholder if exists
        const placeholder = this.logsContainer.querySelector('.text-muted-foreground:only-child');
        if (placeholder && !placeholder.classList.contains('log-entry')) {
            placeholder.remove();
        }

        const time = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry flex items-start text-xs font-mono mb-1';

        const icon = this.getLogIcon(level);
        const colorClass = this.getLogColorClass(level);

        logEntry.innerHTML = `
            <span class="text-gray-400 dark:text-gray-500 mr-2 shrink-0">[${time}]</span>
            <span class="mr-2 shrink-0">${icon}</span>
            <span class="${colorClass} break-all">${this.escapeHtml(message)}</span>
        `;

        this.logsContainer.appendChild(logEntry);
        this.logsContainer.scrollTop = this.logsContainer.scrollHeight;

        // Keep only last 500 entries
        while (this.logsContainer.children.length > 500) {
            this.logsContainer.removeChild(this.logsContainer.firstChild);
        }
    }

    clearLogs() {
        if (!this.logsContainer) return;
        this.logsContainer.innerHTML = '';
    }

    getLogIcon(level) {
        switch (level) {
            case 'success':
                return '<svg class="w-3 h-3 text-green-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" /></svg>';
            case 'error':
                return '<svg class="w-3 h-3 text-red-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>';
            case 'warning':
                return '<svg class="w-3 h-3 text-yellow-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.21 3.03-1.742 3.03H4.42c-1.532 0-2.492-1.696-1.742-3.03l5.58-9.92zM10 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" /></svg>';
            default:
                return '<svg class="w-3 h-3 text-blue-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" /></svg>';
        }
    }

    getLogColorClass(level) {
        switch (level) {
            case 'success': return 'text-green-600 dark:text-green-400';
            case 'error': return 'text-red-600 dark:text-red-400';
            case 'warning': return 'text-yellow-600 dark:text-yellow-400';
            default: return 'text-gray-700 dark:text-gray-300';
        }
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

    setAgentStatus(text, classes) {
        if (this.agentStatusBadge) {
            this.agentStatusBadge.textContent = text;
            this.agentStatusBadge.className = `px-3 py-1 text-xs font-medium rounded-full ${classes}`;
        }
    }

    showProgress(show) {
        if (this.progressContainer) {
            this.progressContainer.classList.toggle('hidden', !show);
        }
    }

    updateProgress(current, total, label) {
        const percent = Math.round((current / total) * 100);
        if (this.progressBar) this.progressBar.style.width = `${percent}%`;
        if (this.progressPercent) this.progressPercent.textContent = `${percent}%`;
        if (this.progressLabel) this.progressLabel.textContent = label;
    }

    updateMetric(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    addActivityLog(title, message, level = 'info') {
        if (!this.activityLog) return;

        // Remove placeholder
        const placeholder = this.activityLog.querySelector('.text-center');
        if (placeholder) placeholder.remove();

        const time = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = 'flex items-start space-x-3 p-3 bg-accent/30 rounded-lg border border-gray-200';

        const iconClass = level === 'success' ? 'text-green-600' :
                          level === 'error' ? 'text-red-600' :
                          level === 'warning' ? 'text-yellow-600' : 'text-blue-600';

        entry.innerHTML = `
            <div class="flex-shrink-0 mt-0.5">
                <svg class="w-5 h-5 ${iconClass}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2"/>
                </svg>
            </div>
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-card-foreground">${this.escapeHtml(title)}</p>
                <p class="text-xs text-muted-foreground">${this.escapeHtml(message)}</p>
                <p class="text-xs text-muted-foreground mt-1">${time}</p>
            </div>
        `;

        this.activityLog.insertBefore(entry, this.activityLog.firstChild);

        // Keep only last 20 entries
        while (this.activityLog.children.length > 20) {
            this.activityLog.removeChild(this.activityLog.lastChild);
        }
    }

    clearActivity() {
        if (this.activityLog) {
            this.activityLog.innerHTML = `
                <div class="text-sm text-muted-foreground text-center py-4">
                    No recent AI activity
                </div>
            `;
        }
    }

    // Utility Methods

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    truncate(str, len) {
        if (!str) return '';
        return str.length > len ? str.substring(0, len) + '...' : str;
    }

    truncateUrl(url) {
        if (!url) return '';
        try {
            const parsed = new URL(url);
            return parsed.hostname + (parsed.pathname.length > 20 ? parsed.pathname.substring(0, 20) + '...' : parsed.pathname);
        } catch {
            return this.truncate(url, 40);
        }
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    window.aiDashboard = new AIDashboard();
});
