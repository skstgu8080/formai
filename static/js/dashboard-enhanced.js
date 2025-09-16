/**
 * Enhanced Dashboard for FormAI with shadcn/ui styling
 * @license Apache-2.0
 */

class EnhancedDashboardApp extends DashboardApp {
    constructor() {
        super();
        this.stats = {
            totalAutomations: 0,
            formsFilled: 0,
            successRate: 98.7,
            avgSpeed: 3.2,
            activeProfiles: 0
        };
        this.initEnhancedFeatures();
        this.initThemeToggle();
        this.initSidebarToggle();
        this.initContentFocusCollapse();
        this.initSmartCollapse();
    }

    initEnhancedFeatures() {
        this.updateStatistics();
        this.loadProfiles().then(() => this.updateActiveProfiles());
        this.startRealTimeUpdates();
    }

    initThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const html = document.documentElement;
                const isDark = html.classList.contains('dark');
                
                if (isDark) {
                    html.classList.remove('dark');
                    localStorage.setItem('theme', 'light');
                } else {
                    html.classList.add('dark');
                    localStorage.setItem('theme', 'dark');
                }
            });

            // Load saved theme
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                document.documentElement.classList.add('dark');
            }
        }
    }

    initSidebarToggle() {
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');
        const collapseIcon = document.getElementById('collapse-icon');
        const expandIcon = document.getElementById('expand-icon');
        const mainContent = document.querySelector('main');
        
        if (sidebarToggle && sidebar && collapseIcon && expandIcon) {
            // Enhanced toggle functionality
            const toggleSidebar = (forceState = null) => {
                const currentState = sidebar.classList.contains('sidebar-collapsed');
                const newState = forceState !== null ? forceState : !currentState;
                
                // Update sidebar state
                if (newState) {
                    sidebar.classList.add('sidebar-collapsed');
                    collapseIcon.classList.add('hidden');
                    expandIcon.classList.remove('hidden');
                } else {
                    sidebar.classList.remove('sidebar-collapsed');
                    collapseIcon.classList.remove('hidden');
                    expandIcon.classList.add('hidden');
                }
                
                // Update main content layout
                if (mainContent) {
                    if (newState) {
                        mainContent.classList.add('main-content-collapsed');
                    } else {
                        mainContent.classList.remove('main-content-collapsed');
                    }
                }
                
                // Update body class for mobile overlay
                if (newState) {
                    document.body.classList.remove('sidebar-open');
                } else {
                    document.body.classList.add('sidebar-open');
                }
                
                // Save state with timestamp
                const stateData = {
                    collapsed: newState,
                    timestamp: Date.now()
                };
                localStorage.setItem('sidebar-state', JSON.stringify(stateData));
                
                // Update status indicators
                this.updateStatusIndicators(newState);
                
                // Dispatch custom event for other components
                window.dispatchEvent(new CustomEvent('sidebarToggle', {
                    detail: { collapsed: newState }
                }));
                
                return newState;
            };

            // Click handler
            sidebarToggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleSidebar();
            });

            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                // Ctrl/Cmd + B to toggle sidebar
                if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                    e.preventDefault();
                    toggleSidebar();
                }
                // Escape to collapse if expanded
                if (e.key === 'Escape' && !sidebar.classList.contains('sidebar-collapsed')) {
                    toggleSidebar(true);
                }
            });

            // Auto-collapse on mobile/resize
            const handleResize = () => {
                const isMobile = window.innerWidth < 768;
                const savedState = localStorage.getItem('sidebar-state');
                
                if (isMobile) {
                    // Auto-collapse on mobile
                    if (!sidebar.classList.contains('sidebar-collapsed')) {
                        toggleSidebar(true);
                    }
                } else if (savedState) {
                    // Restore desktop state
                    const stateData = JSON.parse(savedState);
                    const isRecent = (Date.now() - stateData.timestamp) < 24 * 60 * 60 * 1000; // 24 hours
                    
                    if (isRecent) {
                        toggleSidebar(stateData.collapsed);
                    }
                }
            };

            // Initial load
            const savedState = localStorage.getItem('sidebar-state');
            if (savedState) {
                try {
                    const stateData = JSON.parse(savedState);
                    const isRecent = (Date.now() - stateData.timestamp) < 24 * 60 * 60 * 1000;
                    
                    if (isRecent) {
                        toggleSidebar(stateData.collapsed);
                    } else {
                        // Default to collapsed on mobile, expanded on desktop
                        const isMobile = window.innerWidth < 768;
                        toggleSidebar(isMobile);
                    }
                } catch (e) {
                    console.warn('Failed to parse saved sidebar state:', e);
                    const isMobile = window.innerWidth < 768;
                    toggleSidebar(isMobile);
                }
            } else {
                // First time - default based on screen size
                const isMobile = window.innerWidth < 768;
                toggleSidebar(isMobile);
            }

            // Listen for resize events
            window.addEventListener('resize', handleResize);
            
            // Click outside to close on mobile
            document.addEventListener('click', (e) => {
                const isMobile = window.innerWidth < 768;
                if (isMobile && !sidebar.classList.contains('sidebar-collapsed')) {
                    const isClickInsideSidebar = sidebar.contains(e.target);
                    const isClickOnToggle = sidebarToggle.contains(e.target);
                    
                    if (!isClickInsideSidebar && !isClickOnToggle) {
                        toggleSidebar(true);
                    }
                }
            });
            
            // Auto-collapse after inactivity (optional)
            let inactivityTimer;
            const resetInactivityTimer = () => {
                clearTimeout(inactivityTimer);
                inactivityTimer = setTimeout(() => {
                    if (!sidebar.classList.contains('sidebar-collapsed') && window.innerWidth < 1024) {
                        toggleSidebar(true);
                    }
                }, 30000); // 30 seconds of inactivity
            };

            // Track user activity
            ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
                document.addEventListener(event, resetInactivityTimer, true);
            });

            // Initialize inactivity timer
            resetInactivityTimer();
            
            // Show keyboard hint on first visit
            this.showKeyboardHint();
        }
    }

    updateStatusIndicators(isCollapsed) {
        const statusIndicator = document.getElementById('sidebar-status');
        const keyboardHint = document.getElementById('keyboard-hint');
        
        if (statusIndicator) {
            if (isCollapsed) {
                statusIndicator.classList.remove('hidden');
                statusIndicator.querySelector('span').textContent = 'Auto-collapse enabled';
            } else {
                statusIndicator.classList.add('hidden');
            }
        }
        
        if (keyboardHint) {
            keyboardHint.classList.remove('hidden');
        }
    }

    showKeyboardHint() {
        const keyboardHint = document.getElementById('keyboard-hint');
        const hasSeenHint = localStorage.getItem('sidebar-keyboard-hint-seen');
        
        if (keyboardHint && !hasSeenHint) {
            keyboardHint.classList.remove('hidden');
            
            // Hide hint after 5 seconds
            setTimeout(() => {
                if (keyboardHint) {
                    keyboardHint.classList.add('hidden');
                    localStorage.setItem('sidebar-keyboard-hint-seen', 'true');
                }
            }, 5000);
        }
    }

    // Auto-collapse based on content focus
    initContentFocusCollapse() {
        const mainContent = document.getElementById('main-content');
        const sidebar = document.getElementById('sidebar');
        
        if (mainContent && sidebar) {
            let focusTimer;
            
            const handleFocus = () => {
                clearTimeout(focusTimer);
                // Auto-collapse sidebar when user focuses on main content
                if (!sidebar.classList.contains('sidebar-collapsed') && window.innerWidth < 1024) {
                    focusTimer = setTimeout(() => {
                        if (document.activeElement && mainContent.contains(document.activeElement)) {
                            const sidebar = document.getElementById('sidebar');
                            if (sidebar) {
                                sidebar.classList.add('sidebar-collapsed');
                                const collapseIcon = document.getElementById('collapse-icon');
                                const expandIcon = document.getElementById('expand-icon');
                                if (collapseIcon && expandIcon) {
                                    collapseIcon.classList.add('hidden');
                                    expandIcon.classList.remove('hidden');
                                }
                            }
                        }
                    }, 2000); // 2 second delay
                }
            };
            
            // Listen for focus events on main content
            mainContent.addEventListener('focusin', handleFocus);
            mainContent.addEventListener('click', handleFocus);
        }
    }

    // Smart collapse based on user behavior
    initSmartCollapse() {
        let lastInteraction = Date.now();
        let interactionCount = 0;
        
        const trackInteraction = () => {
            const now = Date.now();
            const timeSinceLastInteraction = now - lastInteraction;
            
            // If user is actively interacting, don't auto-collapse
            if (timeSinceLastInteraction < 5000) { // 5 seconds
                interactionCount++;
            } else {
                interactionCount = 1;
            }
            
            lastInteraction = now;
            
            // Auto-collapse if user seems to be focused on main content
            if (interactionCount > 3 && window.innerWidth < 1024) {
                const sidebar = document.getElementById('sidebar');
                if (sidebar && !sidebar.classList.contains('sidebar-collapsed')) {
                    sidebar.classList.add('sidebar-collapsed');
                    const collapseIcon = document.getElementById('collapse-icon');
                    const expandIcon = document.getElementById('expand-icon');
                    if (collapseIcon && expandIcon) {
                        collapseIcon.classList.add('hidden');
                        expandIcon.classList.remove('hidden');
                    }
                }
            }
        };
        
        // Track various user interactions
        ['click', 'keydown', 'scroll', 'mousemove'].forEach(event => {
            document.addEventListener(event, trackInteraction, { passive: true });
        });
    }

    updateStatistics() {
        // Update statistics cards with shadcn/ui styling
        const elements = {
            'total-automations': this.stats.totalAutomations,
            'forms-filled': this.stats.formsFilled,
            'success-rate': `${this.stats.successRate}%`,
            'avg-speed': `${this.stats.avgSpeed}s`,
            'active-profiles': this.stats.activeProfiles
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
                // Add fade-in animation
                element.classList.add('fade-in');
                setTimeout(() => element.classList.remove('fade-in'), 300);
            }
        });
    }

    updateActiveProfiles() {
        // Count profiles and update stat
        if (this.profileSelect && this.profileSelect.options.length > 1) {
            this.stats.activeProfiles = this.profileSelect.options.length - 1; // Exclude "Loading..." option
            const activeProfilesElement = document.getElementById('active-profiles');
            if (activeProfilesElement) {
                activeProfilesElement.textContent = this.stats.activeProfiles;
            }
        }
    }

    startRealTimeUpdates() {
        // Update timestamps and other real-time elements
        setInterval(() => {
            const timeElements = document.querySelectorAll('.logs-container .text-gray-400');
            if (timeElements.length === 0) {
                // Add a real-time log entry
                this.addLog('info', 'System monitoring active');
            }
        }, 30000); // Every 30 seconds
    }

    // Override the original addLog to work with shadcn/ui styling
    addLog(level, message, timestamp = null) {
        const logsContainer = document.querySelector('.logs-container');
        if (!logsContainer) return;

        const time = timestamp || new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry fade-in';

        const icon = this.getLogIcon(level);
        const colorClass = this.getLogColorClass(level);

        logEntry.innerHTML = `
            <span class="log-time">[${time}]</span>
            <span class="log-icon">${icon}</span>
            <span class="log-message ${colorClass}">${this.escapeHtml(message)}</span>
        `;

        logsContainer.appendChild(logEntry);
        logsContainer.scrollTop = logsContainer.scrollHeight;

        // Limit to 100 log entries
        if (logsContainer.children.length > 100) {
            logsContainer.removeChild(logsContainer.firstChild);
        }
    }

    // Helper methods for log styling
    getLogIcon(level) {
        const icons = {
            info: '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-primary" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" /></svg>',
            success: '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-green-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" /></svg>',
            warning: '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-yellow-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" /></svg>',
            error: '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-red-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg>'
        };
        return icons[level] || icons.info;
    }

    getLogColorClass(level) {
        const classes = {
            info: 'log-info',
            success: 'log-success',
            warning: 'log-warning',
            error: 'log-error'
        };
        return classes[level] || 'log-info';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Override automation start to update statistics
    async startAutomation() {
        const result = await super.startAutomation();
        if (result !== false) {
            this.stats.totalAutomations++;
            this.updateStatistics();
        }
        return result;
    }

    // Handle WebSocket messages for enhanced features
    handleWebSocketMessage(data) {
        super.handleWebSocketMessage(data);
        
        switch (data.type) {
            case 'automation_complete':
                this.stats.formsFilled += data.forms_filled || 1;
                this.stats.successRate = data.success_rate || this.stats.successRate;
                this.stats.avgSpeed = data.avg_speed || this.stats.avgSpeed;
                this.updateStatistics();
                break;
            case 'profile_count_updated':
                this.stats.activeProfiles = data.count;
                this.updateStatistics();
                break;
        }
    }
}

// Initialize enhanced dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new EnhancedDashboardApp();
});
