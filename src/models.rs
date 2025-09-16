use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Profile {
    pub id: String,
    pub name: String,
    pub data: HashMap<String, String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldMapping {
    pub id: String,
    pub url: String,
    pub fields: HashMap<String, String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

// Enhanced field mapping structures for comprehensive site support
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnhancedFieldMapping {
    pub id: String,
    pub url: String,
    pub site_name: String,
    pub form_type: String,
    pub fields: HashMap<String, FieldDefinition>,
    pub success_rate: u8,
    pub last_tested: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldDefinition {
    pub selectors: Vec<String>,
    pub field_type: String,
    pub required: bool,
    pub profile_field: Option<String>,
    pub sample_values: Option<Vec<String>>,
    pub options: Option<Vec<String>>,
}

// Recording structures for training system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FormRecording {
    pub id: String,
    pub name: String,
    pub url: String,
    pub recorded_actions: Vec<RecordedAction>,
    pub form_analysis: Option<FormAnalysis>,
    pub success_rate: f64,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecordedAction {
    pub element_selector: String,
    pub fallback_selectors: Vec<String>,
    pub action_type: ActionType,
    pub value: Option<String>,
    pub confidence: f64,
    pub dom_context: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ActionType {
    Fill,
    Click,
    Select,
    Check,
    Submit,
    Navigate,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FormAnalysis {
    pub total_fields: usize,
    pub field_types: HashMap<String, usize>,
    pub complexity_score: f64,
    pub anti_bot_detected: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutomationRequest {
    pub profile: String,
    pub urls: Vec<String>,
    pub headless: bool,
    pub delay: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashboardAutomationRequest {
    pub profile_id: String,
    pub url_config: UrlConfig,
    pub mode: String, // "visible" or "headless"
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum UrlConfig {
    #[serde(rename = "all")]
    All,
    #[serde(rename = "amount")]
    Amount { amount: u32 },
    #[serde(rename = "group")]
    Group { group_id: String },
    #[serde(rename = "single")]
    Single { url: String },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutomationStatus {
    pub running: bool,
    pub current_url: Option<String>,
    pub progress: f32,
    pub processed_count: usize,
    pub total_count: usize,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum WebSocketMessage {
    #[serde(rename = "connection_ack")]
    ConnectionAck {
        timestamp: DateTime<Utc>,
        message: String,
        server_version: String,
    },
    
    #[serde(rename = "automation_started")]
    AutomationStarted {
        timestamp: DateTime<Utc>,
        profile: String,
        total_urls: usize,
        headless: bool,
        message: String,
    },
    
    #[serde(rename = "automation_progress")]
    AutomationProgress {
        timestamp: DateTime<Utc>,
        current_url: String,
        progress: f32,
        processed_count: usize,
        total_count: usize,
        message: String,
    },
    
    #[serde(rename = "automation_completed")]
    AutomationCompleted {
        timestamp: DateTime<Utc>,
        total_processed: usize,
        message: String,
    },
    
    #[serde(rename = "automation_error")]
    AutomationError {
        timestamp: DateTime<Utc>,
        error: String,
        message: String,
    },
    
    #[serde(rename = "script_log")]
    ScriptLog {
        timestamp: DateTime<Utc>,
        message: String,
    },

    #[serde(rename = "recording_started")]
    RecordingStarted {
        timestamp: DateTime<Utc>,
        session_id: String,
        url: String,
        recording_type: String,
        message: String,
    },

    #[serde(rename = "recording_action")]
    RecordingAction {
        timestamp: DateTime<Utc>,
        session_id: String,
        action_type: String,
        selector: String,
        value: Option<String>,
        message: String,
    },

    #[serde(rename = "recording_completed")]
    RecordingCompleted {
        timestamp: DateTime<Utc>,
        session_id: String,
        actions_count: usize,
        duration: f64,
        message: String,
    },

    #[serde(rename = "ai_fill_started")]
    AIFillStarted {
        timestamp: DateTime<Utc>,
        session_id: String,
        url: String,
        provider: String,
        model: String,
        message: String,
    },

    #[serde(rename = "ai_fill_progress")]
    AIFillProgress {
        timestamp: DateTime<Utc>,
        session_id: String,
        stage: String,
        progress: f32,
        current_action: String,
        fields_completed: usize,
        total_fields: usize,
        message: String,
    },

    #[serde(rename = "ai_fill_completed")]
    AIFillCompleted {
        timestamp: DateTime<Utc>,
        session_id: String,
        success: bool,
        fields_filled: usize,
        execution_time: f64,
        tokens_used: Option<u32>,
        message: String,
    },

    // JavaScript-compatible message types
    #[serde(rename = "log")]
    Log {
        level: String,
        message: String,
        timestamp: Option<DateTime<Utc>>,
    },

    #[serde(rename = "automation_status")]
    AutomationStatusUpdate {
        running: bool,
        current_url: Option<String>,
        progress: Option<f32>,
        processed_count: Option<usize>,
        total_count: Option<usize>,
        error: Option<String>,
    },

    #[serde(rename = "profile_updated")]
    ProfileUpdated {
        timestamp: DateTime<Utc>,
        profile_id: String,
        message: String,
    },

    #[serde(rename = "url_groups_updated")]
    UrlGroupsUpdated {
        timestamp: DateTime<Utc>,
        message: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateProfileRequest {
    pub name: String,
    pub data: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateProfileRequest {
    pub name: Option<String>,
    pub data: Option<HashMap<String, String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateMappingRequest {
    pub url: String,
    pub fields: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateMappingRequest {
    pub url: Option<String>,
    pub fields: Option<HashMap<String, String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Recording {
    pub id: String,
    pub name: String,
    pub url: Option<String>,
    pub description: Option<String>,
    pub group: Option<String>,
}

// URL Management Structures
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SavedUrl {
    pub id: String,
    pub url: String,
    pub name: Option<String>,
    pub description: Option<String>,
    pub group: Option<String>,
    pub tags: Vec<String>,
    pub status: UrlStatus,
    pub success_rate: Option<f32>,
    pub last_tested: Option<DateTime<Utc>>,
    pub test_count: u32,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum UrlStatus {
    #[serde(rename = "active")]
    Active,
    #[serde(rename = "inactive")]
    Inactive,
    #[serde(rename = "testing")]
    Testing,
    #[serde(rename = "failed")]
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UrlGroup {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub color: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateUrlRequest {
    pub url: String,
    pub name: Option<String>,
    pub description: Option<String>,
    pub group: Option<String>,
    pub tags: Option<Vec<String>>,
    pub test_url: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateUrlRequest {
    pub url: Option<String>,
    pub name: Option<String>,
    pub description: Option<String>,
    pub group: Option<String>,
    pub tags: Option<Vec<String>>,
    pub status: Option<UrlStatus>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateGroupRequest {
    pub name: String,
    pub description: Option<String>,
    pub color: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UrlTestResult {
    pub url_id: String,
    pub url: String,
    pub success: bool,
    pub response_time: u64,
    pub status_code: Option<u16>,
    pub error: Option<String>,
    pub fields_detected: Option<u32>,
    pub form_complexity: Option<f32>,
    pub tested_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BulkUrlOperation {
    pub url_ids: Vec<String>,
    pub operation: BulkOperation,
    pub data: Option<HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BulkOperation {
    #[serde(rename = "delete")]
    Delete,
    #[serde(rename = "update_group")]
    UpdateGroup,
    #[serde(rename = "update_status")]
    UpdateStatus,
    #[serde(rename = "test")]
    Test,
    #[serde(rename = "add_tags")]
    AddTags,
}

impl Profile {
    pub fn new(name: String, data: HashMap<String, String>) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            name,
            data,
            created_at: now,
            updated_at: now,
        }
    }
    
    pub fn update(&mut self, name: Option<String>, data: Option<HashMap<String, String>>) {
        if let Some(name) = name {
            self.name = name;
        }
        if let Some(data) = data {
            self.data = data;
        }
        self.updated_at = Utc::now();
    }
}

impl FieldMapping {
    pub fn new(url: String, fields: HashMap<String, String>) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            url,
            fields,
            created_at: now,
            updated_at: now,
        }
    }
    
    pub fn update(&mut self, url: Option<String>, fields: Option<HashMap<String, String>>) {
        if let Some(url) = url {
            self.url = url;
        }
        if let Some(fields) = fields {
            self.fields = fields;
        }
        self.updated_at = Utc::now();
    }
}

impl Default for AutomationStatus {
    fn default() -> Self {
        Self {
            running: false,
            current_url: None,
            progress: 0.0,
            processed_count: 0,
            total_count: 0,
            error: None,
        }
    }
}

impl SavedUrl {
    pub fn new(url: String, name: Option<String>, description: Option<String>, group: Option<String>, tags: Vec<String>) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            url,
            name,
            description,
            group,
            tags,
            status: UrlStatus::Active,
            success_rate: None,
            last_tested: None,
            test_count: 0,
            created_at: now,
            updated_at: now,
        }
    }

    pub fn update(&mut self, req: UpdateUrlRequest) {
        if let Some(url) = req.url {
            self.url = url;
        }
        if let Some(name) = req.name {
            self.name = Some(name);
        }
        if let Some(description) = req.description {
            self.description = Some(description);
        }
        if let Some(group) = req.group {
            self.group = Some(group);
        }
        if let Some(tags) = req.tags {
            self.tags = tags;
        }
        if let Some(status) = req.status {
            self.status = status;
        }
        self.updated_at = Utc::now();
    }

    pub fn update_test_result(&mut self, success: bool) {
        self.test_count += 1;
        self.last_tested = Some(Utc::now());

        // Calculate new success rate
        let current_success_rate = self.success_rate.unwrap_or(0.0);
        let total_tests = self.test_count as f32;
        let previous_successes = if self.test_count == 1 {
            0.0
        } else {
            current_success_rate * (total_tests - 1.0) / 100.0
        };

        let new_successes = previous_successes + if success { 1.0 } else { 0.0 };
        self.success_rate = Some((new_successes / total_tests) * 100.0);

        // Update status based on success
        if success {
            if self.status == UrlStatus::Failed {
                self.status = UrlStatus::Active;
            }
        } else {
            self.status = UrlStatus::Failed;
        }

        self.updated_at = Utc::now();
    }
}

impl UrlGroup {
    pub fn new(name: String, description: Option<String>, color: Option<String>) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            name,
            description,
            color: color.unwrap_or_else(|| "#1DB954".to_string()),
            created_at: now,
            updated_at: now,
        }
    }

}

impl Default for UrlStatus {
    fn default() -> Self {
        UrlStatus::Active
    }
}

// API Key Management Structures
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiKey {
    pub id: String,
    pub service: String,
    pub encrypted_key: String,
    pub created_at: DateTime<Utc>,
    pub last_used: Option<DateTime<Utc>>,
    pub is_active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SaveApiKeyRequest {
    pub service: String,
    pub api_key: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiKeyResponse {
    pub service: String,
    pub has_key: bool,
    pub created_at: Option<DateTime<Utc>>,
    pub last_used: Option<DateTime<Utc>>,
    pub key_preview: Option<String>,
}

impl ApiKey {
    pub fn new(service: String, encrypted_key: String) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            service,
            encrypted_key,
            created_at: now,
            last_used: None,
            is_active: true,
        }
    }

    pub fn update_last_used(&mut self) {
        self.last_used = Some(Utc::now());
    }
}

impl ToString for UrlStatus {
    fn to_string(&self) -> String {
        match self {
            UrlStatus::Active => "active".to_string(),
            UrlStatus::Inactive => "inactive".to_string(),
            UrlStatus::Testing => "testing".to_string(),
            UrlStatus::Failed => "failed".to_string(),
        }
    }
}