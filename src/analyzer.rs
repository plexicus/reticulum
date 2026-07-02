//! Exposure analysis: evaluate rule engine against chart metadata and values files.

use crate::model::Chart;
use crate::rules::RuleEngine;
use serde_yaml::Value as Yaml;
use std::fs;
use std::path::{Path, PathBuf};

pub fn analyze_exposure(chart: &mut Chart, engine: &RuleEngine) {
    println!(
        "  [Analyzer] Analyzing chart: {} → {}",
        chart.name, chart.path
    );
    chart.risk.reset();

    // 1. Evaluate Metadata Rules
    engine.evaluate_metadata(chart);

    let mut value_files = collect_value_files(Path::new(&chart.path));
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

/// Select candidate values files in the chart directory (shallow scan).
fn collect_value_files(chart_dir: &Path) -> Vec<PathBuf> {
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

        // Allow standard values.yaml, variations like values-prod.yaml,
        // or specific environment files
        let is_yaml = fname.ends_with(".yaml") || fname.ends_with(".yml");
        let looks_like_values = fname.starts_with("values")
            || fname == "prod.yaml"
            || fname == "staging.yaml"
            || fname == "dev.yaml";

        if is_yaml && looks_like_values {
            value_files.push(entry.path());
        }
    }
    value_files
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

        let mut files: Vec<String> = collect_value_files(&dir)
            .into_iter()
            .map(|p| p.file_name().unwrap().to_string_lossy().to_string())
            .collect();
        files.sort();
        assert_eq!(files, vec!["prod.yaml", "values-prod.yaml", "values.yaml"]);

        let _ = fs::remove_dir_all(&dir);
    }
}
