# Changelog

All notable changes to Reticulum are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [2.0.0] — 2026-07-02

Complete rewrite in Rust plus a major capability expansion. Reports are a
superset of v1 (new fields are additive) with two intentional changes noted
below.

### Added
- **Multi-source resource mapping**: raw Kubernetes manifests (Deployments,
  StatefulSets, DaemonSets, ReplicaSets, Jobs, CronJobs, Pods) and
  docker-compose stacks, alongside the existing Helm chart discovery. Each
  service in the report carries a `source` field (`helm` | `k8s` | `compose`).
- **Exposure traceability**: label-selector and backend-ref resolution across
  manifests produces explicit chains (`Ingress/x → Service/y → Deployment/z`,
  LoadBalancer/NodePort services, NetworkPolicy open egress), reported in the
  CLI, in `riskProfile.exposurePaths` and in the new exposure graph.
- **`--graph <file>`**: Mermaid flowchart of the exposure surface with
  priority-colored nodes and per-chain edges.
- **Rule DSL v2** (backward compatible): `\.` escaped dots, `*` wildcards and
  numeric indices in key paths; `any:` OR blocks; `in`, `gte`, `lte`,
  `not_exists` operators; finding matching on `severity` and `location`;
  `set_flags` with explicit booleans (flags can now be cleared); `manifest`
  target with `kind:` filter — including compose services as
  `kind: ComposeService`; validation warnings for malformed rules.
- **`--rules <dir>`**: explicit rule-set location, with CWD and
  executable-directory fallbacks.
- Default manifest rules (`rules/manifest/`): privileged containers,
  hostNetwork, dangerous capabilities, hostPath mounts.
- Documentation set: rewritten `RULES.md` (full reference + cookbook),
  `docs/architecture.md`, `docs/scoring.md`, `docs/sources.md`,
  `docs/integrations.md`.
- CI (tests, clippy, rustfmt, e2e smoke, Docker build) and tag-driven release
  automation (multi-platform binaries + multi-arch GHCR image).
- Test fixtures `tests/monorepo-08` (raw K8s traceability) and
  `tests/monorepo-09` (docker-compose).

### Fixed
Thirteen defects inherited from the D implementation, documented in
[AUDIT.md](AUDIT.md). Highlights:
- NaN score corruption when rules omitted `score_multiplier`/`score_factor`.
- Per-finding fixability mutating the shared chart profile (SARIF
  order-dependent scores).
- Crash on SARIF results without `ruleId`; integer `security-severity`
  ignored; out-of-range severities now clamped.
- Rules silently not loading when the binary ran outside the repo root.
- String-prefix path matching mislinking sibling directories
  (`apps/api` vs `apps/api-gateway`) in both finding attribution and
  chart linking.
- The shipped IAM rules (IRSA / GCP Workload Identity) never matched — the
  v1 engine could not address annotation keys containing dots.

### Changed
- **Intentional output changes:** service `type` is now `HelmLinked`
  (was the `HelmVinked` typo); `riskProfile.baseRiskScore` no longer depends
  on SARIF result order. Rule load order is deterministic (sorted), so
  `appliedRuleIds` ordering is stable across machines.
- Build toolchain: `cargo build --release` replaces `dub build`;
  the Docker image builds from `rust:1-slim-bookworm`.

## [1.0.0] — 2025

Initial public release (D implementation): Helm chart discovery, values-based
exposure rules, SARIF ingestion with contextual scoring, enriched SARIF and
JSON reports.
