use axum::{
    response::{Html, IntoResponse},
    routing::{get, post, delete},
    Router,
    Json,
    extract::{State, Path},
    http::StatusCode,
};
use std::{
    collections::HashMap,
    sync::Arc,
};
use tokio::sync::{broadcast, RwLock};
use tower::ServiceBuilder;
use tower_http::{cors::CorsLayer, services::ServeDir};

mod models;
mod profile_adapter;
mod services;
mod websocket;
mod field_mapping_service;
// mod firecrawl_service;
mod stats;
mod openrouter;
mod dropdown_service;
use models::*;
use services::*;
use websocket::*;
use field_mapping_service::FieldMappingService;
use serde::{Deserialize, Serialize};

// Application state
#[derive(Clone)]
pub struct AppState {
    pub profiles: Arc<RwLock<HashMap<String, models::Profile>>>,
    pub mappings: Arc<RwLock<HashMap<String, FieldMapping>>>,
    pub field_mapping_service: Arc<RwLock<FieldMappingService>>,
    pub dropdown_service: Arc<RwLock<dropdown_service::SmartDropdownService>>,
    pub automation_tx: broadcast::Sender<WebSocketMessage>,
    pub stats_tracker: Arc<RwLock<stats::StatsTracker>>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Load environment variables first
    dotenv::dotenv().ok();

    // Initialize tracing
    tracing_subscriber::fmt::init();

    // Create broadcast channel for WebSocket messages
    let (automation_tx, _) = broadcast::channel::<WebSocketMessage>(100);

    // Initialize field mapping service
    let mut field_mapping_service = match FieldMappingService::new() {
        Ok(service) => service,
        Err(e) => {
            eprintln!("Warning: Failed to initialize field mapping service: {}", e);
            eprintln!("Dynamic form discovery will be disabled");
            FieldMappingService::new().unwrap_or_else(|_| {
                panic!("Failed to create field mapping service even without Firecrawl");
            })
        }
    };

    // Initialize stats tracker
    let stats_tracker = match stats::StatsTracker::new().await {
        Ok(tracker) => tracker,
        Err(e) => {
            eprintln!("Warning: Failed to initialize stats tracker: {}", e);
            eprintln!("Using default stats tracker without persistence");
            stats::StatsTracker::create_fallback()
        }
    };
    if let Err(e) = field_mapping_service.load_mappings().await {
        eprintln!("Warning: Failed to load field mappings: {}", e);
    }

    // No template engine needed - serving static HTML files

    // Initialize application state
    // Initialize dropdown service
    let dropdown_service = match dropdown_service::SmartDropdownService::new().await {
        Ok(service) => service,
        Err(e) => {
            eprintln!("Warning: Failed to initialize dropdown service: {}", e);
            eprintln!("Enhanced dropdown detection will be disabled");
            return Err(e.into());
        }
    };

    let state = AppState {
        profiles: Arc::new(RwLock::new(HashMap::new())),
        mappings: Arc::new(RwLock::new(HashMap::new())),
        field_mapping_service: Arc::new(RwLock::new(field_mapping_service)),
        dropdown_service: Arc::new(RwLock::new(dropdown_service)),
        automation_tx,
        stats_tracker: Arc::new(RwLock::new(stats_tracker)),
    };

    // Load existing profiles (if any exist)
    let _ = services::load_profiles(&state).await;

    // Build the application routes
    let app = Router::new()
        // Template routes
        .route("/", get(home_page))
        .route("/profiles", get(profiles_page))
        .route("/automation", get(automation_page))
        .route("/account", get(account_page))
        .route("/saved-urls", get(saved_urls_page))
        .route("/saved-pages", get(saved_pages_page))
        .route("/previous-orders", get(previous_orders_page))
        .route("/recorder", get(recorder_page))
        .route("/settings", get(settings_page))

        // WebSocket endpoint
        .route("/ws", get(websocket_handler))

        // API routes
        .route("/api/health", get(health_check))
        .route("/api/profiles", get(get_profile_names).post(create_profile))
        .route("/api/profiles/{id}", get(get_profile).put(update_profile).delete(delete_profile))
        .route("/api/mappings", get(get_mappings))
        .route("/api/mappings/{id}", get(get_mapping).put(update_mapping).delete(delete_mapping))
        .route("/api/automation/start", post(start_dashboard_automation))
        .route("/api/automation/stop", post(stop_automation))
        .route("/api/automation/status", get(get_automation_status))
        .route("/api/groups", get(get_groups))
        .route("/api/urls", get(get_saved_urls).post(create_saved_url))
        .route("/api/urls/{id}", get(get_saved_url_by_id).put(update_saved_url).delete(delete_saved_url))
        .route("/api/urls/{id}/test", post(test_saved_url))
        .route("/api/urls/bulk", post(bulk_url_operation))
        .route("/api/url-groups", get(get_url_groups_list).post(create_url_group))
        .route("/api/recordings", get(get_recordings))
        .route("/api/field_mappings", get(get_mappings))
        .route("/api/playwright_scripts", get(get_playwright_scripts))
        .route("/api/smart_mappings", get(get_smart_mappings))
        .route("/api/settings", get(get_settings).post(update_settings))
        .route("/api/stats", get(get_stats))
        .route("/api/ai/analyze-form", post(analyze_form_with_ai))
        .route("/api/ai/generate-mapping", post(generate_field_mapping_ai))
        .route("/api/ai/analyze-dropdown", post(analyze_dropdown_with_ai))
        .route("/api/models", get(get_ai_models))
        .route("/api/api-keys", get(get_api_keys_status).post(save_api_key_handler))
        .route("/api/api-keys/{service}", delete(delete_api_key_handler))

        // Add middleware
        .layer(
            ServiceBuilder::new()
                .layer(CorsLayer::permissive())
        )
        // Serve static files (CSS, JS, images, etc.)
        .nest_service("/static", ServeDir::new("static"))
        .with_state(state);

    // Run the server
    let listener = tokio::net::TcpListener::bind("0.0.0.0:5511").await?;

    // Print startup message to console (visible to users)
    println!("╔══════════════════════════════════════════════════════╗");
    println!("║              FormAI - SINGLE BINARY                   ║");
    println!("╠══════════════════════════════════════════════════════╣");
    println!("║  Application:    http://localhost:5511                ║");
    println!("║  API Endpoint:   http://localhost:5511/api/*          ║");
    println!("║  Health Check:   http://localhost:5511/api/health     ║");
    println!("║  WebSocket:      ws://localhost:5511/ws               ║");
    println!("╚══════════════════════════════════════════════════════╝");

    println!("Starting server...");
    match axum::serve(listener, app).await {
        Ok(_) => println!("Server shut down gracefully"),
        Err(e) => {
            eprintln!("Server error: {}", e);
            return Err(e.into());
        }
    }

    Ok(())
}

// Static HTML route handlers
async fn home_page() -> impl IntoResponse {
    serve_html_file("web/index.html").await
}

async fn serve_html_file(file_path: &str) -> impl IntoResponse {
    match tokio::fs::read_to_string(file_path).await {
        Ok(content) => Html(content),
        Err(e) => {
            eprintln!("Error reading file {}: {}", file_path, e);
            Html("<h1>Page not found</h1>".to_string())
        }
    }
}

async fn profiles_page() -> impl IntoResponse {
    serve_html_file("web/profiles.html").await
}

async fn user_data_page() -> impl IntoResponse {
    serve_html_file("web/user_data.html").await
}

async fn account_page() -> impl IntoResponse {
    serve_html_file("web/account.html").await
}

async fn saved_urls_page() -> impl IntoResponse {
    serve_html_file("web/saved_urls.html").await
}

async fn previous_orders_page() -> impl IntoResponse {
    serve_html_file("web/previous_orders.html").await
}

async fn settings_page() -> impl IntoResponse {
    serve_html_file("web/settings.html").await
}

async fn saved_pages_page() -> impl IntoResponse {
    serve_html_file("web/saved_pages.html").await
}

async fn recorder_page() -> impl IntoResponse {
    serve_html_file("web/recorder.html").await
}

async fn automation_page() -> impl IntoResponse {
    serve_html_file("web/automation.html").await
}

// OpenRouter AI endpoint handlers

#[derive(Debug, Deserialize)]
struct AnalyzeFormRequest {
    form_html: String,
    url: String,
    model: Option<String>,
}

#[derive(Debug, Deserialize)]
struct GenerateFieldMappingRequest {
    form_html: String,
    model: Option<String>,
}

#[derive(Debug, Deserialize)]
struct AnalyzeDropdownRequest {
    dropdown_html: String,
    field_name: String,
    user_value: String,
    form_context: Option<String>,
    model: Option<String>,
}

#[derive(Debug, Serialize)]
struct DropdownAnalysisResponse {
    success: bool,
    suggested_option: Option<String>,
    confidence: Option<f32>,
    reasoning: Option<String>,
    error: Option<String>,
}

#[derive(Debug, Serialize)]
struct AIResponse {
    success: bool,
    result: String,
    error: Option<String>,
}

async fn analyze_form_with_ai(
    State(_state): State<AppState>,
    Json(request): Json<AnalyzeFormRequest>
) -> axum::response::Json<AIResponse> {
    dotenv::dotenv().ok();

    match openrouter::OpenRouterClient::new().await {
        Ok(client) => {
            let model = request.model.as_deref().unwrap_or("anthropic/claude-3.5-sonnet");
            match client.generate_form_analysis_with_model(&request.form_html, &request.url, model).await {
                Ok(result) => Json(AIResponse {
                    success: true,
                    result,
                    error: None,
                }),
                Err(e) => Json(AIResponse {
                    success: false,
                    result: String::new(),
                    error: Some(e.to_string()),
                }),
            }
        }
        Err(e) => Json(AIResponse {
            success: false,
            result: String::new(),
            error: Some(format!("Failed to initialize OpenRouter client: {}", e)),
        }),
    }
}

async fn generate_field_mapping_ai(
    State(_state): State<AppState>,
    Json(request): Json<GenerateFieldMappingRequest>
) -> axum::response::Json<AIResponse> {
    dotenv::dotenv().ok();

    match openrouter::OpenRouterClient::new().await {
        Ok(client) => {
            let model = request.model.as_deref().unwrap_or("anthropic/claude-3.5-sonnet");
            match client.generate_field_mapping_with_model(&request.form_html, model).await {
                Ok(result) => Json(AIResponse {
                    success: true,
                    result,
                    error: None,
                }),
                Err(e) => Json(AIResponse {
                    success: false,
                    result: String::new(),
                    error: Some(e.to_string()),
                }),
            }
        }
        Err(e) => Json(AIResponse {
            success: false,
            result: String::new(),
            error: Some(format!("Failed to initialize OpenRouter client: {}", e)),
        }),
    }
}

async fn analyze_dropdown_with_ai(
    State(_state): State<AppState>,
    Json(request): Json<AnalyzeDropdownRequest>
) -> axum::response::Json<DropdownAnalysisResponse> {
    dotenv::dotenv().ok();

    match openrouter::OpenRouterClient::new().await {
        Ok(client) => {
            let model = request.model.as_deref().unwrap_or("anthropic/claude-3.5-sonnet");
            match client.analyze_dropdown_options(&request.dropdown_html, &request.field_name, &request.user_value, request.form_context.as_deref(), model).await {
                Ok(result) => {
                    // Parse the AI response to extract suggestion and confidence
                    if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&result) {
                        Json(DropdownAnalysisResponse {
                            success: true,
                            suggested_option: parsed.get("suggested_option").and_then(|v| v.as_str()).map(|s| s.to_string()),
                            confidence: parsed.get("confidence").and_then(|v| v.as_f64()).map(|f| f as f32),
                            reasoning: parsed.get("reasoning").and_then(|v| v.as_str()).map(|s| s.to_string()),
                            error: None,
                        })
                    } else {
                        // Fallback if AI doesn't return JSON
                        Json(DropdownAnalysisResponse {
                            success: true,
                            suggested_option: Some(result.trim().to_string()),
                            confidence: Some(0.8),
                            reasoning: Some("AI provided text response".to_string()),
                            error: None,
                        })
                    }
                }
                Err(e) => Json(DropdownAnalysisResponse {
                    success: false,
                    suggested_option: None,
                    confidence: None,
                    reasoning: None,
                    error: Some(e.to_string()),
                }),
            }
        }
        Err(e) => Json(DropdownAnalysisResponse {
            success: false,
            suggested_option: None,
            confidence: None,
            reasoning: None,
            error: Some(format!("Failed to initialize OpenRouter client: {}", e)),
        }),
    }
}

async fn get_ai_models() -> axum::response::Json<serde_json::Value> {
    match tokio::fs::read_to_string("Models.json").await {
        Ok(content) => {
            match serde_json::from_str::<serde_json::Value>(&content) {
                Ok(models_data) => Json(models_data),
                Err(_) => Json(serde_json::json!({
                    "error": "Failed to parse Models.json"
                }))
            }
        },
        Err(_) => Json(serde_json::json!({
            "error": "Models.json not found"
        }))
    }
}

// API Key Management Handlers
async fn get_api_keys_status() -> impl IntoResponse {
    match services::load_api_keys().await {
        Ok(api_keys) => {
            let mut status = std::collections::HashMap::new();

            // Check for known services
            let services = vec!["openrouter", "firecrawl"];
            for service in services {
                if let Some(api_key) = api_keys.get(service) {
                    let key_preview = services::get_api_key_preview(service).await;
                    let response = models::ApiKeyResponse {
                        service: service.to_string(),
                        has_key: true,
                        created_at: Some(api_key.created_at),
                        last_used: api_key.last_used,
                        key_preview,
                    };
                    status.insert(service, response);
                } else {
                    let response = models::ApiKeyResponse {
                        service: service.to_string(),
                        has_key: false,
                        created_at: None,
                        last_used: None,
                        key_preview: None,
                    };
                    status.insert(service, response);
                }
            }

            Json(status).into_response()
        },
        Err(e) => {
            (StatusCode::INTERNAL_SERVER_ERROR, format!("Failed to load API keys: {}", e)).into_response()
        }
    }
}

async fn save_api_key_handler(Json(request): Json<models::SaveApiKeyRequest>) -> impl IntoResponse {
    // Encrypt the API key before saving
    let encrypted_key = services::encrypt_api_key(&request.api_key);

    match services::save_api_key(&request.service, &encrypted_key).await {
        Ok(_) => {
            (StatusCode::OK, Json(serde_json::json!({
                "message": format!("API key for {} saved successfully", request.service),
                "service": request.service
            }))).into_response()
        },
        Err(e) => {
            (StatusCode::INTERNAL_SERVER_ERROR, format!("Failed to save API key: {}", e)).into_response()
        }
    }
}

async fn delete_api_key_handler(Path(service): Path<String>) -> impl IntoResponse {
    match services::delete_api_key(&service).await {
        Ok(_) => {
            (StatusCode::OK, Json(serde_json::json!({
                "message": format!("API key for {} deleted successfully", service),
                "service": service
            }))).into_response()
        },
        Err(e) => {
            (StatusCode::INTERNAL_SERVER_ERROR, format!("Failed to delete API key: {}", e)).into_response()
        }
    }
}