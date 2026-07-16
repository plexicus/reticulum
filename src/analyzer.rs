//! Exposure analysis: evaluate rule engine against chart metadata and values files.

use crate::model::Chart;
use crate::rules::RuleEngine;
use serde_yaml::Value as Yaml;
use std::fs;
use std::path::{Path, PathBuf};

pub fn analyze_exposure(chart: &mut Chart, engine: &RuleEngine, env: Option<&str>) {
    println!(
        "  [Analyzer] Analyzing chart: {} → {}",
        chart.name, chart.path
    );
    chart.risk.reset();

    // 1. Evaluate Metadata Rules
    engine.evaluate_metadata(chart);

    let mut value_files = collect_value_files(Path::new(&chart.path), env);
    value_files.sort();

    for path in value_files {
        println!(
            "    → Loading values: {}",
            path.file_name().unwrap_or_default().to_string_lossy()
        );
        analyze_values_file(chart, &path, engine);
    }

    println!("    [Final Risk Profile]");
    println!(
        "      • Public Exposure    : {}",
        if chart.risk.is_public { "YES" } else { "NO" }
    );
    println!(
        "      • Privileged         : {}",
        if chart.risk.is_privileged {
            "YES"
        } else {
            "NO"
        }
    );
    println!(
        "      • Dangerous Caps     : {}",
        if chart.risk.has_dangerous_caps {
            "YES"
        } else {
            "NO"
        }
    );
    println!(
        "      • Svc Token Mount    : {}",
        if chart.risk.mount_service_token {
            "YES (Default)"
        } else {
            "NO (Secured)"
        }
    );
}

/// Environment tags recognized in overlay file names (`values-prod.yaml`,
/// `values.staging.yaml`, the legacy bare `dev.yaml`, ...). An unrecognized
/// tag (e.g. `values-secrets.yaml`) is treated as an untagged overlay and
/// stays in scope regardless of `--env`, so a custom, non-environment
/// overlay is never silently dropped.
const KNOWN_ENV_TOKENS: [&str; 11] = [
    "prod",
    "production",
    "staging",
    "stage",
    "dev",
    "development",
    "test",
    "testing",
    "qa",
    "uat",
    "sandbox",
];

/// Select candidate values files in the chart directory (shallow scan).
///
/// With `env: None` every discovered overlay is analyzed — today's union,
/// kept as the default for back-compat. With `env: Some(name)`, only the
/// base `values.yaml`/`values.yml` plus the overlay tagged for that single
/// environment are analyzed, so exposure reflects one deployed topology
/// instead of the union of every environment ever committed.
fn collect_value_files(chart_dir: &Path, env: Option<&str>) -> Vec<PathBuf> {
    let mut value_files = Vec::new();
    let entries = match fs::read_dir(chart_dir) {
        Ok(e) => e,
        Err(_) => return value_files,
    };

    for entry in entries.filter_map(Result::ok) {
        if !entry.file_type().map(|t| t.is_file()).unwrap_or(false) {
            continue;
        }
        let fname = entry.file_name().to_string_lossy().to_lowercase();

        // Strictly exclude non-value files
        if fname == "chart.yaml"
            || fname == "chart.yml"
            || fname == "chart.lock"
            || fname.starts_with(".helm")
        {
            continue;
        }

        if !(fname.ends_with(".yaml") || fname.ends_with(".yml")) {
            continue;
        }

        match classify_values_file(&fname) {
            None => {}                                    // not a values file at all
            Some(None) => value_files.push(entry.path()), // base / untagged overlay — always in scope
            Some(Some(tag)) => {
                let in_scope = match env {
                    None => true, // no selector — today's union
                    Some(selected) => tag.eq_ignore_ascii_case(selected),
                };
                if in_scope {
                    value_files.push(entry.path());
                }
            }
        }
    }
    value_files
}

/// Classify a lowercased values-file name as: not a values file (`None`), an
/// untagged values file (`Some(None)`), or a recognized environment overlay
/// (`Some(Some(tag))`).
fn classify_values_file(fname: &str) -> Option<Option<String>> {
    let stem = fname.rsplit_once('.').map(|(s, _)| s).unwrap_or(fname);

    let tag = if fname == "prod.yaml" || fname == "staging.yaml" || fname == "dev.yaml" {
        Some(stem.to_string())
    } else if fname.starts_with("values") {
        stem[("values".len())..]
            .strip_prefix(['-', '.', '_'])
            .filter(|t| !t.is_empty())
            .map(|t| t.to_string())
    } else {
        return None;
    };

    match tag {
        Some(t) if KNOWN_ENV_TOKENS.contains(&t.as_str()) => Some(Some(t)),
        _ => Some(None),
    }
}

fn analyze_values_file(chart: &mut Chart, path: &Path, engine: &RuleEngine) {
    let content = match fs::read_to_string(path) {
        Ok(c) => c,
        Err(e) => {
            print_parse_error(path, &e.to_string());
            return;
        }
    };

    match serde_yaml::from_str::<Yaml>(&content) {
        Ok(root) => {
            if root.is_mapping() {
                // 2. Evaluate Values Rules
                engine.evaluate_values(chart, &root);
            }
        }
        Err(e) => print_parse_error(path, &e.to_string()),
    }
}

fn print_parse_error(path: &Path, msg: &str) {
    println!(
        "    [Error] Failed to parse {}: {}",
        path.file_name().unwrap_or_default().to_string_lossy(),
        msg
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn value_file_selection_rules() {
        let dir = std::env::temp_dir().join("reticulum-analyzer-test");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        for name in [
            "Chart.yaml",
            "chart.lock",
            ".helmignore",
            "values.yaml",
            "values-prod.yaml",
            "prod.yaml",
            "README.md",
            "notes.yaml",
        ] {
            fs::write(dir.join(name), "x: 1\n").unwrap();
        }

        // No --env selector: every discovered overlay is in scope (union, back-compat).
        let mut files: Vec<String> = collect_value_files(&dir, None)
            .into_iter()
            .map(|p| p.file_name().unwrap().to_string_lossy().to_string())
            .collect();
        files.sort();
        assert_eq!(files, vec!["prod.yaml", "values-prod.yaml", "values.yaml"]);

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn env_selector_excludes_other_environment_overlays() {
        let dir = std::env::temp_dir().join("reticulum-analyzer-env-test");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        for name in [
            "values.yaml",
            "values-prod.yaml",
            "values-dev.yaml",
            "values-secrets.yaml",
        ] {
            fs::write(dir.join(name), "x: 1\n").unwrap();
        }

        let mut prod_only: Vec<String> = collect_value_files(&dir, Some("prod"))
            .into_iter()
            .map(|p| p.file_name().unwrap().to_string_lossy().to_string())
            .collect();
        prod_only.sort();
        // dev overlay is excluded; base + untagged secrets overlay stay in scope.
        assert_eq!(
            prod_only,
            vec!["values-prod.yaml", "values-secrets.yaml", "values.yaml"]
        );

        let mut union: Vec<String> = collect_value_files(&dir, None)
            .into_iter()
            .map(|p| p.file_name().unwrap().to_string_lossy().to_string())
            .collect();
        union.sort();
        assert_eq!(
            union,
            vec![
                "values-dev.yaml",
                "values-prod.yaml",
                "values-secrets.yaml",
                "values.yaml"
            ]
        );

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn classify_recognizes_tagged_and_untagged_overlays() {
        assert_eq!(classify_values_file("values.yaml"), Some(None));
        assert_eq!(
            classify_values_file("values-prod.yaml"),
            Some(Some("prod".to_string()))
        );
        assert_eq!(
            classify_values_file("values.staging.yaml"),
            Some(Some("staging".to_string()))
        );
        assert_eq!(
            classify_values_file("dev.yaml"),
            Some(Some("dev".to_string()))
        );
        assert_eq!(classify_values_file("values-secrets.yaml"), Some(None));
        assert_eq!(classify_values_file("notes.yaml"), None);
    }
}
