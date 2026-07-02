//! Service discovery: walk the repo, find Dockerfiles and Helm charts, link them.

use crate::model::{Chart, Service};
use serde_yaml::Value as Yaml;
use std::fs;
use std::path::Path;
use walkdir::WalkDir;

#[derive(Debug, Default)]
pub struct Mapper {
    pub services: Vec<Service>,
    pub charts: Vec<Chart>,
}

impl Mapper {
    pub fn new() -> Mapper {
        Mapper::default()
    }

    pub fn walk(&mut self, root_dir: &Path) {
        println!("=== Discovery Walk: {} ===", root_dir.display());
        if !root_dir.exists() {
            println!("Error: Root directory does not exist.");
            return;
        }

        for entry in WalkDir::new(root_dir)
            .sort_by_file_name()
            .into_iter()
            .filter_map(Result::ok)
            .filter(|e| e.file_type().is_file())
        {
            let entry_path = entry.path();
            let fname = entry.file_name().to_string_lossy().to_string();
            let fdir = entry_path.parent().unwrap_or(Path::new(""));
            let lower_name = fname.to_lowercase();

            // 1. Dockerfile
            if lower_name.contains("dockerfile") && !lower_name.ends_with(".dockerignore") {
                let mut service_id = dir_base_name(fdir);
                if let Some(suffix) = fname.strip_prefix("Dockerfile.") {
                    // Dockerfile.worker -> worker
                    service_id = suffix.to_string();
                } else if lower_name != "dockerfile" {
                    // auth.Dockerfile -> auth
                    service_id = strip_extension(&fname);
                }

                if !self.service_exists(&service_id) {
                    self.services.push(Service::new(
                        &service_id,
                        &entry_path.to_string_lossy(),
                        &fdir.to_string_lossy(),
                    ));
                }
            }

            // 2. Helm Chart (Strict Check)
            if lower_name == "chart.yaml" {
                let chart_dir = fdir.to_string_lossy();
                let chart_name = fs::read_to_string(entry_path)
                    .ok()
                    .and_then(|content| serde_yaml::from_str::<Yaml>(&content).ok())
                    .and_then(|node| node.get("name").and_then(|n| n.as_str().map(String::from)))
                    .unwrap_or_else(|| dir_base_name(fdir));
                self.charts.push(Chart::new(&chart_name, &chart_dir));
            }
        }
    }

    pub fn link(&mut self) {
        println!("=== Linking Services to Charts ===");
        for service in &mut self.services {
            let mut best_match: Option<usize> = None;
            let mut best_score = 0;

            for (idx, chart) in self.charts.iter().enumerate() {
                let score = calculate_match_score(service, chart);
                if score > best_score {
                    best_score = score;
                    best_match = Some(idx);
                }
            }

            if let Some(idx) = best_match {
                service.chart = Some(idx);
                println!(
                    "  LINKED: {} <--> {} (Score: {})",
                    service.id, self.charts[idx].name, best_score
                );
            }
        }
    }

    fn service_exists(&self, id: &str) -> bool {
        self.services.iter().any(|s| s.id == id)
    }
}

fn dir_base_name(dir: &Path) -> String {
    dir.file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default()
}

fn strip_extension(fname: &str) -> String {
    match fname.rfind('.') {
        Some(idx) if idx > 0 => fname[..idx].to_string(),
        _ => fname.to_string(),
    }
}

fn calculate_match_score(s: &Service, c: &Chart) -> i32 {
    let mut score = 0;
    if s.id.eq_ignore_ascii_case(&c.name) {
        score += 100;
    }
    // AUDIT FIX: component-wise containment; the D string prefix check
    // false-matched sibling dirs like apps/api vs apps/api-gateway.
    let chart_path = Path::new(&c.path);
    let service_dir = Path::new(&s.directory);
    if chart_path.starts_with(service_dir) || service_dir.starts_with(chart_path) {
        score += 80;
    }

    // values.yaml image repo check: simple string scan is faster and
    // safer than a full parse for just one check
    let values_path = Path::new(&c.path).join("values.yaml");
    if let Ok(content) = fs::read_to_string(&values_path) {
        if content.contains(&s.id) {
            score += 60;
        }
    }
    score
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dockerfile_naming_variants() {
        assert_eq!(strip_extension("auth.Dockerfile"), "auth");
        assert_eq!(strip_extension("Dockerfile"), "Dockerfile");
    }

    #[test]
    fn match_score_name_and_path() {
        let s = Service::new("payment-go", "/repo/apps/payment-go/Dockerfile", "/repo/apps/payment-go");
        let c = Chart::new("payment-go", "/repo/charts/payment-go");
        // Name matches (+100); paths don't nest; no values.yaml on disk
        assert_eq!(calculate_match_score(&s, &c), 100);
    }

    #[test]
    fn match_score_path_prefix() {
        let s = Service::new("api", "/repo/apps/api/Dockerfile", "/repo/apps/api");
        let c = Chart::new("other", "/repo/apps/api/chart");
        assert_eq!(calculate_match_score(&s, &c), 80);
    }

    #[test]
    fn match_score_sibling_dirs_do_not_false_match() {
        // AUDIT FIX regression test: string prefix matching linked
        // apps/api-gateway to the chart of apps/api.
        let s = Service::new("api", "/repo/apps/api/Dockerfile", "/repo/apps/api");
        let c = Chart::new("gateway", "/repo/apps/api-gateway");
        assert_eq!(calculate_match_score(&s, &c), 0);
    }
}
