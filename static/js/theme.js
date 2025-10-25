// FormAI Theme Management - Clean Implementation
// Default: Dark mode | Persists in localStorage | No flash on load

class ThemeManager {
    constructor() {
        // Default to dark mode on first visit
        this.theme = localStorage.getItem('theme') || 'dark';

        // Sun icon SVG (for dark mode - click to go light)
        this.sunIcon = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
        `;

        // Moon icon SVG (for light mode - click to go dark)
        this.moonIcon = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
        `;

        this.init();
    }

    init() {
        this.applyTheme();
        this.setupToggleButton();
    }

    applyTheme() {
        // Apply or remove dark class
        if (this.theme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }

        // Update toggle button icon
        this.updateIcon();
    }

    toggleTheme() {
        // Switch between light and dark
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('theme', this.theme);
        this.applyTheme();
    }

    updateIcon() {
        const toggleButton = document.getElementById('theme-toggle');
        if (!toggleButton) return;

        // Show icon for destination mode (sun in dark, moon in light)
        toggleButton.innerHTML = this.theme === 'dark' ? this.sunIcon : this.moonIcon;
    }

    setupToggleButton() {
        const toggleButton = document.getElementById('theme-toggle');
        if (!toggleButton) return;

        toggleButton.addEventListener('click', () => {
            this.toggleTheme();
        });
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new ThemeManager();
    });
} else {
    // DOM already loaded
    new ThemeManager();
}
