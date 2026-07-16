//! Raw Kubernetes manifest discovery and exposure-chain tracing.
//!
//! Discovery collects every YAML document with `apiVersion` + `kind` +
//! `metadata.name` outside Helm chart directories (templated chart files
//! don't parse as YAML and are skipped naturally; anything under a directory
//! owning a Chart.yaml is excluded explicitly).
//!
//! Traceability: workloads are connected to Services by label selectors and
//! Services to Ingress/HTTPRoute by backend references, producing explicit
//! exposure chains like `Ingress/web → Service/web-svc → Deployment/web`.

use crate::model::{Chart, Service, SourceKind};
use crate::pathfilter::{relative_str, PathFilter};
use crate::rules::RuleEngine;
use serde_yaml::Value as Yaml;
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

const WORKLOAD_KINDS: [&str; 7] = [
    "Deployment",
    "StatefulSet",
    "DaemonSet",
    "ReplicaSet",
    "Job",
    "CronJob",
    "Pod",
];

#[derive(Debug)]
pub struct ManifestDoc {
    pub kind: String,
    pub name: String,
    pub doc: Yaml,
    pub dir: String,
    pub file: String,
}

/// One discovered workload: its config unit index plus the manifest docs that
/// belong to its exposure analysis.
#[derive(Debug)]
pub struct K8sUnit {
    pub chart_idx: usize,
    pub workload_doc: usize,
}

#[derive(Debug, Default)]
pub struct K8sInventory {
    pub docs: Vec<ManifestDoc>,
    pub units: Vec<K8sUnit>,
}

/// Scan for raw manifests, appending one config unit per workload and a
/// Service entry (for finding attribution) when none exists for that id.
pub fn discover(
    root: &Path,
    charts: &mut Vec<Chart>,
    services: &mut Vec<Service>,
    filter: &PathFilter,
) -> K8sInventory {
    let mut inv = K8sInventory::default();
    let helm_dirs = collect_helm_dirs(root);

    let mut files: Vec<PathBuf> = WalkDir::new(root)
        .sort_by_file_name()
        .into_iter()
        .filter_map(Result::ok)
        .filter(|e| {
            let name = e.file_name().to_string_lossy().to_lowercase();
            e.file_type().is_file()
                && (name.ends_with(".yaml") || name.ends_with(".yml"))
                && !crate::sources::compose::is_compose_file(&name)
                && filter.is_allowed(&relative_str(root, e.path()))
        })
        .map(|e| e.into_path())
        .collect();
    files.retain(|f| !helm_dirs.iter().any(|d| f.starts_with(d)));
    files.sort();

    for file in files {
        let Ok(content) = fs::read_to_string(&file) else {
            continue;
        };
        for doc_de in serde_yaml::Deserializer::from_str(&content) {
            use serde::Deserialize;
            let Ok(doc) = Yaml::deserialize(doc_de) else {
                continue; // templated or invalid YAML — not a raw manifest
            };
            let (Some(kind), Some(name)) = (
                doc.get("kind").and_then(|k| k.as_str()).map(String::from),
                doc.get("metadata")
                    .and_then(|m| m.get("name"))
                    .and_then(|n| n.as_str())
                    .map(String::from),
            ) else {
                continue;
            };
            if doc.get("apiVersion").is_none() {
                continue;
            }
            inv.docs.push(ManifestDoc {
                kind,
                name,
                doc,
                dir: file
                    .parent()
                    .unwrap_or(Path::new(""))
                    .to_string_lossy()
                    .to_string(),
                file: file.to_string_lossy().to_string(),
            });
        }
    }

    // One config unit per workload document
    for (doc_idx, doc) in inv.docs.iter().enumerate() {
        if !WORKLOAD_KINDS.contains(&doc.kind.as_str()) {
            continue;
        }
        let chart_idx = charts.len();
        charts.push(Chart::with_source(&doc.name, &doc.dir, SourceKind::K8s));
        inv.units.push(K8sUnit {
            chart_idx,
            workload_doc: doc_idx,
        });

        // Make the workload addressable in the report / SARIF matching
        if !services.iter().any(|s| s.id == doc.name) {
            let mut svc = Service::new(&doc.name, &doc.file, &doc.dir);
            svc.chart = Some(chart_idx);
            services.push(svc);
        }
    }

    if !inv.units.is_empty() {
        println!(
            "  [K8s] Discovered {} manifest documents, {} workloads",
            inv.docs.len(),
            inv.units.len()
        );
    }
    inv
}

fn collect_helm_dirs(root: &Path) -> Vec<PathBuf> {
    WalkDir::new(root)
        .into_iter()
        .filter_map(Result::ok)
        .filter(|e| {
            e.file_type().is_file()
                && e.file_name()
                    .to_string_lossy()
                    .eq_ignore_ascii_case("chart.yaml")
        })
        .filter_map(|e| e.path().parent().map(Path::to_path_buf))
        .collect()
}

/// Analyze every K8s workload unit: selector-based exposure chains plus
/// user-defined `manifest`-target rules.
pub fn analyze(inv: &K8sInventory, charts: &mut [Chart], engine: &RuleEngine) {
    for unit in &inv.units {
        let workload = &inv.docs[unit.workload_doc];
        let chart = &mut charts[unit.chart_idx];
        println!(
            "  [Analyzer] Analyzing {}/{} ({})",
            workload.kind, workload.name, workload.file
        );
        chart.risk.reset();
        engine.evaluate_metadata(chart);

        let labels = workload_labels(&workload.doc);
        let mut related: Vec<usize> = vec![unit.workload_doc];

        // Service edges via label selectors
        for (svc_idx, svc) in inv.docs.iter().enumerate() {
            if svc.kind != "Service" {
                continue;
            }
            let selector = svc.doc.get("spec").and_then(|s| s.get("selector"));
            if !selector_matches(selector, &labels) {
                continue;
            }
            related.push(svc_idx);

            let svc_type = svc
                .doc
                .get("spec")
                .and_then(|s| s.get("type"))
                .and_then(|t| t.as_str())
                .unwrap_or("ClusterIP");

            match svc_type {
                "LoadBalancer" => expose(
                    chart,
                    "k8s-exposure-loadbalancer",
                    1.3,
                    format!(
                        "Service/{} (LoadBalancer) → {}/{}",
                        svc.name, workload.kind, workload.name
                    ),
                ),
                "NodePort" => expose(
                    chart,
                    "k8s-exposure-nodeport",
                    1.1,
                    format!(
                        "Service/{} (NodePort) → {}/{}",
                        svc.name, workload.kind, workload.name
                    ),
                ),
                _ => {}
            }

            // Ingress / HTTPRoute edges via backend references
            for (edge_idx, edge) in inv.docs.iter().enumerate() {
                let backends = match edge.kind.as_str() {
                    "Ingress" => ingress_backends(&edge.doc),
                    "HTTPRoute" => httproute_backends(&edge.doc),
                    _ => continue,
                };
                if !backends.contains(&svc.name) {
                    continue;
                }
                related.push(edge_idx);
                expose(
                    chart,
                    if edge.kind == "Ingress" {
                        "k8s-exposure-ingress"
                    } else {
                        "k8s-exposure-httproute"
                    },
                    1.3,
                    format!(
                        "{}/{} → Service/{} → {}/{}",
                        edge.kind, edge.name, svc.name, workload.kind, workload.name
                    ),
                );
            }
        }

        // NetworkPolicy: open egress to the internet
        for (np_idx, np) in inv.docs.iter().enumerate() {
            if np.kind != "NetworkPolicy" {
                continue;
            }
            let pod_selector = np
                .doc
                .get("spec")
                .and_then(|s| s.get("podSelector"))
                .and_then(|p| p.get("matchLabels"));
            if !selector_matches(pod_selector, &labels) {
                continue;
            }
            related.push(np_idx);
            if has_open_egress(&np.doc) {
                chart.risk.set_flag("hasInternetEgress", true);
                chart
                    .risk
                    .applied_rule_ids
                    .push("k8s-netpol-open-egress".to_string());
                chart.risk.exposure_paths.push(format!(
                    "NetworkPolicy/{} egress 0.0.0.0/0 ← {}/{}",
                    np.name, workload.kind, workload.name
                ));
            }
        }

        // User-defined manifest rules over every related document
        related.sort_unstable();
        related.dedup();
        for idx in related {
            engine.evaluate_manifest(chart, &inv.docs[idx].doc);
        }

        chart.risk.dedup_applied_rules();
        print_profile(chart);
    }
}

fn expose(chart: &mut Chart, rule_id: &str, multiplier: f32, path: String) {
    println!("      → EXPOSURE: {} [{}]", path, rule_id);
    chart.risk.set_flag("isPublic", true);
    if !chart.risk.applied_rule_ids.iter().any(|r| r == rule_id) {
        chart.risk.add_multiplier(multiplier);
        chart.risk.applied_rule_ids.push(rule_id.to_string());
    }
    chart.risk.exposure_paths.push(path);
}

/// Pod template labels (or Pod labels for bare Pods).
fn workload_labels(doc: &Yaml) -> Vec<(String, String)> {
    let template_labels = doc
        .get("spec")
        .and_then(|s| s.get("template"))
        .and_then(|t| t.get("metadata"))
        .and_then(|m| m.get("labels"));
    let labels = template_labels.or_else(|| doc.get("metadata").and_then(|m| m.get("labels")));

    let Some(Yaml::Mapping(map)) = labels else {
        return Vec::new();
    };
    map.iter()
        .filter_map(|(k, v)| Some((k.as_str()?.to_string(), yaml_scalar(v)?)))
        .collect()
}

/// True when `selector` is a non-empty subset of `labels`.
fn selector_matches(selector: Option<&Yaml>, labels: &[(String, String)]) -> bool {
    let Some(Yaml::Mapping(sel)) = selector else {
        return false;
    };
    if sel.is_empty() || labels.is_empty() {
        return false;
    }
    sel.iter().all(|(k, v)| {
        let (Some(key), Some(val)) = (k.as_str(), yaml_scalar(v)) else {
            return false;
        };
        labels.iter().any(|(lk, lv)| lk == key && *lv == val)
    })
}

fn yaml_scalar(v: &Yaml) -> Option<String> {
    match v {
        Yaml::String(s) => Some(s.clone()),
        Yaml::Number(n) => Some(n.to_string()),
        Yaml::Bool(b) => Some(b.to_string()),
        _ => None,
    }
}

/// Service names referenced by an Ingress (networking.k8s.io/v1 and legacy).
fn ingress_backends(doc: &Yaml) -> HashSet<String> {
    let mut out = HashSet::new();
    let spec = doc.get("spec");

    // Default backend
    if let Some(name) = spec
        .and_then(|s| s.get("defaultBackend"))
        .and_then(|b| b.get("service"))
        .and_then(|s| s.get("name"))
        .and_then(|n| n.as_str())
    {
        out.insert(name.to_string());
    }

    let Some(Yaml::Sequence(rules)) = spec.and_then(|s| s.get("rules")) else {
        return out;
    };
    for rule in rules {
        let Some(Yaml::Sequence(paths)) = rule.get("http").and_then(|h| h.get("paths")) else {
            continue;
        };
        for p in paths {
            let backend = p.get("backend");
            // networking.k8s.io/v1
            if let Some(name) = backend
                .and_then(|b| b.get("service"))
                .and_then(|s| s.get("name"))
                .and_then(|n| n.as_str())
            {
                out.insert(name.to_string());
            }
            // extensions/v1beta1 legacy
            if let Some(name) = backend
                .and_then(|b| b.get("serviceName"))
                .and_then(|n| n.as_str())
            {
                out.insert(name.to_string());
            }
        }
    }
    out
}

/// Service names referenced by a Gateway API HTTPRoute.
fn httproute_backends(doc: &Yaml) -> HashSet<String> {
    let mut out = HashSet::new();
    let Some(Yaml::Sequence(rules)) = doc.get("spec").and_then(|s| s.get("rules")) else {
        return out;
    };
    for rule in rules {
        let Some(Yaml::Sequence(refs)) = rule.get("backendRefs") else {
            continue;
        };
        for r in refs {
            if let Some(name) = r.get("name").and_then(|n| n.as_str()) {
                out.insert(name.to_string());
            }
        }
    }
    out
}

/// Any egress rule reaching 0.0.0.0/0 (or ::/0), or an egress policy with no
/// restrictions at all.
fn has_open_egress(doc: &Yaml) -> bool {
    let spec = doc.get("spec");
    let Some(Yaml::Sequence(egress)) = spec.and_then(|s| s.get("egress")) else {
        return false;
    };
    for rule in egress {
        match rule.get("to") {
            None => return true, // egress rule without 'to' = allow all
            Some(Yaml::Sequence(tos)) => {
                for to in tos {
                    if let Some(cidr) = to
                        .get("ipBlock")
                        .and_then(|b| b.get("cidr"))
                        .and_then(|c| c.as_str())
                    {
                        if cidr == "0.0.0.0/0" || cidr == "::/0" {
                            return true;
                        }
                    }
                }
            }
            _ => {}
        }
    }
    false
}

fn print_profile(chart: &Chart) {
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
        "      • Internet Egress    : {}",
        if chart.risk.has_internet_egress {
            "YES"
        } else {
            "NO"
        }
    );
    for path in &chart.risk.exposure_paths {
        println!("      ⇢ EXPOSURE PATH: {}", path);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn yaml(s: &str) -> Yaml {
        serde_yaml::from_str(s).unwrap()
    }

    #[test]
    fn selector_subset_semantics() {
        let labels = vec![
            ("app".to_string(), "web".to_string()),
            ("tier".to_string(), "frontend".to_string()),
        ];
        let sel = yaml("app: web\n");
        assert!(selector_matches(Some(&sel), &labels));
        let sel2 = yaml("app: web\ntier: frontend\n");
        assert!(selector_matches(Some(&sel2), &labels));
        let sel3 = yaml("app: other\n");
        assert!(!selector_matches(Some(&sel3), &labels));
        let empty = yaml("{}");
        assert!(!selector_matches(Some(&empty), &labels));
        assert!(!selector_matches(None, &labels));
    }

    #[test]
    fn workload_labels_from_pod_template() {
        let dep = yaml(
            "spec:\n  template:\n    metadata:\n      labels:\n        app: web\n        version: '2'\n",
        );
        let labels = workload_labels(&dep);
        assert!(labels.contains(&("app".to_string(), "web".to_string())));
        assert!(labels.contains(&("version".to_string(), "2".to_string())));
    }

    #[test]
    fn ingress_backend_extraction_v1_and_legacy() {
        let ing = yaml(
            r#"
spec:
  defaultBackend:
    service:
      name: fallback
  rules:
    - host: a.com
      http:
        paths:
          - backend:
              service:
                name: web-svc
          - backend:
              serviceName: legacy-svc
"#,
        );
        let backends = ingress_backends(&ing);
        assert!(backends.contains("web-svc"));
        assert!(backends.contains("legacy-svc"));
        assert!(backends.contains("fallback"));
    }

    #[test]
    fn httproute_backend_extraction() {
        let route = yaml(
            "spec:\n  rules:\n    - backendRefs:\n        - name: api-svc\n          port: 80\n",
        );
        assert!(httproute_backends(&route).contains("api-svc"));
    }

    #[test]
    fn open_egress_detection() {
        let open =
            yaml("spec:\n  egress:\n    - to:\n        - ipBlock:\n            cidr: 0.0.0.0/0\n");
        assert!(has_open_egress(&open));
        let unrestricted = yaml("spec:\n  egress:\n    - {}\n");
        assert!(has_open_egress(&unrestricted));
        let closed =
            yaml("spec:\n  egress:\n    - to:\n        - ipBlock:\n            cidr: 10.0.0.0/8\n");
        assert!(!has_open_egress(&closed));
        let none = yaml("spec: {}\n");
        assert!(!has_open_egress(&none));
    }
}
