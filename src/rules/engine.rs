//! Rule loading and evaluation.

use crate::model::{Chart, Finding};
use crate::rules::*;
use regex::Regex;
use serde_yaml::Value as Yaml;
use std::fs;
use std::path::Path;
use walkdir::WalkDir;

#[derive(Debug, Default)]
pub struct RuleEngine {
    pub rules: Vec<Rule>,
}

impl RuleEngine {
    pub fn new() -> RuleEngine {
        RuleEngine::default()
    }

    pub fn load_rules(&mut self, directory: &Path) {
        if !directory.exists() {
            return;
        }

        let mut entries: Vec<_> = WalkDir::new(directory)
            .into_iter()
            .filter_map(Result::ok)
            .filter(|e| {
                let name = e.file_name().to_string_lossy().to_lowercase();
                e.file_type().is_file() && (name.ends_with(".yaml") || name.ends_with(".yml"))
            })
            .map(|e| e.into_path())
            .collect();
        entries.sort();

        for entry in entries {
            if let Err(msg) = self.load_rule_file(&entry) {
                println!(
                    "    [RuleEngine] Error loading {}: {}",
                    entry.file_name().unwrap_or_default().to_string_lossy(),
                    msg
                );
            }
        }
        println!(
            "    [RuleEngine] Loaded {} rules from {}",
            self.rules.len(),
            directory.display()
        );
    }

    fn load_rule_file(&mut self, path: &Path) -> Result<(), String> {
        let content = fs::read_to_string(path).map_err(|e| e.to_string())?;

        // Support multiple documents in a single file (separated by ---)
        for doc in serde_yaml::Deserializer::from_str(&content) {
            match Yaml::deserialize(doc) {
                Ok(root) => {
                    if root.is_mapping() {
                        self.rules.push(parse_rule_node(&root));
                    }
                }
                Err(e) => {
                    println!(
                        "      [Warning] Failed to parse rule in {}: {}",
                        path.file_name().unwrap_or_default().to_string_lossy(),
                        e
                    );
                }
            }
        }
        Ok(())
    }

    /// Evaluate rules against Chart Metadata
    pub fn evaluate_metadata(&self, chart: &mut Chart) {
        for rule in &self.rules {
            if rule.target != RuleTarget::ChartMetadata {
                continue;
            }
            if rule.matches.iter().all(|m| check_metadata_match(chart, m)) {
                apply_action(chart, rule);
            }
        }
    }

    /// Evaluate rules against Values (YAML)
    pub fn evaluate_values(&self, chart: &mut Chart, values: &Yaml) {
        for rule in &self.rules {
            if rule.target != RuleTarget::Values {
                continue;
            }
            if rule.matches.iter().all(|m| check_values_match(values, m)) {
                apply_action(chart, rule);
            }
        }
    }

    /// Evaluate rules against a Finding (Contextual Analysis).
    /// Returns true if the finding should be KEPT, false if SUPPRESSED.
    pub fn evaluate_finding(&self, finding: &mut Finding, chart: &Chart) -> bool {
        for rule in &self.rules {
            if rule.target != RuleTarget::Finding {
                continue;
            }
            if !rule
                .matches
                .iter()
                .all(|m| check_finding_match(finding, chart, m))
            {
                continue;
            }

            if rule.action.finding.suppress {
                println!("      → RULE MATCH: {} [SUPPRESSED]", rule.name);
                return false; // Immediate suppression
            }

            // AUDIT FIX: D compared `scoreFactor != 0.0` where the default was
            // NaN, corrupting the score of any finding matched by a rule
            // without an explicit score_factor.
            if let Some(factor) = rule.action.finding.score_factor {
                println!("      → RULE MATCH: {} [SCORE REDUCED]", rule.name);
                finding.base_score = (finding.base_score as f32 * factor) as i32;
            }
        }
        true
    }
}

fn parse_rule_node(root: &Yaml) -> Rule {
    let mut rule = Rule::default();

    if let Some(s) = yaml_str(root, "id") {
        rule.id = s;
    }
    if let Some(s) = yaml_str(root, "name") {
        rule.name = s;
    }
    if let Some(s) = yaml_str(root, "description") {
        rule.description = s;
    }
    if let Some(s) = yaml_str(root, "severity") {
        rule.severity = s;
    }

    if let Some(Yaml::Sequence(tags)) = root.get("tags") {
        for t in tags {
            if let Some(s) = t.as_str() {
                rule.tags.push(s.to_string());
            }
        }
    }

    if let Some(t) = yaml_str(root, "target") {
        rule.target = match t.to_lowercase().as_str() {
            "values" => RuleTarget::Values,
            "chart_metadata" => RuleTarget::ChartMetadata,
            "file_content" => RuleTarget::FileContent,
            "finding" => RuleTarget::Finding,
            _ => RuleTarget::Values,
        };
    }

    if let Some(Yaml::Sequence(matches)) = root.get("match") {
        for m in matches {
            let mut rm = RuleMatch::default();
            if let Some(k) = yaml_str(m, "key") {
                rm.key = k;
            }
            rm.op = match yaml_str(m, "op").unwrap_or_default().to_lowercase().as_str() {
                "neq" => MatchOp::Neq,
                "contains" => MatchOp::Contains,
                "regex" => MatchOp::Regex,
                "exists" => MatchOp::Exists,
                "gt" => MatchOp::Gt,
                "lt" => MatchOp::Lt,
                "contains_tag" => MatchOp::ContainsTag,
                _ => MatchOp::Eq, // Default
            };
            if let Some(val) = m.get("value") {
                rm.value = match val {
                    Yaml::Bool(b) => MatchValue::Bool(*b),
                    Yaml::Number(n) if n.is_i64() => MatchValue::Int(n.as_i64().unwrap_or(0)),
                    Yaml::String(s) => MatchValue::Str(s.clone()),
                    other => MatchValue::Str(yaml_to_string(other)),
                };
            }
            rule.matches.push(rm);
        }
    }

    if let Some(act) = root.get("action") {
        if let Some(rp) = act.get("risk_profile") {
            rule.action.risk_profile.set_flag = yaml_str(rp, "set_flag");
            rule.action.risk_profile.score_multiplier = yaml_f32(rp, "score_multiplier");
            rule.action.risk_profile.score_boost =
                yaml_f32(rp, "score_boost").map(|v| v as i32);
        }
        if let Some(f) = act.get("finding") {
            if let Some(Yaml::Bool(b)) = f.get("suppress") {
                rule.action.finding.suppress = *b;
            }
            rule.action.finding.score_factor = yaml_f32(f, "score_factor");
        }
        if let Some(Yaml::Sequence(tags)) = act.get("tags") {
            for t in tags {
                if let Some(s) = t.as_str() {
                    rule.action.tags.push(s.to_string());
                }
            }
        }
    }

    rule
}

fn yaml_str(node: &Yaml, key: &str) -> Option<String> {
    node.get(key).map(yaml_to_string).filter(|s| !s.is_empty())
}

/// Numeric fields may arrive as float, int or quoted string.
fn yaml_f32(node: &Yaml, key: &str) -> Option<f32> {
    match node.get(key)? {
        Yaml::Number(n) => n.as_f64().map(|v| v as f32),
        Yaml::String(s) => s.trim().parse::<f32>().ok(),
        _ => None,
    }
}

fn yaml_to_string(node: &Yaml) -> String {
    match node {
        Yaml::String(s) => s.clone(),
        Yaml::Bool(b) => b.to_string(),
        Yaml::Number(n) => n.to_string(),
        _ => String::new(),
    }
}

fn check_metadata_match(chart: &Chart, m: &RuleMatch) -> bool {
    let val_to_check = match m.key.as_str() {
        "name" => &chart.name,
        "path" => &chart.path,
        _ => return false, // Unknown metadata key
    };
    check_string_match(val_to_check, m)
}

fn check_values_match(root: &Yaml, m: &RuleMatch) -> bool {
    // 1. Navigate to key (dot notation)
    let mut current = root;
    for part in m.key.split('.') {
        match current.get(part) {
            Some(next) => current = next,
            None => return false, // Key not found (Exists check also fails)
        }
    }

    // 2. Perform Check
    if m.op == MatchOp::Exists {
        return true;
    }

    match current {
        Yaml::Bool(b) => {
            let expected = match &m.value {
                MatchValue::Bool(v) => *v,
                MatchValue::Str(s) => match s.parse::<bool>() {
                    Ok(v) => v,
                    Err(_) => return false,
                },
                _ => return false,
            };
            match m.op {
                MatchOp::Eq => *b == expected,
                MatchOp::Neq => *b != expected,
                _ => false,
            }
        }
        Yaml::Number(n) if n.is_i64() => {
            let i = n.as_i64().unwrap_or(0);
            let expected = match &m.value {
                MatchValue::Int(v) => *v,
                MatchValue::Str(s) => match s.parse::<i64>() {
                    Ok(v) => v,
                    Err(_) => return false,
                },
                _ => return false,
            };
            match m.op {
                MatchOp::Eq => i == expected,
                MatchOp::Neq => i != expected,
                MatchOp::Gt => i > expected,
                MatchOp::Lt => i < expected,
                _ => false,
            }
        }
        Yaml::String(s) => check_string_match(s, m),
        // "List contains" semantics documented on MatchOp::Contains
        Yaml::Sequence(seq) if m.op == MatchOp::Contains => {
            if let MatchValue::Str(expected) = &m.value {
                seq.iter().any(|item| item.as_str() == Some(expected))
            } else {
                false
            }
        }
        _ => false,
    }
}

fn check_finding_match(f: &Finding, chart: &Chart, m: &RuleMatch) -> bool {
    // 1. Check Finding Properties
    if m.key == "package_name" {
        if let Some(pkg) = f
            .original_json
            .get("properties")
            .and_then(|p| p.get("trivy:packageName"))
            .and_then(|v| v.as_str())
        {
            return check_string_match(pkg, m);
        }
        return false;
    }

    if m.key == "cve_id" {
        // ruleId is usually the CVE or check ID
        return check_string_match(&f.rule_id, m);
    }

    // 2. Check Chart Tags (Context)
    if m.op == MatchOp::ContainsTag {
        if let MatchValue::Str(tag) = &m.value {
            return chart.tags.iter().any(|t| t == tag);
        }
        return false;
    }

    false
}

fn check_string_match(actual: &str, m: &RuleMatch) -> bool {
    let expected = match &m.value {
        MatchValue::Str(s) => s.as_str(),
        MatchValue::Bool(_) | MatchValue::Int(_) | MatchValue::None => "",
    };
    match m.op {
        MatchOp::Eq => actual == expected,
        MatchOp::Neq => actual != expected,
        MatchOp::Contains => actual.contains(expected),
        MatchOp::Regex => match Regex::new(expected) {
            Ok(re) => re.is_match(actual),
            Err(_) => false,
        },
        _ => false,
    }
}

fn apply_action(chart: &mut Chart, rule: &Rule) {
    println!("      → RULE MATCH: {} ({})", rule.name, rule.id);

    // Track that this rule was applied
    chart.risk.applied_rule_ids.push(rule.id.clone());

    // Apply Risk Profile Modifiers
    let rp = &rule.action.risk_profile;

    if let Some(flag) = rp.set_flag.as_deref() {
        match flag {
            "isPublic" => chart.risk.is_public = true,
            "isPrivileged" => chart.risk.is_privileged = true,
            "hasDangerousCaps" => chart.risk.has_dangerous_caps = true,
            "hasInternetEgress" => chart.risk.has_internet_egress = true,
            "mountServiceToken" => chart.risk.mount_service_token = true,
            _ => {}
        }
    }

    if let Some(mult) = rp.score_multiplier {
        if mult != 1.0 {
            chart.risk.add_multiplier(mult);
        }
    }

    if let Some(boost) = rp.score_boost {
        if boost != 0 {
            chart.risk.add_boost(boost);
        }
    }

    // Apply Tags
    if !rule.action.tags.is_empty() {
        chart.tags.extend(rule.action.tags.iter().cloned());
        chart.tags.sort();
        chart.tags.dedup();
        println!("      → TAGS APPLIED: {:?}", rule.action.tags);
    }
}

use serde::Deserialize;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Chart;

    fn yaml(s: &str) -> Yaml {
        serde_yaml::from_str(s).unwrap()
    }

    fn engine_from(rule_yaml: &str) -> RuleEngine {
        let mut engine = RuleEngine::new();
        for doc in serde_yaml::Deserializer::from_str(rule_yaml) {
            let root = Yaml::deserialize(doc).unwrap();
            engine.rules.push(parse_rule_node(&root));
        }
        engine
    }

    const INGRESS_RULE: &str = r#"
id: "exposure-ingress-enabled"
name: "Public Ingress Exposure"
target: "values"
match:
  - key: "ingress.enabled"
    op: "eq"
    value: true
  - key: "ingress.hosts"
    op: "exists"
action:
  risk_profile:
    set_flag: "isPublic"
    score_multiplier: 1.3
  tags: ["public-facing"]
"#;

    #[test]
    fn values_rule_matches_and_applies() {
        let engine = engine_from(INGRESS_RULE);
        let mut chart = Chart::new("web", "/tmp/web");
        let values = yaml("ingress:\n  enabled: true\n  hosts:\n    - example.com\n");
        engine.evaluate_values(&mut chart, &values);
        assert!(chart.risk.is_public);
        assert_eq!(chart.risk.multipliers, vec![1.3]);
        assert_eq!(chart.risk.applied_rule_ids, vec!["exposure-ingress-enabled"]);
        assert_eq!(chart.tags, vec!["public-facing"]);
    }

    #[test]
    fn values_rule_and_logic_requires_all_matches() {
        let engine = engine_from(INGRESS_RULE);
        let mut chart = Chart::new("web", "/tmp/web");
        // enabled but no hosts -> exists fails -> no match
        let values = yaml("ingress:\n  enabled: true\n");
        engine.evaluate_values(&mut chart, &values);
        assert!(!chart.risk.is_public);
        assert!(chart.risk.applied_rule_ids.is_empty());
    }

    #[test]
    fn match_ops_on_values() {
        let values = yaml("replicas: 3\nservice:\n  type: ClusterIP\nname: auth-api\n");

        let eq_int = RuleMatch {
            key: "replicas".into(),
            op: MatchOp::Eq,
            value: MatchValue::Int(3),
        };
        assert!(check_values_match(&values, &eq_int));

        let gt = RuleMatch {
            key: "replicas".into(),
            op: MatchOp::Gt,
            value: MatchValue::Int(2),
        };
        assert!(check_values_match(&values, &gt));

        let lt = RuleMatch {
            key: "replicas".into(),
            op: MatchOp::Lt,
            value: MatchValue::Int(2),
        };
        assert!(!check_values_match(&values, &lt));

        let neq = RuleMatch {
            key: "service.type".into(),
            op: MatchOp::Neq,
            value: MatchValue::Str("LoadBalancer".into()),
        };
        assert!(check_values_match(&values, &neq));

        let contains = RuleMatch {
            key: "name".into(),
            op: MatchOp::Contains,
            value: MatchValue::Str("auth".into()),
        };
        assert!(check_values_match(&values, &contains));

        let re = RuleMatch {
            key: "name".into(),
            op: MatchOp::Regex,
            value: MatchValue::Str("^auth-.*$".into()),
        };
        assert!(check_values_match(&values, &re));

        let missing = RuleMatch {
            key: "does.not.exist".into(),
            op: MatchOp::Exists,
            value: MatchValue::None,
        };
        assert!(!check_values_match(&values, &missing));
    }

    #[test]
    fn contains_matches_list_elements() {
        let values = yaml("features:\n  - metrics\n  - tracing\n");
        let m = RuleMatch {
            key: "features".into(),
            op: MatchOp::Contains,
            value: MatchValue::Str("tracing".into()),
        };
        assert!(check_values_match(&values, &m));

        let missing = RuleMatch {
            key: "features".into(),
            op: MatchOp::Contains,
            value: MatchValue::Str("debug".into()),
        };
        assert!(!check_values_match(&values, &missing));
    }

    #[test]
    fn invalid_regex_does_not_panic() {
        let m = RuleMatch {
            key: "x".into(),
            op: MatchOp::Regex,
            value: MatchValue::Str("([unclosed".into()),
        };
        assert!(!check_string_match("anything", &m));
    }

    #[test]
    fn finding_suppression() {
        let engine = engine_from(
            r#"
id: "suppress-test-cve"
name: "Suppress test CVE"
target: "finding"
match:
  - key: "cve_id"
    op: "eq"
    value: "CVE-2024-0001"
action:
  finding:
    suppress: true
"#,
        );
        let chart = Chart::new("web", "/tmp/web");
        let mut f = Finding::new(serde_json::json!({}));
        f.rule_id = "CVE-2024-0001".into();
        assert!(!engine.evaluate_finding(&mut f, &chart));

        f.rule_id = "CVE-2024-9999".into();
        assert!(engine.evaluate_finding(&mut f, &chart));
    }

    #[test]
    fn finding_score_factor_via_chart_tag() {
        let engine = engine_from(
            r#"
id: "context-reduce-monitoring"
name: "Reduce Monitoring"
target: "finding"
match:
  - key: "tag"
    op: "contains_tag"
    value: "category:monitoring"
action:
  finding:
    score_factor: 0.3
"#,
        );
        let mut chart = Chart::new("grafana", "/tmp/grafana");
        chart.tags.push("category:monitoring".into());
        let mut f = Finding::new(serde_json::json!({}));
        f.base_score = 75;
        assert!(engine.evaluate_finding(&mut f, &chart));
        assert_eq!(f.base_score, 22); // 75 * 0.3 = 22.5 -> 22
    }

    #[test]
    fn finding_rule_without_score_factor_leaves_score_intact() {
        // AUDIT FIX regression test: D's NaN default corrupted the score here.
        let engine = engine_from(
            r#"
id: "tag-only-rule"
name: "Tag only"
target: "finding"
match:
  - key: "cve_id"
    op: "contains"
    value: "CVE-"
action:
  tags: ["seen"]
"#,
        );
        let chart = Chart::new("web", "/tmp/web");
        let mut f = Finding::new(serde_json::json!({}));
        f.rule_id = "CVE-2024-0001".into();
        f.base_score = 80;
        assert!(engine.evaluate_finding(&mut f, &chart));
        assert_eq!(f.base_score, 80);
    }

    #[test]
    fn metadata_match_by_name_regex() {
        let engine = engine_from(
            r#"
id: "critical-auth"
name: "Auth services are critical"
target: "chart_metadata"
match:
  - key: "name"
    op: "regex"
    value: "(auth|login|iam)"
action:
  risk_profile:
    score_boost: 15
"#,
        );
        let mut chart = Chart::new("auth-service", "/tmp/auth");
        engine.evaluate_metadata(&mut chart);
        assert_eq!(chart.risk.boosts, vec![15]);
    }

    #[test]
    fn multi_document_rule_file() {
        let engine = engine_from(
            "---\nid: r1\nname: one\ntarget: values\n---\nid: r2\nname: two\ntarget: finding\n",
        );
        assert_eq!(engine.rules.len(), 2);
        assert_eq!(engine.rules[0].id, "r1");
        assert_eq!(engine.rules[1].target, RuleTarget::Finding);
    }

    #[test]
    fn package_name_match_from_trivy_properties() {
        let engine = engine_from(
            r#"
id: "suppress-openssl"
name: "Suppress openssl"
target: "finding"
match:
  - key: "package_name"
    op: "contains"
    value: "openssl"
action:
  finding:
    suppress: true
"#,
        );
        let chart = Chart::new("web", "/tmp/web");
        let mut f = Finding::new(serde_json::json!({
            "properties": {"trivy:packageName": "openssl-dev"}
        }));
        assert!(!engine.evaluate_finding(&mut f, &chart));
    }
}
