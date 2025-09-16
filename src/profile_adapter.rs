use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{Utc, Datelike};
use rand::Rng;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldMapping {
    pub selectors: Vec<String>,
    pub field_type: String,
    pub priority: String,
    pub profile_mappings: Option<Vec<String>>,
    pub fallback_values: Option<Vec<String>>,
    pub fallback_generation: Option<String>,
    pub max_length: Option<usize>,
    pub format: Option<String>,
    pub required: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FormTemplate {
    pub id: String,
    pub template_name: String,
    pub url_pattern: String,
    pub fields: HashMap<String, FieldMapping>,
    pub generation_rules: Option<HashMap<String, serde_json::Value>>,
    pub fill_strategy: Option<serde_json::Value>,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct ProfileAdapter {
    pub profile_data: HashMap<String, String>,
    pub template: FormTemplate,
}

#[allow(dead_code)]
impl ProfileAdapter {
    pub fn new(profile_data: HashMap<String, String>, template: FormTemplate) -> Self {
        Self {
            profile_data,
            template,
        }
    }

    /// Get value for a field by checking profile mappings and fallbacks
    pub fn get_field_value(&self, field_name: &str) -> Option<String> {
        if let Some(field_mapping) = self.template.fields.get(field_name) {
            // First, try to get value from profile using mapping priority
            if let Some(profile_mappings) = &field_mapping.profile_mappings {
                for mapping in profile_mappings {
                    if let Some(value) = self.profile_data.get(mapping) {
                        if !value.is_empty() {
                            return Some(self.format_value(value, field_mapping));
                        }
                    }
                }
            }

            // If no profile value found, try generation rules
            if let Some(generation_rule) = &field_mapping.fallback_generation {
                if let Some(generated_value) = self.generate_value(generation_rule, field_name) {
                    return Some(generated_value);
                }
            }

            // Finally, use fallback values
            if let Some(fallback_values) = &field_mapping.fallback_values {
                if !fallback_values.is_empty() {
                    let fallback = &fallback_values[0];
                    if !fallback.is_empty() {
                        return Some(fallback.clone());
                    }
                }
            }
        }

        None
    }

    /// Format value according to field requirements
    fn format_value(&self, value: &str, field_mapping: &FieldMapping) -> String {
        let mut formatted_value = value.to_string();

        if let Some(format_type) = &field_mapping.format {
            formatted_value = match format_type.as_str() {
                "single_char_lowercase" => {
                    if let Some(first_char) = formatted_value.chars().next() {
                        first_char.to_lowercase().to_string()
                    } else {
                        formatted_value
                    }
                }
                "first_char_uppercase" => {
                    if let Some(first_char) = formatted_value.chars().next() {
                        first_char.to_uppercase().to_string()
                    } else {
                        formatted_value
                    }
                }
                "alphanumeric_lowercase" => {
                    formatted_value.chars()
                        .filter(|c| c.is_alphanumeric())
                        .collect::<String>()
                        .to_lowercase()
                }
                "phone_us" => self.format_phone_us(&formatted_value),
                "email_format" => {
                    if formatted_value.contains('@') {
                        formatted_value
                    } else {
                        format!("{}@example.com", formatted_value)
                    }
                }
                "url" => {
                    if formatted_value.starts_with("http") {
                        formatted_value
                    } else if formatted_value.starts_with("www.") {
                        formatted_value
                    } else {
                        format!("www.{}", formatted_value)
                    }
                }
                "zero_padded" => {
                    if let Ok(num) = formatted_value.parse::<u32>() {
                        format!("{:02}", num)
                    } else {
                        formatted_value
                    }
                }
                "four_digit_year" => {
                    if formatted_value.len() == 4 {
                        formatted_value
                    } else if formatted_value.len() == 2 {
                        format!("20{}", formatted_value)
                    } else {
                        formatted_value
                    }
                }
                "month_abbrev" => self.format_month_abbrev(&formatted_value),
                "numeric" => formatted_value.chars().filter(|c| c.is_numeric()).collect(),
                "integer" => formatted_value.parse::<i32>().unwrap_or(0).to_string(),
                _ => formatted_value,
            }
        }

        // Apply max length if specified
        if let Some(max_len) = field_mapping.max_length {
            if formatted_value.len() > max_len {
                formatted_value.truncate(max_len);
            }
        }

        formatted_value
    }

    /// Generate value based on generation rules
    fn generate_value(&self, generation_rule: &str, field_name: &str) -> Option<String> {
        match generation_rule {
            "combine_first_last" => {
                let first = self.get_profile_value(&["firstName", "first_name", "fname"])?;
                let last = self.get_profile_value(&["lastName", "last_name", "lname"])?;
                Some(format!("{} {}", first, last))
            }
            "generate_from_name" => {
                let first = self.get_profile_value(&["firstName", "first_name", "fname"])
                    .unwrap_or_else(|| "user".to_string());
                let last = self.get_profile_value(&["lastName", "last_name", "lname"])
                    .unwrap_or_else(|| "example".to_string());

                match field_name {
                    "email" => Some(format!("{}.{}@example.com", first.to_lowercase(), last.to_lowercase())),
                    "username" => Some(format!("{}{}", first.to_lowercase(), last.to_lowercase())),
                    "website" => Some(format!("www.{}{}.dev", first.to_lowercase(), last.to_lowercase())),
                    _ => None,
                }
            }
            "use_full_name" => {
                Some(self.get_profile_value(&["fullName", "full_name", "name"])
                     .or_else(|| {
                         let first = self.get_profile_value(&["firstName", "first_name"])?;
                         let last = self.get_profile_value(&["lastName", "last_name"])?;
                         Some(format!("{} {}", first, last))
                     })
                     .unwrap_or_else(|| "John Smith".to_string()))
            }
            "use_city_state" => {
                let city = self.get_profile_value(&["city"]).unwrap_or_else(|| "New York".to_string());
                let state = self.get_profile_value(&["state", "province"]).unwrap_or_else(|| "NY".to_string());
                Some(format!("{}, {}", city, state))
            }
            "calculate_from_birth_year" => {
                if let Some(birth_year_str) = self.get_profile_value(&["birthYear", "birth_year"]) {
                    if let Ok(birth_year) = birth_year_str.parse::<i32>() {
                        let current_year = Utc::now().year();
                        let age = current_year - birth_year;
                        return Some(age.to_string());
                    }
                }
                Some("25".to_string())
            }
            "generate_secure" => {
                Some(self.generate_secure_password())
            }
            "random_month" => {
                let months = vec!["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                let mut rng = rand::thread_rng();
                Some(months[rng.gen_range(0..months.len())].to_string())
            }
            "random_day" => {
                let mut rng = rand::thread_rng();
                Some(format!("{:02}", rng.gen_range(1..29)))
            }
            "adult_birth_year" => {
                let mut rng = rand::thread_rng();
                let current_year = Utc::now().year();
                let age = rng.gen_range(25..55);
                Some((current_year - age).to_string())
            }
            "future_month" => {
                let mut rng = rand::thread_rng();
                Some(format!("{:02}", rng.gen_range(1..13)))
            }
            "future_year" => {
                let current_year = Utc::now().year();
                let mut rng = rand::thread_rng();
                Some((current_year + rng.gen_range(2..6)).to_string())
            }
            "random_3_digit" => {
                let mut rng = rand::thread_rng();
                Some(format!("{:03}", rng.gen_range(100..1000)))
            }
            "generate_realistic_income" => {
                let mut rng = rand::thread_rng();
                let income = rng.gen_range(35000..150000);
                Some((income / 1000 * 1000).to_string()) // Round to nearest thousand
            }
            "generate_fake_ssn" => {
                let mut rng = rand::thread_rng();
                Some(format!("{:03}-{:02}-{:04}", 
                           rng.gen_range(100..999),
                           rng.gen_range(10..99),
                           rng.gen_range(1000..9999)))
            }
            "generate_license" => {
                let mut rng = rand::thread_rng();
                Some(format!("D{:09}", rng.gen_range(100000000..999999999)))
            }
            _ => None,
        }
    }

    /// Get profile value from multiple possible field names
    fn get_profile_value(&self, field_names: &[&str]) -> Option<String> {
        for field_name in field_names {
            if let Some(value) = self.profile_data.get(*field_name) {
                if !value.is_empty() {
                    return Some(value.clone());
                }
            }
        }
        None
    }

    /// Format phone number to US format
    fn format_phone_us(&self, phone: &str) -> String {
        let digits: String = phone.chars().filter(|c| c.is_numeric()).collect();
        
        if digits.len() == 10 {
            format!("({}) {}-{}", &digits[0..3], &digits[3..6], &digits[6..10])
        } else if digits.len() == 11 && digits.starts_with('1') {
            format!("({}) {}-{}", &digits[1..4], &digits[4..7], &digits[7..11])
        } else {
            phone.to_string()
        }
    }

    /// Format month to abbreviation
    fn format_month_abbrev(&self, month: &str) -> String {
        match month.to_lowercase().as_str() {
            "january" | "jan" | "1" | "01" => "Jan".to_string(),
            "february" | "feb" | "2" | "02" => "Feb".to_string(),
            "march" | "mar" | "3" | "03" => "Mar".to_string(),
            "april" | "apr" | "4" | "04" => "Apr".to_string(),
            "may" | "5" | "05" => "May".to_string(),
            "june" | "jun" | "6" | "06" => "Jun".to_string(),
            "july" | "jul" | "7" | "07" => "Jul".to_string(),
            "august" | "aug" | "8" | "08" => "Aug".to_string(),
            "september" | "sep" | "9" | "09" => "Sep".to_string(),
            "october" | "oct" | "10" => "Oct".to_string(),
            "november" | "nov" | "11" => "Nov".to_string(),
            "december" | "dec" | "12" => "Dec".to_string(),
            _ => month.to_string(),
        }
    }

    /// Generate a secure password
    fn generate_secure_password(&self) -> String {
        let mut rng = rand::thread_rng();
        let adjectives = vec!["Quick", "Smart", "Strong", "Bright", "Swift"];
        let nouns = vec!["Lion", "Eagle", "Tiger", "Wolf", "Bear"];
        let adjective = &adjectives[rng.gen_range(0..adjectives.len())];
        let noun = &nouns[rng.gen_range(0..nouns.len())];
        let number = rng.gen_range(100..999);
        let symbols = vec!["!", "@", "#", "$", "%"];
        let symbol = &symbols[rng.gen_range(0..symbols.len())];
        
        format!("{}{}{}{}", adjective, noun, number, symbol)
    }

    /// Get all form values for filling
    pub fn get_form_values(&self) -> HashMap<String, String> {
        let mut values = HashMap::new();
        
        for (field_name, _field_mapping) in &self.template.fields {
            if let Some(value) = self.get_field_value(field_name) {
                values.insert(field_name.clone(), value);
            }
        }
        
        values
    }

}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_profile_adapter_basic() {
        let mut profile_data = HashMap::new();
        profile_data.insert("firstName".to_string(), "John".to_string());
        profile_data.insert("lastName".to_string(), "Doe".to_string());

        let mut fields = HashMap::new();
        let field_mapping = FieldMapping {
            selectors: vec!["input[name='firstName']".to_string()],
            field_type: "text".to_string(),
            priority: "high".to_string(),
            profile_mappings: Some(vec!["firstName".to_string()]),
            fallback_values: Some(vec!["DefaultFirst".to_string()]),
            fallback_generation: None,
            max_length: Some(50),
            format: None,
            required: Some(true),
        };
        fields.insert("firstName".to_string(), field_mapping);

        let template = FormTemplate {
            id: "test".to_string(),
            template_name: "Test Template".to_string(),
            url_pattern: "test.com".to_string(),
            fields,
            generation_rules: None,
            fill_strategy: None,
        };

        let adapter = ProfileAdapter::new(profile_data, template);
        assert_eq!(adapter.get_field_value("firstName"), Some("John".to_string()));
    }

    #[test]
    fn test_fallback_generation() {
        let mut profile_data = HashMap::new();
        profile_data.insert("firstName".to_string(), "John".to_string());
        profile_data.insert("lastName".to_string(), "Doe".to_string());

        let mut fields = HashMap::new();
        let field_mapping = FieldMapping {
            selectors: vec!["input[name='fullName']".to_string()],
            field_type: "text".to_string(),
            priority: "high".to_string(),
            profile_mappings: Some(vec!["fullName".to_string()]),
            fallback_values: None,
            fallback_generation: Some("combine_first_last".to_string()),
            max_length: None,
            format: None,
            required: None,
        };
        fields.insert("fullName".to_string(), field_mapping);

        let template = FormTemplate {
            id: "test".to_string(),
            template_name: "Test Template".to_string(),
            url_pattern: "test.com".to_string(),
            fields,
            generation_rules: None,
            fill_strategy: None,
        };

        let adapter = ProfileAdapter::new(profile_data, template);
        assert_eq!(adapter.get_field_value("fullName"), Some("John Doe".to_string()));
    }
}