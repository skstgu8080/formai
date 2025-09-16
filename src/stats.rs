use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use tokio::fs;
use anyhow::Result;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutomationStats {
    pub total_forms_filled: u32,
    pub success_rate: f32,
    pub average_speed_ms: u32,
    pub active_profiles: u32,
    pub total_profiles: u32,
    pub active_urls: u32,
    pub total_urls: u32,
    pub recent_activities: Vec<Activity>,
    pub daily_stats: Vec<DailyStat>,
    pub profile_performance: Vec<ProfilePerformance>,
    pub url_performance: Vec<UrlPerformance>,
    pub errors_today: u32,
    pub forms_today: u32,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Activity {
    pub timestamp: DateTime<Utc>,
    pub activity_type: String,
    pub description: String,
    pub status: String,
    pub duration_ms: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DailyStat {
    pub date: String,
    pub forms_filled: u32,
    pub success_rate: f32,
    pub average_speed_ms: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfilePerformance {
    pub profile_id: String,
    pub profile_name: String,
    pub usage_count: u32,
    pub success_rate: f32,
    pub last_used: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UrlPerformance {
    pub url: String,
    pub success_count: u32,
    pub failure_count: u32,
    pub average_time_ms: u32,
    pub last_tested: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatsTracker {
    stats_file: String,
    current_stats: AutomationStats,
}

impl StatsTracker {
    pub async fn new() -> Result<Self> {
        let stats_file = "stats/automation_stats.json".to_string();

        // Ensure stats directory exists
        fs::create_dir_all("stats").await?;

        // Load existing stats or create new
        let current_stats = match Self::load_stats(&stats_file).await {
            Ok(stats) => stats,
            Err(_) => Self::default_stats(),
        };

        Ok(Self {
            stats_file,
            current_stats,
        })
    }

    pub fn create_fallback() -> Self {
        Self {
            stats_file: String::new(),
            current_stats: Self::default_stats(),
        }
    }

    async fn load_stats(file_path: &str) -> Result<AutomationStats> {
        let content = fs::read_to_string(file_path).await?;
        let stats = serde_json::from_str(&content)?;
        Ok(stats)
    }

    fn default_stats() -> AutomationStats {
        AutomationStats {
            total_forms_filled: 0,
            success_rate: 0.0,
            average_speed_ms: 0,
            active_profiles: 0,
            total_profiles: 0,
            active_urls: 0,
            total_urls: 0,
            recent_activities: Vec::new(),
            daily_stats: Vec::new(),
            profile_performance: Vec::new(),
            url_performance: Vec::new(),
            errors_today: 0,
            forms_today: 0,
            last_updated: Utc::now(),
        }
    }

    pub async fn save_stats(&self) -> Result<()> {
        if self.stats_file.is_empty() {
            // Fallback mode - don't save to disk
            return Ok(());
        }
        let json = serde_json::to_string_pretty(&self.current_stats)?;
        fs::write(&self.stats_file, json).await?;
        Ok(())
    }

    pub fn get_stats(&self) -> AutomationStats {
        self.current_stats.clone()
    }

    pub async fn record_automation(&mut self,
        success: bool,
        duration_ms: u32,
        profile_name: &str,
        url: &str
    ) -> Result<()> {
        // Update total forms filled
        self.current_stats.total_forms_filled += 1;
        self.current_stats.forms_today += 1;

        if !success {
            self.current_stats.errors_today += 1;
        }

        // Update success rate
        let total = self.current_stats.total_forms_filled as f32;
        let current_successes = (self.current_stats.success_rate / 100.0 * (total - 1.0)) + if success { 1.0 } else { 0.0 };
        self.current_stats.success_rate = (current_successes / total) * 100.0;

        // Update average speed
        if self.current_stats.average_speed_ms == 0 {
            self.current_stats.average_speed_ms = duration_ms;
        } else {
            let current_total_time = self.current_stats.average_speed_ms * (self.current_stats.total_forms_filled - 1);
            self.current_stats.average_speed_ms = (current_total_time + duration_ms) / self.current_stats.total_forms_filled;
        }

        // Add to recent activities
        let activity = Activity {
            timestamp: Utc::now(),
            activity_type: "automation".to_string(),
            description: format!("Filled form on {} using profile {}", url, profile_name),
            status: if success { "success".to_string() } else { "failed".to_string() },
            duration_ms: Some(duration_ms),
        };

        self.current_stats.recent_activities.insert(0, activity);

        // Keep only last 50 activities
        if self.current_stats.recent_activities.len() > 50 {
            self.current_stats.recent_activities.truncate(50);
        }

        // Update profile performance
        if let Some(profile_perf) = self.current_stats.profile_performance
            .iter_mut()
            .find(|p| p.profile_name == profile_name) {
            profile_perf.usage_count += 1;
            profile_perf.last_used = Some(Utc::now());
            let profile_total = profile_perf.usage_count as f32;
            let current_profile_successes = (profile_perf.success_rate / 100.0 * (profile_total - 1.0)) + if success { 1.0 } else { 0.0 };
            profile_perf.success_rate = (current_profile_successes / profile_total) * 100.0;
        } else {
            self.current_stats.profile_performance.push(ProfilePerformance {
                profile_id: format!("profile_{}", self.current_stats.profile_performance.len()),
                profile_name: profile_name.to_string(),
                usage_count: 1,
                success_rate: if success { 100.0 } else { 0.0 },
                last_used: Some(Utc::now()),
            });
        }

        // Update URL performance
        if let Some(url_perf) = self.current_stats.url_performance
            .iter_mut()
            .find(|u| u.url == url) {
            if success {
                url_perf.success_count += 1;
            } else {
                url_perf.failure_count += 1;
            }
            url_perf.last_tested = Some(Utc::now());

            // Update average time
            let total_runs = url_perf.success_count + url_perf.failure_count;
            if total_runs > 1 {
                url_perf.average_time_ms = ((url_perf.average_time_ms * (total_runs - 1)) + duration_ms) / total_runs;
            } else {
                url_perf.average_time_ms = duration_ms;
            }
        } else {
            self.current_stats.url_performance.push(UrlPerformance {
                url: url.to_string(),
                success_count: if success { 1 } else { 0 },
                failure_count: if success { 0 } else { 1 },
                average_time_ms: duration_ms,
                last_tested: Some(Utc::now()),
            });
        }

        // Update daily stats
        let today = Utc::now().format("%Y-%m-%d").to_string();
        if let Some(daily) = self.current_stats.daily_stats
            .iter_mut()
            .find(|d| d.date == today) {
            daily.forms_filled += 1;
            let daily_total = daily.forms_filled as f32;
            let current_daily_successes = (daily.success_rate / 100.0 * (daily_total - 1.0)) + if success { 1.0 } else { 0.0 };
            daily.success_rate = (current_daily_successes / daily_total) * 100.0;
            daily.average_speed_ms = ((daily.average_speed_ms * (daily.forms_filled - 1)) + duration_ms) / daily.forms_filled;
        } else {
            self.current_stats.daily_stats.push(DailyStat {
                date: today,
                forms_filled: 1,
                success_rate: if success { 100.0 } else { 0.0 },
                average_speed_ms: duration_ms,
            });
        }

        // Keep only last 30 days of daily stats
        if self.current_stats.daily_stats.len() > 30 {
            self.current_stats.daily_stats.remove(0);
        }

        self.current_stats.last_updated = Utc::now();

        // Save stats to file
        self.save_stats().await?;

        Ok(())
    }

    pub async fn update_profile_count(&mut self, total: u32, active: u32) -> Result<()> {
        self.current_stats.total_profiles = total;
        self.current_stats.active_profiles = active;
        self.current_stats.last_updated = Utc::now();
        self.save_stats().await?;
        Ok(())
    }

    pub async fn update_url_count(&mut self, total: u32, active: u32) -> Result<()> {
        self.current_stats.total_urls = total;
        self.current_stats.active_urls = active;
        self.current_stats.last_updated = Utc::now();
        self.save_stats().await?;
        Ok(())
    }

    pub async fn add_activity(&mut self, activity_type: &str, description: &str, status: &str) -> Result<()> {
        let activity = Activity {
            timestamp: Utc::now(),
            activity_type: activity_type.to_string(),
            description: description.to_string(),
            status: status.to_string(),
            duration_ms: None,
        };

        self.current_stats.recent_activities.insert(0, activity);

        // Keep only last 50 activities
        if self.current_stats.recent_activities.len() > 50 {
            self.current_stats.recent_activities.truncate(50);
        }

        self.current_stats.last_updated = Utc::now();
        self.save_stats().await?;

        Ok(())
    }

    pub fn reset_daily_stats(&mut self) {
        self.current_stats.forms_today = 0;
        self.current_stats.errors_today = 0;
    }

    pub fn get_dashboard_summary(&self) -> serde_json::Value {
        let trend = if self.current_stats.daily_stats.len() >= 2 {
            let yesterday = &self.current_stats.daily_stats[self.current_stats.daily_stats.len() - 2];
            let today = &self.current_stats.daily_stats[self.current_stats.daily_stats.len() - 1];

            let forms_trend = ((today.forms_filled as f32 - yesterday.forms_filled as f32) / yesterday.forms_filled.max(1) as f32 * 100.0) as i32;
            let success_trend = today.success_rate - yesterday.success_rate;
            let speed_trend = ((yesterday.average_speed_ms as f32 - today.average_speed_ms as f32) / yesterday.average_speed_ms.max(1) as f32 * 100.0) as i32;

            serde_json::json!({
                "forms": forms_trend,
                "success": success_trend,
                "speed": speed_trend
            })
        } else {
            serde_json::json!({
                "forms": 0,
                "success": 0.0,
                "speed": 0
            })
        };

        serde_json::json!({
            "total_forms_filled": self.current_stats.total_forms_filled,
            "success_rate": format!("{:.1}", self.current_stats.success_rate),
            "average_speed": format!("{:.1}s", self.current_stats.average_speed_ms as f32 / 1000.0),
            "active_profiles": self.current_stats.active_profiles,
            "total_profiles": self.current_stats.total_profiles,
            "active_urls": self.current_stats.active_urls,
            "total_urls": self.current_stats.total_urls,
            "forms_today": self.current_stats.forms_today,
            "errors_today": self.current_stats.errors_today,
            "trends": trend,
            "recent_activities": self.current_stats.recent_activities.iter().take(10).collect::<Vec<_>>(),
            "daily_chart_data": self.current_stats.daily_stats.iter().rev().take(7).rev().collect::<Vec<_>>(),
            "top_profiles": self.current_stats.profile_performance.iter().take(5).collect::<Vec<_>>(),
            "top_urls": self.current_stats.url_performance.iter().take(5).collect::<Vec<_>>(),
        })
    }
}