//! Reticulum - Contextual Security Prioritizer for Kubernetes
//!
//! Author: Jose Ramon Palanco <jose.palanco@plexicus.ai>
//! By: PLEXICUS (https://www.plexicus.ai)
//! License: MIT

mod analyzer;
mod ingestor;
mod mapper;
mod model;
mod rules;
mod ui;

use clap::Parser;
use mapper::Mapper;
use rules::RuleEngine;
use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

#[derive(Parser, Debug)]
#[command(name = "reticulum", disable_help_flag = true)]
struct Args {
    /// Path to the source repository (Required)
    #[arg(short = 'p', long = "path")]
    path: Option<String>,

    /// Path to input SARIF file (Required unless --scan-only)
    #[arg(short = 's', long = "sarif")]
    sarif: Option<String>,

    /// Path to save the output JSON report
    #[arg(short = 'o', long = "output")]
    output: Option<String>,

    /// Path to save enriched SARIF (optional)
    #[arg(long = "sarif-output")]
    sarif_output: Option<String>,

    /// Perform exposure analysis only (ignores SARIF)
    #[arg(long = "scan-only")]
    scan_only: bool,

    /// Base directory containing rule sets (exposure/, security/, scoring/, custom/)
    #[arg(long = "rules")]
    rules: Option<String>,

    /// This help information
    #[arg(short = 'h', long = "help")]
    help: bool,
}

/// Locate the rules base directory.
///
/// AUDIT FIX: the D version only looked at CWD-relative "rules/", so running
/// the binary from any other directory silently loaded zero rules. We accept
/// an explicit --rules flag, then fall back to CWD, then to the directory of
/// the executable.
fn find_rules_base(cli_rules: Option<&str>) -> Option<PathBuf> {
    if let Some(dir) = cli_rules {
        let p = PathBuf::from(dir);
        if p.exists() {
            return Some(p);
        }
        ui::print_warning(&format!("Rules directory not found: {}", dir));
        return None;
    }

    let cwd_rules = PathBuf::from("rules");
    if cwd_rules.exists() {
        return Some(cwd_rules);
    }

    if let Ok(exe) = std::env::current_exe() {
        if let Some(exe_dir) = exe.parent() {
            let exe_rules = exe_dir.join("rules");
            if exe_rules.exists() {
                return Some(exe_rules);
            }
        }
    }

    None
}

fn load_rule_sets(engine: &mut RuleEngine, base: &Path) {
    // Load rules from organized directories; custom last (can override defaults)
    for sub in ["exposure", "security", "scoring", "custom"] {
        let dir = base.join(sub);
        if dir.exists() {
            engine.load_rules(&dir);
        }
    }
}

fn build_report(m: &Mapper, scan_type: &str) -> Value {
    let services: Vec<Value> = m
        .services
        .iter()
        .map(|s| s.to_json(s.chart.map(|idx| &m.charts[idx])))
        .collect();

    json!({
        "services": services,
        "totalServices": m.services.len(),
        "scanType": scan_type,
    })
}

fn write_json_report(path: &str, root: &Value, success_msg: &str) {
    match serde_json::to_string_pretty(root) {
        Ok(pretty) => match fs::write(path, pretty) {
            Ok(()) => ui::print_success(&format!("{}: {}", success_msg, path)),
            Err(e) => ui::print_error(&format!("Error writing output: {}", e)),
        },
        Err(e) => ui::print_error(&format!("Error serializing output: {}", e)),
    }
}

fn main() -> ExitCode {
    ui::print_banner();

    let args = match Args::try_parse() {
        Ok(a) => a,
        Err(e) => {
            ui::print_error(&format!("Error parsing arguments: {}", e));
            return ExitCode::FAILURE;
        }
    };

    let repo_path = match &args.path {
        Some(p) if !p.is_empty() && !args.help => p.clone(),
        _ => {
            ui::print_help();
            return ExitCode::SUCCESS;
        }
    };

    if !args.scan_only && args.sarif.as_deref().unwrap_or("").is_empty() {
        ui::print_error("--sarif is required unless --scan-only is used.");
        return ExitCode::FAILURE;
    }

    // 1. Resolve absolute path for the repo
    let abs_repo_path = match fs::canonicalize(&repo_path) {
        Ok(p) => p,
        Err(e) => {
            ui::print_error(&format!("Cannot resolve repository path '{}': {}", repo_path, e));
            return ExitCode::FAILURE;
        }
    };
    ui::print_info(&format!("Target Repository: {}", abs_repo_path.display()));

    // --- Initialize Rule Engine ---
    ui::print_info("Initializing Rule Engine...");
    let mut engine = RuleEngine::new();
    match find_rules_base(args.rules.as_deref()) {
        Some(base) => load_rule_sets(&mut engine, &base),
        None => ui::print_warning(
            "No rules directory found (use --rules); running without rules.",
        ),
    }

    ui::print_phase("Phase 1: Service Discovery", "Mapping services and Helm charts");
    let mut m = Mapper::new();
    m.walk(&abs_repo_path);
    m.link();

    ui::print_phase(
        "Phase 2: Exposure Analysis",
        "Analyzing Kubernetes deployment configurations",
    );
    // Analyze each chart that is linked to at least one service (D iterated
    // services and analyzed s.chart; dedupe so shared charts run once).
    let mut analyzed = vec![false; m.charts.len()];
    for s in &m.services {
        if let Some(idx) = s.chart {
            if !analyzed[idx] {
                analyzed[idx] = true;
                analyzer::analyze_exposure(&mut m.charts[idx], &engine);
            }
        }
    }

    if args.scan_only {
        ui::print_warning("Mode: Exposure Analysis Only (Skipping SARIF ingestion)");

        let root = build_report(&m, "exposure-audit");
        match args.output.as_deref() {
            Some(out) if !out.is_empty() => {
                write_json_report(out, &root, "Exposure report saved to")
            }
            _ => match serde_json::to_string_pretty(&root) {
                Ok(pretty) => println!("{}", pretty),
                Err(e) => ui::print_error(&format!("Error serializing output: {}", e)),
            },
        }
        return ExitCode::SUCCESS;
    }

    ui::print_phase(
        "Phase 3: Vulnerability Scoring",
        "Ingesting SARIF and applying contextual scoring",
    );
    let sarif_input = args.sarif.as_deref().unwrap_or("");
    ingestor::process_sarif(
        sarif_input,
        &mut m.services,
        &m.charts,
        &abs_repo_path,
        &engine,
        args.sarif_output.as_deref().filter(|s| !s.is_empty()),
    );

    // --- Generate JSON Report (Full Scan) ---
    if let Some(out) = args.output.as_deref().filter(|s| !s.is_empty()) {
        let root = build_report(&m, "full-analysis");
        write_json_report(out, &root, "Full analysis report saved to");
    }

    ui::print_success("Reticulum Analysis Complete.");
    ExitCode::SUCCESS
}
