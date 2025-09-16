use crate::openrouter::{OpenRouterClient, InteractionStrategy, DropdownAnalysis};
use crate::AppState;
use crate::models::WebSocketMessage;
use crate::websocket::broadcast_automation_message;
use playwright::api::Page;
use anyhow::{Result, Context};
use chrono::Utc;
use serde_json;
use std::collections::HashMap;

pub struct SmartDropdownService {
    openrouter_client: OpenRouterClient,
    dropdown_cache: HashMap<String, DropdownAnalysis>,
}

impl SmartDropdownService {
    pub async fn new() -> Result<Self> {
        Ok(Self {
            openrouter_client: OpenRouterClient::new().await?,
            dropdown_cache: HashMap::new(),
        })
    }

    pub async fn analyze_and_select_dropdown(
        &mut self,
        page: &Page,
        selector: &str,
        value: &str,
        field_name: &str,
        state: &AppState,
    ) -> Result<()> {
        let detection_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🤖 Using AI-enhanced dropdown detection for field: '{}'", field_name),
        };
        let _ = broadcast_automation_message(state, detection_message).await;

        // Step 1: Get dropdown HTML and surrounding context
        let (dropdown_html, surrounding_context) = self.extract_dropdown_context(page, selector).await?;

        // Step 2: Check cache first
        let cache_key = format!("{}:{}", selector, dropdown_html.len());
        let analysis = if let Some(cached) = self.dropdown_cache.get(&cache_key) {
            let cache_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("📋 Using cached analysis for dropdown type: {:?}", cached.dropdown_type),
            };
            let _ = broadcast_automation_message(state, cache_message).await;
            cached.clone()
        } else {
            // Step 3: Analyze dropdown type with AI
            let analysis = self.openrouter_client
                .detect_dropdown_type(&dropdown_html, Some(&surrounding_context))
                .await
                .context("Failed to analyze dropdown type")?;

            let analysis_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("🔍 AI detected dropdown type: {:?}, strategy: {:?} (confidence: {:.1}%)",
                    analysis.dropdown_type, analysis.interaction_strategy, analysis.confidence * 100.0),
            };
            let _ = broadcast_automation_message(state, analysis_message).await;

            // Cache the analysis
            self.dropdown_cache.insert(cache_key, analysis.clone());
            analysis
        };

        // Step 4: Check if dynamic loading is needed
        if analysis.is_dynamic {
            self.handle_dynamic_loading(page, selector, &analysis, state).await?;
        }

        // Step 5: Execute interaction strategy
        self.execute_interaction_strategy(page, selector, value, field_name, &analysis, state).await
    }

    async fn extract_dropdown_context(&self, page: &Page, selector: &str) -> Result<(String, String)> {
        // Get the dropdown element HTML
        let dropdown_html = page.inner_html(selector, Some(5000.0)).await
            .with_context(|| format!("Failed to get dropdown HTML for selector: {}", selector))?;

        // Get surrounding context (parent elements, siblings)
        let context_js = format!(r#"
            const element = document.querySelector('{}');
            if (!element) return '';

            // Get parent element and siblings for context
            const parent = element.parentElement;
            const context = {{
                parent: parent ? parent.outerHTML : '',
                siblings: Array.from(parent?.children || [])
                    .filter(el => el !== element)
                    .slice(0, 3)
                    .map(el => el.outerHTML),
                attributes: Array.from(element.attributes).map(attr => `${{attr.name}}="${{attr.value}}"`),
                classes: element.className,
                id: element.id
            }};

            return JSON.stringify(context);
        "#, selector);

        let surrounding_context = page.evaluate(&context_js, serde_json::Value::Null).await
            .unwrap_or_else(|_| serde_json::Value::String("".to_string()))
            .as_str()
            .unwrap_or("")
            .to_string();

        Ok((dropdown_html, surrounding_context))
    }

    async fn handle_dynamic_loading(
        &self,
        page: &Page,
        selector: &str,
        analysis: &DropdownAnalysis,
        state: &AppState,
    ) -> Result<()> {
        let loading_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("⏳ Detected dynamic loading dropdown, checking load strategy..."),
        };
        let _ = broadcast_automation_message(state, loading_message).await;

        // Get current page HTML for loading analysis
        let page_html = page.content().await.unwrap_or_default();

        let loading_strategy = self.openrouter_client
            .detect_dynamic_loading(&page_html, selector)
            .await
            .context("Failed to analyze dynamic loading")?;

        if loading_strategy.has_dynamic_loading {
            let wait_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("⏱️ Waiting {}ms for dynamic content to load...", loading_strategy.estimated_wait_time),
            };
            let _ = broadcast_automation_message(state, wait_message).await;

            // Trigger loading if needed
            for trigger in &loading_strategy.trigger_conditions {
                match trigger.as_str() {
                    "click" => {
                        let _ = page.click_builder(selector).click().await;
                    },
                    "focus" => {
                        let _ = page.focus(selector, None).await;
                    },
                    "hover" => {
                        // Note: hover functionality simplified for now
                        let _ = page.click_builder(selector).click().await;
                    },
                    _ => {}
                }
            }

            // Wait for loading to complete
            tokio::time::sleep(tokio::time::Duration::from_millis(loading_strategy.estimated_wait_time as u64)).await;

            // Check for loading indicators to disappear
            for indicator in &loading_strategy.loading_indicators {
                let _ = page.wait_for_selector_builder(indicator)
                    .timeout(5000.0)
                    .wait_for_selector()
                    .await;
            }
        }

        Ok(())
    }

    async fn execute_interaction_strategy(
        &self,
        page: &Page,
        selector: &str,
        value: &str,
        field_name: &str,
        analysis: &DropdownAnalysis,
        state: &AppState,
    ) -> Result<()> {
        let strategy_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🎯 Executing {:?} strategy for '{}'", analysis.interaction_strategy, field_name),
        };
        let _ = broadcast_automation_message(state, strategy_message).await;

        match analysis.interaction_strategy {
            InteractionStrategy::DirectSelect => {
                self.execute_direct_select(page, selector, value, field_name, state).await
            },
            InteractionStrategy::ClickToOpen => {
                self.execute_click_to_open(page, selector, value, field_name, analysis, state).await
            },
            InteractionStrategy::KeyboardNavigation => {
                self.execute_keyboard_navigation(page, selector, value, field_name, state).await
            },
            InteractionStrategy::TypeToSearch => {
                self.execute_type_to_search(page, selector, value, field_name, analysis, state).await
            },
            InteractionStrategy::MultiStep => {
                self.execute_multi_step(page, selector, value, field_name, analysis, state).await
            },
        }
    }

    async fn execute_direct_select(
        &self,
        page: &Page,
        selector: &str,
        value: &str,
        field_name: &str,
        state: &AppState,
    ) -> Result<()> {
        // First, enhance option matching with AI
        let dropdown_html = page.inner_html(selector, Some(5000.0)).await?;
        let enhanced_match = self.openrouter_client
            .enhance_option_matching(&dropdown_html, value, field_name)
            .await?;

        #[derive(serde::Deserialize)]
        struct MatchResult {
            recommended_option: String,
            confidence: f32,
            reasoning: String,
        }

        let match_result: MatchResult = serde_json::from_str(&enhanced_match)
            .context("Failed to parse enhanced matching result")?;

        let match_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🎯 AI recommended option: '{}' (confidence: {:.1}%) - {}",
                match_result.recommended_option, match_result.confidence * 100.0, match_result.reasoning),
        };
        let _ = broadcast_automation_message(state, match_message).await;

        // Try selecting with the AI-recommended option
        let result = page.select_option_builder(selector)
            .add_value(match_result.recommended_option.clone())
            .select_option()
            .await;

        match result {
            Ok(_) => {
                let success_message = WebSocketMessage::ScriptLog {
                    timestamp: Utc::now(),
                    message: format!("✅ Successfully selected '{}' in dropdown '{}'", match_result.recommended_option, field_name),
                };
                let _ = broadcast_automation_message(state, success_message).await;
                Ok(())
            },
            Err(_e) => {
                // Fallback to original value if AI recommendation fails
                let fallback_result = page.select_option_builder(selector)
                    .add_value(value.to_string())
                    .select_option()
                    .await;

                match fallback_result {
                    Ok(_) => Ok(()),
                    Err(e) => Err(anyhow::anyhow!("Direct select failed: {}", e))
                }
            }
        }
    }

    async fn execute_click_to_open(
        &self,
        page: &Page,
        selector: &str,
        value: &str,
        field_name: &str,
        analysis: &DropdownAnalysis,
        state: &AppState,
    ) -> Result<()> {
        // Step 1: Click to open dropdown
        let default_selector = selector.to_string();
        let trigger_selector = analysis.trigger_selector.as_ref().unwrap_or(&default_selector);

        page.click_builder(trigger_selector).click().await
            .context("Failed to click dropdown trigger")?;

        // Step 2: Wait for options to appear
        tokio::time::sleep(tokio::time::Duration::from_millis(300)).await;

        // Step 3: Find and click the option
        let default_container = selector.to_string();
        let options_container = analysis.options_container_selector.as_ref().unwrap_or(&default_container);

        // Enhanced option finding with AI
        let dropdown_html = page.inner_html(options_container, Some(5000.0)).await?;
        let enhanced_match = self.openrouter_client
            .enhance_option_matching(&dropdown_html, value, field_name)
            .await?;

        #[derive(serde::Deserialize)]
        struct MatchResult {
            recommended_option: String,
        }

        let match_result: MatchResult = serde_json::from_str(&enhanced_match)
            .context("Failed to parse enhanced matching result")?;

        // Try to click the recommended option
        let option_click_js = format!(r#"
            const container = document.querySelector('{}');
            if (!container) return false;

            const options = container.querySelectorAll('div, li, span, a');
            for (const option of options) {{
                if (option.textContent?.trim() === '{}' ||
                    option.getAttribute('value') === '{}' ||
                    option.textContent?.trim().toLowerCase().includes('{}')) {{
                    option.click();
                    return true;
                }}
            }}
            return false;
        "#, options_container, match_result.recommended_option, match_result.recommended_option, value.to_lowercase());

        let clicked = page.evaluate(&option_click_js, serde_json::Value::Null).await
            .unwrap_or(serde_json::Value::Bool(false))
            .as_bool()
            .unwrap_or(false);

        if clicked {
            let success_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("✅ Successfully clicked option '{}' in dropdown '{}'", match_result.recommended_option, field_name),
            };
            let _ = broadcast_automation_message(state, success_message).await;
            Ok(())
        } else {
            Err(anyhow::anyhow!("Failed to find and click option: {}", value))
        }
    }

    async fn execute_keyboard_navigation(
        &self,
        page: &Page,
        selector: &str,
        value: &str,
        field_name: &str,
        state: &AppState,
    ) -> Result<()> {
        // Focus the dropdown
        page.focus(selector, None).await?;

        // Press Enter or Space to open
        page.keyboard.press("Space", None).await?;
        tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;

        // Type the first few characters to navigate
        if !value.is_empty() {
            page.keyboard.r#type(&value[..1.min(value.len())], None).await?;
            tokio::time::sleep(tokio::time::Duration::from_millis(300)).await;
        }

        // Press Enter to select
        page.keyboard.press("Enter", None).await?;

        let success_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("⌨️ Used keyboard navigation for dropdown '{}'", field_name),
        };
        let _ = broadcast_automation_message(state, success_message).await;

        Ok(())
    }

    async fn execute_type_to_search(
        &self,
        page: &Page,
        selector: &str,
        value: &str,
        field_name: &str,
        analysis: &DropdownAnalysis,
        state: &AppState,
    ) -> Result<()> {
        // Find search input within the dropdown
        let search_input_js = format!(r#"
            const dropdown = document.querySelector('{}');
            if (!dropdown) return null;

            const searchInput = dropdown.querySelector('input[type="text"], input[type="search"], input:not([type])');
            return searchInput ? searchInput.getAttribute('data-selector') || 'input' : null;
        "#, selector);

        let search_input_selector: Option<String> = page.evaluate(&search_input_js, serde_json::Value::Null).await
            .ok()
            .and_then(|v: serde_json::Value| v.as_str().map(|s| s.to_string()));

        if let Some(input_selector) = search_input_selector {
            // Type in search input
            page.fill_builder(&input_selector, value).fill().await?;
            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

            // Press Enter or click first result
            page.keyboard.press("Enter", None).await?;
        } else {
            // Fallback to typing in the main element
            page.click_builder(selector).click().await?;
            page.keyboard.r#type(value, None).await?;
            tokio::time::sleep(tokio::time::Duration::from_millis(300)).await;
            page.keyboard.press("Enter", None).await?;
        }

        let success_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🔍 Used type-to-search for dropdown '{}'", field_name),
        };
        let _ = broadcast_automation_message(state, success_message).await;

        Ok(())
    }

    async fn execute_multi_step(
        &self,
        page: &Page,
        selector: &str,
        value: &str,
        field_name: &str,
        analysis: &DropdownAnalysis,
        state: &AppState,
    ) -> Result<()> {
        let multi_step_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🔄 Executing multi-step interaction for complex dropdown '{}'", field_name),
        };
        let _ = broadcast_automation_message(state, multi_step_message).await;

        // Try each strategy in sequence until one works
        let strategies = [
            InteractionStrategy::ClickToOpen,
            InteractionStrategy::TypeToSearch,
            InteractionStrategy::KeyboardNavigation,
            InteractionStrategy::DirectSelect,
        ];

        for strategy in &strategies {
            let attempt_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("🔄 Trying {:?} as part of multi-step approach", strategy),
            };
            let _ = broadcast_automation_message(state, attempt_message).await;

            let mut temp_analysis = analysis.clone();
            temp_analysis.interaction_strategy = strategy.clone();

            let result = match strategy {
                InteractionStrategy::DirectSelect => self.execute_direct_select(page, selector, value, field_name, state).await,
                InteractionStrategy::ClickToOpen => self.execute_click_to_open(page, selector, value, field_name, &temp_analysis, state).await,
                InteractionStrategy::KeyboardNavigation => self.execute_keyboard_navigation(page, selector, value, field_name, state).await,
                InteractionStrategy::TypeToSearch => self.execute_type_to_search(page, selector, value, field_name, &temp_analysis, state).await,
                InteractionStrategy::MultiStep => continue, // Avoid infinite recursion
            };

            if result.is_ok() {
                return result;
            }

            // Wait before trying next strategy
            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
        }

        Err(anyhow::anyhow!("All multi-step strategies failed for dropdown: {}", field_name))
    }

    pub async fn handle_selection_failure(
        &self,
        page: &Page,
        selector: &str,
        attempted_value: &str,
        error_message: &str,
        field_name: &str,
        state: &AppState,
    ) -> Result<()> {
        let failure_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🚨 Analyzing dropdown selection failure for '{}'...", field_name),
        };
        let _ = broadcast_automation_message(state, failure_message).await;

        // Get current page HTML for failure analysis
        let page_html = page.content().await.unwrap_or_default();

        let failure_analysis = self.openrouter_client
            .analyze_selection_failure(&page_html, selector, attempted_value, error_message)
            .await
            .context("Failed to analyze selection failure")?;

        let analysis_message = WebSocketMessage::ScriptLog {
            timestamp: Utc::now(),
            message: format!("🔍 AI analysis: {} (confidence: {:.1}%)",
                failure_analysis.likely_cause, failure_analysis.confidence * 100.0),
        };
        let _ = broadcast_automation_message(state, analysis_message).await;

        // Try suggested fixes
        for (i, fix) in failure_analysis.suggested_fixes.iter().enumerate() {
            let fix_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("🔧 Trying fix #{}: {}", i + 1, fix),
            };
            let _ = broadcast_automation_message(state, fix_message).await;

            // Implementation of suggested fixes would go here
            // This is a framework for future enhancement
        }

        // Try alternative selectors
        for alt_selector in &failure_analysis.alternative_selectors {
            let alt_message = WebSocketMessage::ScriptLog {
                timestamp: Utc::now(),
                message: format!("🔄 Trying alternative selector: {}", alt_selector),
            };
            let _ = broadcast_automation_message(state, alt_message).await;

            if let Ok(_) = page.select_option_builder(alt_selector)
                .add_value(attempted_value.to_string())
                .select_option()
                .await
            {
                let success_message = WebSocketMessage::ScriptLog {
                    timestamp: Utc::now(),
                    message: format!("✅ Alternative selector worked: {}", alt_selector),
                };
                let _ = broadcast_automation_message(state, success_message).await;
                return Ok(());
            }
        }

        Err(anyhow::anyhow!("All failure recovery attempts failed"))
    }
}