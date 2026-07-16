//! docker-compose discovery: each compose service becomes a config unit; its
//! published ports, privileges and capabilities feed the risk profile.
//!
//! Manifest-target rules also run against compose services: every service is
//! evaluated as a synthetic document of kind `ComposeService`, so the YAML
//! DSL reaches compose stacks too.

use crate::model::{Chart, Service, SourceKind};
use crate::pathfilter::{relative_str, PathFilter};
use crate::rules::RuleEngine;
use serde_yaml::{Mapping, Value as Yaml};
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

const COMPOSE_NAMES: [&str; 4] = [
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
];

const DANGEROUS_CAPS: [&str; 6] = [
    "SYS_ADMIN",
    "NET_ADMIN",
    "SYS_PTRACE",
    "SYS_MODULE",
    "DAC_READ_SEARCH",
    "ALL",
];

pub fn is_compose_file(lower_name: &str) -> bool {
    COMPOSE_NAMES.contains(&lower_name)
}

#[derive(Debug)]
pub struct ComposeUnit {
    pub chart_idx: usize,
    pub name: String,
    pub definition: Yaml,
    pub file: String,
}

#[derive(Debug, Default)]
pub struct ComposeInventory {
    pub units: Vec<ComposeUnit>,
}

pub fn discover(
    root: &Path,
    charts: &mut Vec<Chart>,
    services: &mut Vec<Service>,
    filter: &PathFilter,
) -> ComposeInventory {
    let mut inv = ComposeInventory::default();

    let mut files: Vec<PathBuf> = WalkDir::new(root)
        .sort_by_file_name()
        .into_iter()
        .filter_map(Result::ok)
        .filter(|e| {
            e.file_type().is_file()
                && is_compose_file(&e.file_name().to_string_lossy().to_lowercase())
                && filter.is_allowed(&relative_str(root, e.path()))
        })
        .map(|e| e.into_path())
        .collect();
    files.sort();

    for file in files {
        let Ok(content) = fs::read_to_string(&file) else {
            continue;
        };
        let Ok(doc) = serde_yaml::from_str::<Yaml>(&content) else {
            println!("  [Compose] Failed to parse {}", file.display());
            continue;
        };
        let Some(Yaml::Mapping(svcs)) = doc.get("services") else {
            continue;
        };
        let compose_dir = file.parent().unwrap_or(Path::new("")).to_path_buf();

        for (name_node, definition) in svcs {
            let Some(name) = name_node.as_str() else {
                continue;
            };

            let (context_dir, dockerfile) = build_context(definition, &compose_dir);
            let unit_dir = context_dir
                .as_deref()
                .unwrap_or(&compose_dir)
                .to_string_lossy()
                .to_string();

            let chart_idx = charts.len();
            charts.push(Chart::with_source(name, &unit_dir, SourceKind::Compose));
            inv.units.push(ComposeUnit {
                chart_idx,
                name: name.to_string(),
                definition: definition.clone(),
                file: file.to_string_lossy().to_string(),
            });

            if !services.iter().any(|s| s.id == name) {
                // Image-only services (no build context) get the compose file
                // itself as their "directory" so repo-wide findings don't
                // spuriously attach to them.
                let attribution_dir = if context_dir.is_some() {
                    unit_dir.clone()
                } else {
                    file.to_string_lossy().to_string()
                };
                let mut svc = Service::new(
                    name,
                    &dockerfile.unwrap_or_else(|| file.to_string_lossy().to_string()),
                    &attribution_dir,
                );
                svc.chart = Some(chart_idx);
                services.push(svc);
            }
        }
    }

    if !inv.units.is_empty() {
        println!(
            "  [Compose] Discovered {} compose services",
            inv.units.len()
        );
    }
    inv
}

/// Resolve the build context directory and Dockerfile of a compose service.
fn build_context(definition: &Yaml, compose_dir: &Path) -> (Option<PathBuf>, Option<String>) {
    let build = definition.get("build");
    let (context, dockerfile) = match build {
        Some(Yaml::String(ctx)) => (Some(ctx.clone()), None),
        Some(Yaml::Mapping(_)) => (
            build
                .and_then(|b| b.get("context"))
                .and_then(|c| c.as_str())
                .map(String::from),
            build
                .and_then(|b| b.get("dockerfile"))
                .and_then(|d| d.as_str())
                .map(String::from),
        ),
        _ => (None, None),
    };

    let context_dir = context.map(|c| {
        let p = compose_dir.join(c);
        p.canonicalize().unwrap_or(p)
    });
    let dockerfile_path = context_dir.as_ref().map(|dir| {
        dir.join(dockerfile.as_deref().unwrap_or("Dockerfile"))
            .to_string_lossy()
            .to_string()
    });
    (context_dir, dockerfile_path)
}

pub fn analyze(inv: &ComposeInventory, charts: &mut [Chart], engine: &RuleEngine) {
    for unit in &inv.units {
        let chart = &mut charts[unit.chart_idx];
        println!(
            "  [Analyzer] Analyzing compose service: {} ({})",
            unit.name, unit.file
        );
        chart.risk.reset();
        engine.evaluate_metadata(chart);

        analyze_ports(chart, unit);
        analyze_security(chart, unit);

        // User-defined manifest rules, as kind: ComposeService
        engine.evaluate_manifest(chart, &synthetic_doc(unit));

        chart.risk.dedup_applied_rules();
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
        for path in &chart.risk.exposure_paths {
            println!("      ⇢ EXPOSURE PATH: {}", path);
        }
    }
}

fn analyze_ports(chart: &mut Chart, unit: &ComposeUnit) {
    let Some(Yaml::Sequence(ports)) = unit.definition.get("ports") else {
        return;
    };
    let mut published = Vec::new();
    for port in ports {
        if let Some(desc) = published_port(port) {
            published.push(desc);
        }
    }
    if published.is_empty() {
        return;
    }
    chart.risk.set_flag("isPublic", true);
    chart.risk.add_multiplier(1.3);
    chart
        .risk
        .applied_rule_ids
        .push("compose-exposure-ports".to_string());
    for desc in published {
        chart
            .risk
            .exposure_paths
            .push(format!("Compose/{} publishes {}", unit.name, desc));
        println!(
            "      → EXPOSURE: Compose/{} publishes {} [compose-exposure-ports]",
            unit.name, desc
        );
    }
}

/// Returns a description when the port mapping is actually published to a
/// non-loopback interface. Container-only ports ("80") and localhost binds
/// ("127.0.0.1:8080:80") are not public.
fn published_port(port: &Yaml) -> Option<String> {
    match port {
        Yaml::String(s) => {
            let parts: Vec<&str> = s.split(':').collect();
            match parts.len() {
                2 => Some(format!("{}→{}", parts[0], parts[1])),
                3 => {
                    let host_ip = parts[0];
                    if host_ip == "127.0.0.1" || host_ip == "::1" || host_ip == "localhost" {
                        None
                    } else {
                        Some(format!("{}:{}→{}", parts[0], parts[1], parts[2]))
                    }
                }
                _ => None, // "80" alone: container port, not published
            }
        }
        Yaml::Number(_) => None, // bare container port
        Yaml::Mapping(_) => {
            let publ = port.get("published")?;
            let target = port.get("target").map(yaml_to_display).unwrap_or_default();
            let host_ip = port.get("host_ip").and_then(|h| h.as_str()).unwrap_or("");
            if host_ip == "127.0.0.1" || host_ip == "::1" {
                return None;
            }
            Some(format!("{}→{}", yaml_to_display(publ), target))
        }
        _ => None,
    }
}

fn yaml_to_display(v: &Yaml) -> String {
    match v {
        Yaml::String(s) => s.clone(),
        Yaml::Number(n) => n.to_string(),
        _ => String::new(),
    }
}

fn analyze_security(chart: &mut Chart, unit: &ComposeUnit) {
    let def = &unit.definition;

    if def.get("privileged").and_then(|p| p.as_bool()) == Some(true) {
        chart.risk.set_flag("isPrivileged", true);
        chart.risk.add_boost(20);
        chart
            .risk
            .applied_rule_ids
            .push("compose-privileged".to_string());
        println!("      → RULE MATCH: Compose privileged container (compose-privileged)");
    }

    if def.get("network_mode").and_then(|n| n.as_str()) == Some("host") {
        chart.risk.set_flag("isPrivileged", true);
        chart.risk.add_multiplier(1.5);
        chart
            .risk
            .applied_rule_ids
            .push("compose-host-network".to_string());
        println!("      → RULE MATCH: Compose host network (compose-host-network)");
    }

    if let Some(Yaml::Sequence(caps)) = def.get("cap_add") {
        let dangerous: Vec<&str> = caps
            .iter()
            .filter_map(|c| c.as_str())
            .filter(|c| DANGEROUS_CAPS.contains(&c.to_uppercase().as_str()))
            .collect();
        if !dangerous.is_empty() {
            chart.risk.set_flag("hasDangerousCaps", true);
            chart.risk.add_boost(15);
            chart
                .risk
                .applied_rule_ids
                .push("compose-dangerous-caps".to_string());
            println!(
                "      → RULE MATCH: Compose dangerous capabilities {:?} (compose-dangerous-caps)",
                dangerous
            );
        }
    }
}

/// Wrap a compose service definition as a manifest-like document so
/// `target: manifest` rules with `kind: ComposeService` can match it.
fn synthetic_doc(unit: &ComposeUnit) -> Yaml {
    let mut map = Mapping::new();
    map.insert(Yaml::from("kind"), Yaml::from("ComposeService"));
    map.insert(Yaml::from("name"), Yaml::from(unit.name.clone()));
    if let Yaml::Mapping(def) = &unit.definition {
        for (k, v) in def {
            map.insert(k.clone(), v.clone());
        }
    }
    Yaml::Mapping(map)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn yaml(s: &str) -> Yaml {
        serde_yaml::from_str(s).unwrap()
    }

    #[test]
    fn short_syntax_port_publishing() {
        assert_eq!(published_port(&yaml("\"8080:80\"")), Some("8080→80".into()));
        assert_eq!(
            published_port(&yaml("\"0.0.0.0:443:8443\"")),
            Some("0.0.0.0:443→8443".into())
        );
        // Loopback binds and container-only ports are not public
        assert_eq!(published_port(&yaml("\"127.0.0.1:5432:5432\"")), None);
        assert_eq!(published_port(&yaml("\"80\"")), None);
        assert_eq!(published_port(&yaml("80")), None);
    }

    #[test]
    fn long_syntax_port_publishing() {
        assert_eq!(
            published_port(&yaml("published: 8080\ntarget: 80\n")),
            Some("8080→80".into())
        );
        assert_eq!(
            published_port(&yaml("published: 8080\ntarget: 80\nhost_ip: 127.0.0.1\n")),
            None
        );
        assert_eq!(published_port(&yaml("target: 80\n")), None);
    }

    #[test]
    fn synthetic_doc_has_kind_and_fields() {
        let unit = ComposeUnit {
            chart_idx: 0,
            name: "web".into(),
            definition: yaml("image: nginx\nports:\n  - \"8080:80\"\n"),
            file: "docker-compose.yml".into(),
        };
        let doc = synthetic_doc(&unit);
        assert_eq!(
            doc.get("kind").and_then(|k| k.as_str()),
            Some("ComposeService")
        );
        assert_eq!(doc.get("image").and_then(|i| i.as_str()), Some("nginx"));
    }
}
