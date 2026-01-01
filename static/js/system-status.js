/**
 * System Status Manager
 * Handles real-time status updates for browser, WebSocket, memory, and server metrics
 */
class SystemStatusManager {
    constructor() {
        this.statusElements = {
            browser: null,
            websocket: null,
            memory: null,
            version: null,
            cpuPercent: null,
            memoryPercent: null,
            activeAgents: null,
            maxAgents: null
        };
        this.websocket = null;
        this.metricsWebSocket = null;
        this.init();
    }

    init() {
        // Get status elements (with retry for dynamically rendered sidebar)
        this.initElements();

        // Start monitoring
        this.startMonitoring();

        // Try to connect WebSocket
        this.connectWebSocket();

        // Connect to metrics WebSocket for real-time server metrics
        this.connectMetricsWebSocket();
    }

    initElements() {
        this.statusElements.browser = document.getElementById('browser-status');
        this.statusElements.websocket = document.getElementById('websocket-status');
        this.statusElements.memory = document.getElementById('memory-status');
        this.statusElements.version = document.getElementById('version-status');
        this.statusElements.cpuPercent = document.getElementById('cpu-percent');
        this.statusElements.memoryPercent = document.getElementById('memory-percent');
        this.statusElements.activeAgents = document.getElementById('active-agents');
        this.statusElements.maxAgents = document.getElementById('max-agents');
        this.statusElements.cpuProgress = document.getElementById('cpu-progress');
        this.statusElements.memoryProgress = document.getElementById('memory-progress');

        // If version element not found, retry after sidebar renders
        if (!this.statusElements.version) {
            setTimeout(() => {
                this.statusElements.version = document.getElementById('version-status');
                this.fetchVersion();
            }, 100);
        } else {
            this.fetchVersion();
        }

        // Fetch initial metrics
        this.fetchServerMetrics();
    }

    async fetchVersion() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            if (this.statusElements.version && data.version) {
                this.statusElements.version.textContent = `v${data.version}`;
                this.statusElements.version.className = 'text-sm font-medium text-blue-600';
            }
        } catch (error) {
            if (this.statusElements.version) {
                this.statusElements.version.textContent = '--';
                this.statusElements.version.className = 'text-sm font-medium text-muted-foreground';
            }
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

        // Check browser status every 10 seconds
        setInterval(() => {
            this.checkBrowserEngine();
        }, 10000);

        // Fetch server metrics every 3 seconds as fallback
        setInterval(() => {
            if (!this.metricsWebSocket || this.metricsWebSocket.readyState !== WebSocket.OPEN) {
                this.fetchServerMetrics();
            }
        }, 3000);
    }

    connectMetricsWebSocket() {
        try {
            this.metricsWebSocket = new WebSocket('ws://localhost:5511/ws/metrics');

            this.metricsWebSocket.onopen = () => {
                console.log('Metrics WebSocket connected');
            };

            this.metricsWebSocket.onclose = () => {
                console.log('Metrics WebSocket disconnected');
                // Retry connection after 5 seconds
                setTimeout(() => this.connectMetricsWebSocket(), 5000);
            };

            this.metricsWebSocket.onerror = () => {
                console.log('Metrics WebSocket error');
            };

            this.metricsWebSocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    // Handle nested format from WebSocket: {type: "system_metrics", data: {...}}
                    const metrics = message.data || message;
                    this.updateServerMetricsDisplay(metrics);
                } catch (e) {
                    console.error('Error parsing metrics:', e);
                }
            };
        } catch (error) {
            console.error('Failed to connect metrics WebSocket:', error);
            // Retry connection after 5 seconds
            setTimeout(() => this.connectMetricsWebSocket(), 5000);
        }
    }

    async fetchServerMetrics() {
        try {
            const response = await fetch('/api/system/metrics');
            if (response.ok) {
                const metrics = await response.json();
                this.updateServerMetricsDisplay(metrics);
            }
        } catch (error) {
            console.debug('Failed to fetch server metrics:', error);
        }
    }

    updateServerMetricsDisplay(metrics) {
        // Update CPU percentage
        if (this.statusElements.cpuPercent) {
            this.statusElements.cpuPercent.textContent = `${Math.round(metrics.cpu_percent || 0)}%`;
            this.updateMetricColor(this.statusElements.cpuPercent, metrics.cpu_percent || 0);
        }

        // Update CPU progress bar
        if (this.statusElements.cpuProgress) {
            const cpuPercent = Math.min(100, metrics.cpu_percent || 0);
            this.statusElements.cpuProgress.style.width = `${cpuPercent}%`;
            this.updateProgressColor(this.statusElements.cpuProgress, cpuPercent);
        }

        // Update Memory percentage
        if (this.statusElements.memoryPercent) {
            this.statusElements.memoryPercent.textContent = `${Math.round(metrics.memory_percent || 0)}%`;
            this.updateMetricColor(this.statusElements.memoryPercent, metrics.memory_percent || 0);
        }

        // Update Memory progress bar
        if (this.statusElements.memoryProgress) {
            const memPercent = Math.min(100, metrics.memory_percent || 0);
            this.statusElements.memoryProgress.style.width = `${memPercent}%`;
            this.updateProgressColor(this.statusElements.memoryProgress, memPercent);
        }

        // Update active agents count
        if (this.statusElements.activeAgents) {
            this.statusElements.activeAgents.textContent = metrics.active_agents || 0;
        }

        // Update max agents
        if (this.statusElements.maxAgents) {
            this.statusElements.maxAgents.textContent = metrics.max_parallel || '--';
        }

        // Update scaling indicator if present
        const scalingIndicator = document.getElementById('scaling-indicator');
        if (scalingIndicator && metrics.can_scale !== undefined) {
            if (metrics.can_scale) {
                scalingIndicator.className = 'h-2 w-2 bg-green-500 rounded-full';
                scalingIndicator.title = 'Can scale - resources available';
            } else {
                scalingIndicator.className = 'h-2 w-2 bg-yellow-500 rounded-full';
                scalingIndicator.title = 'At capacity';
            }
        }
    }

    updateMetricColor(element, value) {
        if (value < 50) {
            element.className = 'text-lg font-bold text-green-600';
        } else if (value < 80) {
            element.className = 'text-lg font-bold text-yellow-600';
        } else {
            element.className = 'text-lg font-bold text-red-600';
        }
    }

    updateProgressColor(element, value) {
        // Remove existing color classes
        element.classList.remove('bg-green-500', 'bg-yellow-500', 'bg-red-500');

        if (value < 50) {
            element.classList.add('bg-green-500');
        } else if (value < 80) {
            element.classList.add('bg-yellow-500');
        } else {
            element.classList.add('bg-red-500');
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.systemStatus = new SystemStatusManager();
});