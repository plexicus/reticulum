//! Reticulum - Contextual Security Prioritizer for Kubernetes
//!
//! Author: Jose Ramon Palanco <jose.palanco@plexicus.ai>
//! By: PLEXICUS (https://www.plexicus.ai)
//! License: MIT

mod analyzer;
mod graph;
mod ingestor;
mod mapper;
mod model;
mod pathfilter;
mod rules;
mod sources;
mod ui;

use clap::Parser;
use mapper::Mapper;
use pathfilter::PathFilter;
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

    /// Path to save an exposure graph (Mermaid flowchart)
    #[arg(long = "graph")]
    graph: Option<String>,

    /// Analyze a single deployed environment: base values.yaml/values.yml
    /// plus only the overlay tagged for this environment (e.g. `prod`).
    /// Default (omitted): merge every discovered environment overlay,
    /// matching pre-selector behavior.
    #[arg(long = "env")]
    env: Option<String>,

    /// Only analyze paths matching this glob, relative to --path (repeatable,
    /// supports `*`, `**`, `?`). Default: no restriction.
    #[arg(long = "include")]
    include: Vec<String>,

    /// Skip paths matching this glob, relative to their walk root
    /// (repeatable; always wins over --include).
    #[arg(long = "exclude")]
    exclude: Vec<String>,

    /// Additional external gitops root (e.g. a separate deploy repo) to scan
    /// for Helm charts and Kubernetes manifests alongside --path.
    #[arg(long = "gitops-root")]
    gitops_root: Option<String>,

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
    for sub in ["exposure", "security", "scoring", "manifest", "custom"] {
        let dir = base.join(sub);
        if dir.exists() {
            engine.load_rules(&dir);
        }
    }
}

fn write_graph(args: &Args, m: &Mapper) {
    let Some(path) = args.graph.as_deref().filter(|s| !s.is_empty()) else {
        return;
    };
    let mermaid = graph::render_mermaid(&m.services, &m.charts);
    match fs::write(path, mermaid) {
        Ok(()) => ui::print_success(&format!("Exposure graph saved to: {}", path)),
        Err(e) => ui::print_error(&format!("Error writing graph: {}", e)),
    }
}

fn build_report(
    m: &Mapper,
    scan_type: &str,
    ingest: Option<&ingestor::SarifIngestResult>,
) -> Value {
    let services: Vec<Value> = m
        .services
        .iter()
        .map(|s| s.to_json(s.chart.map(|idx| &m.charts[idx])))
        .collect();

    let mut root = json!({
        "services": services,
        "totalServices": m.services.len(),
        "scanType": scan_type,
    });

    if let Some(ingest) = ingest {
        root["unmatchedFindings"] = json!(ingest.unmatched_findings);
        if ingest.unmatched_findings > 0 {
            root["warnings"] = json!([format!(
                "{} SARIF result(s) resolved outside every known service directory and were not scored",
                ingest.unmatched_findings
            )]);
        }
    }

    root
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
            ui::print_error(&format!(
                "Cannot resolve repository path '{}': {}",
                repo_path, e
            ));
            return ExitCode::FAILURE;
        }
    };
    ui::print_info(&format!("Target Repository: {}", abs_repo_path.display()));

    // Optional external gitops root (e.g. a separate deploy repo), scanned
    // alongside --path for Helm charts / Kubernetes manifests.
    let gitops_root = match args.gitops_root.as_deref().filter(|s| !s.is_empty()) {
        Some(p) => match fs::canonicalize(p) {
            Ok(abs) => Some(abs),
            Err(e) => {
                ui::print_error(&format!("Cannot resolve --gitops-root '{}': {}", p, e));
                return ExitCode::FAILURE;
            }
        },
        None => None,
    };
    let filter = PathFilter::new(&args.include, &args.exclude);

    // --- Initialize Rule Engine ---
    ui::print_info("Initializing Rule Engine...");
    let mut engine = RuleEngine::new();
    match find_rules_base(args.rules.as_deref()) {
        Some(base) => load_rule_sets(&mut engine, &base),
        None => ui::print_warning("No rules directory found (use --rules); running without rules."),
    }

    ui::print_phase(
        "Phase 1: Service Discovery",
        "Mapping services, Helm charts, K8s manifests and compose stacks",
    );
    // Every root scanned for charts/manifests: the source repo, plus an
    // optional external gitops root (kept separate from the SARIF/report
    // repo path, which always stays `abs_repo_path`).
    let mut disc_roots = vec![abs_repo_path.clone()];
    if let Some(g) = &gitops_root {
        disc_roots.push(g.clone());
    }

    let mut m = Mapper::new();
    for root in &disc_roots {
        m.walk(root, &filter);
    }
    let k8s_invs: Vec<sources::k8s::K8sInventory> = disc_roots
        .iter()
        .map(|root| sources::k8s::discover(root, &mut m.charts, &mut m.services, &filter))
        .collect();
    let compose_inv =
        sources::compose::discover(&abs_repo_path, &mut m.charts, &mut m.services, &filter);
    m.link();

    ui::print_phase(
        "Phase 2: Exposure Analysis",
        "Analyzing Kubernetes deployment configurations",
    );
    // Analyze each Helm chart that is linked to at least one service (dedupe
    // so shared charts run once). K8s/compose units have their own analyzers.
    let mut analyzed = vec![false; m.charts.len()];
    for s in &m.services {
        if let Some(idx) = s.chart {
            if !analyzed[idx] && m.charts[idx].source == model::SourceKind::Helm {
                analyzed[idx] = true;
                analyzer::analyze_exposure(&mut m.charts[idx], &engine, args.env.as_deref());
            }
        }
    }
    for k8s_inv in &k8s_invs {
        sources::k8s::analyze(k8s_inv, &mut m.charts, &engine);
    }
    sources::compose::analyze(&compose_inv, &mut m.charts, &engine);

    if args.scan_only {
        ui::print_warning("Mode: Exposure Analysis Only (Skipping SARIF ingestion)");

        write_graph(&args, &m);
        let root = build_report(&m, "exposure-audit", None);
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
    let ingest_result = ingestor::process_sarif(
        sarif_input,
        &mut m.services,
        &m.charts,
        &abs_repo_path,
        &engine,
        args.sarif_output.as_deref().filter(|s| !s.is_empty()),
    );

    if ingest_result.sarif_missing {
        return ExitCode::FAILURE;
    }

    write_graph(&args, &m);

    // --- Generate JSON Report (Full Scan) ---
    if let Some(out) = args.output.as_deref().filter(|s| !s.is_empty()) {
        let root = build_report(&m, "full-analysis", Some(&ingest_result));
        write_json_report(out, &root, "Full analysis report saved to");
    }

    ui::print_success("Reticulum Analysis Complete.");
    ExitCode::SUCCESS
}
