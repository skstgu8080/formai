/**
 * System Status Manager
 * Handles real-time status updates for browser, WebSocket, AI model, and memory
 */
class SystemStatusManager {
    constructor() {
        this.statusElements = {
            browser: null,
            websocket: null,
            aiModel: null,
            memory: null
        };
        this.apiKeyStatus = false;
        this.websocket = null;
        this.init();
    }

    init() {
        // Get status elements
        this.statusElements.browser = document.getElementById('browser-status');
        this.statusElements.websocket = document.getElementById('websocket-status');
        this.statusElements.aiModel = document.getElementById('ai-model-status');
        this.statusElements.memory = document.getElementById('memory-status');

        // Check API key status
        this.checkApiKeyStatus();

        // Start monitoring
        this.startMonitoring();

        // Try to connect WebSocket
        this.connectWebSocket();
    }

    async checkApiKeyStatus() {
        try {
            const response = await fetch('/api/settings');
            if (response.ok) {
                const settings = await response.json();
                const apiKeys = settings.apiKeys || {};

                // Check if any API key is configured
                this.apiKeyStatus = !!(
                    apiKeys.openai ||
                    apiKeys.anthropic ||
                    apiKeys.google ||
                    apiKeys.openrouter
                );

                this.updateAIModelStatus();
            }
        } catch (error) {
            console.error('Failed to check API key status:', error);
            this.apiKeyStatus = false;
            this.updateAIModelStatus();
        }
    }

    connectWebSocket() {
        try {
            // Attempt to connect to WebSocket
            this.websocket = new WebSocket('ws://localhost:5511/ws');

            this.websocket.onopen = () => {
                this.updateWebSocketStatus(true);
            };

            this.websocket.onclose = () => {
                this.updateWebSocketStatus(false);
                // Retry connection after 5 seconds
                setTimeout(() => this.connectWebSocket(), 5000);
            };

            this.websocket.onerror = () => {
                this.updateWebSocketStatus(false);
            };

            this.websocket.onmessage = (event) => {
                // Handle incoming messages if needed
                console.log('WebSocket message:', event.data);
            };
        } catch (error) {
            this.updateWebSocketStatus(false);
            // Retry connection after 5 seconds
            setTimeout(() => this.connectWebSocket(), 5000);
        }
    }

    updateBrowserStatus(isActive) {
        if (this.statusElements.browser) {
            if (isActive) {
                this.statusElements.browser.textContent = 'Active';
                this.statusElements.browser.className = 'text-sm font-medium text-green-600';
            } else {
                this.statusElements.browser.textContent = 'Inactive';
                this.statusElements.browser.className = 'text-sm font-medium text-red-600';
            }
        }
    }

    updateWebSocketStatus(isConnected) {
        if (this.statusElements.websocket) {
            if (isConnected) {
                this.statusElements.websocket.textContent = 'Connected';
                this.statusElements.websocket.className = 'text-sm font-medium text-green-600';
            } else {
                this.statusElements.websocket.textContent = 'Disconnected';
                this.statusElements.websocket.className = 'text-sm font-medium text-red-600';
            }
        }
    }

    updateAIModelStatus() {
        if (this.statusElements.aiModel) {
            if (this.apiKeyStatus) {
                this.statusElements.aiModel.textContent = 'Ready';
                this.statusElements.aiModel.className = 'text-sm font-medium text-green-600';
            } else {
                this.statusElements.aiModel.textContent = 'No API Key';
                this.statusElements.aiModel.className = 'text-sm font-medium text-yellow-600';
            }
        }
    }

    updateMemoryUsage() {
        if (this.statusElements.memory) {
            // Get memory usage (this is approximate since we can't get real process memory from browser)
            if (performance.memory) {
                const usedMemory = Math.round(performance.memory.usedJSHeapSize / 1048576); // Convert to MB
                const limitMemory = Math.round(performance.memory.jsHeapSizeLimit / 1048576);
                const percentage = (usedMemory / limitMemory) * 100;

                this.statusElements.memory.textContent = `${usedMemory}MB`;

                if (percentage < 50) {
                    this.statusElements.memory.className = 'text-sm font-medium text-green-600';
                } else if (percentage < 80) {
                    this.statusElements.memory.className = 'text-sm font-medium text-yellow-600';
                } else {
                    this.statusElements.memory.className = 'text-sm font-medium text-red-600';
                }
            } else {
                // Fallback for browsers that don't support performance.memory
                this.statusElements.memory.textContent = 'N/A';
                this.statusElements.memory.className = 'text-sm font-medium text-muted-foreground';
            }
        }
    }

    checkBrowserEngine() {
        // Check if browser automation is available
        const isBrowserAvailable = typeof window !== 'undefined' && navigator.userAgent;

        // Check for Playwright or Puppeteer indicators
        const isAutomationBrowser =
            window.navigator.webdriver === true ||
            window.__playwright !== undefined ||
            window.puppeteer !== undefined ||
            navigator.userAgent.includes('HeadlessChrome');

        this.updateBrowserStatus(isBrowserAvailable);
    }

    startMonitoring() {
        // Initial checks
        this.checkBrowserEngine();
        this.updateMemoryUsage();

        // Update memory usage every 5 seconds
        setInterval(() => {
            this.updateMemoryUsage();
        }, 5000);

        // Check API key status every 30 seconds
        setInterval(() => {
            this.checkApiKeyStatus();
        }, 30000);

        // Check browser status every 10 seconds
        setInterval(() => {
            this.checkBrowserEngine();
        }, 10000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.systemStatus = new SystemStatusManager();
});