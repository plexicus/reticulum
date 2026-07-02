//! Rule file loading: YAML documents -> validated `Rule` values.

use crate::model::KNOWN_FLAGS;
use crate::rules::*;
use serde::Deserialize;
use serde_yaml::Value as Yaml;

/// Parse every YAML document in `content` (multi-doc `---` supported).
/// Returns the rules plus human-readable validation warnings.
pub fn parse_rules(content: &str, source_name: &str) -> (Vec<Rule>, Vec<String>) {
    let mut rules = Vec::new();
    let mut warnings = Vec::new();

    for doc in serde_yaml::Deserializer::from_str(content) {
        match Yaml::deserialize(doc) {
            Ok(root) => {
                if root.is_mapping() {
                    rules.push(parse_rule_node(&root, source_name, &mut warnings));
                }
            }
            Err(e) => {
                warnings.push(format!("{}: failed to parse document: {}", source_name, e));
            }
        }
    }
    (rules, warnings)
}

fn parse_rule_node(root: &Yaml, source: &str, warnings: &mut Vec<String>) -> Rule {
    let mut rule = Rule::default();

    if let Some(s) = yaml_str(root, "id") {
        rule.id = s;
    } else {
        warnings.push(format!("{}: rule without 'id'", source));
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
    rule.kind = yaml_str(root, "kind");

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
            "manifest" => RuleTarget::Manifest,
            other => {
                warnings.push(format!(
                    "{}: rule '{}' has unknown target '{}', defaulting to 'values'",
                    source, rule.id, other
                ));
                RuleTarget::Values
            }
        };
    }

    rule.matches = parse_match_list(root.get("match"), &rule.id, source, warnings);
    rule.any_matches = parse_match_list(root.get("any"), &rule.id, source, warnings);

    if let Some(act) = root.get("action") {
        parse_action(act, &mut rule, source, warnings);
    }

    if rule.matches.is_empty() && rule.any_matches.is_empty() {
        warnings.push(format!(
            "{}: rule '{}' has no match conditions and will fire on everything",
            source, rule.id
        ));
    }

    rule
}

fn parse_match_list(
    node: Option<&Yaml>,
    rule_id: &str,
    source: &str,
    warnings: &mut Vec<String>,
) -> Vec<RuleMatch> {
    let mut out = Vec::new();
    let Some(Yaml::Sequence(items)) = node else {
        return out;
    };

    for m in items {
        let mut rm = RuleMatch::default();
        if let Some(k) = yaml_str(m, "key") {
            rm.key = k;
        }

        if let Some(op) = yaml_str(m, "op") {
            rm.op = match op.to_lowercase().as_str() {
                "eq" => MatchOp::Eq,
                "neq" => MatchOp::Neq,
                "contains" => MatchOp::Contains,
                "regex" => MatchOp::Regex,
                "exists" => MatchOp::Exists,
                "not_exists" => MatchOp::NotExists,
                "gt" => MatchOp::Gt,
                "lt" => MatchOp::Lt,
                "gte" => MatchOp::Gte,
                "lte" => MatchOp::Lte,
                "in" => MatchOp::In,
                "contains_tag" => MatchOp::ContainsTag,
                other => {
                    warnings.push(format!(
                        "{}: rule '{}' has unknown op '{}', defaulting to 'eq'",
                        source, rule_id, other
                    ));
                    MatchOp::Eq
                }
            };
        }

        if let Some(val) = m.get("value") {
            rm.value = match val {
                Yaml::Bool(b) => MatchValue::Bool(*b),
                Yaml::Number(n) if n.is_i64() => MatchValue::Int(n.as_i64().unwrap_or(0)),
                Yaml::Number(n) => MatchValue::Float(n.as_f64().unwrap_or(0.0)),
                Yaml::String(s) => MatchValue::Str(s.clone()),
                Yaml::Sequence(seq) => MatchValue::List(
                    seq.iter().map(yaml_scalar_to_string).collect(),
                ),
                _ => MatchValue::None,
            };
        }

        if rm.op == MatchOp::In && !matches!(rm.value, MatchValue::List(_)) {
            warnings.push(format!(
                "{}: rule '{}' uses op 'in' with a non-list value",
                source, rule_id
            ));
        }

        out.push(rm);
    }
    out
}

fn parse_action(act: &Yaml, rule: &mut Rule, source: &str, warnings: &mut Vec<String>) {
    if let Some(rp) = act.get("risk_profile") {
        let action = &mut rule.action.risk_profile;
        action.set_flag = yaml_str(rp, "set_flag");
        if let Some(flag) = action.set_flag.as_deref() {
            if !KNOWN_FLAGS.contains(&flag) {
                warnings.push(format!(
                    "{}: rule '{}' sets unknown flag '{}'",
                    source, rule.id, flag
                ));
            }
        }

        if let Some(Yaml::Mapping(flags)) = rp.get("set_flags") {
            for (k, v) in flags {
                let (Some(name), Some(value)) = (k.as_str(), v.as_bool()) else {
                    warnings.push(format!(
                        "{}: rule '{}' has malformed set_flags entry (want flag: bool)",
                        source, rule.id
                    ));
                    continue;
                };
                if !KNOWN_FLAGS.contains(&name) {
                    warnings.push(format!(
                        "{}: rule '{}' sets unknown flag '{}'",
                        source, rule.id, name
                    ));
                }
                action.set_flags.push((name.to_string(), value));
            }
        }

        action.score_multiplier = yaml_f32(rp, "score_multiplier");
        action.score_boost = yaml_f32(rp, "score_boost").map(|v| v as i32);
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

pub(crate) fn yaml_str(node: &Yaml, key: &str) -> Option<String> {
    node.get(key).map(yaml_scalar_to_string).filter(|s| !s.is_empty())
}

/// Numeric fields may arrive as float, int or quoted string.
fn yaml_f32(node: &Yaml, key: &str) -> Option<f32> {
    match node.get(key)? {
        Yaml::Number(n) => n.as_f64().map(|v| v as f32),
        Yaml::String(s) => s.trim().parse::<f32>().ok(),
        _ => None,
    }
}

pub(crate) fn yaml_scalar_to_string(node: &Yaml) -> String {
    match node {
        Yaml::String(s) => s.clone(),
        Yaml::Bool(b) => b.to_string(),
        Yaml::Number(n) => n.to_string(),
        _ => String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse_one(s: &str) -> (Rule, Vec<String>) {
        let (mut rules, warnings) = parse_rules(s, "test.yaml");
        (rules.remove(0), warnings)
    }

    #[test]
    fn legacy_v1_rule_parses_without_warnings() {
        let (rule, warnings) = parse_one(
            r#"
id: "exposure-ingress-enabled"
name: "Public Ingress Exposure"
target: "values"
match:
  - key: "ingress.enabled"
    op: "eq"
    value: true
action:
  risk_profile:
    set_flag: "isPublic"
    score_multiplier: 1.3
  tags: ["public-facing"]
"#,
        );
        assert!(warnings.is_empty(), "unexpected: {:?}", warnings);
        assert_eq!(rule.id, "exposure-ingress-enabled");
        assert_eq!(rule.matches.len(), 1);
        assert_eq!(rule.action.risk_profile.set_flag.as_deref(), Some("isPublic"));
        assert_eq!(rule.action.risk_profile.score_multiplier, Some(1.3));
    }

    #[test]
    fn v2_any_block_and_set_flags() {
        let (rule, warnings) = parse_one(
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
    set_flags:
      isPublic: true
      mountServiceToken: false
"#,
        );
        assert!(warnings.is_empty(), "unexpected: {:?}", warnings);
        assert_eq!(rule.any_matches.len(), 2);
        assert_eq!(
            rule.action.risk_profile.set_flags,
            vec![("isPublic".to_string(), true), ("mountServiceToken".to_string(), false)]
        );
    }

    #[test]
    fn in_op_parses_list_value() {
        let (rule, warnings) = parse_one(
            r#"
id: "svc-type"
target: "values"
match:
  - key: "service.type"
    op: "in"
    value: ["LoadBalancer", "NodePort"]
"#,
        );
        assert!(warnings.is_empty());
        assert_eq!(
            rule.matches[0].value,
            MatchValue::List(vec!["LoadBalancer".into(), "NodePort".into()])
        );
    }

    #[test]
    fn manifest_target_with_kind() {
        let (rule, _) = parse_one(
            "id: r\ntarget: manifest\nkind: Ingress\nmatch:\n  - key: spec.rules\n    op: exists\n",
        );
        assert_eq!(rule.target, RuleTarget::Manifest);
        assert_eq!(rule.kind.as_deref(), Some("Ingress"));
    }

    #[test]
    fn warnings_for_unknown_target_op_flag_and_empty_match() {
        let (_, warnings) = parse_one(
            r#"
id: "bad"
target: "nonsense"
match:
  - key: "x"
    op: "wat"
    value: 1
action:
  risk_profile:
    set_flag: "isTeapot"
"#,
        );
        let text = warnings.join("\n");
        assert!(text.contains("unknown target 'nonsense'"));
        assert!(text.contains("unknown op 'wat'"));
        assert!(text.contains("unknown flag 'isTeapot'"));

        let (_, warnings) = parse_one("id: empty\ntarget: values\n");
        assert!(warnings.iter().any(|w| w.contains("no match conditions")));
    }

    #[test]
    fn missing_id_warns() {
        let (_, warnings) = parse_one("target: values\nmatch:\n  - key: x\n    op: exists\n");
        assert!(warnings.iter().any(|w| w.contains("without 'id'")));
    }
}
