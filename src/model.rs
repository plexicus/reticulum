//! Core domain model: risk profiles, charts, services and findings.
//!
//! Author: Jose Ramon Palanco <jose.palanco@plexicus.ai>
//! By: PLEXICUS (https://www.plexicus.ai)
//! License: MIT

use serde_json::{json, Value};
use std::fmt;

/// Where a config unit was discovered.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum SourceKind {
    #[default]
    Helm, // Helm chart (Chart.yaml + values)
    K8s,     // Raw Kubernetes manifests
    Compose, // docker-compose service
}

impl SourceKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            SourceKind::Helm => "helm",
            SourceKind::K8s => "k8s",
            SourceKind::Compose => "compose",
        }
    }
}

/// The Decision Matrix Levels
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Priority {
    P0Bleeding, // Score 90-100: Public + Critical
    P1Critical, // Score 70-89:  Public + High OR Internal + Critical
    P2High,     // Score 50-69:  Internal + High
    P3Medium,   // Score 30-49:  Medium issues
    P4Low,      // Score 0-29:   Low/Info
}

impl Priority {
    pub fn from_score(score: i32) -> Priority {
        match score {
            s if s >= 90 => Priority::P0Bleeding,
            s if s >= 70 => Priority::P1Critical,
            s if s >= 50 => Priority::P2High,
            s if s >= 30 => Priority::P3Medium,
            _ => Priority::P4Low,
        }
    }
}

impl fmt::Display for Priority {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            Priority::P0Bleeding => "P0_BLEEDING",
            Priority::P1Critical => "P1_CRITICAL",
            Priority::P2High => "P2_HIGH",
            Priority::P3Medium => "P3_MEDIUM",
            Priority::P4Low => "P4_LOW",
        };
        f.write_str(s)
    }
}

#[derive(Debug, Clone)]
pub struct RiskProfile {
    // --- Context Flags ---
    pub is_public: bool,           // Ingress / LoadBalancer
    pub is_privileged: bool,       // hostNetwork / privileged: true / runs as root
    pub has_fix: bool,             // Patch available?
    pub has_dangerous_caps: bool,  // SYS_ADMIN, NET_ADMIN, etc.
    pub has_internet_egress: bool, // 0.0.0.0/0 allowed
    pub mount_service_token: bool, // automountServiceAccountToken (default true is risky)

    // --- Dynamic Scoring ---
    pub multipliers: Vec<f32>,
    pub boosts: Vec<i32>,
    pub applied_rule_ids: Vec<String>, // Track which rules were applied

    // --- Traceability ---
    /// Human-readable chains explaining HOW exposure was established,
    /// e.g. "Ingress/web-ingress → Service/web → Deployment/web".
    pub exposure_paths: Vec<String>,
}

impl Default for RiskProfile {
    fn default() -> Self {
        RiskProfile {
            is_public: false,
            is_privileged: false,
            has_fix: true,
            has_dangerous_caps: false,
            has_internet_egress: false,
            mount_service_token: true,
            multipliers: Vec::new(),
            boosts: Vec::new(),
            applied_rule_ids: Vec::new(),
            exposure_paths: Vec::new(),
        }
    }
}

/// Flag names addressable from rule actions (`set_flag` / `set_flags`).
pub const KNOWN_FLAGS: [&str; 5] = [
    "isPublic",
    "isPrivileged",
    "hasDangerousCaps",
    "hasInternetEgress",
    "mountServiceToken",
];

impl RiskProfile {
    /// Set a context flag by its rule-facing name. Returns false for unknown
    /// names so callers can surface a warning instead of failing silently.
    pub fn set_flag(&mut self, name: &str, value: bool) -> bool {
        match name {
            "isPublic" => self.is_public = value,
            "isPrivileged" => self.is_privileged = value,
            "hasDangerousCaps" => self.has_dangerous_caps = value,
            "hasInternetEgress" => self.has_internet_egress = value,
            "mountServiceToken" => self.mount_service_token = value,
            _ => return false,
        }
        true
    }

    /// Order-preserving dedup of the applied-rule audit trail
    /// (`Vec::dedup` only strips consecutive repeats).
    pub fn dedup_applied_rules(&mut self) {
        let mut seen = std::collections::HashSet::new();
        self.applied_rule_ids.retain(|r| seen.insert(r.clone()));
    }

    pub fn add_multiplier(&mut self, m: f32) {
        self.multipliers.push(m);
    }

    pub fn add_boost(&mut self, b: i32) {
        self.boosts.push(b);
    }

    /// Transforms a raw severity (0-100) into a Contextual Risk Score.
    ///
    /// AUDIT FIX: the D version mutated the shared profile (`risk.hasFix = fixable`)
    /// before each finding, leaking per-finding state into the chart-level profile.
    /// Here fixability is passed per call instead.
    pub fn calculate_score_with_fix(&self, base_severity: i32, has_fix: bool) -> i32 {
        let mut score = base_severity as f32;

        // 1. Apply Multipliers (Exposure, Context). No multipliers = neutral.
        for m in &self.multipliers {
            score *= m;
        }

        // 2. Apply Boosts (Threats)
        for b in &self.boosts {
            score += *b as f32;
        }

        // 3. Actionability Modifier
        if !has_fix {
            score -= 10.0;
        }

        // Clamping 0-100
        (score as i32).clamp(0, 100)
    }

    pub fn calculate_score(&self, base_severity: i32) -> i32 {
        self.calculate_score_with_fix(base_severity, self.has_fix)
    }

    pub fn reset(&mut self) {
        // AUDIT FIX: the D version left `appliedRuleIds` populated across resets.
        *self = RiskProfile::default();
    }

    pub fn to_json(&self) -> Value {
        let mut j = json!({
            "isPublic": self.is_public,
            "isPrivileged": self.is_privileged,
            "hasDangerousCaps": self.has_dangerous_caps,
            "hasInternetEgress": self.has_internet_egress,
            "mountServiceToken": self.mount_service_token,
        });
        if !self.applied_rule_ids.is_empty() {
            j["appliedRuleIds"] = json!(self.applied_rule_ids);
        }
        if !self.exposure_paths.is_empty() {
            j["exposurePaths"] = json!(self.exposure_paths);
        }
        // Raw score for the report based on a baseline (50), just for visibility
        j["baseRiskScore"] = json!(self.calculate_score(50));
        j
    }
}

#[derive(Debug)]
pub struct Chart {
    pub name: String,
    pub path: String,
    pub source: SourceKind,
    pub risk: RiskProfile,
    pub tags: Vec<String>,
}

impl Chart {
    pub fn new(name: &str, path: &str) -> Chart {
        Chart::with_source(name, path, SourceKind::Helm)
    }

    pub fn with_source(name: &str, path: &str, source: SourceKind) -> Chart {
        Chart {
            name: name.to_string(),
            path: path.to_string(),
            source,
            risk: RiskProfile::default(),
            tags: Vec::new(),
        }
    }
}

#[derive(Debug)]
pub struct Service {
    pub id: String,
    pub dockerfile_path: String,
    pub directory: String,
    /// Index into the shared chart list (D used a class reference).
    pub chart: Option<usize>,
    pub findings: Vec<Finding>,
}

impl Service {
    pub fn new(id: &str, dockerfile_path: &str, directory: &str) -> Service {
        Service {
            id: id.to_string(),
            dockerfile_path: dockerfile_path.to_string(),
            directory: directory.to_string(),
            chart: None,
            findings: Vec::new(),
        }
    }

    pub fn to_json(&self, chart: Option<&Chart>) -> Value {
        let mut j = json!({
            "id": self.id,
            // AUDIT FIX: D emitted the typo "HelmVinked"
            "type": if chart.is_some() { "HelmLinked" } else { "Orphan" },
            "directory": self.directory,
        });

        match chart {
            Some(c) => {
                j["chartName"] = json!(c.name);
                j["source"] = json!(c.source.as_str());
                j["riskProfile"] = c.risk.to_json();
            }
            None => {
                j["riskProfile"] = Value::Null;
            }
        }

        // Findings Summary
        let max_base = self
            .findings
            .iter()
            .map(|f| f.base_score)
            .max()
            .unwrap_or(0);
        let max_ret = self
            .findings
            .iter()
            .map(|f| f.reticulum_score)
            .max()
            .unwrap_or(0);

        j["maxBaseScore"] = json!(max_base);
        j["maxReticulumScore"] = json!(max_ret);
        j["findingCount"] = json!(self.findings.len());
        j["findings"] = Value::Array(self.findings.iter().map(|f| f.to_json()).collect());

        j
    }
}

#[derive(Debug, Clone)]
pub struct Finding {
    pub rule_id: String,
    pub severity: String,
    pub location: String,
    pub base_score: i32,      // Original severity score (0-100)
    pub reticulum_score: i32, // Contextual score
    pub description: String,
    pub priority: Priority,
    pub original_json: Value,
    pub applied_rules: Vec<String>, // Track which rules modified this finding
}

impl Finding {
    pub fn new(original_json: Value) -> Finding {
        Finding {
            rule_id: String::new(),
            severity: String::new(),
            location: String::new(),
            base_score: 0,
            reticulum_score: 0,
            description: String::new(),
            priority: Priority::P4Low,
            original_json,
            applied_rules: Vec::new(),
        }
    }

    pub fn to_json(&self) -> Value {
        let mut j = json!({
            "ruleId": self.rule_id,
            "severity": self.severity,
            "location": self.location,
            "baseScore": self.base_score,
            "reticulumScore": self.reticulum_score,
            "priority": self.priority.to_string(),
        });
        if !self.applied_rules.is_empty() {
            j["appliedRules"] = json!(self.applied_rules);
        }
        j
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn priority_thresholds() {
        assert_eq!(Priority::from_score(100), Priority::P0Bleeding);
        assert_eq!(Priority::from_score(90), Priority::P0Bleeding);
        assert_eq!(Priority::from_score(89), Priority::P1Critical);
        assert_eq!(Priority::from_score(70), Priority::P1Critical);
        assert_eq!(Priority::from_score(69), Priority::P2High);
        assert_eq!(Priority::from_score(50), Priority::P2High);
        assert_eq!(Priority::from_score(49), Priority::P3Medium);
        assert_eq!(Priority::from_score(30), Priority::P3Medium);
        assert_eq!(Priority::from_score(29), Priority::P4Low);
        assert_eq!(Priority::from_score(0), Priority::P4Low);
    }

    #[test]
    fn priority_display_matches_d_enum_names() {
        assert_eq!(Priority::P0Bleeding.to_string(), "P0_BLEEDING");
        assert_eq!(Priority::P4Low.to_string(), "P4_LOW");
    }

    #[test]
    fn score_neutral_without_rules() {
        let risk = RiskProfile::default();
        assert_eq!(risk.calculate_score(50), 50);
    }

    #[test]
    fn score_multipliers_then_boosts() {
        let mut risk = RiskProfile::default();
        risk.add_multiplier(1.3);
        risk.add_boost(20);
        // 50 * 1.3 + 20 = 85
        assert_eq!(risk.calculate_score(50), 85);
    }

    #[test]
    fn score_clamps_to_0_100() {
        let mut risk = RiskProfile::default();
        risk.add_boost(1000);
        assert_eq!(risk.calculate_score(50), 100);
        let mut low = RiskProfile::default();
        low.add_boost(-1000);
        assert_eq!(low.calculate_score(50), 0);
    }

    #[test]
    fn no_fix_penalty_does_not_mutate_profile() {
        let risk = RiskProfile::default();
        assert_eq!(risk.calculate_score_with_fix(50, false), 40);
        // Shared profile stays untouched
        assert!(risk.has_fix);
        assert_eq!(risk.calculate_score(50), 50);
    }

    #[test]
    fn reset_clears_applied_rules() {
        let mut risk = RiskProfile::default();
        risk.applied_rule_ids.push("r1".to_string());
        risk.add_multiplier(2.0);
        risk.reset();
        assert!(risk.applied_rule_ids.is_empty());
        assert!(risk.multipliers.is_empty());
    }
}
