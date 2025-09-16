// Enhanced HTML UI for FormAI
pub fn get_html() -> &'static str {
    r#"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>FormAI - Automation Control Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #333;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-badge {
            background: #4CAF50;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            margin-left: auto;
        }
        
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            color: #666;
            margin-bottom: 8px;
            font-weight: 500;
        }
        
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-group textarea {
            resize: vertical;
            min-height: 100px;
        }
        
        .btn {
            background: #333;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            width: 100%;
        }
        
        .btn:hover {
            background: #555;
            transform: translateY(-2px);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .profiles-list {
            max-height: 300px;
            overflow-y: auto;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 10px;
        }
        
        .profile-item {
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
            background: #f8f9fa;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .profile-item:hover {
            background: #e9ecef;
        }
        
        .profile-item.selected {
            background: #e8f5e8;
            border: 2px solid #4CAF50;
        }
        
        .logs {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 8px;
            height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            margin-top: 20px;
        }
        
        .log-entry {
            margin-bottom: 5px;
        }
        
        .log-time {
            color: #858585;
        }
        
        .log-success {
            color: #4CAF50;
        }
        
        .log-error {
            color: #f44336;
        }
        
        .log-info {
            color: #2196F3;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: none;
            margin-left: 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .automation-status {
            display: flex;
            align-items: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                🚀 FormAI Control Panel
                <span class="status-badge">Connected</span>
            </h1>
        </div>
        
        <div class="grid">
            <!-- Profile Management -->
            <div class="card">
                <h2>👤 Profile Management</h2>
                
                <div class="form-group">
                    <label>Select Profile</label>
                    <select id="profileSelect">
                        <option value="">-- Create New Profile --</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Profile Name</label>
                    <input type="text" id="profileName" placeholder="e.g., John Doe">
                </div>
                
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="email" placeholder="john@example.com">
                </div>
                
                <div class="form-group">
                    <label>Phone</label>
                    <input type="tel" id="phone" placeholder="+1-555-0123">
                </div>
                
                <div class="form-group">
                    <label>Additional Data (JSON)</label>
                    <textarea id="additionalData" placeholder='{"company": "ACME Corp", "address": "123 Main St"}'></textarea>
                </div>
                
                <button class="btn" onclick="saveProfile()">💾 Save Profile</button>
            </div>
            
            <!-- Automation Control -->
            <div class="card">
                <h2>🤖 Automation Control</h2>
                
                <div class="automation-status">
                    <span id="automationStatus">Ready to start</span>
                    <div class="spinner" id="spinner"></div>
                </div>
                
                <div class="form-group">
                    <label>Target URLs (one per line)</label>
                    <textarea id="urls" placeholder="https://example.com/form1&#10;https://example.com/form2"></textarea>
                </div>
                
                <div class="form-group">
                    <label>Mode</label>
                    <select id="mode">
                        <option value="headless">Headless (Fast)</option>
                        <option value="visible">Visible (Debug)</option>
                    </select>
                </div>
                
                <button class="btn" onclick="startAutomation()">▶️ Start Automation</button>
                <button class="btn btn-secondary" onclick="stopAutomation()" style="margin-top: 10px;">⏹️ Stop</button>
            </div>
        </div>
        
        <!-- Live Logs -->
        <div class="card" style="margin-top: 30px;">
            <h2>📋 Live Logs</h2>
            <div class="logs" id="logs">
                <div class="log-entry">
                    <span class="log-time">[12:00:00]</span>
                    <span class="log-info">System ready. Select a profile and add URLs to begin.</span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let currentProfile = null;
        
        // Initialize WebSocket connection
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:5003/ws');
            
            ws.onopen = () => {
                addLog('Connected to server', 'success');
                document.querySelector('.status-badge').textContent = 'Connected';
                document.querySelector('.status-badge').style.background = '#4CAF50';
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            
            ws.onclose = () => {
                addLog('Disconnected from server', 'error');
                document.querySelector('.status-badge').textContent = 'Disconnected';
                document.querySelector('.status-badge').style.background = '#f44336';
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function handleWebSocketMessage(data) {
            const spinner = document.getElementById('spinner');
            const statusElement = document.getElementById('automationStatus');
            
            switch (data.type) {
                case 'connection_ack':
                    addLog(data.message, 'success');
                    break;
                    
                case 'automation_started':
                    addLog(data.message, 'success');
                    statusElement.textContent = `Starting automation: ${data.total_urls} URL(s)`;
                    spinner.style.display = 'inline-block';
                    break;
                    
                case 'automation_progress':
                    addLog(data.message, 'info');
                    statusElement.textContent = `Processing: ${data.current_url} (${data.processed_count}/${data.total_count})`;
                    // Update progress if you want to add a progress bar later
                    break;
                    
                case 'automation_completed':
                    addLog(data.message, 'success');
                    statusElement.textContent = `Completed: ${data.total_processed} URL(s) processed`;
                    spinner.style.display = 'none';
                    break;
                    
                case 'automation_error':
                    addLog(data.message, 'error');
                    statusElement.textContent = `Error: ${data.error}`;
                    spinner.style.display = 'none';
                    break;
                    
                case 'script_log':
                    addLog(data.message, 'info');
                    break;
                    
                default:
                    addLog(`Unknown message type: ${data.type}`, 'info');
                    console.log('Unhandled WebSocket message:', data);
            }
        }
        
        function addLog(message, type = 'info') {
            const logs = document.getElementById('logs');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `
                <span class="log-time">[${time}]</span>
                <span class="log-${type}">${message}</span>
            `;
            logs.appendChild(entry);
            logs.scrollTop = logs.scrollHeight;
        }
        
        async function loadProfiles() {
            try {
                const response = await fetch('/api/profiles');
                const profiles = await response.json();
                const select = document.getElementById('profileSelect');
                
                // Clear existing options except the first
                select.innerHTML = '<option value="">-- Create New Profile --</option>';
                
                profiles.forEach(profile => {
                    const option = document.createElement('option');
                    option.value = profile.id || profile.name;
                    option.textContent = profile.name;
                    select.appendChild(option);
                });
                
                addLog(`Loaded ${profiles.length} profiles`, 'info');
            } catch (error) {
                addLog('Failed to load profiles: ' + error.message, 'error');
            }
        }
        
        async function saveProfile() {
            const profileData = {
                name: document.getElementById('profileName').value,
                email: document.getElementById('email').value,
                phone: document.getElementById('phone').value,
            };
            
            // Parse additional data
            const additionalData = document.getElementById('additionalData').value;
            if (additionalData) {
                try {
                    const parsed = JSON.parse(additionalData);
                    Object.assign(profileData, parsed);
                } catch (e) {
                    addLog('Invalid JSON in additional data', 'error');
                    return;
                }
            }
            
            try {
                const response = await fetch('/api/profiles', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(profileData)
                });
                
                if (response.ok) {
                    addLog('Profile saved successfully', 'success');
                    loadProfiles();
                } else {
                    throw new Error('Failed to save profile');
                }
            } catch (error) {
                addLog('Error saving profile: ' + error.message, 'error');
            }
        }
        
        async function startAutomation() {
            const profileSelect = document.getElementById('profileSelect');
            const urls = document.getElementById('urls').value.split('\n').filter(u => u.trim());
            const mode = document.getElementById('mode').value;
            
            if (!profileSelect.value) {
                addLog('Please select a profile', 'error');
                return;
            }
            
            if (urls.length === 0) {
                addLog('Please enter at least one URL', 'error');
                return;
            }
            
            document.getElementById('spinner').style.display = 'inline-block';
            document.getElementById('automationStatus').textContent = 'Starting automation...';
            
            try {
                const response = await fetch('/api/automation/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        profile_id: profileSelect.value,
                        url_config: { type: "all" },
                        mode: mode === 'headless' ? 'headless' : 'visible'
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    addLog('Automation started successfully', 'success');
                    addLog(`Processing ${result.urls_count} URL(s)`, 'info');
                } else {
                    const errorText = await response.text();
                    throw new Error(errorText || 'Failed to start automation');
                }
            } catch (error) {
                addLog('Error starting automation: ' + error.message, 'error');
                document.getElementById('spinner').style.display = 'none';
                document.getElementById('automationStatus').textContent = 'Failed to start';
            }
        }
        
        async function stopAutomation() {
            try {
                const response = await fetch('/api/automation/stop', { method: 'POST' });
                if (response.ok) {
                    addLog('Automation stopped', 'info');
                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('automationStatus').textContent = 'Stopped';
                }
            } catch (error) {
                addLog('Error stopping automation: ' + error.message, 'error');
            }
        }
        
        // Handle profile selection
        document.getElementById('profileSelect').addEventListener('change', async (e) => {
            if (e.target.value) {
                try {
                    const response = await fetch(`/api/profiles/${e.target.value}`);
                    const profile = await response.json();
                    
                    document.getElementById('profileName').value = profile.name || '';
                    document.getElementById('email').value = profile.email || '';
                    document.getElementById('phone').value = profile.phone || '';
                    
                    // Remove standard fields from profile for additional data
                    const {name, email, phone, id, ...additional} = profile;
                    if (Object.keys(additional).length > 0) {
                        document.getElementById('additionalData').value = JSON.stringify(additional, null, 2);
                    }
                    
                    addLog(`Loaded profile: ${profile.name}`, 'info');
                } catch (error) {
                    addLog('Error loading profile: ' + error.message, 'error');
                }
            } else {
                // Clear form for new profile
                document.getElementById('profileName').value = '';
                document.getElementById('email').value = '';
                document.getElementById('phone').value = '';
                document.getElementById('additionalData').value = '';
            }
        });
        
        // Initialize on page load
        window.onload = () => {
            connectWebSocket();
            loadProfiles();
        };
    </script>
</body>
</html>
    "#
}