//! SARIF ingestion: parse scanner results, match them to services and score them.

use crate::model::{Chart, Finding, Priority, RiskProfile, Service};
use crate::rules::RuleEngine;
use crate::ui;
use serde_json::{json, Value};
use std::fs;
use std::path::{Component, Path, PathBuf};

pub fn map_severity(s: &str) -> f32 {
    let v = s.trim().to_lowercase();
    match v.as_str() {
        "critical" | "crit" | "blocker" => 10.0,
        "high" | "error" | "severe" => 7.5,
        "medium" | "moderate" | "warning" | "major" => 5.0,
        "low" | "minor" | "info" => 2.5,
        _ => v.parse::<f32>().unwrap_or(5.0),
    }
}

pub fn float_to_severity_label(score: f32) -> &'static str {
    if score >= 9.0 {
        "CRITICAL"
    } else if score >= 7.0 {
        "HIGH"
    } else if score >= 4.0 {
        "MEDIUM"
    } else {
        "LOW"
    }
}

pub fn is_fixable(result: &Value) -> bool {
    let props = result.get("properties");

    if let Some(fixed) = props.and_then(|p| p.get("trivy:fixedVersion")) {
        if let Some(ver) = fixed.as_str() {
            return !ver.is_empty() && ver != "null";
        }
        return false;
    }
    if let Some(val) = props.and_then(|p| p.get("github:fixAvailable")) {
        return match val {
            Value::Bool(b) => *b,
            Value::String(s) => s == "true",
            _ => false,
        };
    }
    // Static analysis fixes
    if let Some(fix) = result.get("fix") {
        if !fix.is_null() {
            return true;
        }
    }

    // Default assumption for SAST (Code) is that it is fixable by dev
    true
}

/// Severity is on the CVSS-like 0-10 scale. Untrusted SARIF input may carry
/// out-of-range values (e.g. "1e40" parses to infinity); clamp so the derived
/// base score stays within the documented 0-100 range.
pub fn extract_severity(result: &Value, rules: &Value) -> f32 {
    extract_severity_raw(result, rules).clamp(0.0, 10.0)
}

fn extract_severity_raw(result: &Value, rules: &Value) -> f32 {
    // 1. GitHub security-severity
    if let Some(s) = result
        .get("properties")
        .and_then(|p| p.get("security-severity"))
    {
        match s {
            // AUDIT FIX: D crashed on unparseable strings and ignored
            // integer-typed values; fall through gracefully instead.
            Value::String(text) => {
                if let Ok(v) = text.trim().parse::<f32>() {
                    return v;
                }
            }
            Value::Number(n) => {
                if let Some(v) = n.as_f64() {
                    return v as f32;
                }
            }
            _ => {}
        }
    }

    // 2. Rule lookup
    // AUDIT FIX: D read result["ruleId"] unchecked and crashed when absent.
    let rule_id = result.get("ruleId").and_then(|r| r.as_str()).unwrap_or("");
    if let Some(rules_arr) = rules.as_array() {
        for r in rules_arr {
            if r.get("id").and_then(|i| i.as_str()) == Some(rule_id) {
                if let Some(level) = r
                    .get("defaultConfiguration")
                    .and_then(|d| d.get("level"))
                    .and_then(|l| l.as_str())
                {
                    return map_severity(level);
                }
                break;
            }
        }
    }

    // 3. Fallback
    if let Some(level) = result.get("level").and_then(|l| l.as_str()) {
        return map_severity(level);
    }
    5.0
}

/// Lexical path normalization (no filesystem access), like D's buildNormalizedPath.
fn normalize(path: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for comp in path.components() {
        match comp {
            Component::CurDir => {}
            Component::ParentDir => {
                if !out.pop() {
                    out.push("..");
                }
            }
            other => out.push(other),
        }
    }
    out
}

fn absolutize(path: &Path) -> PathBuf {
    if path.is_absolute() {
        normalize(path)
    } else {
        let cwd = std::env::current_dir().unwrap_or_default();
        normalize(&cwd.join(path))
    }
}

/// Resolve a SARIF-reported file path against the scanned repository.
///
/// Trivy returns paths relative to the scanned root (e.g. "apps/foo/...").
/// Semgrep returns paths relative to CWD (e.g. "./tests/monorepo-01/apps/foo/...").
fn resolve_finding_path(file_path: &str, repo_path: &Path) -> PathBuf {
    // 1. Strip file:// prefix if present
    let file_path = file_path.strip_prefix("file://").unwrap_or(file_path);
    let raw = Path::new(file_path);

    // Join() would discard repo_path entirely for absolute inputs (common
    // from containerized scanners); anchor them by their relative part.
    let raw_rel: PathBuf = raw
        .components()
        .filter(|c| matches!(c, Component::Normal(_)))
        .collect();

    // 2. Dual Resolution Strategy
    let p1 = absolutize(raw); // Assume relative to CWD
    let p2 = absolutize(&repo_path.join(&raw_rel)); // Assume relative to repoPath

    // Prefer the one that actually exists on disk.
    // AUDIT FIX: D compared string prefixes (`startsWith`), which lets
    // "/repo/app-extra" pass as inside "/repo/app". Path::starts_with is
    // component-wise.
    if p1.exists() && p1.starts_with(repo_path) {
        return p1;
    }
    if p2.exists() && p2.starts_with(repo_path) {
        return p2;
    }

    // 3. Prefix Stripping Strategy: if the tool ran from a parent dir
    // (e.g. "project/backend/src/main.py") and we scan "backend", strip
    // leading components until something matches inside repoPath.
    let parts: Vec<&std::ffi::OsStr> = raw.iter().collect();
    for i in 1..parts.len() {
        let stripped: PathBuf = parts[i..].iter().collect();
        let candidate = absolutize(&repo_path.join(&stripped));
        if candidate.exists() && candidate.starts_with(repo_path) {
            return candidate; // Shortest strip that works (most specific)
        }
    }

    // Final Fallback
    if p1.starts_with(repo_path) {
        p1
    } else {
        p2
    }
}

fn extract_description(result: &Value) -> String {
    let raw = result
        .get("shortDescription")
        .and_then(|d| d.get("text"))
        .and_then(|t| t.as_str())
        .or_else(|| {
            result
                .get("message")
                .and_then(|m| m.get("text"))
                .and_then(|t| t.as_str())
        })
        .unwrap_or("No description available");

    // Clean up description: remove newlines and excessive whitespace
    raw.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn extract_line_number(result: &Value) -> i32 {
    result
        .get("locations")
        .and_then(|l| l.as_array())
        .and_then(|a| a.first())
        .and_then(|loc| loc.get("physicalLocation"))
        .and_then(|pl| pl.get("region"))
        .and_then(|r| r.get("startLine"))
        .and_then(|s| s.as_i64())
        .map(|v| v as i32)
        .unwrap_or(0)
}

fn extract_file_path(result: &Value) -> String {
    result
        .get("locations")
        .and_then(|l| l.as_array())
        .and_then(|a| a.first())
        .and_then(|loc| loc.get("physicalLocation"))
        .and_then(|pl| pl.get("artifactLocation"))
        .and_then(|al| al.get("uri"))
        .and_then(|u| u.as_str())
        .unwrap_or("")
        .to_string()
}

/// Outcome of a SARIF ingestion pass, surfaced in the JSON report and used
/// by the caller to decide the process exit code.
#[derive(Debug, Default)]
pub struct SarifIngestResult {
    /// The `--sarif` path did not exist on disk.
    pub sarif_missing: bool,
    /// Number of SARIF results whose path did not resolve inside any known
    /// service directory (silently dropped before this fix).
    pub unmatched_findings: usize,
}

pub fn process_sarif(
    filename: &str,
    services: &mut [Service],
    charts: &[Chart],
    repo_path: &Path,
    engine: &RuleEngine,
    sarif_output: Option<&str>,
) -> SarifIngestResult {
    if !Path::new(filename).exists() {
        ui::print_error(&format!("SARIF file not found: {}", filename));
        return SarifIngestResult {
            sarif_missing: true,
            unmatched_findings: 0,
        };
    }

    println!("=== Processing SARIF file: {} ===", filename);
    let content = match fs::read_to_string(filename) {
        Ok(c) => c,
        Err(e) => {
            ui::print_error(&format!("Error reading SARIF file: {}", e));
            return SarifIngestResult::default();
        }
    };
    let mut sarif: Value = match serde_json::from_str(&content) {
        Ok(j) => j,
        Err(e) => {
            ui::print_error(&format!("Error parsing SARIF file: {}", e));
            return SarifIngestResult::default();
        }
    };

    let mut first_finding = true;
    let mut unmatched_findings: usize = 0;

    let runs = match sarif.get_mut("runs").and_then(|r| r.as_array_mut()) {
        Some(r) => r,
        None => return SarifIngestResult::default(),
    };

    for run in runs.iter_mut() {
        let rules = run
            .get("tool")
            .and_then(|t| t.get("driver"))
            .and_then(|d| d.get("rules"))
            .cloned()
            .unwrap_or_else(|| json!([]));

        let results = match run.get_mut("results").and_then(|r| r.as_array_mut()) {
            Some(r) => r,
            None => continue,
        };

        for result in results.iter_mut() {
            let rule_id = result
                .get("ruleId")
                .and_then(|r| r.as_str())
                .unwrap_or("unknown")
                .to_string();

            let sev_float = extract_severity(result, &rules);
            let base_score = (sev_float * 10.0) as i32; // 0-100 base
            let fixable = is_fixable(result);
            let severity_label = float_to_severity_label(sev_float);

            let file_path = extract_file_path(result);
            let finding_path = resolve_finding_path(&file_path, repo_path);

            let mut matched_service = false;

            for service in services.iter_mut() {
                let svc_dir = normalize(Path::new(&service.directory));
                let svc_docker = normalize(Path::new(&service.dockerfile_path));

                let is_inside = finding_path == svc_docker || finding_path.starts_with(&svc_dir);
                if !is_inside {
                    continue;
                }
                matched_service = true;

                let chart = service.chart.map(|idx| &charts[idx]);

                let mut f = Finding::new(result.clone());
                f.rule_id = rule_id.clone();
                f.location = file_path.clone();
                f.severity = severity_label.to_string();
                f.base_score = base_score;
                f.description = extract_description(result);

                // --- RULE ENGINE EVALUATION ---
                // Check if finding should be suppressed or modified based on context
                if let Some(c) = chart {
                    if !engine.evaluate_finding(&mut f, c) {
                        continue; // Suppress finding
                    }
                }

                // --- SCORING ---
                // AUDIT FIX: fixability is passed per finding instead of
                // mutating the shared chart profile (D leaked hasFix state
                // across findings and into the JSON report).
                let default_risk = RiskProfile::default();
                let risk = chart.map(|c| &c.risk).unwrap_or(&default_risk);
                f.reticulum_score = risk.calculate_score_with_fix(f.base_score, fixable);
                f.priority = Priority::from_score(f.reticulum_score);

                // Use the rule IDs that were tracked during chart analysis
                f.applied_rules = chart
                    .map(|c| c.risk.applied_rule_ids.clone())
                    .unwrap_or_default();

                let line_num = extract_line_number(result);

                if first_finding {
                    println!();
                    first_finding = false;
                }
                ui::print_match(
                    &service.id,
                    &rule_id,
                    &file_path,
                    line_num,
                    base_score,
                    f.reticulum_score,
                    &f.priority.to_string(),
                    &f.applied_rules,
                    &f.description,
                );

                // Enrich SARIF
                let rich_data = json!({
                    "score": f.reticulum_score,
                    "priority": f.priority.to_string(),
                    "serviceId": service.id,
                    "exposure": if risk.is_public { "Public" } else { "Internal" },
                });

                match result.get_mut("properties") {
                    Some(props) => {
                        props["reticulum"] = rich_data;
                    }
                    None => {
                        result["properties"] = json!({ "reticulum": rich_data });
                    }
                }

                service.findings.push(f);
            }

            if !matched_service {
                unmatched_findings += 1;
            }
        }
    }

    // Save Output (Optional)
    if let Some(out) = sarif_output {
        match serde_json::to_string_pretty(&sarif) {
            Ok(pretty) => match fs::write(out, pretty) {
                Ok(()) => println!("=== Done. Saved enriched SARIF to {} ===", out),
                Err(e) => println!("Error writing SARIF output: {}", e),
            },
            Err(e) => println!("Error serializing SARIF output: {}", e),
        }
    }

    if unmatched_findings > 0 {
        ui::print_warning(&format!(
            "{} SARIF result(s) resolved outside every known service directory and were not scored",
            unmatched_findings
        ));
    }

    SarifIngestResult {
        sarif_missing: false,
        unmatched_findings,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn severity_labels() {
        assert_eq!(map_severity("CRITICAL"), 10.0);
        assert_eq!(map_severity(" high "), 7.5);
        assert_eq!(map_severity("warning"), 5.0);
        assert_eq!(map_severity("info"), 2.5);
        assert_eq!(map_severity("8.1"), 8.1);
        assert_eq!(map_severity("garbage"), 5.0);

        assert_eq!(float_to_severity_label(9.5), "CRITICAL");
        assert_eq!(float_to_severity_label(7.5), "HIGH");
        assert_eq!(float_to_severity_label(5.0), "MEDIUM");
        assert_eq!(float_to_severity_label(2.5), "LOW");
    }

    #[test]
    fn severity_from_security_severity_property() {
        // String form
        let r = json!({"properties": {"security-severity": "9.8"}});
        assert_eq!(extract_severity(&r, &json!([])), 9.8);
        // Float form
        let r = json!({"properties": {"security-severity": 7.5}});
        assert_eq!(extract_severity(&r, &json!([])), 7.5);
        // AUDIT FIX: integer form (D only handled string/float)
        let r = json!({"properties": {"security-severity": 8}});
        assert_eq!(extract_severity(&r, &json!([])), 8.0);
        // AUDIT FIX: unparseable string falls through instead of crashing
        let r = json!({"properties": {"security-severity": "n/a"}, "level": "error"});
        assert_eq!(extract_severity(&r, &json!([])), 7.5);
    }

    #[test]
    fn severity_out_of_range_is_clamped() {
        // Untrusted SARIF: "1e40" parses to f32::INFINITY
        let r = json!({"properties": {"security-severity": "1e40"}});
        assert_eq!(extract_severity(&r, &json!([])), 10.0);
        let r = json!({"properties": {"security-severity": "-5"}});
        assert_eq!(extract_severity(&r, &json!([])), 0.0);
    }

    #[test]
    fn absolute_finding_path_is_anchored_to_repo() {
        // A containerized scanner reports "/sub/file.txt"; the file exists
        // at <repo>/sub/file.txt. Path::join would have discarded the repo
        // base for absolute inputs.
        let repo = std::env::temp_dir().join("reticulum-ingestor-abs-test");
        let _ = fs::remove_dir_all(&repo);
        fs::create_dir_all(repo.join("sub")).unwrap();
        fs::write(repo.join("sub/file.txt"), "x").unwrap();
        let repo = normalize(&repo);

        let resolved = resolve_finding_path("/sub/file.txt", &repo);
        assert_eq!(resolved, repo.join("sub/file.txt"));

        let _ = fs::remove_dir_all(&repo);
    }

    #[test]
    fn severity_missing_rule_id_does_not_panic() {
        // AUDIT FIX: D indexed result["ruleId"] unchecked here
        let r = json!({"level": "warning"});
        assert_eq!(extract_severity(&r, &json!([{"id": "x"}])), 5.0);
    }

    #[test]
    fn severity_from_rule_default_configuration() {
        let r = json!({"ruleId": "CVE-1"});
        let rules = json!([{"id": "CVE-1", "defaultConfiguration": {"level": "error"}}]);
        assert_eq!(extract_severity(&r, &rules), 7.5);
    }

    #[test]
    fn fixable_detection() {
        assert!(is_fixable(
            &json!({"properties": {"trivy:fixedVersion": "1.2.3"}})
        ));
        assert!(!is_fixable(
            &json!({"properties": {"trivy:fixedVersion": ""}})
        ));
        assert!(!is_fixable(
            &json!({"properties": {"trivy:fixedVersion": "null"}})
        ));
        assert!(is_fixable(
            &json!({"properties": {"github:fixAvailable": true}})
        ));
        assert!(is_fixable(
            &json!({"properties": {"github:fixAvailable": "true"}})
        ));
        assert!(!is_fixable(
            &json!({"properties": {"github:fixAvailable": false}})
        ));
        assert!(is_fixable(&json!({"fix": {"description": "x"}})));
        assert!(is_fixable(&json!({}))); // SAST default
    }

    #[test]
    fn lexical_normalize() {
        assert_eq!(
            normalize(Path::new("/a/b/../c/./d")),
            PathBuf::from("/a/c/d")
        );
    }

    #[test]
    fn description_whitespace_cleanup() {
        let r = json!({"message": {"text": "line one\n  line\r\ntwo   spaced"}});
        assert_eq!(extract_description(&r), "line one line two spaced");
    }

    #[test]
    fn path_starts_with_is_component_wise() {
        // AUDIT FIX regression test: "/repo/app-extra" is NOT inside "/repo/app"
        let p = PathBuf::from("/repo/app-extra/file.py");
        assert!(!p.starts_with(Path::new("/repo/app")));
    }

    #[test]
    fn missing_sarif_file_is_reported_and_no_findings_ingested() {
        // H76: a missing --sarif path must be surfaced (and the caller
        // exits non-zero), instead of silently returning as a no-op.
        let mut services = vec![Service::new("svc", "svc/Dockerfile", "svc")];
        let charts: Vec<Chart> = Vec::new();
        let engine = RuleEngine::new();
        let repo = std::env::temp_dir().join("reticulum-ingestor-missing-sarif-test");

        let result = process_sarif(
            "/nonexistent/path/does-not-exist.sarif",
            &mut services,
            &charts,
            &repo,
            &engine,
            None,
        );

        assert!(result.sarif_missing);
        assert_eq!(result.unmatched_findings, 0);
        assert!(services[0].findings.is_empty());
    }

    #[test]
    fn result_outside_every_service_dir_is_counted_as_unmatched() {
        // H76: a SARIF result whose path resolves outside every known
        // service directory must be counted, not silently dropped.
        let repo = std::env::temp_dir().join("reticulum-ingestor-unmatched-test");
        let _ = fs::remove_dir_all(&repo);
        fs::create_dir_all(repo.join("svc")).unwrap();
        fs::write(repo.join("svc/app.py"), "x").unwrap();
        let repo = normalize(&repo);
        let svc_dir = repo.join("svc");

        let sarif_path = repo.join("results.sarif");
        let sarif = json!({
            "runs": [{
                "tool": {"driver": {"rules": []}},
                "results": [
                    {
                        "ruleId": "matched-rule",
                        "level": "error",
                        "locations": [{"physicalLocation": {
                            "artifactLocation": {"uri": "svc/app.py"},
                            "region": {"startLine": 1}
                        }}]
                    },
                    {
                        "ruleId": "unmatched-rule",
                        "level": "error",
                        "locations": [{"physicalLocation": {
                            "artifactLocation": {"uri": "outside/app.py"},
                            "region": {"startLine": 1}
                        }}]
                    }
                ]
            }]
        });
        fs::write(&sarif_path, serde_json::to_string(&sarif).unwrap()).unwrap();

        let mut services = vec![Service::new(
            "svc",
            svc_dir.join("Dockerfile").to_str().unwrap(),
            svc_dir.to_str().unwrap(),
        )];
        let charts: Vec<Chart> = Vec::new();
        let engine = RuleEngine::new();

        let result = process_sarif(
            sarif_path.to_str().unwrap(),
            &mut services,
            &charts,
            &repo,
            &engine,
            None,
        );

        assert!(!result.sarif_missing);
        assert_eq!(result.unmatched_findings, 1);
        assert_eq!(services[0].findings.len(), 1);

        let _ = fs::remove_dir_all(&repo);
    }
}
