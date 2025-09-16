use anyhow::{Result, anyhow};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::env;
use tracing::{info, error, warn};

// Firecrawl API Response structures
#[derive(Debug, Serialize, Deserialize)]
pub struct FirecrawlScrapeRequest {
    pub url: String,
    pub formats: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub extract: Option<FirecrawlExtractConfig>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FirecrawlExtractConfig {
    pub schema: serde_json::Value,
    pub prompt: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FirecrawlScrapeResponse {
    pub success: bool,
    pub data: Option<FirecrawlData>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FirecrawlData {
    pub url: String,
    pub markdown: Option<String>,
    pub html: Option<String>,
    pub extract: Option<serde_json::Value>,
}

// Our form analysis structures
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscoveredFormField {
    pub name: String,
    pub label: String,
    pub field_type: String,
    pub selectors: Vec<String>,
    pub required: bool,
    pub semantic_type: Option<String>, // e.g., "email", "phone", "firstname"
    pub placeholder: Option<String>,
    pub options: Option<Vec<String>>, // For select fields
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscoveredForm {
    pub url: String,
    pub form_id: Option<String>,
    pub form_action: Option<String>,
    pub form_method: String,
    pub fields: Vec<DiscoveredFormField>,
    pub submit_button: Option<String>,
}

pub struct FirecrawlService {
    client: Client,
    api_key: String,
    api_url: String,
    enabled: bool,
}

impl FirecrawlService {
    pub fn new() -> Result<Self> {
        // Load environment variables
        dotenv::dotenv().ok(); // OK if .env doesn't exist
        
        let api_key = env::var("FIRECRAWL_API_KEY")
            .unwrap_or_else(|_| String::new());
        
        let api_url = env::var("FIRECRAWL_API_URL")
            .unwrap_or_else(|_| "https://api.firecrawl.dev".to_string());
        
        let enabled = if api_key.is_empty() {
            warn!("Firecrawl API key not found. Dynamic form discovery will be disabled.");
            false
        } else {
            env::var("FIRECRAWL_ENABLED")
                .unwrap_or_else(|_| "true".to_string())
                .parse::<bool>()
                .unwrap_or(true)
        };

        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()?;

        Ok(Self {
            client,
            api_key,
            api_url,
            enabled,
        })
    }

    pub fn is_enabled(&self) -> bool {
        self.enabled && !self.api_key.is_empty()
    }

    pub async fn discover_form_fields(&self, url: &str) -> Result<Option<DiscoveredForm>> {
        if !self.is_enabled() {
            info!("Firecrawl is disabled, skipping form discovery for: {}", url);
            return Ok(None);
        }

        info!("Discovering form fields for: {}", url);
        
        // Create extraction schema for form fields
        let extract_schema = serde_json::json!({
            "type": "object",
            "properties": {
                "forms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "form_id": {"type": "string"},
                            "form_action": {"type": "string"},
                            "form_method": {"type": "string"},
                            "fields": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "label": {"type": "string"},
                                        "type": {"type": "string"},
                                        "selectors": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "required": {"type": "boolean"},
                                        "semantic_type": {"type": "string"},
                                        "placeholder": {"type": "string"},
                                        "options": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    }
                                }
                            },
                            "submit_button": {"type": "string"}
                        }
                    }
                }
            }
        });

        let extract_config = FirecrawlExtractConfig {
            schema: extract_schema,
            prompt: "Analyze this webpage and extract all form information. For each form, identify all input fields, their types (text, email, password, select, etc.), labels, names, CSS selectors, whether they're required, and any semantic meaning (like 'firstname', 'lastname', 'email', 'phone'). Also identify submit buttons. Pay special attention to registration forms, contact forms, and sign-up forms.".to_string(),
        };

        let request = FirecrawlScrapeRequest {
            url: url.to_string(),
            formats: vec!["extract".to_string()],
            extract: Some(extract_config),
        };

        let response = self.client
            .post(&format!("{}/v1/scrape", self.api_url))
            .header("Authorization", &format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            error!("Firecrawl API error: {} - {}", status, error_text);
            return Err(anyhow!("Firecrawl API error: {}", status));
        }

        let scrape_response: FirecrawlScrapeResponse = response.json().await?;

        if !scrape_response.success {
            let error_msg = scrape_response.error.unwrap_or_default();
            error!("Firecrawl extraction failed: {}", error_msg);
            return Err(anyhow!("Firecrawl extraction failed: {}", error_msg));
        }

        if let Some(data) = scrape_response.data {
            if let Some(extract) = data.extract {
                return self.parse_extracted_forms(url, extract).await;
            }
        }

        info!("No form data extracted for: {}", url);
        Ok(None)
    }

    async fn parse_extracted_forms(&self, url: &str, extract: serde_json::Value) -> Result<Option<DiscoveredForm>> {
        if let Some(forms_array) = extract.get("forms").and_then(|f| f.as_array()) {
            if let Some(form_data) = forms_array.first() {
                let form_id = form_data.get("form_id")
                    .and_then(|v| v.as_str())
                    .map(String::from);
                
                let form_action = form_data.get("form_action")
                    .and_then(|v| v.as_str())
                    .map(String::from);
                
                let form_method = form_data.get("form_method")
                    .and_then(|v| v.as_str())
                    .unwrap_or("POST")
                    .to_string();

                let submit_button = form_data.get("submit_button")
                    .and_then(|v| v.as_str())
                    .map(String::from);

                let mut fields = Vec::new();

                if let Some(fields_array) = form_data.get("fields").and_then(|f| f.as_array()) {
                    for field_data in fields_array {
                        let name = field_data.get("name")
                            .and_then(|v| v.as_str())
                            .unwrap_or_default()
                            .to_string();

                        let label = field_data.get("label")
                            .and_then(|v| v.as_str())
                            .unwrap_or_default()
                            .to_string();

                        let field_type = field_data.get("type")
                            .and_then(|v| v.as_str())
                            .unwrap_or("text")
                            .to_string();

                        let selectors = field_data.get("selectors")
                            .and_then(|v| v.as_array())
                            .map(|arr| arr.iter()
                                .filter_map(|s| s.as_str().map(String::from))
                                .collect::<Vec<String>>())
                            .unwrap_or_else(|| {
                                // Generate fallback selectors
                                vec![
                                    format!("input[name='{}']", name),
                                    format!("input[id='{}']", name),
                                    format!("select[name='{}']", name),
                                    format!("textarea[name='{}']", name),
                                ]
                            });

                        let required = field_data.get("required")
                            .and_then(|v| v.as_bool())
                            .unwrap_or(false);

                        let semantic_type = field_data.get("semantic_type")
                            .and_then(|v| v.as_str())
                            .map(String::from);

                        let placeholder = field_data.get("placeholder")
                            .and_then(|v| v.as_str())
                            .map(String::from);

                        let options = field_data.get("options")
                            .and_then(|v| v.as_array())
                            .map(|arr| arr.iter()
                                .filter_map(|s| s.as_str().map(String::from))
                                .collect::<Vec<String>>());

                        fields.push(DiscoveredFormField {
                            name,
                            label,
                            field_type,
                            selectors,
                            required,
                            semantic_type,
                            placeholder,
                            options,
                        });
                    }
                }

                info!("Discovered {} form fields for: {}", fields.len(), url);
                
                return Ok(Some(DiscoveredForm {
                    url: url.to_string(),
                    form_id,
                    form_action,
                    form_method,
                    fields,
                    submit_button,
                }));
            }
        }

        info!("No valid form structure found for: {}", url);
        Ok(None)
    }


    /// Get smart selectors for a profile field using discovered form data
    pub fn get_smart_selectors(&self, form: &DiscoveredForm, profile_field: &str) -> Vec<String> {
        let profile_lower = profile_field.to_lowercase();
        
        // First try exact semantic type match
        for field in &form.fields {
            if let Some(semantic_type) = &field.semantic_type {
                if semantic_type.to_lowercase() == profile_lower {
                    return field.selectors.clone();
                }
            }
        }
        
        // Then try field name match
        for field in &form.fields {
            if field.name.to_lowercase() == profile_lower {
                return field.selectors.clone();
            }
        }
        
        // Finally try label matching
        for field in &form.fields {
            if field.label.to_lowercase().contains(&profile_lower) {
                return field.selectors.clone();
            }
        }
        
        // Return empty if no match found
        Vec::new()
    }
}