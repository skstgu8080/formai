// User Data Management for FormAI
class ProfileManager {
    constructor() {
        this.profiles = new Map();
        this.currentProfile = null;
        this.init();
    }

    async init() {
        await this.loadProfiles();
        this.setupEventListeners();
        this.renderProfiles();
    }

    async loadProfiles() {
        try {
            const response = await fetch('/api/profiles');
            if (response.ok) {
                const profiles = await response.json();
                this.profiles.clear();
                profiles.forEach(profile => {
                    this.profiles.set(profile.id, profile);
                });
                console.log(`Loaded ${profiles.length} profiles`);
            }
        } catch (error) {
            console.error('Failed to load profiles:', error);
            Utils.showToast('Failed to load profiles', 'error');
        }
    }

    setupEventListeners() {
        // Create new profile button
        const createBtn = document.getElementById('create-profile-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.showCreateModal());
        }

        // Form submission
        const profileForm = document.getElementById('profile-form');
        if (profileForm) {
            profileForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Sample data buttons
        const sampleBtns = document.querySelectorAll('[data-sample-type]');
        sampleBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sampleType = e.target.getAttribute('data-sample-type');
                this.fillSampleData(sampleType);
            });
        });

        // Delete profile buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.delete-profile-btn')) {
                const profileId = e.target.getAttribute('data-profile-id');
                this.confirmDelete(profileId);
            }
        });

        // Edit profile buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.edit-profile-btn')) {
                const profileId = e.target.getAttribute('data-profile-id');
                this.editProfile(profileId);
            }
        });
    }

    showCreateModal() {
        this.currentProfile = null;
        this.clearForm();
        ModalManager.show('profile-modal');
    }

    editProfile(profileId) {
        const profile = this.profiles.get(profileId);
        if (!profile) return;

        this.currentProfile = profile;
        this.populateForm(profile);
        ModalManager.show('profile-modal');
    }

    async handleFormSubmit(e) {
        e.preventDefault();

        const formData = new FormData(e.target);
        const profileData = this.formDataToProfile(formData);

        try {
            const isEdit = this.currentProfile !== null;
            const url = isEdit ? `/api/user_data/${this.currentProfile.id}` : '/api/user_data';
            const method = isEdit ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(profileData)
            });

            if (response.ok) {
                const savedProfile = await response.json();
                this.profiles.set(savedProfile.id, savedProfile);
                this.renderProfiles();
                ModalManager.hide('profile-modal');
                Utils.showToast(`Profile ${isEdit ? 'updated' : 'created'} successfully!`, 'success');
            } else {
                throw new Error(`Failed to ${isEdit ? 'update' : 'create'} profile`);
            }
        } catch (error) {
            console.error('Error saving profile:', error);
            Utils.showToast(`Failed to ${this.currentProfile ? 'update' : 'create'} profile`, 'error');
        }
    }

    async confirmDelete(profileId) {
        const profile = this.profiles.get(profileId);
        if (!profile) return;

        Utils.confirm(`Are you sure you want to delete "${profile.name}"?`, async () => {
            try {
                const response = await fetch(`/api/user_data/${profileId}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    this.profiles.delete(profileId);
                    this.renderProfiles();
                    Utils.showToast('Profile deleted successfully!', 'success');
                } else {
                    throw new Error('Failed to delete profile');
                }
            } catch (error) {
                console.error('Error deleting profile:', error);
                Utils.showToast('Failed to delete profile', 'error');
            }
        });
    }

    formDataToProfile(formData) {
        return {
            name: formData.get('name'),
            email: formData.get('email'),
            phone: formData.get('phone'),
            company: formData.get('company'),
            job_title: formData.get('job_title'),
            website: formData.get('website'),
            linkedin: formData.get('linkedin'),
            github: formData.get('github'),
            twitter: formData.get('twitter'),
            address: formData.get('address'),
            city: formData.get('city'),
            state: formData.get('state'),
            zip_code: formData.get('zip_code'),
            country: formData.get('country'),
            bio: formData.get('bio'),
            skills: formData.get('skills'),
            interests: formData.get('interests'),
            experience: formData.get('experience'),
            education: formData.get('education'),
            certifications: formData.get('certifications')
        };
    }

    populateForm(profile) {
        Object.keys(profile).forEach(key => {
            const input = document.querySelector(`[name="${key}"]`);
            if (input && profile[key]) {
                input.value = profile[key];
            }
        });
    }

    clearForm() {
        const form = document.getElementById('profile-form');
        if (form) {
            form.reset();
        }
    }

    renderProfiles() {
        const container = document.getElementById('profiles-container');
        if (!container) return;

        if (this.profiles.size === 0) {
            container.innerHTML = `
                <div class="text-center p-8">
                    <i class="fas fa-user-plus text-4xl text-gray-400 mb-4"></i>
                    <h3 class="text-lg font-medium text-gray-500 mb-2">No profiles yet</h3>
                    <p class="text-gray-400 mb-4">Create your first profile to get started</p>
                    <button class="btn btn-primary" onclick="profileManager.showCreateModal()">
                        <i class="fas fa-plus"></i> Create Profile
                    </button>
                </div>
            `;
            return;
        }

        const html = Array.from(this.profiles.values()).map(profile => `
            <div class="profile-card">
                <div class="profile-header">
                    <h4>${this.escapeHtml(profile.name || 'Unnamed Profile')}</h4>
                    <div class="profile-actions">
                        <button class="btn-icon edit-profile-btn" data-profile-id="${profile.id}" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-icon delete-profile-btn" data-profile-id="${profile.id}" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="profile-details">
                    ${profile.email ? `<p><strong>Email:</strong> ${this.escapeHtml(profile.email)}</p>` : ''}
                    ${profile.company ? `<p><strong>Company:</strong> ${this.escapeHtml(profile.company)}</p>` : ''}
                    ${profile.job_title ? `<p><strong>Job Title:</strong> ${this.escapeHtml(profile.job_title)}</p>` : ''}
                    ${profile.phone ? `<p><strong>Phone:</strong> ${this.escapeHtml(profile.phone)}</p>` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    fillSampleData(type) {
        const sampleData = this.getSampleData(type);
        Object.keys(sampleData).forEach(key => {
            const input = document.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = sampleData[key];
            }
        });
        Utils.showToast(`Sample ${type} data filled!`, 'info');
    }

    getSampleData(type) {
        const samples = {
            personal: {
                name: 'John Smith',
                email: 'john.smith@email.com',
                phone: '+1 (555) 123-4567',
                address: '123 Main Street',
                city: 'New York',
                state: 'NY',
                zip_code: '10001',
                country: 'United States',
                bio: 'Experienced professional with a passion for innovation and technology.'
            },
            professional: {
                name: 'Sarah Johnson',
                email: 'sarah.johnson@company.com',
                phone: '+1 (555) 987-6543',
                company: 'Tech Solutions Inc.',
                job_title: 'Senior Software Engineer',
                website: 'https://sarahjohnson.dev',
                linkedin: 'https://linkedin.com/in/sarahjohnson',
                github: 'https://github.com/sarahjohnson',
                skills: 'JavaScript, Python, React, Node.js, AWS',
                experience: '8+ years in software development',
                education: 'BS Computer Science, Stanford University'
            },
            creative: {
                name: 'Alex Rivera',
                email: 'alex@creativestudio.com',
                phone: '+1 (555) 456-7890',
                company: 'Creative Studio',
                job_title: 'Creative Director',
                website: 'https://alexrivera.design',
                linkedin: 'https://linkedin.com/in/alexrivera',
                twitter: 'https://twitter.com/alexrivera',
                skills: 'Design, Branding, Photography, Adobe Creative Suite',
                interests: 'Digital art, Photography, Modern architecture',
                bio: 'Award-winning creative director with 10+ years of experience in brand design and digital marketing.'
            }
        };

        return samples[type] || samples.personal;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Statistics Dashboard
class StatsDashboard {
    constructor() {
        this.init();
    }

    async init() {
        await this.loadStats();
        this.setupRefreshTimer();
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            if (response.ok) {
                const stats = await response.json();
                this.updateStatsDisplay(stats);
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    updateStatsDisplay(stats) {
        // Update stat cards
        const updates = {
            'total-profiles': stats.total_profiles || 0,
            'total-urls': stats.total_urls || 0,
            'forms-filled': stats.forms_filled || 0,
            'success-rate': `${stats.success_rate || 0}%`
        };

        Object.entries(updates).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        // Update recent activities
        if (stats.recent_activities) {
            this.updateRecentActivities(stats.recent_activities);
        }
    }

    updateRecentActivities(activities) {
        const container = document.getElementById('recent-activities');
        if (!container) return;

        if (activities.length === 0) {
            container.innerHTML = '<p class="text-center text-gray-500">No recent activity</p>';
            return;
        }

        const html = activities.slice(0, 5).map(activity => `
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="fas fa-${this.getActivityIcon(activity.type)}"></i>
                </div>
                <div class="activity-details">
                    <h4>${activity.description}</h4>
                    <div class="activity-time">${this.formatTime(activity.timestamp)}</div>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    getActivityIcon(type) {
        const icons = {
            'profile_created': 'user-plus',
            'profile_updated': 'user-edit',
            'profile_deleted': 'user-minus',
            'form_filled': 'check-circle',
            'url_tested': 'globe',
            'default': 'info-circle'
        };
        return icons[type] || icons.default;
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
        return `${Math.floor(diff / 86400000)} days ago`;
    }

    setupRefreshTimer() {
        // Refresh stats every 30 seconds
        setInterval(() => {
            this.loadStats();
        }, 30000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.profileManager = new ProfileManager();
    window.statsDashboard = new StatsDashboard();
});

// Export for global use
window.ProfileManager = ProfileManager;
window.StatsDashboard = StatsDashboard;