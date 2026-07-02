//! Exposure graph rendering: services, exposure vectors and their chains as a
//! Mermaid flowchart, ready to paste into READMEs, PRs or dashboards.

use crate::model::{Chart, Priority, Service};
use std::collections::BTreeMap;

pub fn render_mermaid(services: &[Service], charts: &[Chart]) -> String {
    let mut out = String::from("flowchart LR\n");
    out.push_str("    classDef p0 fill:#7f1d1d,stroke:#ef4444,color:#ffffff,stroke-width:2px\n");
    out.push_str("    classDef p1 fill:#9a3412,stroke:#f97316,color:#ffffff\n");
    out.push_str("    classDef p2 fill:#854d0e,stroke:#eab308,color:#ffffff\n");
    out.push_str("    classDef p3 fill:#1e3a8a,stroke:#3b82f6,color:#ffffff\n");
    out.push_str("    classDef p4 fill:#374151,stroke:#9ca3af,color:#e5e7eb\n");
    out.push_str("    classDef vector fill:#0f766e,stroke:#14b8a6,color:#ffffff\n");
    out.push_str("    internet((\"🌐 Internet\"))\n");

    // Deterministic order
    let mut ordered: Vec<&Service> = services.iter().collect();
    ordered.sort_by(|a, b| a.id.cmp(&b.id));

    let mut vector_nodes: BTreeMap<String, String> = BTreeMap::new();
    let mut edges: Vec<String> = Vec::new();

    for svc in &ordered {
        let chart = svc.chart.map(|idx| &charts[idx]);
        let (score, priority) = service_score(svc, chart);
        let node = node_id("svc", &svc.id);
        let mut badges = String::new();
        if let Some(c) = chart {
            if c.risk.is_privileged {
                badges.push_str(" ⚠");
            }
            if c.risk.has_dangerous_caps {
                badges.push_str(" ☠");
            }
        }
        let source = chart.map(|c| c.source.as_str()).unwrap_or("orphan");
        out.push_str(&format!(
            "    {}[\"{}{}<br/>{} · score {} · {}\"]:::{}\n",
            node,
            escape(&svc.id),
            badges,
            source,
            score,
            priority_label(priority),
            priority_class(priority),
        ));

        let Some(c) = chart else { continue };

        if c.risk.exposure_paths.is_empty() {
            if c.risk.is_public {
                // Public via values-level rules: label the edge with them
                let rules = c
                    .risk
                    .applied_rule_ids
                    .iter()
                    .filter(|r| r.contains("exposure"))
                    .cloned()
                    .collect::<Vec<_>>()
                    .join(", ");
                let label = if rules.is_empty() { "exposed".to_string() } else { rules };
                edges.push(format!("    internet -->|\"{}\"| {}\n", escape(&label), node));
            }
            continue;
        }

        for path in &c.risk.exposure_paths {
            if let Some((label, _)) = path.split_once(" ← ") {
                // Outbound: open egress from the workload to the internet
                edges.push(format!("    {} -.->|\"{}\"| internet\n", node, escape(label)));
                continue;
            }

            let segments: Vec<&str> = path.split(" → ").collect();
            let mut prev = "internet".to_string();
            for (i, seg) in segments.iter().enumerate() {
                let is_last = i == segments.len() - 1;
                // The chain's tail is the workload itself -> the service node
                if is_last && seg.ends_with(&format!("/{}", svc.id)) {
                    edges.push(format!("    {} --> {}\n", prev, node));
                    break;
                }
                if is_last {
                    // Single-segment path (e.g. compose port publish)
                    edges.push(format!("    {} -->|\"{}\"| {}\n", prev, escape(seg), node));
                    break;
                }
                let vec_node = vector_nodes
                    .entry(seg.to_string())
                    .or_insert_with(|| node_id("vec", seg))
                    .clone();
                edges.push(format!("    {} --> {}\n", prev, vec_node));
                prev = vec_node;
            }
        }
    }

    for (label, id) in &vector_nodes {
        out.push_str(&format!("    {}[\"{}\"]:::vector\n", id, escape(label)));
    }
    // Dedup edges (shared vectors produce repeats)
    edges.sort();
    edges.dedup();
    for e in edges {
        out.push_str(&e);
    }
    out
}

/// Best available score: max finding score when SARIF was ingested, else the
/// baseline-50 contextual score.
fn service_score(svc: &Service, chart: Option<&Chart>) -> (i32, Priority) {
    let score = svc
        .findings
        .iter()
        .map(|f| f.reticulum_score)
        .max()
        .or_else(|| chart.map(|c| c.risk.calculate_score(50)))
        .unwrap_or(0);
    (score, Priority::from_score(score))
}

fn priority_class(p: Priority) -> &'static str {
    match p {
        Priority::P0Bleeding => "p0",
        Priority::P1Critical => "p1",
        Priority::P2High => "p2",
        Priority::P3Medium => "p3",
        Priority::P4Low => "p4",
    }
}

fn priority_label(p: Priority) -> String {
    p.to_string()
}

fn node_id(prefix: &str, raw: &str) -> String {
    let sanitized: String = raw
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '_' })
        .collect();
    format!("{}_{}", prefix, sanitized)
}

fn escape(s: &str) -> String {
    s.replace('"', "#quot;")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::SourceKind;

    #[test]
    fn graph_renders_chain_and_priority_classes() {
        let mut chart = Chart::with_source("web-frontend", "/repo/k8s", SourceKind::K8s);
        chart.risk.set_flag("isPublic", true);
        chart.risk.add_multiplier(1.3);
        chart
            .risk
            .exposure_paths
            .push("Ingress/web-ingress → Service/web-svc → Deployment/web-frontend".to_string());
        let mut svc = Service::new("web-frontend", "/repo/k8s/web.yaml", "/repo/k8s");
        svc.chart = Some(0);

        let out = render_mermaid(&[svc], &[chart]);
        assert!(out.contains("flowchart LR"));
        assert!(out.contains("internet --> vec_Ingress_web_ingress"));
        assert!(out.contains("vec_Ingress_web_ingress --> vec_Service_web_svc"));
        assert!(out.contains("vec_Service_web_svc --> svc_web_frontend"));
        // 50 * 1.3 = 65 -> P2
        assert!(out.contains(":::p2"));
    }

    #[test]
    fn graph_egress_paths_point_outward() {
        let mut chart = Chart::with_source("batch", "/repo/k8s", SourceKind::K8s);
        chart
            .risk
            .exposure_paths
            .push("NetworkPolicy/open egress 0.0.0.0/0 ← Deployment/batch".to_string());
        let mut svc = Service::new("batch", "/repo/k8s/b.yaml", "/repo/k8s");
        svc.chart = Some(0);

        let out = render_mermaid(&[svc], &[chart]);
        assert!(out.contains("svc_batch -.->"));
        assert!(out.contains("| internet"));
    }

    #[test]
    fn graph_internal_service_has_no_internet_edge() {
        let chart = Chart::new("worker", "/repo/charts/worker");
        let mut svc = Service::new("worker", "/repo/apps/worker/Dockerfile", "/repo/apps/worker");
        svc.chart = Some(0);
        let out = render_mermaid(&[svc], &[chart]);
        assert!(out.contains("svc_worker"));
        assert!(!out.contains("internet --> svc_worker"));
        assert!(!out.contains("internet -->|"));
    }

    #[test]
    fn graph_helm_public_uses_rule_labels() {
        let mut chart = Chart::new("admin-api", "/repo/charts/admin-api");
        chart.risk.set_flag("isPublic", true);
        chart.risk.applied_rule_ids.push("exposure-ingress-enabled".to_string());
        let mut svc = Service::new("admin-api", "/repo/apps/admin/Dockerfile", "/repo/apps/admin");
        svc.chart = Some(0);
        let out = render_mermaid(&[svc], &[chart]);
        assert!(out.contains("internet -->|\"exposure-ingress-enabled\"| svc_admin_api"));
    }
}
