/**
 * Enhanced Dashboard Manager
 * Simplified version without sidebar collapse functionality
 */
class EnhancedDashboardManager {
    constructor() {
        this.initializeEnhancements();
    }

    initializeEnhancements() {
        this.initThemeToggle();
        this.initSidebarToggle();
        this.initContentFocusCollapse();
    }

    initThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                const html = document.documentElement;
                if (html.classList.contains('dark')) {
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
        // Sidebar collapse functionality removed for cleaner UI
        // Desktop sidebar always visible, mobile uses overlay when needed
        console.log('Sidebar initialized - collapse functionality disabled for cleaner appearance');
    }

    initContentFocusCollapse() {
        // Content focus features disabled along with sidebar collapse
        console.log('Content focus features disabled - using simplified layout');
    }

    updateStatusIndicators(isCollapsed) {
        // Status indicators removed along with collapse functionality
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.enhancedDashboard = new EnhancedDashboardManager();
});