//! Rule evaluation against charts, values, findings and raw manifests.

use crate::model::{Chart, Finding};
use crate::rules::{parser, path, MatchOp, MatchValue, Rule, RuleMatch, RuleTarget};
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
            let source_name = entry
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string();
            match fs::read_to_string(&entry) {
                Ok(content) => {
                    let (rules, warnings) = parser::parse_rules(&content, &source_name);
                    for w in warnings {
                        println!("      [Warning] {}", w);
                    }
                    self.rules.extend(rules);
                }
                Err(e) => {
                    println!("    [RuleEngine] Error loading {}: {}", source_name, e);
                }
            }
        }
        println!(
            "    [RuleEngine] Loaded {} rules from {}",
            self.rules.len(),
            directory.display()
        );
    }

    /// Evaluate rules against Chart Metadata
    pub fn evaluate_metadata(&self, chart: &mut Chart) {
        for rule in &self.rules {
            if rule.target != RuleTarget::ChartMetadata {
                continue;
            }
            if rule.matches_with(|m| check_metadata_match(chart, m)) {
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
            if rule.matches_with(|m| check_values_match(values, m)) {
                apply_action(chart, rule);
            }
        }
    }

    /// Evaluate `manifest`-target rules against one raw Kubernetes document.
    /// Rules with a `kind:` filter only run on documents of that kind.
    ///
    /// A unit's exposure analysis spans several related documents (workload,
    /// Services, Ingresses, NetworkPolicies), so a rule matching a field they
    /// share (labels, annotations) would otherwise stack its score once per
    /// document. Each manifest rule therefore contributes to a unit at most
    /// once — same guard the built-in chain tracing uses.
    pub fn evaluate_manifest(&self, chart: &mut Chart, doc: &Yaml) {
        let doc_kind = doc.get("kind").and_then(|k| k.as_str()).unwrap_or("");
        for rule in &self.rules {
            if rule.target != RuleTarget::Manifest {
                continue;
            }
            if let Some(want) = rule.kind.as_deref() {
                if !want.eq_ignore_ascii_case(doc_kind) {
                    continue;
                }
            }
            if chart.risk.applied_rule_ids.iter().any(|r| r == &rule.id) {
                continue;
            }
            if rule.matches_with(|m| check_values_match(doc, m)) {
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
            if !rule.matches_with(|m| check_finding_match(finding, chart, m)) {
                continue;
            }

            if rule.action.finding.suppress {
                println!("      → RULE MATCH: {} [SUPPRESSED]", rule.name);
                return false; // Immediate suppression
            }

            if let Some(factor) = rule.action.finding.score_factor {
                println!("      → RULE MATCH: {} [SCORE REDUCED]", rule.name);
                finding.base_score = (finding.base_score as f32 * factor) as i32;
            }
        }
        true
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

pub(crate) fn check_values_match(root: &Yaml, m: &RuleMatch) -> bool {
    let nodes = path::navigate(root, &path::parse_key(&m.key));

    match m.op {
        MatchOp::Exists => return !nodes.is_empty(),
        MatchOp::NotExists => return nodes.is_empty(),
        _ => {}
    }

    // With wildcards a path can resolve to several nodes; the condition holds
    // if ANY resolved node satisfies it.
    nodes.iter().any(|node| check_node_match(node, m))
}

fn check_node_match(node: &Yaml, m: &RuleMatch) -> bool {
    match node {
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
        Yaml::Number(n) => {
            let actual = n.as_f64().unwrap_or(0.0);
            if m.op == MatchOp::In {
                return list_contains(&m.value, &parser::yaml_scalar_to_string(node));
            }
            let expected = match &m.value {
                MatchValue::Int(v) => *v as f64,
                MatchValue::Float(v) => *v,
                MatchValue::Str(s) => match s.trim().parse::<f64>() {
                    Ok(v) => v,
                    Err(_) => return false,
                },
                _ => return false,
            };
            match m.op {
                MatchOp::Eq => actual == expected,
                MatchOp::Neq => actual != expected,
                MatchOp::Gt => actual > expected,
                MatchOp::Lt => actual < expected,
                MatchOp::Gte => actual >= expected,
                MatchOp::Lte => actual <= expected,
                _ => false,
            }
        }
        Yaml::String(s) => {
            if m.op == MatchOp::In {
                return list_contains(&m.value, s);
            }
            check_string_match(s, m)
        }
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

fn list_contains(value: &MatchValue, actual: &str) -> bool {
    match value {
        MatchValue::List(options) => options.iter().any(|o| o == actual),
        _ => false,
    }
}

fn check_finding_match(f: &Finding, chart: &Chart, m: &RuleMatch) -> bool {
    // 1. Chart Tags (Context)
    if m.op == MatchOp::ContainsTag {
        if let MatchValue::Str(tag) = &m.value {
            return chart.tags.iter().any(|t| t == tag);
        }
        return false;
    }

    // 2. Finding Properties
    match m.key.as_str() {
        "package_name" => f
            .original_json
            .get("properties")
            .and_then(|p| p.get("trivy:packageName"))
            .and_then(|v| v.as_str())
            .is_some_and(|pkg| check_string_match(pkg, m)),
        // ruleId is usually the CVE or check ID
        "cve_id" | "rule_id" => check_string_match(&f.rule_id, m),
        "severity" => check_string_match(&f.severity, m),
        "location" => check_string_match(&f.location, m),
        _ => false,
    }
}

fn check_string_match(actual: &str, m: &RuleMatch) -> bool {
    if m.op == MatchOp::In {
        return list_contains(&m.value, actual);
    }
    let expected = match &m.value {
        MatchValue::Str(s) => s.as_str(),
        _ => "",
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

    // Legacy form: set_flag: "name" sets the flag to true
    if let Some(flag) = rp.set_flag.as_deref() {
        chart.risk.set_flag(flag, true);
    }
    // v2 form: set_flags: {name: bool} — can also clear flags
    for (flag, value) in &rp.set_flags {
        chart.risk.set_flag(flag, *value);
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Chart;

    fn yaml(s: &str) -> Yaml {
        serde_yaml::from_str(s).unwrap()
    }

    fn engine_from(rule_yaml: &str) -> RuleEngine {
        let (rules, warnings) = parser::parse_rules(rule_yaml, "test.yaml");
        assert!(warnings.is_empty(), "rule warnings: {:?}", warnings);
        RuleEngine { rules }
    }

    fn m(key: &str, op: MatchOp, value: MatchValue) -> RuleMatch {
        RuleMatch { key: key.into(), op, value }
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
    fn any_block_or_logic() {
        let engine = engine_from(
            r#"
id: "istio-any"
target: "values"
any:
  - key: "virtualService.enabled"
    op: "eq"
    value: true
  - key: "istio.virtualservice.enabled"
    op: "eq"
    value: true
action:
  risk_profile:
    set_flag: "isPublic"
"#,
        );
        // Nested variant matches
        let mut chart = Chart::new("a", "/tmp/a");
        engine.evaluate_values(&mut chart, &yaml("istio:\n  virtualservice:\n    enabled: true\n"));
        assert!(chart.risk.is_public);
        // Root variant matches
        let mut chart = Chart::new("b", "/tmp/b");
        engine.evaluate_values(&mut chart, &yaml("virtualService:\n  enabled: true\n"));
        assert!(chart.risk.is_public);
        // Neither matches
        let mut chart = Chart::new("c", "/tmp/c");
        engine.evaluate_values(&mut chart, &yaml("service:\n  type: ClusterIP\n"));
        assert!(!chart.risk.is_public);
    }

    #[test]
    fn any_block_combines_with_match_as_and() {
        let engine = engine_from(
            r#"
id: "combo"
target: "values"
match:
  - key: "service.type"
    op: "eq"
    value: "LoadBalancer"
any:
  - key: "a"
    op: "exists"
  - key: "b"
    op: "exists"
action:
  risk_profile:
    score_boost: 5
"#,
        );
        let mut chart = Chart::new("x", "/tmp/x");
        // match holds but no any-condition -> no fire
        engine.evaluate_values(&mut chart, &yaml("service:\n  type: LoadBalancer\n"));
        assert!(chart.risk.boosts.is_empty());
        // both hold -> fire
        engine.evaluate_values(&mut chart, &yaml("service:\n  type: LoadBalancer\nb: 1\n"));
        assert_eq!(chart.risk.boosts, vec![5]);
    }

    #[test]
    fn wildcard_matches_container_lists() {
        let engine = engine_from(
            r#"
id: "privileged-any-container"
target: "values"
match:
  - key: "containers.*.securityContext.privileged"
    op: "eq"
    value: true
action:
  risk_profile:
    set_flag: "isPrivileged"
"#,
        );
        let mut chart = Chart::new("w", "/tmp/w");
        let values = yaml(
            "containers:\n  - name: app\n    securityContext:\n      privileged: false\n  - name: sidecar\n    securityContext:\n      privileged: true\n",
        );
        engine.evaluate_values(&mut chart, &values);
        assert!(chart.risk.is_privileged);
    }

    #[test]
    fn escaped_dot_keys_match_annotations() {
        // Regression: the shipped IAM rules never matched before v2
        let engine = engine_from(
            r#"
id: "security-irsa-role"
target: "values"
match:
  - key: "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    op: "exists"
action:
  risk_profile:
    score_boost: 10
"#,
        );
        let mut chart = Chart::new("s", "/tmp/s");
        let values = yaml(
            "serviceAccount:\n  annotations:\n    eks.amazonaws.com/role-arn: arn:aws:iam::1:role/app\n",
        );
        engine.evaluate_values(&mut chart, &values);
        assert_eq!(chart.risk.boosts, vec![10]);
    }

    #[test]
    fn set_flags_can_clear_a_flag() {
        let engine = engine_from(
            r#"
id: "sa-automount-disabled"
target: "values"
match:
  - key: "serviceAccount.automount"
    op: "eq"
    value: false
action:
  risk_profile:
    set_flags:
      mountServiceToken: false
"#,
        );
        let mut chart = Chart::new("s", "/tmp/s");
        assert!(chart.risk.mount_service_token); // risky default
        engine.evaluate_values(&mut chart, &yaml("serviceAccount:\n  automount: false\n"));
        assert!(!chart.risk.mount_service_token);
    }

    #[test]
    fn new_ops_in_gte_lte_not_exists() {
        let values = yaml("service:\n  type: NodePort\nreplicas: 3\nweight: 2.5\n");

        assert!(check_values_match(
            &values,
            &m("service.type", MatchOp::In, MatchValue::List(vec!["LoadBalancer".into(), "NodePort".into()]))
        ));
        assert!(!check_values_match(
            &values,
            &m("service.type", MatchOp::In, MatchValue::List(vec!["ClusterIP".into()]))
        ));
        assert!(check_values_match(&values, &m("replicas", MatchOp::Gte, MatchValue::Int(3))));
        assert!(!check_values_match(&values, &m("replicas", MatchOp::Gte, MatchValue::Int(4))));
        assert!(check_values_match(&values, &m("replicas", MatchOp::Lte, MatchValue::Int(3))));
        assert!(check_values_match(&values, &m("weight", MatchOp::Gt, MatchValue::Float(2.0))));
        assert!(check_values_match(&values, &m("missing.key", MatchOp::NotExists, MatchValue::None)));
        assert!(!check_values_match(&values, &m("replicas", MatchOp::NotExists, MatchValue::None)));
    }

    #[test]
    fn match_ops_on_values() {
        let values = yaml("replicas: 3\nservice:\n  type: ClusterIP\nname: auth-api\n");

        assert!(check_values_match(&values, &m("replicas", MatchOp::Eq, MatchValue::Int(3))));
        assert!(check_values_match(&values, &m("replicas", MatchOp::Gt, MatchValue::Int(2))));
        assert!(!check_values_match(&values, &m("replicas", MatchOp::Lt, MatchValue::Int(2))));
        assert!(check_values_match(
            &values,
            &m("service.type", MatchOp::Neq, MatchValue::Str("LoadBalancer".into()))
        ));
        assert!(check_values_match(
            &values,
            &m("name", MatchOp::Contains, MatchValue::Str("auth".into()))
        ));
        assert!(check_values_match(
            &values,
            &m("name", MatchOp::Regex, MatchValue::Str("^auth-.*$".into()))
        ));
        assert!(!check_values_match(
            &values,
            &m("does.not.exist", MatchOp::Exists, MatchValue::None)
        ));
    }

    #[test]
    fn contains_matches_list_elements() {
        let values = yaml("features:\n  - metrics\n  - tracing\n");
        assert!(check_values_match(
            &values,
            &m("features", MatchOp::Contains, MatchValue::Str("tracing".into()))
        ));
        assert!(!check_values_match(
            &values,
            &m("features", MatchOp::Contains, MatchValue::Str("debug".into()))
        ));
    }

    #[test]
    fn invalid_regex_does_not_panic() {
        let rm = m("x", MatchOp::Regex, MatchValue::Str("([unclosed".into()));
        assert!(!check_string_match("anything", &rm));
    }

    #[test]
    fn manifest_rules_filter_by_kind() {
        let engine = engine_from(
            r#"
id: "ingress-detected"
target: "manifest"
kind: "Ingress"
match:
  - key: "spec.rules"
    op: "exists"
action:
  risk_profile:
    set_flag: "isPublic"
"#,
        );
        let mut chart = Chart::new("w", "/tmp/w");
        // Wrong kind: no fire even though path exists
        engine.evaluate_manifest(
            &mut chart,
            &yaml("kind: ConfigMap\nspec:\n  rules: []\n"),
        );
        assert!(!chart.risk.is_public);
        // Right kind
        engine.evaluate_manifest(
            &mut chart,
            &yaml("kind: Ingress\nspec:\n  rules:\n    - host: x.com\n"),
        );
        assert!(chart.risk.is_public);
    }

    #[test]
    fn manifest_rule_fires_once_per_unit_across_related_docs() {
        // Regression: a rule matching shared metadata (e.g. team labels) on a
        // Deployment+Service+Ingress trio must not stack its boost per doc.
        let engine = engine_from(
            r#"
id: "team-owned"
target: "manifest"
match:
  - key: "metadata.labels.team"
    op: "eq"
    value: "payments"
action:
  risk_profile:
    score_boost: 20
"#,
        );
        let mut chart = Chart::new("w", "/tmp/w");
        let deployment =
            yaml("kind: Deployment\nmetadata:\n  labels:\n    team: payments\n");
        let service = yaml("kind: Service\nmetadata:\n  labels:\n    team: payments\n");
        let ingress = yaml("kind: Ingress\nmetadata:\n  labels:\n    team: payments\n");
        engine.evaluate_manifest(&mut chart, &deployment);
        engine.evaluate_manifest(&mut chart, &service);
        engine.evaluate_manifest(&mut chart, &ingress);
        assert_eq!(chart.risk.boosts, vec![20]);
        assert_eq!(chart.risk.applied_rule_ids, vec!["team-owned"]);
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
        let engine = engine_from(
            r#"
id: "tag-only-rule"
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
    fn finding_match_on_severity_and_location() {
        let engine = engine_from(
            r#"
id: "downgrade-low-tests"
target: "finding"
match:
  - key: "severity"
    op: "in"
    value: ["LOW", "MEDIUM"]
  - key: "location"
    op: "contains"
    value: "test/"
action:
  finding:
    score_factor: 0.1
"#,
        );
        let chart = Chart::new("w", "/tmp/w");
        let mut f = Finding::new(serde_json::json!({}));
        f.severity = "LOW".into();
        f.location = "apps/web/test/helper.py".into();
        f.base_score = 40;
        assert!(engine.evaluate_finding(&mut f, &chart));
        assert_eq!(f.base_score, 4);

        // Non-test location untouched
        let mut f2 = Finding::new(serde_json::json!({}));
        f2.severity = "LOW".into();
        f2.location = "apps/web/main.py".into();
        f2.base_score = 40;
        engine.evaluate_finding(&mut f2, &chart);
        assert_eq!(f2.base_score, 40);
    }

    #[test]
    fn metadata_match_by_name_regex() {
        let engine = engine_from(
            r#"
id: "critical-auth"
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
            "---\nid: r1\ntarget: values\nmatch:\n  - key: a\n    op: exists\n---\nid: r2\ntarget: finding\nmatch:\n  - key: cve_id\n    op: contains\n    value: CVE\n",
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
