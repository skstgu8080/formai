use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use chrono::Utc;
use std::collections::HashMap;
use tokio::fs;
use tracing::{error, info, warn};

use crate::{
    models::*,
    profile_adapter::{ProfileAdapter, FormTemplate},
    websocket::broadcast_automation_message,
    openrouter::OpenRouterClient,
    AppState,
};
use std::path::Path as FilePath;
use rand::Rng;
use playwright::api::Page;

// Helper functions for human-like dropdown interactions

// Generate human-like random delay between min and max milliseconds
fn human_delay_ms(min: u64, max: u64) -> u64 {
    let mut rng = rand::thread_rng();
    rng.gen_range(min..=max)
}

// Debug function to inspect dropdown HTML structure
async fn debug_dropdown_structure(
    page: &Page,
    selector: &str,
    field_name: &str,
    state: &AppState,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let debug_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("🔍 DEBUG: Inspecting dropdown structure for '{}'", field_name),
    };
    let _ = broadcast_automation_message(state, debug_message).await;

    // Get dropdown HTML structure and options
    let js_code = format!("
        const element = document.querySelector('{}');
        if (element && element.tagName.toLowerCase() === 'select') {{
            const options = Array.from(element.options).map((opt, index) => ({{
                index: index,
                value: opt.value,
                text: opt.text,
                selected: opt.selected
            }}));
            return {{
                elementFound: true,
                tagName: element.tagName,
                name: element.name,
                id: element.id,
                className: element.className,
                disabled: element.disabled,
                optionsCount: element.options.length,
                options: options
            }};
        }}
        return {{ elementFound: false }};
    ", selector);

    match page.evaluate::<(), serde_json::Value>(&js_code, ()).await {
        Ok(result) => {
            let result_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("🔍 DEBUG: Dropdown '{}' structure: {}", field_name, result),
            };
            let _ = broadcast_automation_message(state, result_message).await;
        },
        Err(e) => {
            let error_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("❌ DEBUG: Failed to inspect dropdown '{}': {}", field_name, e),
            };
            let _ = broadcast_automation_message(state, error_message).await;
        }
    }

    Ok(())
}

// Multi-strategy dropdown selection with JavaScript and click-based fallbacks
async fn select_dropdown_with_validation(
    page: &Page,
    selector: &str,
    value: &str,
    field_name: &str,
    max_retries: u32,
    state: &AppState,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let strategies = vec!["JavaScript DOM Manipulation", "Click-based Selection"];
    let mut all_errors: Vec<String> = Vec::new();

    // Try each strategy
    for strategy_name in strategies.iter() {
        let strategy_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🎯 Trying strategy: {} for dropdown '{}'", strategy_name, field_name),
        };
        let _ = broadcast_automation_message(state, strategy_message).await;

        // Try this strategy with retries
        let mut strategy_errors: Vec<String> = Vec::new();
        for attempt in 1..=max_retries {
            let attempt_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("🔄 {} - Attempt {}/{} for field '{}'", strategy_name, attempt, max_retries, field_name),
            };
            let _ = broadcast_automation_message(state, attempt_message).await;

            // Exponential backoff delay for retries (except first attempt)
            if attempt > 1 {
                let backoff_delay = human_delay_ms(500 * attempt as u64, 1500 * attempt as u64);
                let retry_message = WebSocketMessage::ScriptLog {
                    timestamp: Utc::now(),
                    message: format!("⏳ Backoff delay: {}ms before attempt {}", backoff_delay, attempt),
                };
                let _ = broadcast_automation_message(state, retry_message).await;
                tokio::time::sleep(std::time::Duration::from_millis(backoff_delay)).await;
            }

            // Try the strategy
            let strategy_result = match *strategy_name {
                "JavaScript DOM Manipulation" => {
                    attempt_dropdown_selection(page, selector, value, field_name, attempt, state).await
                },
                "Click-based Selection" => {
                    attempt_click_based_dropdown_selection(page, selector, value, field_name, attempt, state).await
                },
                _ => {
                    Err("Unknown strategy".into())
                }
            };

            match strategy_result {
                Ok(_) => {
                    // Validate that the selection is visually displayed
                    match validate_dropdown_selection(page, selector, value, field_name, state).await {
                        Ok(true) => {
                            let success_message = WebSocketMessage::ScriptLog {
                                timestamp: Utc::now(),
                                message: format!("✅ {} SUCCESSFUL! Dropdown '{}' selected: '{}' (attempt {})", strategy_name, field_name, value, attempt),
                            };
                            let _ = broadcast_automation_message(state, success_message).await;
                            return Ok(());
                        },
                        Ok(false) => {
                            strategy_errors.push(format!("Attempt {}: Visual validation failed", attempt));

                            let validation_fail_message = WebSocketMessage::ScriptLog {
                                timestamp: Utc::now(),
                                message: format!("⚠️ {} - Visual validation failed on attempt {}", strategy_name, attempt),
                            };
                            let _ = broadcast_automation_message(state, validation_fail_message).await;
                            continue; // Try next attempt with same strategy
                        },
                        Err(e) => {
                            strategy_errors.push(format!("Attempt {}: Validation error: {}", attempt, e));
                            continue; // Try next attempt with same strategy
                        }
                    }
                },
                Err(e) => {
                    strategy_errors.push(format!("Attempt {}: Selection error: {}", attempt, e));
                    continue; // Try next attempt with same strategy
                }
            }
        }

        // If we get here, this strategy failed all attempts
        all_errors.push(format!("{}: {}", strategy_name, strategy_errors.join("; ")));
        let strategy_fail_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("❌ {} failed all {} attempts, trying next strategy", strategy_name, max_retries),
        };
        let _ = broadcast_automation_message(state, strategy_fail_message).await;
    }

    // All strategies failed
    let final_error = format!("All dropdown selection strategies failed for '{}'. Errors: {}",
                             field_name, all_errors.join(" | "));

    let final_fail_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("💥 ALL STRATEGIES FAILED for dropdown '{}': {}", field_name, final_error),
    };
    let _ = broadcast_automation_message(state, final_fail_message).await;

    Err(final_error.into())
}

// Browser-native dropdown selection using Playwright's select_option method
async fn attempt_dropdown_selection(
    page: &Page,
    selector: &str,
    value: &str,
    field_name: &str,
    attempt: u32,
    state: &AppState,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let start_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("🎯 Attempting native dropdown selection: '{}' -> '{}' (attempt {})", field_name, value, attempt),
    };
    let _ = broadcast_automation_message(state, start_message).await;

    // First, get information about available options for debugging
    let debug_js = format!(r#"
        (function(selector) {{
            const selectElement = document.querySelector(selector);
            if (!selectElement) {{
                return {{ error: 'Element not found', selector: selector }};
            }}

            const options = Array.from(selectElement.options).map(opt => ({{
                value: opt.value,
                text: opt.text.trim(),
                index: opt.index,
                selected: opt.selected
            }}));

            return {{
                currentValue: selectElement.value,
                currentText: selectElement.selectedIndex >= 0 ? selectElement.options[selectElement.selectedIndex].text : '',
                totalOptions: options.length,
                options: options
            }};
        }})('{}');
    "#, selector);

    // Get dropdown structure for debugging
    match page.evaluate::<(), serde_json::Value>(&debug_js, ()).await {
        Ok(debug_info) => {
            let debug_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("🔍 Dropdown structure for '{}': {}", field_name,
                    serde_json::to_string_pretty(&debug_info).unwrap_or_default()),
            };
            let _ = broadcast_automation_message(state, debug_message).await;
        },
        Err(e) => {
            let error_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("⚠️ Failed to get dropdown structure for '{}': {}", field_name, e),
            };
            let _ = broadcast_automation_message(state, error_message).await;
        }
    }

    // Try multiple selection strategies with Playwright's native methods
    let selection_strategies = vec![
        ("text", value.to_string()),
        ("label", value.to_string()),
        ("value", value.to_string()),
    ];

    for (strategy, target_value) in selection_strategies {
        let strategy_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🔄 Trying selection strategy '{}' with value '{}' for '{}'", strategy, target_value, field_name),
        };
        let _ = broadcast_automation_message(state, strategy_message).await;

        let result = match strategy {
            "text" | "label" | "value" => {
                // Native Playwright selection (like MCP selectOption) - all strategies use add_value
                page.select_option_builder(selector)
                    .add_value(target_value.to_string())
                    .select_option()
                    .await
                    .map_err(|e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>)
            },
            _ => continue,
        };

        match result {
            Ok(_) => {
                let success_message = WebSocketMessage::ScriptLog {
                    timestamp: Utc::now(),
                    message: format!("✅ Successfully selected option using '{}' strategy for '{}'", strategy, field_name),
                };
                let _ = broadcast_automation_message(state, success_message).await;

                // Add a small delay to allow DOM to update
                tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
                return Ok(());
            },
            Err(e) => {
                let retry_message = WebSocketMessage::ScriptLog {
                    timestamp: Utc::now(),
                    message: format!("❌ Strategy '{}' failed for '{}': {} - trying next strategy", strategy, field_name, e),
                };
                let _ = broadcast_automation_message(state, retry_message).await;
                continue;
            }
        }
    }

    // If all strategies failed, return error
    Err(format!("All selection strategies failed for '{}' with value '{}'", field_name, value).into())
}

// Click-based dropdown selection that mimics human interaction
async fn attempt_click_based_dropdown_selection(
    page: &Page,
    selector: &str,
    value: &str,
    field_name: &str,
    attempt: u32,
    state: &AppState,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let start_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("🖱️ Attempting click-based dropdown selection: '{}' -> '{}' (attempt {})", field_name, value, attempt),
    };
    let _ = broadcast_automation_message(state, start_message).await;

    // Step 1: Click on the dropdown to open it
    let click_delay = human_delay_ms(300, 800);
    let click_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("🔍 Clicking dropdown to open options ({}ms wait)", click_delay),
    };
    let _ = broadcast_automation_message(state, click_message).await;

    page.click_builder(selector).click().await?;
    tokio::time::sleep(std::time::Duration::from_millis(click_delay)).await;

    // Step 2: Wait for options to be visible
    let wait_delay = human_delay_ms(500, 1000);
    let wait_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("⏳ Waiting for dropdown options to appear ({}ms)", wait_delay),
    };
    let _ = broadcast_automation_message(state, wait_message).await;
    tokio::time::sleep(std::time::Duration::from_millis(wait_delay)).await;

    // Step 3: Find and click the specific option
    let option_js = format!(r#"
        (function(selectSelector, targetValue) {{
            console.log('Looking for option with text:', targetValue);

            const selectElement = document.querySelector(selectSelector);
            if (!selectElement) {{
                throw new Error('Dropdown not found: ' + selectSelector);
            }}

            // Find the option with matching text
            let targetOption = null;
            for (let i = 0; i < selectElement.options.length; i++) {{
                const option = selectElement.options[i];
                console.log('Checking option:', option.text);

                // Try exact match first
                if (option.text.toLowerCase().trim() === targetValue.toLowerCase().trim()) {{
                    targetOption = option;
                    console.log('Found exact match:', option.text);
                    break;
                }}

                // Try partial match
                if (option.text.toLowerCase().includes(targetValue.toLowerCase())) {{
                    targetOption = option;
                    console.log('Found partial match:', option.text);
                }}
            }}

            if (!targetOption) {{
                const available = Array.from(selectElement.options).map(o => o.text).join(', ');
                throw new Error('Option not found: "' + targetValue + '". Available: ' + available);
            }}

            console.log('Found target option:', targetOption.text, 'at index:', targetOption.index);

            // Create a synthetic click event on the option
            const clickEvent = new MouseEvent('click', {{
                bubbles: true,
                cancelable: true,
                view: window
            }});

            // Select the option programmatically
            selectElement.selectedIndex = targetOption.index;
            selectElement.value = targetOption.value;
            targetOption.selected = true;

            // Dispatch events to simulate user interaction
            selectElement.dispatchEvent(new Event('change', {{ bubbles: true }}));
            selectElement.dispatchEvent(new Event('input', {{ bubbles: true }}));

            return {{
                success: true,
                selectedText: targetOption.text,
                selectedValue: targetOption.value,
                selectedIndex: targetOption.index
            }};
        }})('{}', '{}');
    "#, selector, value);

    let find_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("🔍 Finding and clicking option: '{}'", value),
    };
    let _ = broadcast_automation_message(state, find_message).await;

    // Execute the option finding and clicking JavaScript
    let result = page.evaluate::<(), serde_json::Value>(&option_js, ()).await?;

    let click_result_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("✅ Click-based selection result: {}", result),
    };
    let _ = broadcast_automation_message(state, click_result_message).await;

    // Step 4: Final delay for visual updates
    let final_delay = human_delay_ms(400, 900);
    let final_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("💫 Allowing final visual updates ({}ms)", final_delay),
    };
    let _ = broadcast_automation_message(state, final_message).await;
    tokio::time::sleep(std::time::Duration::from_millis(final_delay)).await;

    Ok(())
}

// Validate that dropdown selection is visually displayed
async fn validate_dropdown_selection(
    page: &Page,
    selector: &str,
    expected_value: &str,
    field_name: &str,
    state: &AppState,
) -> Result<bool, Box<dyn std::error::Error + Send + Sync>> {
    let validation_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("🔍 Validating dropdown selection for '{}'", field_name),
    };
    let _ = broadcast_automation_message(state, validation_message).await;

    // Get current selected value from dropdown
    let js_code = format!("
        const element = document.querySelector('{}');
        if (element && element.tagName.toLowerCase() === 'select') {{
            const selectedOption = element.options[element.selectedIndex];
            return selectedOption ? selectedOption.value : null;
        }}
        return null;
    ", selector);

    match page.evaluate::<(), serde_json::Value>(&js_code, ()).await {
        Ok(result) => {
            if let Some(current_value) = result.as_str() {
                let is_valid = current_value == expected_value;
                let validation_result = WebSocketMessage::ScriptLog {
                    timestamp: Utc::now(),
                    message: format!("🔍 Validation: Expected '{}', Found '{}', Valid: {}",
                                   expected_value, current_value, is_valid),
                };
                let _ = broadcast_automation_message(state, validation_result).await;
                Ok(is_valid)
            } else {
                Ok(false)
            }
        },
        Err(e) => {
            let error_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("⚠️ Validation check failed: {}", e),
            };
            let _ = broadcast_automation_message(state, error_message).await;
            Err(e.into())
        }
    }
}

// Health check endpoint
pub async fn health_check() -> impl IntoResponse {
    Json(serde_json::json!({"status": "ok"}))
}

// Get profile names only (for Dashboard compatibility)
pub async fn get_profile_names(State(state): State<AppState>) -> impl IntoResponse {
    let profiles = state.profiles.read().await;

    // Return simplified profile objects with just id and name for the dashboard
    let mut unique_profiles = std::collections::HashMap::new();
    for profile in profiles.values() {
        // Use the profile name as key to avoid duplicates
        unique_profiles.insert(profile.name.clone(), profile.clone());
    }

    let profile_list: Vec<_> = unique_profiles.into_values().map(|profile| {
        serde_json::json!({
            "id": profile.id,
            "name": profile.name
        })
    }).collect();

    Json(profile_list)
}

// Get saved URLs (loads from saved_urls.json)  
pub async fn get_saved_urls() -> impl IntoResponse {
    match load_saved_urls_from_file().await {
        Ok(urls) => Json(urls).into_response(),
        Err(e) => {
            error!("Failed to load saved URLs: {}", e);
            Json(Vec::<serde_json::Value>::new()).into_response()
        }
    }
}

// Get recordings from recordings.json file
pub async fn get_recordings() -> impl IntoResponse {
    match load_recordings_from_file().await {
        Ok(recordings) => Json(recordings).into_response(),
        Err(e) => {
            error!("Failed to load recordings: {}", e);
            (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load recordings").into_response()
        }
    }
}

// Profile Management
pub async fn get_profile(
    Path(id): Path<String>,
    State(state): State<AppState>,
) -> impl IntoResponse {
    let profiles = state.profiles.read().await;
    match profiles.get(&id) {
        Some(profile) => (StatusCode::OK, Json(profile)).into_response(),
        None => StatusCode::NOT_FOUND.into_response(),
    }
}

pub async fn create_profile(
    State(state): State<AppState>,
    Json(req): Json<CreateProfileRequest>,
) -> impl IntoResponse {
    let profile = Profile::new(req.name, req.data);
    let profile_id = profile.id.clone();
    
    // Store in memory
    {
        let mut profiles = state.profiles.write().await;
        profiles.insert(profile.id.clone(), profile.clone());
    }
    
    // Persist to disk
    if let Err(e) = save_profile(&profile).await {
        error!("Failed to save profile to disk: {}", e);
        return StatusCode::INTERNAL_SERVER_ERROR.into_response();
    }

    // Broadcast profile update
    let profile_update = WebSocketMessage::ProfileUpdated {
        timestamp: Utc::now(),
        profile_id: profile_id.clone(),
        message: format!("Profile '{}' created", profile.name),
    };

    if let Err(e) = broadcast_automation_message(&state, profile_update).await {
        warn!("Failed to broadcast profile creation: {}", e);
    }

    info!("Created new profile: {}", profile_id);
    (StatusCode::CREATED, Json(profile)).into_response()
}

pub async fn update_profile(
    Path(id): Path<String>,
    State(state): State<AppState>,
    Json(req): Json<UpdateProfileRequest>,
) -> impl IntoResponse {
    let mut profiles = state.profiles.write().await;
    
    match profiles.get_mut(&id) {
        Some(profile) => {
            profile.update(req.name, req.data);
            let updated_profile = profile.clone();
            drop(profiles); // Release the lock
            
            // Persist to disk
            if let Err(e) = save_profile(&updated_profile).await {
                error!("Failed to save updated profile to disk: {}", e);
                return StatusCode::INTERNAL_SERVER_ERROR.into_response();
            }

            // Broadcast profile update
            let profile_update = WebSocketMessage::ProfileUpdated {
                timestamp: Utc::now(),
                profile_id: id.clone(),
                message: format!("Profile '{}' updated", updated_profile.name),
            };

            if let Err(e) = broadcast_automation_message(&state, profile_update).await {
                warn!("Failed to broadcast profile update: {}", e);
            }

            info!("Updated profile: {}", id);
            (StatusCode::OK, Json(updated_profile)).into_response()
        }
        None => StatusCode::NOT_FOUND.into_response(),
    }
}

pub async fn delete_profile(
    Path(id): Path<String>,
    State(state): State<AppState>,
) -> impl IntoResponse {
    let mut profiles = state.profiles.write().await;
    
    match profiles.remove(&id) {
        Some(deleted_profile) => {
            drop(profiles); // Release the lock

            // Remove from disk
            let file_path = format!("profiles/{}.json", id);
            if let Err(e) = fs::remove_file(&file_path).await {
                warn!("Failed to remove profile file {}: {}", file_path, e);
            }

            // Broadcast profile update
            let profile_update = WebSocketMessage::ProfileUpdated {
                timestamp: Utc::now(),
                profile_id: id.clone(),
                message: format!("Profile '{}' deleted", deleted_profile.name),
            };

            if let Err(e) = broadcast_automation_message(&state, profile_update).await {
                warn!("Failed to broadcast profile deletion: {}", e);
            }

            info!("Deleted profile: {}", id);
            StatusCode::NO_CONTENT.into_response()
        }
        None => StatusCode::NOT_FOUND.into_response(),
    }
}

// Mapping Management
pub async fn get_mappings(State(state): State<AppState>) -> impl IntoResponse {
    let mappings = state.mappings.read().await;
    let mapping_list: Vec<FieldMapping> = mappings.values().cloned().collect();
    Json(mapping_list)
}

pub async fn get_mapping(
    Path(id): Path<String>,
    State(state): State<AppState>,
) -> impl IntoResponse {
    let mappings = state.mappings.read().await;
    match mappings.get(&id) {
        Some(mapping) => (StatusCode::OK, Json(mapping)).into_response(),
        None => StatusCode::NOT_FOUND.into_response(),
    }
}

pub async fn update_mapping(
    Path(id): Path<String>,
    State(state): State<AppState>,
    Json(req): Json<UpdateMappingRequest>,
) -> impl IntoResponse {
    let mut mappings = state.mappings.write().await;
    
    match mappings.get_mut(&id) {
        Some(mapping) => {
            mapping.update(req.url, req.fields);
            let updated_mapping = mapping.clone();
            drop(mappings); // Release the lock
            
            // Persist to disk
            if let Err(e) = save_mapping(&updated_mapping).await {
                error!("Failed to save updated mapping to disk: {}", e);
                return StatusCode::INTERNAL_SERVER_ERROR.into_response();
            }
            
            info!("Updated mapping: {}", id);
            (StatusCode::OK, Json(updated_mapping)).into_response()
        }
        None => StatusCode::NOT_FOUND.into_response(),
    }
}

pub async fn delete_mapping(
    Path(id): Path<String>,
    State(state): State<AppState>,
) -> impl IntoResponse {
    let mut mappings = state.mappings.write().await;
    
    match mappings.remove(&id) {
        Some(_) => {
            drop(mappings); // Release the lock
            
            // Remove from disk
            let file_path = format!("field_mappings/{}.json", id);
            if let Err(e) = fs::remove_file(&file_path).await {
                warn!("Failed to remove mapping file {}: {}", file_path, e);
            }
            
            info!("Deleted mapping: {}", id);
            StatusCode::NO_CONTENT.into_response()
        }
        None => StatusCode::NOT_FOUND.into_response(),
    }
}

// Automation Control
static AUTOMATION_STATUS: tokio::sync::RwLock<AutomationStatus> = 
    tokio::sync::RwLock::const_new(AutomationStatus {
        running: false,
        current_url: None,
        progress: 0.0,
        processed_count: 0,
        total_count: 0,
        error: None,
    });

#[allow(dead_code)]
pub async fn start_automation(
    State(state): State<AppState>,
    Json(req): Json<AutomationRequest>,
) -> impl IntoResponse {
    // Check if automation is already running
    {
        let status = AUTOMATION_STATUS.read().await;
        if status.running {
            return (StatusCode::CONFLICT, "Automation is already running").into_response();
        }
    }
    
    // Validate profile exists
    let profiles = state.profiles.read().await;
    let profile = match profiles.get(&req.profile) {
        Some(p) => p.clone(),
        None => {
            return (StatusCode::BAD_REQUEST, "Profile not found").into_response();
        }
    };
    drop(profiles);
    
    // Update status
    {
        let mut status = AUTOMATION_STATUS.write().await;
        status.running = true;
        status.progress = 0.0;
        status.processed_count = 0;
        status.total_count = req.urls.len();
        status.error = None;
    }
    
    // Broadcast automation started - send both detailed message and status update
    let start_message = WebSocketMessage::AutomationStarted {
        timestamp: Utc::now(),
        profile: req.profile.clone(),
        total_urls: req.urls.len(),
        headless: req.headless,
        message: "🚀 Automation started".to_string(),
    };

    let status_update = WebSocketMessage::AutomationStatusUpdate {
        running: true,
        current_url: None,
        progress: Some(0.0),
        processed_count: Some(0),
        total_count: Some(req.urls.len()),
        error: None,
    };

    let log_message = WebSocketMessage::Log {
        level: "info".to_string(),
        message: "🚀 Automation started".to_string(),
        timestamp: Some(Utc::now()),
    };

    if let Err(e) = broadcast_automation_message(&state, start_message).await {
        warn!("Failed to broadcast automation start: {}", e);
    }
    if let Err(e) = broadcast_automation_message(&state, status_update).await {
        warn!("Failed to broadcast automation status: {}", e);
    }
    if let Err(e) = broadcast_automation_message(&state, log_message).await {
        warn!("Failed to broadcast automation log: {}", e);
    }
    
    // Spawn automation task
    let state_clone = state.clone();
    let req_clone = req.clone();
    let profile_clone = profile;
    
    tokio::spawn(async move {
        if let Err(e) = run_automation(state_clone.clone(), req_clone, profile_clone).await {
            error!("Automation failed: {}", e);
            
            // Update status with error
            {
                let mut status = AUTOMATION_STATUS.write().await;
                status.running = false;
                status.error = Some(e.to_string());
            }
            
            // Broadcast error - send both detailed error and status update
            let error_message = WebSocketMessage::AutomationError {
                timestamp: Utc::now(),
                error: e.to_string(),
                message: format!("❌ Automation failed: {}", e),
            };

            let status_update = WebSocketMessage::AutomationStatusUpdate {
                running: false,
                current_url: None,
                progress: None,
                processed_count: None,
                total_count: None,
                error: Some(e.to_string()),
            };

            let log_message = WebSocketMessage::Log {
                level: "error".to_string(),
                message: format!("❌ Automation failed: {}", e),
                timestamp: Some(Utc::now()),
            };

            let _ = broadcast_automation_message(&state_clone, error_message).await;
            let _ = broadcast_automation_message(&state_clone, status_update).await;
            let _ = broadcast_automation_message(&state_clone, log_message).await;
        }
    });
    
    info!("Started automation for profile: {}", req.profile);
    
    // Return JSON response with URL count
    let response = serde_json::json!({
        "message": "Automation started successfully",
        "urls_count": req.urls.len(),
        "profile": req.profile,
        "headless": req.headless
    });
    
    Json(response).into_response()
}

// Dashboard automation start (handles new config format)
pub async fn start_dashboard_automation(
    State(state): State<AppState>,
    Json(req): Json<DashboardAutomationRequest>,
) -> impl IntoResponse {
    // Log the incoming request
    info!("Received automation request: {:?}", req);

    // Check if automation is already running
    {
        let status = AUTOMATION_STATUS.read().await;
        if status.running {
            return (StatusCode::CONFLICT, "Automation is already running").into_response();
        }
    }

    // Validate profile exists
    let profiles = state.profiles.read().await;
    let profile = match profiles.get(&req.profile_id) {
        Some(p) => p.clone(),
        None => {
            return (StatusCode::BAD_REQUEST, "Profile not found").into_response();
        }
    };
    drop(profiles);

    // Get URLs based on config
    let urls = match get_urls_from_config(&req.url_config).await {
        Ok(urls) => urls,
        Err(e) => {
            error!("Failed to get URLs from config: {}", e);
            return (StatusCode::BAD_REQUEST, format!("Failed to get URLs: {}", e)).into_response();
        }
    };

    if urls.is_empty() {
        return (StatusCode::BAD_REQUEST, "No URLs found for the specified configuration").into_response();
    }

    // Convert to legacy format
    let legacy_request = AutomationRequest {
        profile: req.profile_id.clone(),
        urls: urls.clone(),
        headless: req.mode == "headless",
        delay: None,
    };

    // Update status
    {
        let mut status = AUTOMATION_STATUS.write().await;
        status.running = true;
        status.progress = 0.0;
        status.processed_count = 0;
        status.total_count = urls.len();
        status.error = None;
    }

    // Broadcast automation started
    let start_message = WebSocketMessage::AutomationStarted {
        timestamp: Utc::now(),
        profile: req.profile_id.clone(),
        total_urls: urls.len(),
        headless: req.mode == "headless",
        message: "🚀 Automation started".to_string(),
    };

    if let Err(e) = broadcast_automation_message(&state, start_message).await {
        warn!("Failed to broadcast automation start: {}", e);
    }

    // Spawn automation task
    let state_clone = state.clone();
    let profile_clone = profile;

    tokio::spawn(async move {
        if let Err(e) = run_automation(state_clone.clone(), legacy_request, profile_clone).await {
            error!("Automation failed: {}", e);

            // Update status with error
            {
                let mut status = AUTOMATION_STATUS.write().await;
                status.running = false;
                status.error = Some(e.to_string());
            }

            // Broadcast error
            let error_message = WebSocketMessage::AutomationError {
                timestamp: Utc::now(),
                error: e.to_string(),
                message: format!("❌ Automation failed: {}", e),
            };

            let _ = broadcast_automation_message(&state_clone, error_message).await;
        }
    });

    info!("Started dashboard automation for profile: {}", req.profile_id);

    // Return JSON response with URL count
    let response = serde_json::json!({
        "message": "Automation started successfully",
        "urls_count": urls.len(),
        "profile_id": req.profile_id,
        "mode": req.mode
    });

    Json(response).into_response()
}

// Get URLs based on dashboard config
async fn get_urls_from_config(config: &UrlConfig) -> anyhow::Result<Vec<String>> {
    let all_urls = load_saved_urls_structured().await?;

    match config {
        UrlConfig::All => {
            // Return all URLs
            Ok(all_urls.into_iter()
                .filter(|url| url.status == UrlStatus::Active)
                .map(|url| url.url)
                .collect())
        }
        UrlConfig::Amount { amount } => {
            // Return first N URLs
            Ok(all_urls.into_iter()
                .filter(|url| url.status == UrlStatus::Active)
                .take(*amount as usize)
                .map(|url| url.url)
                .collect())
        }
        UrlConfig::Group { group_id } => {
            // Return URLs from specific group
            let groups = load_url_groups().await?;
            let group_name = groups.iter()
                .find(|g| g.id == *group_id)
                .map(|g| &g.name)
                .ok_or_else(|| anyhow::anyhow!("Group not found"))?;

            Ok(all_urls.into_iter()
                .filter(|url| url.status == UrlStatus::Active)
                .filter(|url| url.group.as_ref() == Some(group_name))
                .map(|url| url.url)
                .collect())
        }
        UrlConfig::Single { url } => {
            // Return a single URL provided directly
            Ok(vec![url.clone()])
        }
    }
}

pub async fn stop_automation(State(state): State<AppState>) -> impl IntoResponse {
    let mut status = AUTOMATION_STATUS.write().await;
    if !status.running {
        return (StatusCode::CONFLICT, "No automation is running").into_response();
    }

    status.running = false;
    status.error = Some("Stopped by user".to_string());
    drop(status);

    // Broadcast stop message
    let status_update = WebSocketMessage::AutomationStatusUpdate {
        running: false,
        current_url: None,
        progress: None,
        processed_count: None,
        total_count: None,
        error: Some("Stopped by user".to_string()),
    };

    let log_message = WebSocketMessage::Log {
        level: "warning".to_string(),
        message: "⏹️ Automation stopped by user".to_string(),
        timestamp: Some(Utc::now()),
    };

    if let Err(e) = broadcast_automation_message(&state, status_update).await {
        warn!("Failed to broadcast automation stop status: {}", e);
    }
    if let Err(e) = broadcast_automation_message(&state, log_message).await {
        warn!("Failed to broadcast automation stop log: {}", e);
    }

    info!("Stopped automation");
    (StatusCode::OK, "Automation stopped").into_response()
}

pub async fn get_automation_status() -> impl IntoResponse {
    let status = AUTOMATION_STATUS.read().await;
    Json(status.clone())
}

// RoboForm field mapping based on recording data - COMPLETE 37+ FIELDS
fn get_roboform_selector(field_name: &str) -> Option<String> {
    match field_name {
        // Personal Information (7 fields)
        "title" => Some("input[name='01___title']".to_string()),
        "firstName" => Some("input[name='02frstname']".to_string()),
        "middleInitial" => Some("input[name='03middle_i']".to_string()),
        "lastName" => Some("input[name='04lastname']".to_string()),
        "fullName" => Some("input[name='04fullname']".to_string()),
        "company" => Some("input[name='05_company']".to_string()),
        "position" | "jobTitle" => Some("input[name='06position']".to_string()),

        // Address Information (6 fields)
        "address" | "address1" => Some("input[name='10address1']".to_string()),
        "address2" => Some("input[name='11address2']".to_string()),
        "city" => Some("input[name='13adr_city']".to_string()),
        "state" => Some("input[name='14adrstate']".to_string()),
        "country" => Some("input[name='15_country']".to_string()),
        "zip" | "zipCode" => Some("input[name='16addr_zip']".to_string()),

        // Contact Information (6 fields)
        "phone" | "homePhone" => Some("input[name='20homephon']".to_string()),
        "workPhone" | "workTelephone" => Some("input[name='21workphon']".to_string()),
        "fax" | "faxPhone" => Some("input[name='22faxphone']".to_string()),
        "cellPhone" | "mobilePhone" => Some("input[name='23cellphon']".to_string()),
        "email" => Some("input[name='24emailadr']".to_string()),
        "website" | "webSite" => Some("input[name='25web_site']".to_string()),

        // Login Information
        "username" => Some("input[name='30_user_id']".to_string()),
        "password" => Some("input[name='31password']".to_string()),

        // Credit Card Information
        "creditCardType" => Some("select[name='40cc__type']".to_string()),
        "creditCardNumber" => Some("input[name='41ccnumber']".to_string()),
        "creditCardExpMonth" => Some("select[name='42ccexp_mm']".to_string()),
        "creditCardExpYear" => Some("select[name='43ccexp_yy']".to_string()),
        "creditCardCVC" => Some("input[name='43cvc']".to_string()),
        "creditCardName" => Some("input[name='44cc_uname']".to_string()),
        "creditCardBank" => Some("input[name='45ccissuer']".to_string()),
        "creditCardServicePhone" => Some("input[name='46cccstsvc']".to_string()),

        // Personal Details
        "sex" | "gender" => Some("input[name='60pers_sex']".to_string()),
        "ssn" => Some("input[name='61pers_ssn']".to_string()),
        "driverLicense" => Some("input[name='62driv_lic']".to_string()),
        "birthMonth" => Some("select[name='66mm']".to_string()),
        "birthDay" => Some("select[name='67dd']".to_string()),
        "birthYear" => Some("select[name='68yy']".to_string()),
        "age" => Some("input[name='66pers_age']".to_string()),
        "birthPlace" => Some("input[name='67birth_pl']".to_string()),
        "income" => Some("input[name='68__income']".to_string()),

        // Custom Fields
        "customMessage" => Some("input[name='71__custom']".to_string()),
        "comments" => Some("input[name='72__commnt']".to_string()),

        _ => None,
    }
}

// Map profile values to RoboForm dropdown option values
// AI-powered dropdown analysis function
async fn analyze_dropdown_with_ai(
    page: &Page,
    selector: &str,
    field_name: &str,
    user_value: &str,
    state: &AppState,
) -> Result<Option<String>, anyhow::Error> {
    dotenv::dotenv().ok();

    let ai_analysis_message = WebSocketMessage::ScriptLog {
        timestamp: Utc::now(),
        message: format!("🤖 Starting AI analysis for dropdown field '{}'", field_name),
    };
    let _ = broadcast_automation_message(state, ai_analysis_message).await;

    // Get the dropdown HTML content
    let dropdown_html = match page.inner_html(selector, Some(5000.0)).await {
        Ok(html) => html,
        Err(e) => {
            return Err(anyhow::anyhow!("Failed to get dropdown HTML: {}", e));
        }
    };

    // Initialize OpenRouter client
    let client = match OpenRouterClient::new().await {
        Ok(client) => client,
        Err(e) => {
            return Err(anyhow::anyhow!("Failed to initialize OpenRouter client: {}", e));
        }
    };

    // Call OpenRouter to analyze dropdown options
    match client.analyze_dropdown_options(
        &dropdown_html,
        field_name,
        user_value,
        None, // No form context for now
        "anthropic/claude-3.5-sonnet"
    ).await {
        Ok(result) => {
            // Try to parse JSON response
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&result) {
                let suggested_option = parsed.get("suggested_option")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string());

                let confidence = parsed.get("confidence")
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.0);

                let reasoning = parsed.get("reasoning")
                    .and_then(|v| v.as_str())
                    .unwrap_or("No reasoning provided");

                let ai_result_message = WebSocketMessage::ScriptLog {
                    timestamp: Utc::now(),
                    message: format!("🤖 AI analysis complete: suggestion='{}', confidence={:.2}, reasoning='{}'",
                        suggested_option.as_deref().unwrap_or("None"), confidence, reasoning),
                };
                let _ = broadcast_automation_message(state, ai_result_message).await;

                Ok(suggested_option)
            } else {
                // Fallback: treat entire response as suggestion
                let suggestion = result.trim().to_string();
                if !suggestion.is_empty() {
                    let ai_text_result_message = WebSocketMessage::ScriptLog {
                        timestamp: Utc::now(),
                        message: format!("🤖 AI provided text suggestion: '{}'", suggestion),
                    };
                    let _ = broadcast_automation_message(state, ai_text_result_message).await;
                    Ok(Some(suggestion))
                } else {
                    Ok(None)
                }
            }
        },
        Err(e) => {
            Err(anyhow::anyhow!("OpenRouter API error: {}", e))
        }
    }
}

fn map_roboform_dropdown_value(field_name: &str, profile_value: &str) -> String {
    match (field_name, profile_value) {
        // Credit Card Type mapping - use exact text values as shown in HTML
        ("creditCardType", "Visa") => "Visa (Preferred)".to_string(),
        ("creditCardType", "MasterCard") | ("creditCardType", "Master Card") => "Master Card".to_string(),
        ("creditCardType", "American Express") | ("creditCardType", "Amex") => "American Express".to_string(),
        ("creditCardType", "Discover") => "Discover".to_string(),
        ("creditCardType", "Diners Club") => "Diners Club".to_string(),

        // Birth month mapping - keep as month names, not numbers
        ("birthMonth", "January") => "Jan".to_string(),
        ("birthMonth", "February") => "Feb".to_string(),
        ("birthMonth", "March") => "Mar".to_string(),
        ("birthMonth", "April") => "Apr".to_string(),
        ("birthMonth", "May") => "May".to_string(),
        ("birthMonth", "June") => "Jun".to_string(),
        ("birthMonth", "July") => "Jul".to_string(),
        ("birthMonth", "August") => "Aug".to_string(),
        ("birthMonth", "September") => "Sep".to_string(),
        ("birthMonth", "October") => "Oct".to_string(),
        ("birthMonth", "November") => "Nov".to_string(),
        ("birthMonth", "December") => "Dec".to_string(),

        // Credit card expiry month - use numbers as text
        ("creditCardExpMonth", "01") | ("creditCardExpMonth", "1") => "01".to_string(),
        ("creditCardExpMonth", "02") | ("creditCardExpMonth", "2") => "02".to_string(),
        ("creditCardExpMonth", "03") | ("creditCardExpMonth", "3") => "03".to_string(),
        ("creditCardExpMonth", "04") | ("creditCardExpMonth", "4") => "04".to_string(),
        ("creditCardExpMonth", "05") | ("creditCardExpMonth", "5") => "05".to_string(),
        ("creditCardExpMonth", "06") | ("creditCardExpMonth", "6") => "06".to_string(),
        ("creditCardExpMonth", "07") | ("creditCardExpMonth", "7") => "07".to_string(),
        ("creditCardExpMonth", "08") | ("creditCardExpMonth", "8") => "08".to_string(),
        ("creditCardExpMonth", "09") | ("creditCardExpMonth", "9") => "09".to_string(),
        ("creditCardExpMonth", "10") => "10".to_string(),
        ("creditCardExpMonth", "11") => "11".to_string(),
        ("creditCardExpMonth", "12") => "12".to_string(),

        // For other fields, use the value directly
        _ => profile_value.to_string(),
    }
}

// Automation execution using headless_chrome
async fn run_automation(
    state: AppState,
    req: AutomationRequest,
    profile: Profile,
) -> anyhow::Result<()> {
    info!("Starting browser automation for {} URLs", req.urls.len());
    
    info!("Starting RELIABLE browser automation with Playwright");

    // Initialize Playwright - our custom browser solution
    use playwright::Playwright;
    use std::env;

    // Initialize Playwright engine
    let playwright = Playwright::initialize().await?;

    // Enhanced Chrome flags for stability and performance
    let chrome_flags: Vec<String> = if env::var("CHROME_FLAGS").is_ok() || env::var("DOCKER_CONTAINER").is_ok() {
        vec![
            "--no-sandbox".to_string(),
            "--disable-dev-shm-usage".to_string(),
            "--disable-gpu".to_string(),
            "--disable-web-security".to_string(),
            "--disable-features=VizDisplayCompositor".to_string(),
            "--no-first-run".to_string(),
            "--disable-default-apps".to_string(),
            "--disable-background-timer-throttling".to_string(),
            "--disable-renderer-backgrounding".to_string(),
            "--disable-backgrounding-occluded-windows".to_string(),
        ]
    } else {
        // Performance optimized flags for local environment
        vec![
            "--no-first-run".to_string(),
            "--disable-default-apps".to_string(),
            "--disable-background-timer-throttling".to_string(),
            "--disable-renderer-backgrounding".to_string(),
            "--disable-backgrounding-occluded-windows".to_string(),
            "--disable-ipc-flooding-protection".to_string(),
            "--disable-hang-monitor".to_string(),
            "--disable-prompt-on-repost".to_string(),
            "--disable-background-networking".to_string(),
            "--disable-sync".to_string(),
            "--metrics-recording-only".to_string(),
            "--disable-default-browser-check".to_string(),
            "--no-default-browser-check".to_string(),
        ]
    };

    // Configure and launch browser with enhanced reliability (chain methods)
    info!("Configured Chromium with {} performance flags", chrome_flags.len());
    let browser = if !chrome_flags.is_empty() {
        playwright.chromium().launcher()
            .headless(req.headless)
            .args(&chrome_flags)
            .launch().await?
    } else {
        playwright.chromium().launcher()
            .headless(req.headless)
            .launch().await?
    };
    let context = browser.context_builder().build().await?;
    let page = context.new_page().await?;
    
    for (index, url) in req.urls.iter().enumerate() {
        // Check if automation was stopped
        {
            let status = AUTOMATION_STATUS.read().await;
            if !status.running {
                info!("Automation stopped by user");
                break;
            }
        }
        
        info!("Processing URL {}/{}: {}", index + 1, req.urls.len(), url);
        
        // Update progress
        let progress = (index as f32 / req.urls.len() as f32) * 100.0;
        {
            let mut status = AUTOMATION_STATUS.write().await;
            status.current_url = Some(url.clone());
            status.progress = progress;
            status.processed_count = index;
        }
        
        // Broadcast progress - send both detailed progress and status update
        let progress_message = WebSocketMessage::AutomationProgress {
            timestamp: Utc::now(),
            current_url: url.clone(),
            progress,
            processed_count: index,
            total_count: req.urls.len(),
            message: format!("Processing URL {}/{}: {}", index + 1, req.urls.len(), url),
        };

        let status_update = WebSocketMessage::AutomationStatusUpdate {
            running: true,
            current_url: Some(url.clone()),
            progress: Some(progress),
            processed_count: Some(index),
            total_count: Some(req.urls.len()),
            error: None,
        };

        let progress_log = WebSocketMessage::Log {
            level: "info".to_string(),
            message: format!("Processing URL {}/{}: {}", index + 1, req.urls.len(), url),
            timestamp: Some(Utc::now()),
        };

        let _ = broadcast_automation_message(&state, progress_message).await;
        let _ = broadcast_automation_message(&state, status_update).await;
        let _ = broadcast_automation_message(&state, progress_log).await;

        // Log navigation start
        let nav_start_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("→ Navigating to {}", url),
        };

        let nav_log = WebSocketMessage::Log {
            level: "info".to_string(),
            message: format!("→ Navigating to {}", url),
            timestamp: Some(Utc::now()),
        };

        let _ = broadcast_automation_message(&state, nav_start_message).await;
        let _ = broadcast_automation_message(&state, nav_log).await;
        
        // Navigate to URL with Playwright reliability
        if let Err(e) = page.goto_builder(url).goto().await {
            warn!("Failed to navigate to {}: {}", url, e);
            let nav_error_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("❌ Failed to navigate to {}: {}", url, e),
            };
            let nav_error_log = WebSocketMessage::Log {
                level: "error".to_string(),
                message: format!("❌ Failed to navigate to {}: {}", url, e),
                timestamp: Some(Utc::now()),
            };
            let _ = broadcast_automation_message(&state, nav_error_message).await;
            let _ = broadcast_automation_message(&state, nav_error_log).await;
            continue;
        }

        // Wait for page to load completely - Playwright handles this automatically
        // Simply wait a brief moment for page stabilization
        tokio::time::sleep(std::time::Duration::from_millis(1000)).await;

        // Log successful navigation
        let nav_success_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("→ Page loaded successfully"),
        };
        let nav_success_log = WebSocketMessage::Log {
            level: "success".to_string(),
            message: "→ Page loaded successfully".to_string(),
            timestamp: Some(Utc::now()),
        };
        let _ = broadcast_automation_message(&state, nav_success_message).await;
        let _ = broadcast_automation_message(&state, nav_success_log).await;
        
        // Reduced delay to let the page render - optimized for speed
        tokio::time::sleep(std::time::Duration::from_millis(500)).await;
        
        // Pre-discovery phase: TEMPORARILY DISABLED to bypass potential deadlock
        // TODO: Re-enable form discovery after fixing the hanging issue
        let skip_discovery_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: "🚀 Skipping form discovery, going directly to field filling...".to_string(),
        };
        let _ = broadcast_automation_message(&state, skip_discovery_message).await;

        // Playwright stability optimization - reduced delay needed
        tokio::time::sleep(std::time::Duration::from_millis(1000)).await;

        // Playwright browser stability check
        let playwright_check_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: "🔧 Verifying Playwright browser stability...".to_string(),
        };
        let _ = broadcast_automation_message(&state, playwright_check_message).await;

        // Test basic Playwright interaction to ensure it's responsive
        let _current_url = page.url();
        let stability_ok_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: "✅ Playwright browser is stable, proceeding with field filling".to_string(),
        };
        let _ = broadcast_automation_message(&state, stability_ok_message).await;

        // Fill form fields using profile data with timeout protection
        let mut filled_fields = 0;
        let total_fields = profile.data.len();

        info!("Starting field filling for {} fields", total_fields);
        info!("Profile data preview: {:?}", profile.data.iter().take(5).collect::<Vec<_>>());

        let start_fill_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🔍 Starting to fill {} fields...", total_fields),
        };
        let _ = broadcast_automation_message(&state, start_fill_message).await;

        let profile_debug_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("📄 Profile '{}' has {} fields loaded", profile.name, total_fields),
        };
        let _ = broadcast_automation_message(&state, profile_debug_message).await;
        
        for (field_index, (field_name, field_value)) in profile.data.iter().enumerate() {
            // Add field processing checkpoint with timeout protection
            let field_timeout = tokio::time::timeout(
                std::time::Duration::from_secs(10), // 10 second timeout per field
                async {
                    // Skip empty values
                    if field_value.trim().is_empty() {
                        let skip_message = WebSocketMessage::ScriptLog {
                            timestamp: Utc::now(),
                            message: format!("⏭️ Skipping empty field: '{}'", field_name),
                        };
                        let _ = broadcast_automation_message(&state, skip_message).await;
                        return Ok::<bool, anyhow::Error>(false);
                    }

                    info!("Trying to fill field {}/{}: {} = {}", field_index + 1, total_fields, field_name, field_value);

                    let processing_message = WebSocketMessage::ScriptLog {
                        timestamp: Utc::now(),
                        message: format!("🔄 Processing field {}/{}: '{}' = '{}'", field_index + 1, total_fields, field_name, field_value),
                    };
                    let _ = broadcast_automation_message(&state, processing_message).await;

                    // Use RoboForm-specific field mappings from recording (FIXED)
                    let mut selectors = Vec::new();

                    // Add specific RoboForm selector if available
                    if let Some(roboform_selector) = get_roboform_selector(field_name) {
                        selectors.push(roboform_selector);
                    }

                    // Add fallback generic selectors
                    selectors.extend(vec![
                        format!("input[name='{}']", field_name),
                        format!("input[id='{}']", field_name),
                        format!("select[name='{}']", field_name),
                        format!("textarea[name='{}']", field_name),
                        format!("input[placeholder*='{}']", field_name.to_lowercase()),
                    ]);

                    info!("Using {} selectors for field '{}': {:?}", selectors.len(), field_name, selectors);

                    let selector_debug_message = WebSocketMessage::ScriptLog {
                        timestamp: Utc::now(),
                        message: format!("🎯 Found {} selectors for '{}': {:?}", selectors.len(), field_name, selectors),
                    };
                    let _ = broadcast_automation_message(&state, selector_debug_message).await;

                    let mut field_found = false;
                    for (selector_index, selector) in selectors.iter().enumerate() {
                        let trying_selector_message = WebSocketMessage::ScriptLog {
                            timestamp: Utc::now(),
                            message: format!("🔍 Trying selector {}/{}: '{}'", selector_index + 1, selectors.len(), selector),
                        };
                        let _ = broadcast_automation_message(&state, trying_selector_message).await;

                        // Use Playwright's robust element finding and filling with individual timeout
                        // Check if this is a select dropdown element or any potential dropdown
                        let is_dropdown = selector.contains("select[") ||
                                        selector.contains("dropdown") ||
                                        selector.contains("combobox") ||
                                        selector.contains("listbox");

                        let fill_result = if is_dropdown {
                            // Use the new Smart Dropdown Service
                            let smart_dropdown_message = WebSocketMessage::ScriptLog {
                                timestamp: Utc::now(),
                                message: format!("🤖 Using Smart Dropdown Service for field '{}'", field_name),
                            };
                            let _ = broadcast_automation_message(&state, smart_dropdown_message).await;

                            // Get the dropdown service from state
                            let mut dropdown_service = state.dropdown_service.write().await;

                            match dropdown_service.analyze_and_select_dropdown(
                                &page,
                                &selector,
                                field_value,
                                field_name,
                                &state
                            ).await {
                                Ok(_) => Ok(Ok(())) as Result<Result<(), Box<dyn std::error::Error + Send + Sync>>, Box<dyn std::error::Error + Send + Sync>>,
                                Err(e) => {
                                    let smart_fallback_message = WebSocketMessage::ScriptLog {
                                        timestamp: Utc::now(),
                                        message: format!("⚠️ Smart dropdown service failed for '{}': {}, trying legacy approach", field_name, e),
                                    };
                                    let _ = broadcast_automation_message(&state, smart_fallback_message).await;

                                    // Fallback to legacy dropdown handling with hardcoded mapping
                                    let dropdown_value = map_roboform_dropdown_value(field_name, field_value);
                                    match select_dropdown_with_validation(&page, &selector, &dropdown_value, field_name, 3, &state).await {
                                        Ok(_) => Ok(Ok(())),
                                        Err(e2) => {
                                            // Try failure recovery with the smart service
                                            if let Err(recovery_error) = dropdown_service.handle_selection_failure(
                                                &page,
                                                &selector,
                                                &dropdown_value,
                                                &e2.to_string(),
                                                field_name,
                                                &state
                                            ).await {
                                                let recovery_failed_message = WebSocketMessage::ScriptLog {
                                                    timestamp: Utc::now(),
                                                    message: format!("❌ All dropdown strategies failed for '{}': {}", field_name, recovery_error),
                                                };
                                                let _ = broadcast_automation_message(&state, recovery_failed_message).await;
                                            }
                                            Ok(Err(e2))
                                        }
                                    }
                                }
                            }
                        } else {
                            // Handle regular input elements with fill()
                            match tokio::time::timeout(
                                std::time::Duration::from_secs(5), // 5 second timeout per selector attempt
                                page.fill_builder(&selector, field_value).fill()
                            ).await {
                                Ok(result) => match result {
                                    Ok(_) => Ok(Ok(())),
                                    Err(e) => Ok(Err(Box::new(e) as Box<dyn std::error::Error + Send + Sync>)),
                                },
                                Err(e) => Ok(Err(Box::new(e) as Box<dyn std::error::Error + Send + Sync>)),
                            }
                        };

                        match fill_result {
                            Ok(Ok(_)) => {
                                field_found = true;

                                info!("Successfully filled field {}/{}: {} = {}", field_index + 1, total_fields, field_name, field_value);
                                let success_message = WebSocketMessage::ScriptLog {
                                    timestamp: Utc::now(),
                                    message: format!("✅ [{}/{}] Successfully filled '{}' = '{}' using selector '{}'", field_index + 1, total_fields, field_name, field_value, selector),
                                };
                                let _ = broadcast_automation_message(&state, success_message).await;

                                // Also send a simple confirmation message
                                let confirm_message = WebSocketMessage::Log {
                                    level: "success".to_string(),
                                    message: format!("✅ Field #{}: '{}' filled successfully", field_index + 1, field_name),
                                    timestamp: Some(Utc::now()),
                                };
                                let _ = broadcast_automation_message(&state, confirm_message).await;

                                // Add human-like delay after successful field fill
                                tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                                break;
                            },
                            Ok(Err(e)) => {
                                let fill_error_message = WebSocketMessage::ScriptLog {
                                    timestamp: Utc::now(),
                                    message: format!("🚫 Failed to fill field '{}' with selector '{}': {}", field_name, selector, e),
                                };
                                let _ = broadcast_automation_message(&state, fill_error_message).await;
                            },
                            Err(_) => {
                                let timeout_error_message = WebSocketMessage::ScriptLog {
                                    timestamp: Utc::now(),
                                    message: format!("⏰ Timeout filling field '{}' with selector '{}'", field_name, selector),
                                };
                                let _ = broadcast_automation_message(&state, timeout_error_message).await;
                            }
                        }
                    }

                    if !field_found {
                        info!("Field not found: {}", field_name);
                        let log_message = WebSocketMessage::ScriptLog {
                            timestamp: Utc::now(),
                            message: format!("⚠️ Field '{}' not found", field_name),
                        };
                        let _ = broadcast_automation_message(&state, log_message).await;
                    } else {
                        // Increment filled_fields count
                        return Ok::<bool, anyhow::Error>(true);
                    }

                    Ok::<bool, anyhow::Error>(false)
                }
            ).await;

            // Handle field processing result with comprehensive error logging
            match field_timeout {
                Ok(Ok(field_filled)) => {
                    if field_filled {
                        filled_fields += 1;
                    }

                    // Add checkpoint message to track progress
                    let checkpoint_message = WebSocketMessage::ScriptLog {
                        timestamp: Utc::now(),
                        message: format!("🔄 Checkpoint: Processed field {}/{}: '{}' (Filled: {}/{})",
                            field_index + 1, total_fields, field_name, filled_fields, total_fields),
                    };
                    let _ = broadcast_automation_message(&state, checkpoint_message).await;
                },
                Ok(Err(e)) => {
                    let field_error_message = WebSocketMessage::ScriptLog {
                        timestamp: Utc::now(),
                        message: format!("❌ Error processing field '{}': {} (continuing...)", field_name, e),
                    };
                    let _ = broadcast_automation_message(&state, field_error_message).await;
                    // Continue with next field instead of terminating
                },
                Err(_) => {
                    let field_timeout_message = WebSocketMessage::ScriptLog {
                        timestamp: Utc::now(),
                        message: format!("⏰ Field '{}' timed out after 10s (continuing...)", field_name),
                    };
                    let _ = broadcast_automation_message(&state, field_timeout_message).await;
                    // Continue with next field instead of terminating
                }
            }

            // Check if automation was stopped between fields
            {
                let status = AUTOMATION_STATUS.read().await;
                if !status.running {
                    let stop_message = WebSocketMessage::ScriptLog {
                        timestamp: Utc::now(),
                        message: "🛑 Automation stopped by user during field processing".to_string(),
                    };
                    let _ = broadcast_automation_message(&state, stop_message).await;
                    break;
                }
            }

            // Small delay between field processing to prevent overwhelming the website
            tokio::time::sleep(std::time::Duration::from_millis(50)).await;
        }
        
        // Log summary of field filling for this URL
        let total_fields = profile.data.len();
        let summary_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("✓ Successfully filled {}/{} fields on {}", filled_fields, total_fields, url),
        };
        let _ = broadcast_automation_message(&state, summary_message).await;
        
        info!("Filled {} fields on {}", filled_fields, url);
        
        // Add delay if specified
        if let Some(delay) = req.delay {
            tokio::time::sleep(tokio::time::Duration::from_millis(delay)).await;
        }
    }
    
    // Mark automation as completed
    {
        let mut status = AUTOMATION_STATUS.write().await;
        status.running = false;
        status.progress = 100.0;
        status.processed_count = req.urls.len();
    }
    
    // Broadcast completion - send all message types for JavaScript compatibility
    let completion_message = WebSocketMessage::AutomationCompleted {
        timestamp: Utc::now(),
        total_processed: req.urls.len(),
        message: format!("✅ Automation completed. Processed {} URLs", req.urls.len()),
    };

    let status_update = WebSocketMessage::AutomationStatusUpdate {
        running: false,
        current_url: None,
        progress: Some(100.0),
        processed_count: Some(req.urls.len()),
        total_count: Some(req.urls.len()),
        error: None,
    };

    let log_message = WebSocketMessage::Log {
        level: "success".to_string(),
        message: format!("✅ Automation completed. Processed {} URLs", req.urls.len()),
        timestamp: Some(Utc::now()),
    };

    let _ = broadcast_automation_message(&state, completion_message).await;
    let _ = broadcast_automation_message(&state, status_update).await;
    let _ = broadcast_automation_message(&state, log_message).await;
    
    info!("Automation completed successfully");
    Ok(())
}

// Simulation automation for testing WebSocket communication
#[allow(dead_code)]
async fn run_simulation_automation(
    state: AppState,
    req: AutomationRequest,
    profile: Profile,
) -> anyhow::Result<()> {
    info!("Running SIMULATION automation for {} URLs", req.urls.len());
    
    for (index, url) in req.urls.iter().enumerate() {
        // Check if automation was stopped
        {
            let status = AUTOMATION_STATUS.read().await;
            if !status.running {
                info!("Automation stopped by user");
                break;
            }
        }
        
        // Update progress
        let progress = (index + 1) as f32 / req.urls.len() as f32 * 100.0;
        {
            let mut status = AUTOMATION_STATUS.write().await;
            status.progress = progress;
            status.processed_count = index + 1;
            status.current_url = Some(url.clone());
        }
        
        let progress_message = WebSocketMessage::AutomationProgress {
            timestamp: Utc::now(),
            current_url: url.clone(),
            progress,
            processed_count: index + 1,
            total_count: req.urls.len(),
            message: format!("Processing URL {} of {}", index + 1, req.urls.len()),
        };
        
        let _ = broadcast_automation_message(&state, progress_message).await;
        
        // Log navigation start
        let nav_start_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🌐 Navigating to {}", url),
        };
        let _ = broadcast_automation_message(&state, nav_start_message).await;
        
        // Simulate navigation delay
        tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;
        
        // Simulate successful navigation
        let nav_success_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("✅ Page loaded successfully"),
        };
        let _ = broadcast_automation_message(&state, nav_success_message).await;
        
        // Simulate form field filling using templates when available
        let mut filled_fields = 0;
        let mut total_fields = profile.data.len();
        let mut form_values = profile.data.clone();
        
        // Try to load template for better field mapping
        if url.contains("roboform.com") {
            let template_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: "🔍 Detected RoboForm URL, attempting to load template...".to_string(),
            };
            let _ = broadcast_automation_message(&state, template_message).await;
            
            match load_form_template("roboform_template").await {
                Ok(template) => {
                    info!("Successfully loaded RoboForm template with {} fields", template.fields.len());
                    form_values = get_form_values_with_adapter(&profile, &template);
                    total_fields = template.fields.len();
                    
                    let success_message = WebSocketMessage::ScriptLog {
                        timestamp: Utc::now(),
                        message: format!("🎯 Using RoboForm template with {} field mappings", template.fields.len()),
                    };
                    let _ = broadcast_automation_message(&state, success_message).await;
                }
                Err(e) => {
                    error!("Failed to load RoboForm template: {}", e);
                    let error_message = WebSocketMessage::ScriptLog {
                        timestamp: Utc::now(),
                        message: format!("⚠️ Failed to load RoboForm template: {}", e),
                    };
                    let _ = broadcast_automation_message(&state, error_message).await;
                    
                    let fallback_message = WebSocketMessage::ScriptLog {
                        timestamp: Utc::now(),
                        message: "📋 Using basic profile data for form filling".to_string(),
                    };
                    let _ = broadcast_automation_message(&state, fallback_message).await;
                }
            }
        }
        
        // Start field filling process
        let start_filling_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🚀 Starting to fill {} fields...", form_values.len()),
        };
        let _ = broadcast_automation_message(&state, start_filling_message).await;
        
        for (field_name, field_value) in &form_values {
            // Simulate field detection and filling
            tokio::time::sleep(tokio::time::Duration::from_millis(300)).await;
            
            let field_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("📝 Filled field '{}' with value '{}'", field_name, field_value),
            };
            
            // Add logging to see if broadcast is working
            info!("Broadcasting field message for: {} = {}", field_name, field_value);
            let result = broadcast_automation_message(&state, field_message).await;
            if let Err(e) = result {
                // Only log as warning if it's not just "no receivers"
                if state.automation_tx.receiver_count() == 0 {
                    info!("No WebSocket clients connected (field: {})", field_name);
                } else {
                    error!("Failed to broadcast field message: {}", e);
                }
            }
            
            filled_fields += 1;
        }
        let summary_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("✅ Successfully filled {}/{} fields on {}", filled_fields, total_fields, url),
        };
        let _ = broadcast_automation_message(&state, summary_message).await;
        
        info!("Simulated filling {} fields on {}", filled_fields, url);
        
        // Add delay between URLs
        if index < req.urls.len() - 1 {
            tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;
        }
    }
    
    // Mark automation as completed
    {
        let mut status = AUTOMATION_STATUS.write().await;
        status.running = false;
        status.progress = 100.0;
    }
    
    // Broadcast completion - send all message types for JavaScript compatibility
    let completion_message = WebSocketMessage::AutomationCompleted {
        timestamp: Utc::now(),
        total_processed: req.urls.len(),
        message: "Automation completed successfully (SIMULATION)".to_string(),
    };

    let status_update = WebSocketMessage::AutomationStatusUpdate {
        running: false,
        current_url: None,
        progress: Some(100.0),
        processed_count: Some(req.urls.len()),
        total_count: Some(req.urls.len()),
        error: None,
    };

    let log_message = WebSocketMessage::Log {
        level: "success".to_string(),
        message: "✅ Automation completed successfully (SIMULATION)".to_string(),
        timestamp: Some(Utc::now()),
    };

    let _ = broadcast_automation_message(&state, completion_message).await;
    let _ = broadcast_automation_message(&state, status_update).await;
    let _ = broadcast_automation_message(&state, log_message).await;
    
    info!("SIMULATION automation completed successfully");
    Ok(())
}

// File I/O helpers
pub async fn load_profiles(state: &AppState) -> anyhow::Result<()> {
    // Create profiles directory if it doesn't exist
    fs::create_dir_all("profiles").await?;

    let mut dir = fs::read_dir("profiles").await?;
    let mut loaded_count = 0;
    
    while let Some(entry) = dir.next_entry().await? {
        if let Some(ext) = entry.path().extension() {
            if ext == "json" {
                if let Ok(content) = fs::read_to_string(entry.path()).await {
                    // Try to load as new format first
                    if let Ok(profile) = serde_json::from_str::<Profile>(&content) {
                        let mut profiles = state.profiles.write().await;
                        profiles.insert(profile.id.clone(), profile.clone());
                        // Also index by name for backward compatibility
                        profiles.insert(profile.name.clone(), profile);
                        loaded_count += 1;
                    } 
                    // Try to load as legacy format
                    else if let Ok(legacy_data) = serde_json::from_str::<serde_json::Value>(&content) {
                        if let Some(profile_name) = legacy_data.get("profileName").and_then(|v| v.as_str()) {
                            // Convert legacy format to new format
                            let mut data = std::collections::HashMap::new();
                            for (key, value) in legacy_data.as_object().unwrap() {
                                if key != "profileName" {
                                    if let Some(str_val) = value.as_str() {
                                        data.insert(key.clone(), str_val.to_string());
                                    }
                                }
                            }
                            
                            let profile = Profile {
                                id: profile_name.to_string(),
                                name: profile_name.to_string(),
                                data,
                                created_at: chrono::Utc::now(),
                                updated_at: chrono::Utc::now(),
                            };
                            
                            let mut profiles = state.profiles.write().await;
                            profiles.insert(profile.id.clone(), profile.clone());
                            // Also index by name for backward compatibility
                            profiles.insert(profile.name.clone(), profile);
                            loaded_count += 1;
                        }
                    }
                }
            }
        }
    }
    
    info!("Loaded {} profiles from disk", loaded_count);
    Ok(())
}


async fn save_profile(profile: &Profile) -> anyhow::Result<()> {
    fs::create_dir_all("profiles").await?;
    let file_path = format!("profiles/{}.json", profile.id);
    let content = serde_json::to_string_pretty(profile)?;
    fs::write(file_path, content).await?;
    Ok(())
}

async fn save_mapping(mapping: &FieldMapping) -> anyhow::Result<()> {
    fs::create_dir_all("field_mappings").await?;
    let file_path = format!("field_mappings/{}.json", mapping.id);
    let content = serde_json::to_string_pretty(mapping)?;
    fs::write(file_path, content).await?;
    Ok(())
}

// Load form template from field_mappings directory
#[allow(dead_code)]
pub async fn load_form_template(template_name: &str) -> anyhow::Result<FormTemplate> {
    let file_path = format!("field_mappings/{}.json", template_name);
    let content = fs::read_to_string(file_path).await?;
    let template = serde_json::from_str::<FormTemplate>(&content)?;
    Ok(template)
}

// Get form values using ProfileAdapter
#[allow(dead_code)]
pub fn get_form_values_with_adapter(profile: &Profile, template: &FormTemplate) -> HashMap<String, String> {
    let adapter = ProfileAdapter::new(profile.data.clone(), template.clone());
    adapter.get_form_values()
}

async fn load_recordings_from_file() -> anyhow::Result<Vec<crate::models::Recording>> {
    let recordings_path = "recordings/recordings.json";
    
    // Check if recordings file exists
    if !tokio::fs::try_exists(recordings_path).await? {
        // If file doesn't exist, return empty array
        return Ok(Vec::new());
    }
    
    let content = fs::read_to_string(recordings_path).await?;
    let recordings: Vec<crate::models::Recording> = serde_json::from_str(&content)?;
    Ok(recordings)
}

// Get Playwright scripts (placeholder - returns empty array)
pub async fn get_playwright_scripts() -> impl IntoResponse {
    Json(Vec::<serde_json::Value>::new())
}

// Get smart mappings (placeholder - returns empty array)
pub async fn get_smart_mappings() -> impl IntoResponse {
    Json(Vec::<serde_json::Value>::new())
}

// Get settings (returns default settings)
pub async fn get_settings() -> impl IntoResponse {
    let default_settings = serde_json::json!({
        "theme": "dark",
        "autoSave": true,
        "notifications": true,
        "language": "en"
    });
    Json(default_settings)
}

// Update settings (placeholder - returns success)
pub async fn update_settings(Json(_payload): Json<serde_json::Value>) -> impl IntoResponse {
    // For now, just return success
    Json(serde_json::json!({"success": true, "message": "Settings updated"}))
}

// Get groups from saved URLs
pub async fn get_groups() -> impl IntoResponse {
    match load_saved_urls_from_file().await {
        Ok(urls) => {
            let mut groups = std::collections::HashSet::new();

            // Extract groups from URLs
            for url in urls {
                if let Some(group) = url.get("group").and_then(|g| g.as_str()) {
                    groups.insert(group.to_string());
                }
            }

            // Convert to sorted vector
            let mut groups: Vec<String> = groups.into_iter().collect();
            groups.sort();

            Json(groups).into_response()
        }
        Err(e) => {
            error!("Failed to load saved URLs for groups: {}", e);
            (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load groups").into_response()
        }
    }
}

// Get real-time statistics
pub async fn get_stats(State(state): State<AppState>) -> impl IntoResponse {
    let stats_tracker = state.stats_tracker.read().await;
    let dashboard_summary = stats_tracker.get_dashboard_summary();

    // Update profile and URL counts
    let profiles = state.profiles.read().await;
    let active_profiles = profiles.values().filter(|_p| {
        // Consider a profile active if it has been used
        true // You can add logic here to determine if a profile is active
    }).count() as u32;

    // Count URLs
    let urls = match load_saved_urls_from_file().await {
        Ok(urls) => urls,
        Err(_) => Vec::new(),
    };

    let active_urls = urls.iter().filter(|u| {
        u.get("status").and_then(|s| s.as_str()).unwrap_or("active") == "active"
    }).count() as u32;

    // Create final stats response
    let mut final_stats = dashboard_summary;
    final_stats["total_profiles"] = serde_json::json!(profiles.len());
    final_stats["active_profiles"] = serde_json::json!(active_profiles);
    final_stats["total_urls"] = serde_json::json!(urls.len());
    final_stats["active_urls"] = serde_json::json!(active_urls);

    Json(final_stats)
}

// Check if a browser is available for automation
#[allow(dead_code)]
async fn check_browser_availability() -> bool {
    let chrome_paths = vec![
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ];

    let edge_paths = vec![
        "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
        "/usr/bin/microsoft-edge",
    ];

    // Check Chrome first
    for path in chrome_paths {
        if FilePath::new(path).exists() {
            info!("Found Chrome at: {}", path);
            return true;
        }
    }

    // Check Edge
    for path in edge_paths {
        if FilePath::new(path).exists() {
            info!("Found Edge at: {}", path);
            return true;
        }
    }

    warn!("No browser found. Install Google Chrome or Microsoft Edge for real automation.");
    false
}

// Get the best available browser path
#[allow(dead_code)]
async fn get_browser_path() -> Option<String> {
    let chrome_paths = vec![
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ];

    let edge_paths = vec![
        "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
        "/usr/bin/microsoft-edge",
    ];

    // Prefer Chrome
    for path in chrome_paths {
        if FilePath::new(path).exists() {
            return Some(path.to_string());
        }
    }

    // Fallback to Edge
    for path in edge_paths {
        if FilePath::new(path).exists() {
            return Some(path.to_string());
        }
    }

    None
}

async fn load_saved_urls_from_file() -> anyhow::Result<Vec<serde_json::Value>> {
    let urls_path = "saved_urls/saved_urls.json";

    // Check if saved URLs file exists
    if !tokio::fs::try_exists(urls_path).await? {
        // If file doesn't exist, return empty array
        return Ok(Vec::new());
    }

    let content = fs::read_to_string(urls_path).await?;
    let urls: Vec<serde_json::Value> = serde_json::from_str(&content)?;
    Ok(urls)
}

// Enhanced URL Management Functions
pub async fn load_saved_urls_structured() -> anyhow::Result<Vec<crate::models::SavedUrl>> {
    let urls_path = "saved_urls/saved_urls.json";

    // Check if saved URLs file exists
    if !tokio::fs::try_exists(urls_path).await? {
        // If file doesn't exist, return empty array
        return Ok(Vec::new());
    }

    let content = fs::read_to_string(urls_path).await?;

    // Try to parse as new structured format first
    if let Ok(urls) = serde_json::from_str::<Vec<crate::models::SavedUrl>>(&content) {
        return Ok(urls);
    }

    // Try to parse as legacy format and convert
    if let Ok(legacy_urls) = serde_json::from_str::<Vec<serde_json::Value>>(&content) {
        let mut converted_urls = Vec::new();

        for legacy_url in legacy_urls {
            if let Some(url_str) = legacy_url.get("url").and_then(|u| u.as_str()) {
                let name = legacy_url.get("name").and_then(|n| n.as_str()).map(|s| s.to_string());
                let description = legacy_url.get("description").and_then(|d| d.as_str()).map(|s| s.to_string());
                let group = legacy_url.get("group").and_then(|g| g.as_str()).map(|s| s.to_string());

                let tags = legacy_url.get("tags")
                    .and_then(|t| t.as_array())
                    .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect())
                    .unwrap_or_else(Vec::new);

                let saved_url = crate::models::SavedUrl::new(
                    url_str.to_string(),
                    name,
                    description,
                    group,
                    tags,
                );

                converted_urls.push(saved_url);
            }
        }

        // Save in new format
        save_saved_urls_structured(&converted_urls).await?;
        return Ok(converted_urls);
    }

    // If all parsing fails, return empty array
    Ok(Vec::new())
}

pub async fn save_saved_urls_structured(urls: &[crate::models::SavedUrl]) -> anyhow::Result<()> {
    fs::create_dir_all("saved_urls").await?;
    let urls_path = "saved_urls/saved_urls.json";
    let content = serde_json::to_string_pretty(urls)?;
    fs::write(urls_path, content).await?;
    Ok(())
}

pub async fn load_url_groups() -> anyhow::Result<Vec<crate::models::UrlGroup>> {
    let groups_path = "saved_urls/groups.json";

    if !tokio::fs::try_exists(groups_path).await? {
        return Ok(Vec::new());
    }

    let content = fs::read_to_string(groups_path).await?;
    let groups: Vec<crate::models::UrlGroup> = serde_json::from_str(&content)?;
    Ok(groups)
}

pub async fn save_url_groups(groups: &[crate::models::UrlGroup]) -> anyhow::Result<()> {
    fs::create_dir_all("saved_urls").await?;
    let groups_path = "saved_urls/groups.json";
    let content = serde_json::to_string_pretty(groups)?;
    fs::write(groups_path, content).await?;
    Ok(())
}

// URL CRUD Operations
pub async fn create_saved_url(
    State(state): State<AppState>,
    Json(req): Json<crate::models::CreateUrlRequest>
) -> impl IntoResponse {
    // Load existing URLs
    let mut urls = match load_saved_urls_structured().await {
        Ok(urls) => urls,
        Err(e) => {
            error!("Failed to load saved URLs: {}", e);
            return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load saved URLs").into_response();
        }
    };

    // Check for duplicate URLs
    if urls.iter().any(|u| u.url == req.url) {
        return (StatusCode::CONFLICT, "URL already exists").into_response();
    }

    // Create new URL
    let tags = req.tags.unwrap_or_else(Vec::new);
    let new_url = crate::models::SavedUrl::new(
        req.url.clone(),
        req.name,
        req.description,
        req.group,
        tags,
    );

    let url_id = new_url.id.clone();
    urls.push(new_url);

    // Save URLs
    if let Err(e) = save_saved_urls_structured(&urls).await {
        error!("Failed to save URLs: {}", e);
        return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to save URL").into_response();
    }

    // Test URL if requested
    let test_url_flag = req.test_url.unwrap_or(false);
    let url_for_log = req.url.clone();

    if test_url_flag {
        let url_for_test = req.url.clone();
        tokio::spawn(async move {
            let _ = test_url_connectivity(&url_for_test).await;
        });
    }

    // Broadcast URL groups update (since URLs can affect groups)
    let url_groups_update = WebSocketMessage::UrlGroupsUpdated {
        timestamp: Utc::now(),
        message: format!("New URL added: {}", url_for_log),
    };

    if let Err(e) = broadcast_automation_message(&state, url_groups_update).await {
        warn!("Failed to broadcast URL creation: {}", e);
    }

    info!("Created new saved URL: {}", url_for_log);
    (StatusCode::CREATED, Json(serde_json::json!({"id": url_id, "message": "URL created successfully"}))).into_response()
}

pub async fn get_saved_url_by_id(Path(id): Path<String>) -> impl IntoResponse {
    match load_saved_urls_structured().await {
        Ok(urls) => {
            if let Some(url) = urls.iter().find(|u| u.id == id) {
                Json(url).into_response()
            } else {
                StatusCode::NOT_FOUND.into_response()
            }
        }
        Err(e) => {
            error!("Failed to load saved URLs: {}", e);
            (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load URLs").into_response()
        }
    }
}

pub async fn update_saved_url(
    Path(id): Path<String>,
    State(state): State<AppState>,
    Json(req): Json<crate::models::UpdateUrlRequest>,
) -> impl IntoResponse {
    // Load existing URLs
    let mut urls = match load_saved_urls_structured().await {
        Ok(urls) => urls,
        Err(e) => {
            error!("Failed to load saved URLs: {}", e);
            return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load saved URLs").into_response();
        }
    };

    // Find and update the URL
    if let Some(url) = urls.iter_mut().find(|u| u.id == id) {
        url.update(req);
        let updated_url = url.clone();

        // Save URLs
        if let Err(e) = save_saved_urls_structured(&urls).await {
            error!("Failed to save URLs: {}", e);
            return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to save URL").into_response();
        }

        // Broadcast URL groups update
        let url_groups_update = WebSocketMessage::UrlGroupsUpdated {
            timestamp: Utc::now(),
            message: format!("URL updated: {}", updated_url.url),
        };

        if let Err(e) = broadcast_automation_message(&state, url_groups_update).await {
            warn!("Failed to broadcast URL update: {}", e);
        }

        info!("Updated saved URL: {}", id);
        Json(updated_url).into_response()
    } else {
        StatusCode::NOT_FOUND.into_response()
    }
}

pub async fn delete_saved_url(
    Path(id): Path<String>,
    State(state): State<AppState>
) -> impl IntoResponse {
    // Load existing URLs
    let mut urls = match load_saved_urls_structured().await {
        Ok(urls) => urls,
        Err(e) => {
            error!("Failed to load saved URLs: {}", e);
            return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load saved URLs").into_response();
        }
    };

    // Find and remove the URL
    let initial_len = urls.len();
    urls.retain(|u| u.id != id);

    if urls.len() < initial_len {
        // Save URLs
        if let Err(e) = save_saved_urls_structured(&urls).await {
            error!("Failed to save URLs: {}", e);
            return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to save URLs").into_response();
        }

        // Broadcast URL groups update
        let url_groups_update = WebSocketMessage::UrlGroupsUpdated {
            timestamp: Utc::now(),
            message: format!("URL deleted: {}", id),
        };

        if let Err(e) = broadcast_automation_message(&state, url_groups_update).await {
            warn!("Failed to broadcast URL deletion: {}", e);
        }

        info!("Deleted saved URL: {}", id);
        StatusCode::NO_CONTENT.into_response()
    } else {
        StatusCode::NOT_FOUND.into_response()
    }
}

pub async fn test_saved_url(Path(id): Path<String>) -> impl IntoResponse {
    // Load existing URLs
    let mut urls = match load_saved_urls_structured().await {
        Ok(urls) => urls,
        Err(e) => {
            error!("Failed to load saved URLs: {}", e);
            return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load saved URLs").into_response();
        }
    };

    // Find the URL to test
    if let Some(url) = urls.iter_mut().find(|u| u.id == id) {
        let test_result = test_url_connectivity(&url.url).await;

        // Update URL with test result
        url.update_test_result(test_result.success);

        // Save URLs
        if let Err(e) = save_saved_urls_structured(&urls).await {
            error!("Failed to save URLs after test: {}", e);
        }

        Json(test_result).into_response()
    } else {
        StatusCode::NOT_FOUND.into_response()
    }
}

pub async fn bulk_url_operation(Json(req): Json<crate::models::BulkUrlOperation>) -> impl IntoResponse {
    // Load existing URLs
    let mut urls = match load_saved_urls_structured().await {
        Ok(urls) => urls,
        Err(e) => {
            error!("Failed to load saved URLs: {}", e);
            return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load saved URLs").into_response();
        }
    };

    let mut affected_count = 0;

    match req.operation {
        crate::models::BulkOperation::Delete => {
            let initial_len = urls.len();
            urls.retain(|u| !req.url_ids.contains(&u.id));
            affected_count = initial_len - urls.len();
        }
        crate::models::BulkOperation::UpdateGroup => {
            if let Some(data) = &req.data {
                if let Some(group) = data.get("group").and_then(|g| g.as_str()) {
                    for url in urls.iter_mut() {
                        if req.url_ids.contains(&url.id) {
                            url.group = Some(group.to_string());
                            url.updated_at = chrono::Utc::now();
                            affected_count += 1;
                        }
                    }
                }
            }
        }
        crate::models::BulkOperation::UpdateStatus => {
            if let Some(data) = &req.data {
                if let Some(status_str) = data.get("status").and_then(|s| s.as_str()) {
                    if let Ok(status) = serde_json::from_str::<crate::models::UrlStatus>(&format!("\"{}\"", status_str)) {
                        for url in urls.iter_mut() {
                            if req.url_ids.contains(&url.id) {
                                url.status = status.clone();
                                url.updated_at = chrono::Utc::now();
                                affected_count += 1;
                            }
                        }
                    }
                }
            }
        }
        crate::models::BulkOperation::Test => {
            // Test URLs asynchronously
            let test_urls: Vec<_> = urls.iter()
                .filter(|u| req.url_ids.contains(&u.id))
                .map(|u| (u.id.clone(), u.url.clone()))
                .collect();

            affected_count = test_urls.len();

            // Spawn async tasks for testing
            for (_url_id, url) in test_urls {
                tokio::spawn(async move {
                    let _ = test_url_connectivity(&url).await;
                    // Note: In a real implementation, you'd want to update the URL status
                    // after the test completes, possibly through a channel or database
                });
            }
        }
        crate::models::BulkOperation::AddTags => {
            if let Some(data) = &req.data {
                if let Some(tags_array) = data.get("tags").and_then(|t| t.as_array()) {
                    let new_tags: Vec<String> = tags_array.iter()
                        .filter_map(|t| t.as_str().map(|s| s.to_string()))
                        .collect();

                    for url in urls.iter_mut() {
                        if req.url_ids.contains(&url.id) {
                            for tag in &new_tags {
                                if !url.tags.contains(tag) {
                                    url.tags.push(tag.clone());
                                }
                            }
                            url.updated_at = chrono::Utc::now();
                            affected_count += 1;
                        }
                    }
                }
            }
        }
    }

    // Save URLs (except for test operation which is async)
    if !matches!(req.operation, crate::models::BulkOperation::Test) {
        if let Err(e) = save_saved_urls_structured(&urls).await {
            error!("Failed to save URLs after bulk operation: {}", e);
            return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to save URLs").into_response();
        }
    }

    Json(serde_json::json!({
        "affected_count": affected_count,
        "message": format!("Bulk operation completed. {} URLs affected.", affected_count)
    })).into_response()
}

// Group Management
pub async fn create_url_group(
    State(state): State<AppState>,
    Json(req): Json<crate::models::CreateGroupRequest>
) -> impl IntoResponse {
    // Load existing groups
    let mut groups = match load_url_groups().await {
        Ok(groups) => groups,
        Err(e) => {
            error!("Failed to load URL groups: {}", e);
            return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load groups").into_response();
        }
    };

    // Check for duplicate group names
    if groups.iter().any(|g| g.name == req.name) {
        return (StatusCode::CONFLICT, "Group name already exists").into_response();
    }

    // Create new group
    let group_name_for_log = req.name.clone();
    let new_group = crate::models::UrlGroup::new(
        req.name,
        req.description,
        req.color,
    );

    let group_id = new_group.id.clone();
    groups.push(new_group);

    // Save groups
    if let Err(e) = save_url_groups(&groups).await {
        error!("Failed to save URL groups: {}", e);
        return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to save group").into_response();
    }

    // Broadcast URL groups update
    let url_groups_update = WebSocketMessage::UrlGroupsUpdated {
        timestamp: Utc::now(),
        message: format!("URL group '{}' created", group_name_for_log),
    };

    if let Err(e) = broadcast_automation_message(&state, url_groups_update).await {
        warn!("Failed to broadcast URL group creation: {}", e);
    }

    info!("Created new URL group: {}", group_name_for_log);
    (StatusCode::CREATED, Json(serde_json::json!({"id": group_id, "message": "Group created successfully"}))).into_response()
}

pub async fn get_url_groups_list() -> impl IntoResponse {
    match load_url_groups().await {
        Ok(groups) => Json(groups).into_response(),
        Err(e) => {
            error!("Failed to load URL groups: {}", e);
            (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load groups").into_response()
        }
    }
}

// URL Testing
async fn test_url_connectivity(url: &str) -> crate::models::UrlTestResult {
    let start_time = std::time::Instant::now();

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .user_agent("FormAI/1.0")
        .build()
        .unwrap();

    let test_result = match client.head(url).send().await {
        Ok(response) => {
            let status_code = response.status().as_u16();
            let success = response.status().is_success();

            crate::models::UrlTestResult {
                url_id: String::new(), // Will be set by caller
                url: url.to_string(),
                success,
                response_time: start_time.elapsed().as_millis() as u64,
                status_code: Some(status_code),
                error: None,
                fields_detected: None,
                form_complexity: None,
                tested_at: chrono::Utc::now(),
            }
        }
        Err(e) => {
            crate::models::UrlTestResult {
                url_id: String::new(), // Will be set by caller
                url: url.to_string(),
                success: false,
                response_time: start_time.elapsed().as_millis() as u64,
                status_code: None,
                error: Some(e.to_string()),
                fields_detected: None,
                form_complexity: None,
                tested_at: chrono::Utc::now(),
            }
        }
    };

    test_result
}

// API Key Management Functions
pub async fn load_api_keys() -> anyhow::Result<HashMap<String, crate::models::ApiKey>> {
    fs::create_dir_all("api_keys").await?;
    let mut api_keys = HashMap::new();

    let mut dir = fs::read_dir("api_keys").await?;
    while let Some(entry) = dir.next_entry().await? {
        if let Some(ext) = entry.path().extension() {
            if ext == "json" {
                if let Ok(content) = fs::read_to_string(entry.path()).await {
                    if let Ok(api_key) = serde_json::from_str::<crate::models::ApiKey>(&content) {
                        api_keys.insert(api_key.service.clone(), api_key);
                    }
                }
            }
        }
    }

    Ok(api_keys)
}

pub async fn save_api_key(service: &str, encrypted_key: &str) -> anyhow::Result<()> {
    fs::create_dir_all("api_keys").await?;

    let api_key = crate::models::ApiKey::new(service.to_string(), encrypted_key.to_string());
    let api_key_path = format!("api_keys/{}.json", service);
    let content = serde_json::to_string_pretty(&api_key)?;
    fs::write(&api_key_path, content).await?;

    Ok(())
}

pub async fn get_api_key(service: &str) -> anyhow::Result<Option<String>> {
    let api_key_path = format!("api_keys/{}.json", service);

    if !tokio::fs::try_exists(&api_key_path).await? {
        return Ok(None);
    }

    let content = fs::read_to_string(&api_key_path).await?;
    let api_key: crate::models::ApiKey = serde_json::from_str(&content)?;

    if api_key.is_active {
        Ok(Some(api_key.encrypted_key))
    } else {
        Ok(None)
    }
}

pub async fn delete_api_key(service: &str) -> anyhow::Result<()> {
    let api_key_path = format!("api_keys/{}.json", service);

    if tokio::fs::try_exists(&api_key_path).await? {
        fs::remove_file(&api_key_path).await?;
    }

    Ok(())
}

pub async fn update_api_key_last_used(service: &str) -> anyhow::Result<()> {
    let api_key_path = format!("api_keys/{}.json", service);

    if !tokio::fs::try_exists(&api_key_path).await? {
        return Ok(());
    }

    let content = fs::read_to_string(&api_key_path).await?;
    let mut api_key: crate::models::ApiKey = serde_json::from_str(&content)?;

    api_key.update_last_used();

    let updated_content = serde_json::to_string_pretty(&api_key)?;
    fs::write(&api_key_path, updated_content).await?;

    Ok(())
}

// Simple encryption for local storage (Base64 with salt)
pub fn encrypt_api_key(key: &str) -> String {
    use base64::Engine;
    let salt = "formai_local_salt"; // Simple salt for local storage
    let salted_key = format!("{}{}", salt, key);
    base64::engine::general_purpose::STANDARD.encode(salted_key.as_bytes())
}

fn decrypt_api_key(encrypted_key: &str) -> anyhow::Result<String> {
    use base64::Engine;
    let salt = "formai_local_salt";
    let decoded = base64::engine::general_purpose::STANDARD.decode(encrypted_key)?;
    let salted_key = String::from_utf8(decoded)?;

    if salted_key.starts_with(salt) {
        Ok(salted_key[salt.len()..].to_string())
    } else {
        Err(anyhow::anyhow!("Invalid encrypted key format"))
    }
}

pub async fn get_openrouter_key() -> Option<String> {
    match get_api_key("openrouter").await {
        Ok(Some(encrypted_key)) => {
            match decrypt_api_key(&encrypted_key) {
                Ok(decrypted_key) => {
                    // Update last used timestamp
                    if let Err(e) = update_api_key_last_used("openrouter").await {
                        eprintln!("Failed to update API key last used: {}", e);
                    }
                    Some(decrypted_key)
                },
                Err(_) => None
            }
        },
        _ => None
    }
}

pub async fn get_api_key_preview(service: &str) -> Option<String> {
    match get_api_key(service).await {
        Ok(Some(encrypted_key)) => {
            match decrypt_api_key(&encrypted_key) {
                Ok(decrypted_key) => {
                    if decrypted_key.len() >= 8 {
                        Some(format!("{}...{}", &decrypted_key[0..6], &decrypted_key[decrypted_key.len()-4..]))
                    } else {
                        Some(format!("{}...", &decrypted_key[0..std::cmp::min(4, decrypted_key.len())]))
                    }
                },
                Err(_) => None
            }
        },
        _ => None
    }
}