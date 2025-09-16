use serde::{Deserialize, Serialize};
use reqwest::Client;
use anyhow::{Result, Context};
use std::env;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum DropdownType {
    StandardSelect,
    CustomDiv,
    ReactComponent,
    VueComponent,
    AriaDropdown,
    MultiSelect,
    SearchableDropdown,
    CascadingDropdown,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum InteractionStrategy {
    DirectSelect,
    ClickToOpen,
    KeyboardNavigation,
    TypeToSearch,
    MultiStep,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DropdownAnalysis {
    pub dropdown_type: DropdownType,
    pub interaction_strategy: InteractionStrategy,
    pub trigger_selector: Option<String>,
    pub options_container_selector: Option<String>,
    pub requires_scroll: bool,
    pub is_dynamic: bool,
    pub confidence: f32,
    pub reasoning: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FailureAnalysis {
    pub likely_cause: String,
    pub suggested_fixes: Vec<String>,
    pub alternative_selectors: Vec<String>,
    pub retry_strategy: InteractionStrategy,
    pub confidence: f32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoadingStrategy {
    pub has_dynamic_loading: bool,
    pub loading_indicators: Vec<String>,
    pub estimated_wait_time: u32,
    pub trigger_conditions: Vec<String>,
}

#[derive(Debug, Serialize)]
struct OpenRouterRequest {
    model: String,
    messages: Vec<Message>,
    max_tokens: Option<u32>,
    temperature: Option<f32>,
}

#[derive(Debug, Serialize)]
struct Message {
    role: String,
    content: String,
}

#[derive(Debug, Deserialize)]
struct OpenRouterResponse {
    choices: Vec<Choice>,
    usage: Option<Usage>,
}

#[derive(Debug, Deserialize)]
struct Choice {
    message: ResponseMessage,
}

#[derive(Debug, Deserialize)]
struct ResponseMessage {
    content: String,
}

#[derive(Debug, Deserialize)]
struct Usage {
    prompt_tokens: u32,
    completion_tokens: u32,
    total_tokens: u32,
}

pub struct OpenRouterClient {
    client: Client,
    api_key: String,
    base_url: String,
}

impl OpenRouterClient {
    pub async fn new() -> Result<Self> {
        // Try to get API key from local file first, then fallback to environment variable
        let api_key = match crate::services::get_openrouter_key().await {
            Some(key) => key,
            None => env::var("OPENROUTER_API_KEY")
                .context("OPENROUTER_API_KEY not found in local storage or environment variables")?
        };

        Ok(Self {
            client: Client::new(),
            api_key,
            base_url: "https://openrouter.ai/api/v1".to_string(),
        })
    }

    pub async fn generate_form_analysis(&self, form_html: &str, url: &str) -> Result<String> {
        self.generate_form_analysis_with_model(form_html, url, "anthropic/claude-3.5-sonnet").await
    }

    pub async fn generate_form_analysis_with_model(&self, form_html: &str, url: &str, model: &str) -> Result<String> {
        let prompt = format!(
            "Analyze this form from {} and provide form filling instructions:\n\n{}\n\n\
            Please provide a JSON response with field mappings and automation strategy.",
            url, form_html
        );

        self.chat_completion(
            model,
            &prompt,
            Some(2000),
            Some(0.3)
        ).await
    }

    pub async fn generate_field_mapping(&self, form_html: &str) -> Result<String> {
        self.generate_field_mapping_with_model(form_html, "anthropic/claude-3.5-sonnet").await
    }

    pub async fn generate_field_mapping_with_model(&self, form_html: &str, model: &str) -> Result<String> {
        let prompt = format!(
            "Generate field mappings for this form HTML:\n\n{}\n\n\
            Return a JSON object mapping field names to selectors and field types.",
            form_html
        );

        self.chat_completion(
            model,
            &prompt,
            Some(1500),
            Some(0.2)
        ).await
    }

    pub async fn analyze_dropdown_options(&self, dropdown_html: &str, field_name: &str, user_value: &str, form_context: Option<&str>, model: &str) -> Result<String> {
        let context_info = form_context.map(|c| format!("\n\nForm context:\n{}", c)).unwrap_or_default();

        let prompt = format!(
            "Analyze this dropdown/select element and determine the best option to select:\n\n\
            Field name: '{}'\n\
            User wants to enter: '{}'\n\
            Dropdown HTML: {}{}\n\n\
            Please respond with a JSON object containing:\n\
            - \"suggested_option\": the exact option value/text that best matches the user's input\n\
            - \"confidence\": a number from 0.0 to 1.0 indicating confidence in the selection\n\
            - \"reasoning\": explanation of why this option was chosen\n\n\
            Look for exact matches first, then partial matches, then semantic matches. \
            Consider common abbreviations and variations (e.g., 'US' for 'United States', 'CA' for 'California').",
            field_name, user_value, dropdown_html, context_info
        );

        self.chat_completion(
            model,
            &prompt,
            Some(1000),
            Some(0.3)
        ).await
    }

    pub async fn detect_dropdown_type(&self, element_html: &str, surrounding_context: Option<&str>) -> Result<DropdownAnalysis> {
        let context = surrounding_context.unwrap_or("");

        let prompt = format!(
            "Analyze this HTML element and determine what type of dropdown it is and how to interact with it:\n\n\
            Element HTML:\n{}\n\n\
            Surrounding context:\n{}\n\n\
            Please respond with a JSON object containing:\n\
            - \"dropdown_type\": one of [\"StandardSelect\", \"CustomDiv\", \"ReactComponent\", \"VueComponent\", \"AriaDropdown\", \"MultiSelect\", \"SearchableDropdown\", \"CascadingDropdown\"]\n\
            - \"interaction_strategy\": one of [\"DirectSelect\", \"ClickToOpen\", \"KeyboardNavigation\", \"TypeToSearch\", \"MultiStep\"]\n\
            - \"trigger_selector\": CSS selector for the element to click to open dropdown (if applicable)\n\
            - \"options_container_selector\": CSS selector for the container holding options (if different from trigger)\n\
            - \"requires_scroll\": boolean indicating if scrolling is needed to see all options\n\
            - \"is_dynamic\": boolean indicating if options load dynamically\n\
            - \"confidence\": number from 0.0 to 1.0 indicating confidence in analysis\n\
            - \"reasoning\": explanation of the analysis\n\n\
            Look for patterns like:\n\
            - Standard <select> elements\n\
            - Custom divs with role=\"combobox\" or role=\"listbox\"\n\
            - React/Vue component patterns (data-* attributes, specific class names)\n\
            - ARIA accessibility patterns\n\
            - Multi-select indicators\n\
            - Search input fields within dropdowns",
            element_html, context
        );

        let response = self.chat_completion("anthropic/claude-3.5-sonnet", &prompt, Some(1500), Some(0.2)).await?;

        serde_json::from_str::<DropdownAnalysis>(&response)
            .map_err(|e| anyhow::anyhow!("Failed to parse dropdown analysis: {}", e))
    }

    pub async fn suggest_interaction_strategy(&self, dropdown_html: &str, previous_failures: Option<&str>) -> Result<InteractionStrategy> {
        let failure_context = previous_failures
            .map(|f| format!("\n\nPrevious failed attempts:\n{}", f))
            .unwrap_or_default();

        let prompt = format!(
            "Given this dropdown HTML and any previous failures, suggest the best interaction strategy:\n\n\
            Dropdown HTML:\n{}\n{}\n\n\
            Please respond with a JSON object containing:\n\
            - \"strategy\": one of [\"DirectSelect\", \"ClickToOpen\", \"KeyboardNavigation\", \"TypeToSearch\", \"MultiStep\"]\n\
            - \"steps\": array of specific steps to take\n\
            - \"confidence\": number from 0.0 to 1.0\n\
            - \"reasoning\": explanation of why this strategy was chosen\n\n\
            Consider:\n\
            - If it's a standard <select>, use DirectSelect\n\
            - If it's a custom dropdown, likely needs ClickToOpen\n\
            - If it has search functionality, use TypeToSearch\n\
            - If it has complex interactions, use MultiStep\n\
            - Learn from previous failures to avoid repeating mistakes",
            dropdown_html, failure_context
        );

        let response = self.chat_completion("anthropic/claude-3.5-sonnet", &prompt, Some(1000), Some(0.2)).await?;

        #[derive(Deserialize)]
        struct StrategyResponse {
            strategy: InteractionStrategy,
        }

        let parsed: StrategyResponse = serde_json::from_str(&response)
            .map_err(|e| anyhow::anyhow!("Failed to parse strategy response: {}", e))?;

        Ok(parsed.strategy)
    }

    pub async fn analyze_selection_failure(&self, page_html: &str, dropdown_selector: &str, attempted_value: &str, error_message: &str) -> Result<FailureAnalysis> {
        let prompt = format!(
            "Analyze why this dropdown selection failed and suggest fixes:\n\n\
            Dropdown selector: {}\n\
            Attempted value: {}\n\
            Error message: {}\n\n\
            Relevant page HTML:\n{}\n\n\
            Please respond with a JSON object containing:\n\
            - \"likely_cause\": string describing the most probable reason for failure\n\
            - \"suggested_fixes\": array of specific actions to try\n\
            - \"alternative_selectors\": array of alternative CSS selectors to try\n\
            - \"retry_strategy\": one of [\"DirectSelect\", \"ClickToOpen\", \"KeyboardNavigation\", \"TypeToSearch\", \"MultiStep\"]\n\
            - \"confidence\": number from 0.0 to 1.0\n\n\
            Common failure causes:\n\
            - Selector targets wrong element\n\
            - Dropdown needs to be opened first\n\
            - Options are loaded dynamically\n\
            - Value format doesn't match option format\n\
            - Timing issues with page loading\n\
            - JavaScript event handlers not triggered properly",
            dropdown_selector, attempted_value, error_message, page_html
        );

        let response = self.chat_completion("anthropic/claude-3.5-sonnet", &prompt, Some(1500), Some(0.3)).await?;

        serde_json::from_str::<FailureAnalysis>(&response)
            .map_err(|e| anyhow::anyhow!("Failed to parse failure analysis: {}", e))
    }

    pub async fn detect_dynamic_loading(&self, page_html: &str, dropdown_selector: &str) -> Result<LoadingStrategy> {
        let prompt = format!(
            "Analyze if this dropdown loads options dynamically and how to detect when loading is complete:\n\n\
            Dropdown selector: {}\n\
            Page HTML context:\n{}\n\n\
            Please respond with a JSON object containing:\n\
            - \"has_dynamic_loading\": boolean indicating if options load asynchronously\n\
            - \"loading_indicators\": array of selectors or text that indicate loading is in progress\n\
            - \"estimated_wait_time\": estimated milliseconds to wait for loading to complete\n\
            - \"trigger_conditions\": array of actions that trigger option loading (e.g., \"click\", \"focus\", \"input\")\n\n\
            Look for:\n\
            - Loading spinners or indicators\n\
            - Empty option lists that might populate later\n\
            - AJAX/fetch calls in JavaScript\n\
            - Event listeners that might trigger loading\n\
            - Placeholder text like 'Loading...' or 'Please wait'",
            dropdown_selector, page_html
        );

        let response = self.chat_completion("anthropic/claude-3.5-sonnet", &prompt, Some(1200), Some(0.2)).await?;

        serde_json::from_str::<LoadingStrategy>(&response)
            .map_err(|e| anyhow::anyhow!("Failed to parse loading strategy: {}", e))
    }

    pub async fn enhance_option_matching(&self, dropdown_html: &str, user_value: &str, field_context: &str) -> Result<String> {
        let prompt = format!(
            "Find the best matching option for this dropdown using advanced semantic understanding:\n\n\
            Field context: {}\n\
            User wants to enter: '{}'\n\
            Dropdown HTML: {}\n\n\
            Please respond with a JSON object containing:\n\
            - \"exact_match\": the option that matches exactly (if any)\n\
            - \"fuzzy_matches\": array of options that partially match\n\
            - \"semantic_matches\": array of options that match semantically (e.g., 'USA' for 'United States')\n\
            - \"recommended_option\": the single best option to select\n\
            - \"confidence\": number from 0.0 to 1.0\n\
            - \"reasoning\": detailed explanation of the matching logic\n\n\
            Consider these matching strategies:\n\
            1. Exact text match (case insensitive)\n\
            2. Exact value attribute match\n\
            3. Partial text matching\n\
            4. Common abbreviations (CA → California, US → United States, etc.)\n\
            5. Synonyms and alternate names\n\
            6. Language variations\n\
            7. Context-based matching (e.g., if field is 'country', prefer country names)",
            field_context, user_value, dropdown_html
        );

        self.chat_completion("anthropic/claude-3.5-sonnet", &prompt, Some(1500), Some(0.2)).await
    }

    pub async fn chat_completion(
        &self,
        model: &str,
        prompt: &str,
        max_tokens: Option<u32>,
        temperature: Option<f32>
    ) -> Result<String> {
        let request = OpenRouterRequest {
            model: model.to_string(),
            messages: vec![Message {
                role: "user".to_string(),
                content: prompt.to_string(),
            }],
            max_tokens,
            temperature,
        };

        let response = self.client
            .post(&format!("{}/chat/completions", self.base_url))
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("HTTP-Referer", "https://formai.dev")
            .header("X-Title", "FormAI")
            .json(&request)
            .send()
            .await
            .context("Failed to send request to OpenRouter")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            return Err(anyhow::anyhow!(
                "OpenRouter API error: {} - {}",
                status,
                error_text
            ));
        }

        let openrouter_response: OpenRouterResponse = response
            .json()
            .await
            .context("Failed to parse OpenRouter response")?;

        openrouter_response
            .choices
            .first()
            .map(|choice| choice.message.content.clone())
            .ok_or_else(|| anyhow::anyhow!("No response content received"))
    }
}