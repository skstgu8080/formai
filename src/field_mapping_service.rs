use crate::models::{EnhancedFieldMapping, FieldDefinition};
// use crate::firecrawl_service::{FirecrawlService, DiscoveredForm};
use anyhow::Result;
use serde_json;
use std::collections::HashMap;
use tokio::fs;
use tracing::{info, warn};

// Stub types for disabled firecrawl functionality
#[derive(Debug, Clone)]
pub struct DiscoveredFormField {
    pub name: String,
}

#[derive(Debug, Clone)]
pub struct DiscoveredForm {
    pub fields: Vec<DiscoveredFormField>,
}

pub struct FirecrawlService;

impl FirecrawlService {
    pub fn new() -> Result<Self> {
        Ok(Self)
    }

    pub fn is_enabled(&self) -> bool {
        false
    }

    pub async fn discover_form_fields(&self, _url: &str) -> Result<Option<DiscoveredForm>> {
        Ok(None)
    }

    pub fn get_smart_selectors(&self, _form: &DiscoveredForm, _profile_field: &str) -> Vec<String> {
        Vec::new()
    }
}

pub struct FieldMappingService {
    mappings: HashMap<String, EnhancedFieldMapping>,
    firecrawl_service: FirecrawlService,
    discovered_forms: HashMap<String, DiscoveredForm>, // Cache for dynamic discoveries
}

impl FieldMappingService {
    pub fn new() -> Result<Self> {
        let firecrawl_service = FirecrawlService::new()?;
        
        Ok(Self {
            mappings: HashMap::new(),
            firecrawl_service,
            discovered_forms: HashMap::new(),
        })
    }

    pub async fn load_mappings(&mut self) -> Result<()> {
        info!("Loading enhanced field mappings from disk...");
        
        // Load the comprehensive RoboForm mapping
        if let Ok(roboform_mapping) = self.load_roboform_mapping().await {
            let url = roboform_mapping.url.clone();
            self.mappings.insert(url, roboform_mapping);
            info!("Loaded RoboForm comprehensive mapping");
        }

        // Load other mappings from field_mappings directory
        let mapping_dir = "field_mappings";
        if let Ok(mut entries) = fs::read_dir(mapping_dir).await {
            while let Ok(Some(entry)) = entries.next_entry().await {
                if let Some(file_name) = entry.file_name().to_str() {
                    if file_name.ends_with(".json") && file_name != "roboform_test_mapping.json" {
                        if let Ok(mapping) = self.load_mapping_from_file(entry.path()).await {
                            let url = mapping.url.clone();
                            self.mappings.insert(url, mapping);
                            info!("Loaded mapping from: {}", file_name);
                        }
                    }
                }
            }
        }

        info!("Loaded {} enhanced field mappings", self.mappings.len());
        Ok(())
    }

    async fn load_roboform_mapping(&self) -> Result<EnhancedFieldMapping> {
        let content = fs::read_to_string("field_mappings/roboform_test_mapping.json").await?;
        let raw_mapping: serde_json::Value = serde_json::from_str(&content)?;
        
        // Convert the existing mapping format to our enhanced format
        let mut fields = HashMap::new();
        
        if let Some(raw_fields) = raw_mapping.get("fields").and_then(|v| v.as_object()) {
            for (field_name, field_data) in raw_fields {
                if let Some(field_obj) = field_data.as_object() {
                    let selectors = field_obj.get("selectors")
                        .and_then(|v| v.as_array())
                        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
                        .unwrap_or_else(|| vec![format!("input[name='{}']", field_name)]);
                    
                    let field_type = field_obj.get("field_type")
                        .and_then(|v| v.as_str())
                        .unwrap_or("text")
                        .to_string();
                    
                    let required = field_obj.get("required")
                        .and_then(|v| v.as_bool())
                        .unwrap_or(false);
                    
                    let profile_field = field_obj.get("profile_field")
                        .and_then(|v| v.as_str())
                        .map(String::from);
                    
                    let sample_values = field_obj.get("sample_values")
                        .and_then(|v| v.as_array())
                        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect());
                    
                    let options = field_obj.get("options")
                        .and_then(|v| v.as_array())
                        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect());

                    fields.insert(field_name.clone(), FieldDefinition {
                        selectors,
                        field_type,
                        required,
                        profile_field,
                        sample_values,
                        options,
                    });
                }
            }
        }

        Ok(EnhancedFieldMapping {
            id: raw_mapping.get("id").and_then(|v| v.as_str()).unwrap_or("roboform_test").to_string(),
            url: raw_mapping.get("url").and_then(|v| v.as_str()).unwrap_or("https://www.roboform.com/filling-test-all-fields").to_string(),
            site_name: raw_mapping.get("site_name").and_then(|v| v.as_str()).unwrap_or("RoboForm Test").to_string(),
            form_type: raw_mapping.get("form_type").and_then(|v| v.as_str()).unwrap_or("test").to_string(),
            fields,
            success_rate: raw_mapping.get("success_rate").and_then(|v| v.as_u64()).unwrap_or(100) as u8,
            last_tested: raw_mapping.get("last_tested").and_then(|v| v.as_str()).unwrap_or("2025-09-09").to_string(),
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        })
    }

    async fn load_mapping_from_file(&self, path: std::path::PathBuf) -> Result<EnhancedFieldMapping> {
        let content = fs::read_to_string(path).await?;
        let mapping: EnhancedFieldMapping = serde_json::from_str(&content)?;
        Ok(mapping)
    }

    pub fn get_mapping_for_url(&self, url: &str) -> Option<&EnhancedFieldMapping> {
        // Direct URL match
        if let Some(mapping) = self.mappings.get(url) {
            return Some(mapping);
        }

        // Try to find by domain/partial match
        for (mapped_url, mapping) in &self.mappings {
            if url.contains(&extract_domain(mapped_url)) {
                return Some(mapping);
            }
        }

        None
    }

    pub async fn get_field_selectors(&mut self, url: &str, profile_field: &str) -> Vec<String> {
        // First, try static mapping
        if let Some(mapping) = self.get_mapping_for_url(url) {
            // First, try to find by exact profile field match
            for (_field_name, field_def) in &mapping.fields {
                if let Some(ref pf) = field_def.profile_field {
                    if pf == profile_field {
                        return field_def.selectors.clone();
                    }
                }
            }

            // Then try to find by field name match
            if let Some(field_def) = mapping.fields.get(profile_field) {
                return field_def.selectors.clone();
            }

            // Finally, try semantic matching
            let semantic_match = self.find_semantic_match(mapping, profile_field);
            if !semantic_match.is_empty() {
                return semantic_match;
            }
        }

        // Try dynamic discovery if static mapping failed or is incomplete
        if let Some(selectors) = self.get_dynamic_selectors(url, profile_field).await {
            if !selectors.is_empty() {
                info!("Using dynamic discovery for field '{}' on {}: {:?}", profile_field, url, selectors);
                return selectors;
            }
        }

        // Fallback to simple selectors
        vec![
            format!("input[name='{}']", profile_field),
            format!("input[id='{}']", profile_field),
            format!("select[name='{}']", profile_field),
            format!("textarea[name='{}']", profile_field),
        ]
    }

    fn find_semantic_match(&self, mapping: &EnhancedFieldMapping, profile_field: &str) -> Vec<String> {
        let profile_lower = profile_field.to_lowercase();
        
        // Semantic field matching rules
        let semantic_rules = vec![
            ("firstname", vec!["firstName", "first_name", "fname", "given_name"]),
            ("lastname", vec!["lastName", "last_name", "lname", "family_name", "surname"]),
            ("fullname", vec!["fullName", "full_name", "name", "display_name"]),
            ("email", vec!["email", "emailAddress", "email_address", "mail"]),
            ("phone", vec!["phoneNumber", "phone_number", "tel", "telephone", "mobile"]),
            ("address", vec!["address", "address1", "street", "street_address"]),
            ("city", vec!["city", "locality", "town"]),
            ("state", vec!["state", "region", "province"]),
            ("zip", vec!["zip", "postal_code", "postcode", "zipcode"]),
            ("company", vec!["company", "organization", "employer"]),
            ("password", vec!["password", "pwd", "pass"]),
            ("username", vec!["username", "user_name", "login", "user_id"]),
        ];

        for (semantic_type, field_names) in semantic_rules {
            if profile_lower.contains(semantic_type) {
                for field_name in field_names {
                    if let Some(field_def) = mapping.fields.get(field_name) {
                        return field_def.selectors.clone();
                    }
                }
            }
        }

        // No semantic match found, return empty
        vec![]
    }

    /// Get selectors using dynamic discovery with Firecrawl
    async fn get_dynamic_selectors(&mut self, url: &str, profile_field: &str) -> Option<Vec<String>> {
        // Check if we already have this form discovered and cached
        if let Some(discovered_form) = self.discovered_forms.get(url) {
            let selectors = self.firecrawl_service.get_smart_selectors(discovered_form, profile_field);
            if !selectors.is_empty() {
                return Some(selectors);
            }
        }

        // If not cached or no match found, try to discover the form
        if self.firecrawl_service.is_enabled() {
            match self.firecrawl_service.discover_form_fields(url).await {
                Ok(Some(discovered_form)) => {
                    info!("Dynamically discovered form with {} fields for: {}", 
                          discovered_form.fields.len(), url);
                    
                    // Get selectors for this specific field
                    let selectors = self.firecrawl_service.get_smart_selectors(&discovered_form, profile_field);
                    
                    // Cache the discovered form for future use
                    self.discovered_forms.insert(url.to_string(), discovered_form);
                    
                    if !selectors.is_empty() {
                        return Some(selectors);
                    }
                }
                Ok(None) => {
                    info!("No forms discovered for: {}", url);
                }
                Err(e) => {
                    warn!("Failed to discover forms for {}: {}", url, e);
                }
            }
        }

        None
    }

    /// Discover all form fields for a URL and cache them
    pub async fn discover_and_cache_form(&mut self, url: &str) -> Result<Option<&DiscoveredForm>> {
        if self.discovered_forms.contains_key(url) {
            return Ok(self.discovered_forms.get(url));
        }

        if !self.firecrawl_service.is_enabled() {
            return Ok(None);
        }

        match self.firecrawl_service.discover_form_fields(url).await {
            Ok(Some(discovered_form)) => {
                info!("Pre-discovered form with {} fields for: {}", 
                      discovered_form.fields.len(), url);
                
                self.discovered_forms.insert(url.to_string(), discovered_form);
                Ok(self.discovered_forms.get(url))
            }
            Ok(None) => {
                info!("No forms found during pre-discovery for: {}", url);
                Ok(None)
            }
            Err(e) => {
                warn!("Failed to pre-discover forms for {}: {}", url, e);
                Err(e)
            }
        }
    }

    /// Get all discovered field names for a URL (useful for debugging)
    pub fn get_discovered_field_names(&self, url: &str) -> Vec<String> {
        if let Some(form) = self.discovered_forms.get(url) {
            form.fields.iter().map(|f| f.name.clone()).collect()
        } else {
            Vec::new()
        }
    }

    /// Check if dynamic discovery is available
    pub fn is_dynamic_discovery_enabled(&self) -> bool {
        self.firecrawl_service.is_enabled()
    }

    pub fn get_all_mappings(&self) -> &HashMap<String, EnhancedFieldMapping> {
        &self.mappings
    }
}

fn extract_domain(url: &str) -> String {
    if let Ok(parsed) = url::Url::parse(url) {
        if let Some(host) = parsed.host_str() {
            return host.to_string();
        }
    }
    
    // Fallback parsing
    url.split('/').nth(2).unwrap_or(url).to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_field_mapping_service() {
        let mut service = FieldMappingService::new();
        
        // This test would require the mapping file to exist
        if service.load_mappings().await.is_ok() {
            let selectors = service.get_field_selectors(
                "https://www.roboform.com/filling-test-all-fields",
                "firstName"
            );
            
            assert!(!selectors.is_empty());
        }
    }
}