/**
 * Shared Sidebar Component
 * Dynamically generates responsive sidebar for all pages
 */
class Sidebar {
    constructor() {
        this.currentPage = this.getCurrentPage();
        this.isOpen = false;
        this.render();
        this.setupMobileToggle();
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
                        id: 'sites',
                        label: 'Sites',
                        href: '/sites',
                        icon: '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/>'
                    },
                    {
                        id: 'training',
                        label: 'Training',
                        href: '/training',
                        icon: '<path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>'
                    },
                    {
                        id: 'mappings',
                        label: 'Mappings',
                        href: '/mappings',
                        icon: '<path d="M9 17H7A5 5 0 017 7h2"/><path d="M15 7h2a5 5 0 010 10h-2"/><line x1="8" y1="12" x2="16" y2="12"/>'
                    }
                ]
            },
            {
                group: 'Settings',
                items: [
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
            <!-- Mobile Header -->
            <div id="mobile-header" class="lg:hidden fixed top-0 left-0 right-0 z-40 bg-sidebar border-b border-sidebar-border px-4 py-3 flex items-center justify-between">
                <h1 class="text-lg font-semibold text-sidebar-foreground">FormAI</h1>
                <button id="mobile-menu-btn" class="p-2 rounded-md text-sidebar-foreground hover:bg-sidebar-accent">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="3" y1="12" x2="21" y2="12"></line>
                        <line x1="3" y1="6" x2="21" y2="6"></line>
                        <line x1="3" y1="18" x2="21" y2="18"></line>
                    </svg>
                </button>
            </div>

            <!-- Mobile Overlay -->
            <div id="sidebar-overlay" class="lg:hidden fixed inset-0 bg-black/50 z-40 hidden"></div>

            <!-- Sidebar -->
            <aside id="sidebar" class="fixed lg:static inset-y-0 left-0 z-50 w-64 bg-sidebar border-r border-sidebar-border flex-shrink-0 flex flex-col h-full transition-transform duration-300 -translate-x-full lg:translate-x-0">
                <!-- Sidebar Header -->
                <div class="p-4 border-b border-sidebar-border">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <h1 class="text-lg font-semibold text-sidebar-foreground sidebar-text tracking-tight">FormAI</h1>
                        </div>
                        <button id="sidebar-close-btn" class="lg:hidden p-1 rounded-md text-sidebar-foreground hover:bg-sidebar-accent">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="18" y1="6" x2="6" y2="18"></line>
                                <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                        </button>
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
                <div class="p-4 border-t border-sidebar-border hidden lg:block">
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
                            <span class="text-sm text-muted-foreground">Memory Usage</span>
                            <span id="memory-status" class="text-sm font-medium text-muted-foreground">Calculating...</span>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-muted-foreground">Version</span>
                            <span id="version-status" class="text-sm font-medium text-muted-foreground">--</span>
                        </div>
                    </div>
                </div>
            </aside>
        `;
    }

    setupMobileToggle() {
        const menuBtn = document.getElementById('mobile-menu-btn');
        const closeBtn = document.getElementById('sidebar-close-btn');
        const overlay = document.getElementById('sidebar-overlay');
        const sidebar = document.getElementById('sidebar');

        if (menuBtn) {
            menuBtn.addEventListener('click', () => this.openSidebar());
        }
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeSidebar());
        }
        if (overlay) {
            overlay.addEventListener('click', () => this.closeSidebar());
        }

        // Close sidebar on navigation (for mobile)
        const navLinks = sidebar?.querySelectorAll('a');
        navLinks?.forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth < 1024) {
                    this.closeSidebar();
                }
            });
        });
    }

    openSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        sidebar?.classList.remove('-translate-x-full');
        overlay?.classList.remove('hidden');
        this.isOpen = true;
    }

    closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        sidebar?.classList.add('-translate-x-full');
        overlay?.classList.add('hidden');
        this.isOpen = false;
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
