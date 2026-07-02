# Architecture

Reticulum is a three-phase pipeline: **discover** what runs, **analyze** how
exposed it is, **score** what the scanners found — in context.

```mermaid
flowchart TB
    subgraph inputs [Inputs]
        repo[(Repository)]
        sarif[SARIF from Trivy / Semgrep / any scanner]
        rules[YAML rules]
    end

    subgraph phase1 [Phase 1 — Service Discovery]
        docker[Dockerfile scan]
        helm[Helm charts<br/>Chart.yaml + values]
        k8s[Raw K8s manifests<br/>Deployments, Services, Ingress…]
        compose[docker-compose<br/>services & ports]
        link[Service ↔ unit linking<br/>name · path · image heuristics]
    end

    subgraph phase2 [Phase 2 — Exposure Analysis]
        engine[Rule engine<br/>values · metadata · manifest rules]
        chains[Exposure chain tracing<br/>Ingress → Service → Workload]
        profile[RiskProfile per unit<br/>flags · multipliers · boosts · paths]
    end

    subgraph phase3 [Phase 3 — Contextual Scoring]
        ingest[SARIF ingestion<br/>severity extraction · path resolution]
        frules[Finding rules<br/>suppress · score_factor]
        score[Contextual score + priority]
    end

    subgraph outputs [Outputs]
        cli[CLI report]
        json[JSON report]
        esarif[Enriched SARIF]
        graph[Exposure graph<br/>Mermaid]
    end

    repo --> docker & helm & k8s & compose --> link
    rules --> engine
    link --> engine --> profile
    k8s --> chains --> profile
    sarif --> ingest --> frules --> score
    profile --> score
    profile --> graph
    score --> cli & json & esarif
```

## Modules

| Module | Responsibility |
|---|---|
| `main.rs` | CLI, rule loading, phase orchestration, reports |
| `mapper.rs` | Dockerfile + Helm chart discovery, service↔unit linking |
| `sources/k8s.rs` | Raw manifest discovery, label-selector exposure chains |
| `sources/compose.rs` | docker-compose services, published-port analysis |
| `analyzer.rs` | Helm values analysis through the rule engine |
| `rules/` | The DSL: `parser.rs` (load + validate), `path.rs` (dot-paths, wildcards, escapes), `engine.rs` (evaluation) |
| `ingestor.rs` | SARIF parsing, severity extraction, finding↔service attribution, scoring |
| `model.rs` | Domain: `Service`, `Chart` (config unit), `RiskProfile`, `Finding`, `Priority` |
| `graph.rs` | Mermaid exposure graph |
| `ui.rs` | Terminal presentation |

## Phase 1 — Service Discovery

Four discoverers contribute to a single inventory:

1. **Dockerfiles** — every `Dockerfile`, `Dockerfile.<name>`,
   `<name>.Dockerfile` becomes a *service* (the unit findings attach to).
2. **Helm charts** — every `Chart.yaml` directory becomes a *config unit*.
3. **Raw Kubernetes manifests** — every YAML document with
   `apiVersion` + `kind` + `metadata.name` outside chart directories.
   Workload kinds (Deployment, StatefulSet, DaemonSet, ReplicaSet, Job,
   CronJob, Pod) become config units; Services, Ingresses, HTTPRoutes and
   NetworkPolicies feed exposure tracing.
4. **docker-compose** — every service in
   `docker-compose.y(a)ml` / `compose.y(a)ml` becomes a config unit.

Linking scores each service↔unit pair: exact name match (+100), directory
containment (+80, component-wise), `values.yaml` mentioning the service id
(+60). Best non-zero score wins.

## Phase 2 — Exposure Analysis

Each config unit gets a **RiskProfile**: five context flags
(`isPublic`, `isPrivileged`, `hasDangerousCaps`, `hasInternetEgress`,
`mountServiceToken`), accumulated score multipliers and boosts, the list of
applied rule ids, and — for K8s/compose — **exposure paths**: explicit chains
like `Ingress/web-ingress → Service/web-svc → Deployment/web-frontend`,
resolved through label selectors and backend references, not guesses.

Everything else is driven by YAML rules (see [RULES.md](../RULES.md)).

## Phase 3 — Contextual Scoring

Every SARIF finding is attributed to a service by robust path resolution
(CWD-relative, repo-relative, prefix-strip fallback; absolute container paths
are re-anchored). Its base severity (0–100) is then transformed by the owning
unit's RiskProfile — the math is in [scoring.md](scoring.md) — and mapped to a
priority (P0_BLEEDING … P4_LOW).

## Design principles

- **Rules over hardcode.** Detection logic belongs in YAML that users can
  read, fork and extend. Code-level detection is reserved for what YAML can't
  express (label-selector graph traversal).
- **Additive outputs.** New capabilities add fields (`source`,
  `exposurePaths`) without breaking existing consumers.
- **Fail soft.** Malformed YAML, broken rules or weird SARIF produce warnings
  and degraded output, never a crash.
- **Deterministic.** Sorted discovery and rule loading — same input, same
  output, byte for byte.
