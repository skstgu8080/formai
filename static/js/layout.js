/**
 * Shared Layout Component
 * Provides consistent layout structure for all pages
 */
class Layout {
    constructor(options = {}) {
        this.pageTitle = options.pageTitle || 'FormAI Dashboard';
        this.pageContent = options.pageContent || '';
        this.scripts = options.scripts || [];
        this.additionalHead = options.additionalHead || '';

        this.render();
    }

    getBaseHTML() {
        return `
<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${this.pageTitle}</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        border: "hsl(var(--border))",
                        input: "hsl(var(--input))",
                        ring: "hsl(var(--ring))",
                        background: "hsl(var(--background))",
                        foreground: "hsl(var(--foreground))",
                        primary: {
                            DEFAULT: "hsl(var(--primary))",
                            foreground: "hsl(var(--primary-foreground))",
                        },
                        secondary: {
                            DEFAULT: "hsl(var(--secondary))",
                            foreground: "hsl(var(--secondary-foreground))",
                        },
                        destructive: {
                            DEFAULT: "hsl(var(--destructive))",
                            foreground: "hsl(var(--destructive-foreground))",
                        },
                        muted: {
                            DEFAULT: "hsl(var(--muted))",
                            foreground: "hsl(var(--muted-foreground))",
                        },
                        accent: {
                            DEFAULT: "hsl(var(--accent))",
                            foreground: "hsl(var(--accent-foreground))",
                        },
                        popover: {
                            DEFAULT: "hsl(var(--popover))",
                            foreground: "hsl(var(--popover-foreground))",
                        },
                        card: {
                            DEFAULT: "hsl(var(--card))",
                            foreground: "hsl(var(--card-foreground))",
                        },
                        sidebar: {
                            DEFAULT: "hsl(var(--sidebar-background))",
                            foreground: "hsl(var(--sidebar-foreground))",
                            primary: "hsl(var(--sidebar-primary))",
                            "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
                            accent: "hsl(var(--sidebar-accent))",
                            "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
                            border: "hsl(var(--sidebar-border))",
                            ring: "hsl(var(--sidebar-ring))",
                            "muted-foreground": "hsl(var(--sidebar-muted-foreground))",
                        },
                    },
                    borderRadius: {
                        lg: "var(--radius)",
                        md: "calc(var(--radius) - 2px)",
                        sm: "calc(var(--radius) - 4px)",
                    },
                },
            },
        }
    </script>
    <link rel="stylesheet" href="/static/css/input.css">
    <link rel="stylesheet" href="/static/css/dashboard.css">
    ${this.additionalHead}
</head>
<body class="h-full bg-background text-foreground overflow-hidden">
    <div class="flex h-full">
        <!-- Sidebar will be injected here -->
        <div id="sidebar-container"></div>

        <!-- Main Content -->
        <main class="flex-1 flex flex-col overflow-hidden">
            <!-- Header -->
            <header class="bg-card border-b border-gray-200">
                <div class="px-6 py-4">
                    <div class="flex items-center justify-between">
                        <div>
                            <h2 class="text-xl font-semibold text-card-foreground tracking-tight">${this.getPageDisplayName()}</h2>
                            <p class="text-sm text-muted-foreground">Manage your form automation and AI-powered workflows</p>
                        </div>
                        <div class="flex items-center space-x-4">
                            <button id="theme-toggle" class="p-2 rounded-md text-muted-foreground hover:text-card-foreground hover:bg-accent">
                                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                                </svg>
                            </button>
                            <div class="flex items-center space-x-2 text-sm text-muted-foreground">
                                <div class="h-2 w-2 bg-green-500 rounded-full"></div>
                                <span>Connected</span>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            <!-- Page Content -->
            <div class="flex-1 overflow-auto">
                <div class="p-6">
                    ${this.pageContent}
                </div>
            </div>
        </main>
    </div>

    <!-- Scripts -->
    <script src="/static/js/sidebar.js"></script>
    <script src="/static/js/dashboard.js"></script>
    <script src="/static/js/dashboard-enhanced.js"></script>
    <script src="/static/js/system-status.js"></script>
    ${this.scripts.map(script => `<script src="${script}"></script>`).join('\\n    ')}
</body>
</html>
        `;
    }

    getPageDisplayName() {
        const path = window.location.pathname;
        const pageMap = {
            '/': 'Dashboard',
            '/profiles': 'Profiles',
            '/automation': 'Automation',
            '/saved-urls': 'Saved URLs',
            '/saved-pages': 'Saved Pages',
            '/previous-orders': 'Previous Orders',
            '/account': 'Account',
            '/settings': 'Settings',
            '/recorder': 'Recorder'
        };
        return pageMap[path] || this.pageTitle;
    }

    render() {
        document.documentElement.innerHTML = this.getBaseHTML();
    }

    static create(options) {
        return new Layout(options);
    }
}

// Make Layout available globally
window.Layout = Layout;