/**
 * Shared Sidebar Component
 * Dynamically generates consistent sidebar for all pages
 */
class Sidebar {
    constructor() {
        this.currentPage = this.getCurrentPage();
        this.render();
    }

    getCurrentPage() {
        const path = window.location.pathname;
        if (path === '/' || path === '/index.html') return 'dashboard';
        return path.replace('/', '').replace('.html', '');
    }

    getNavigationItems() {
        return [
            {
                group: 'Main',
                items: [
                    {
                        id: 'dashboard',
                        label: 'Dashboard',
                        href: '/',
                        icon: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9,22 9,12 15,12 15,22"/>'
                    }
                ]
            },
            {
                group: 'Automation',
                items: [
                    {
                        id: 'profiles',
                        label: 'Profiles',
                        href: '/profiles',
                        icon: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
                    },
                    {
                        id: 'automation',
                        label: 'Automation',
                        href: '/automation',
                        icon: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M8 12h8"/><path d="M12 8v8"/>'
                    },
                    {
                        id: 'recorder',
                        label: 'Recorder',
                        href: '/recorder',
                        icon: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/>'
                    }
                ]
            },
            {
                group: 'Data',
                items: [
                    {
                        id: 'saved-urls',
                        label: 'URLs',
                        href: '/saved-urls',
                        icon: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.72"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.72-1.72"/>'
                    },
                    {
                        id: 'saved-pages',
                        label: 'Saved Pages',
                        href: '/saved-pages',
                        icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/>'
                    },
                    {
                        id: 'previous-orders',
                        label: 'Previous Orders',
                        href: '/previous-orders',
                        icon: '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M9 14l2 2 4-4"/>'
                    }
                ]
            },
            {
                group: 'Settings',
                items: [
                    {
                        id: 'account',
                        label: 'Account',
                        href: '/account',
                        icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'
                    },
                    {
                        id: 'settings',
                        label: 'Settings',
                        href: '/settings',
                        icon: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
                    }
                ]
            }
        ];
    }

    generateSidebarHTML() {
        const navigationGroups = this.getNavigationItems();

        let groupsHTML = '';
        navigationGroups.forEach(group => {
            let itemsHTML = '';
            group.items.forEach(item => {
                const isActive = this.currentPage === item.id ||
                               (this.currentPage === 'dashboard' && item.id === 'dashboard');
                const activeClass = isActive ? 'text-sidebar-foreground bg-sidebar-accent active' : 'text-sidebar-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent';

                itemsHTML += `
                    <a href="${item.href}" class="flex items-center px-3 py-2 text-sm font-medium ${activeClass} rounded-md transition-colors sidebar-nav-item" data-tooltip="${item.label}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-3 sidebar-icon">
                            ${item.icon}
                        </svg>
                        <span class="sidebar-text">${item.label}</span>
                    </a>
                `;
            });

            groupsHTML += `
                <div class="space-y-1">
                    <div class="px-3 py-2">
                        <h3 class="text-xs font-semibold text-sidebar-foreground/70 uppercase tracking-wider">${group.group}</h3>
                    </div>
                    <nav class="space-y-1">
                        ${itemsHTML}
                    </nav>
                </div>
            `;
        });

        return `
            <aside id="sidebar" class="w-64 bg-sidebar border-r border-sidebar-border flex-shrink-0 flex flex-col h-full transition-all duration-300">
                <!-- Sidebar Header -->
                <div class="p-4 border-b border-sidebar-border">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <h1 class="text-lg font-semibold text-sidebar-foreground sidebar-text tracking-tight">FormAI</h1>
                        </div>
                    </div>
                </div>

                <!-- Sidebar Content -->
                <div class="flex-1 overflow-y-auto">
                    <!-- Navigation Groups -->
                    <div class="p-2 space-y-6">
                        ${groupsHTML}
                    </div>
                </div>

                <!-- Sidebar Footer -->
                <div class="p-4 border-t border-sidebar-border">
                    <div class="space-y-3">
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-muted-foreground">Browser Engine</span>
                            <span id="browser-status" class="text-sm font-medium text-muted-foreground">Checking...</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-muted-foreground">WebSocket</span>
                            <span id="websocket-status" class="text-sm font-medium text-muted-foreground">Checking...</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-muted-foreground">AI Model</span>
                            <span id="ai-model-status" class="text-sm font-medium text-muted-foreground">Checking...</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-muted-foreground">Memory Usage</span>
                            <span id="memory-status" class="text-sm font-medium text-muted-foreground">Calculating...</span>
                        </div>
                    </div>
                </div>
            </aside>
        `;
    }

    render() {
        // Find the sidebar container or create one
        let sidebarContainer = document.getElementById('sidebar-container');
        if (!sidebarContainer) {
            sidebarContainer = document.createElement('div');
            sidebarContainer.id = 'sidebar-container';
            document.body.insertBefore(sidebarContainer, document.body.firstChild);
        }

        sidebarContainer.innerHTML = this.generateSidebarHTML();
    }
}

// Auto-initialize sidebar when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.sidebar = new Sidebar();
});