# Reticulum Rule DSL — Complete Reference

Reticulum's brain is a YAML rule engine. Rules read your deployment context
(Helm values, chart metadata, raw Kubernetes manifests, docker-compose
services) and your scanner findings (SARIF), and they shape the final risk
score of every vulnerability.

This document is the full reference for the DSL, followed by a
[cookbook](#cookbook) of ready-to-use recipes.

- Rules live in `rules/` (`exposure/`, `security/`, `scoring/`, `manifest/`,
  `custom/` — loaded in that order, `custom/` last so it can build on top).
- A file may contain **multiple rules** separated by `---`.
- Loading is recursive and sorted, so evaluation order is deterministic.
- Malformed rules never crash the run: the engine prints a warning and moves
  on. Unknown targets, operators or flags are also reported as warnings.

## Anatomy of a rule

```yaml
id: "exposure-ingress-enabled"          # Unique identifier (required)
name: "Public Ingress Exposure"         # Human-readable name
description: "Detects if Ingress is explicitly enabled"
severity: "high"                        # Informational metadata
tags: ["exposure", "ingress"]           # Informational metadata

target: "values"                        # WHERE to look (see Targets)

match:                                  # ALL must hold (AND)
  - key: "ingress.enabled"
    op: "eq"
    value: true
  - key: "ingress.hosts"
    op: "exists"

any:                                    # optional: at least ONE must hold (OR)
  - key: "ingress.className"
    op: "eq"
    value: "nginx"
  - key: "ingress.className"
    op: "eq"
    value: "traefik"

action:                                 # WHAT to do when it fires
  risk_profile:
    set_flag: "isPublic"
    score_multiplier: 1.3
  tags: ["public-facing"]
```

A rule fires when **every** `match:` condition holds **and**, if an `any:`
block is present, **at least one** of its conditions holds.

## Targets

| target | Evaluated against | When |
|---|---|---|
| `values` | Each Helm values file (`values.yaml`, `values-*.yaml`, `prod/staging/dev.yaml`) | Phase 2, per chart |
| `chart_metadata` | The chart/unit itself — keys `name` and `path` | Phase 2, per unit (all sources) |
| `manifest` | Each raw Kubernetes document related to a workload, and each compose service (as `kind: ComposeService`) | Phase 2, per K8s/compose unit |
| `finding` | Each SARIF finding, with the owning unit's tags as context | Phase 3, per finding |

### `manifest` + `kind`

`manifest` rules can restrict themselves to one Kubernetes kind
(case-insensitive). Without `kind:` they run on every document.

```yaml
id: "k8s-privileged-container"
target: "manifest"
kind: "Deployment"          # optional — omit to match any kind
match:
  - key: "spec.template.spec.containers.*.securityContext.privileged"
    op: "eq"
    value: true
```

A workload's exposure analysis spans several related documents (the workload
itself, its Services, Ingresses/HTTPRoutes and NetworkPolicies). A `manifest`
rule **contributes to a unit's score at most once**, even when several related
documents match — e.g. a rule keying off a `metadata.labels.team` label shared
by a Deployment/Service/Ingress trio fires once, not three times.

docker-compose services are evaluated as synthetic documents of kind
`ComposeService`, with the service definition at the top level plus `name`:

```yaml
id: "compose-host-networking"
target: "manifest"
kind: "ComposeService"
match:
  - key: "network_mode"
    op: "eq"
    value: "host"
```

## Key paths

`key` is a dot-notation path into the YAML document:

| Syntax | Meaning | Example |
|---|---|---|
| `a.b.c` | Nested mapping keys | `ingress.enabled` |
| `a\.b` | Escaped dot — key contains a literal `.` | `annotations.eks\.amazonaws\.com/role-arn` |
| `*` | Wildcard — every mapping value / sequence element | `containers.*.securityContext.privileged` |
| `0`, `1`, … | Numeric index into a sequence | `containers.0.name` |

A wildcard path can resolve to **many** nodes; the condition holds if **any**
resolved node satisfies it.

## Operators

| op | Works on | Semantics |
|---|---|---|
| `eq` | bool, number, string | Equality |
| `neq` | bool, number, string | Inequality |
| `contains` | string, list | Substring, or list contains the value |
| `regex` | string | Regular expression match ([syntax](https://docs.rs/regex)) |
| `exists` | any | The key path resolves to at least one node |
| `not_exists` | any | The key path resolves to nothing |
| `gt` / `lt` / `gte` / `lte` | number | Numeric comparison (int and float) |
| `in` | scalar | Value is one of a list of options |
| `contains_tag` | finding rules | The owning unit carries a given tag |

`in` takes a list:

```yaml
- key: "service.type"
  op: "in"
  value: ["LoadBalancer", "NodePort"]
```

### Finding-rule keys

`finding`-target rules match on these keys instead of YAML paths:

| key | Matches against |
|---|---|
| `cve_id` / `rule_id` | The SARIF rule id (usually the CVE or check id) |
| `package_name` | `properties."trivy:packageName"` of the finding |
| `severity` | The normalized label: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `location` | The reported file path |
| any key with `op: contains_tag` | Tags applied to the unit during Phase 2 |

## Actions

```yaml
action:
  risk_profile:               # for values / chart_metadata / manifest rules
    set_flag: "isPublic"      # legacy: sets the flag to true
    set_flags:                # v2: explicit values — flags can be CLEARED
      mountServiceToken: false
    score_multiplier: 1.3     # multiplies the base severity
    score_boost: 20           # adds raw points
  finding:                    # for finding rules
    suppress: true            # drop the finding entirely
    score_factor: 0.3         # multiply the finding's base score
  tags: ["public-facing"]     # attach tags to the unit (dedup'd)
```

Available flags: `isPublic`, `isPrivileged`, `hasDangerousCaps`,
`hasInternetEgress`, `mountServiceToken`.

Multipliers and boosts **accumulate** across rules and are applied in order:
multipliers first, then boosts. See [docs/scoring.md](docs/scoring.md) for the
exact math and worked examples.

**How Priority Works** — priority is derived from the final score:
`≥90 P0_BLEEDING`, `≥70 P1_CRITICAL`, `≥50 P2_HIGH`, `≥30 P3_MEDIUM`,
else `P4_LOW`.

Rules that only add `tags` are the glue between phases: a `chart_metadata`
rule can tag a unit `category:monitoring`, and a `finding` rule can later
react to that tag with `contains_tag`.

## Cookbook

**Escalate anything reachable from the internet AND privileged:**

```yaml
id: "custom-crown-jewel"
target: "values"
match:
  - key: "ingress.enabled"
    op: "eq"
    value: true
  - key: "securityContext.privileged"
    op: "eq"
    value: true
action:
  risk_profile:
    score_boost: 30
  tags: ["crown-jewel"]
```

**Detect exposure regardless of which mesh flavor a team used (OR logic):**

```yaml
id: "custom-any-mesh-exposure"
target: "values"
any:
  - key: "virtualService.enabled"
    op: "eq"
    value: true
  - key: "istio.virtualservice.enabled"
    op: "eq"
    value: true
  - key: "gateway.httproute.enabled"
    op: "eq"
    value: true
action:
  risk_profile:
    set_flag: "isPublic"
    score_multiplier: 1.3
```

**Catch privileged sidecars in raw manifests (wildcard):**

```yaml
id: "custom-privileged-anywhere"
target: "manifest"
match:
  - key: "spec.template.spec.containers.*.securityContext.privileged"
    op: "eq"
    value: true
action:
  risk_profile:
    set_flag: "isPrivileged"
    score_boost: 20
```

**Match cloud IAM annotations (escaped dots):**

```yaml
id: "custom-irsa"
target: "values"
match:
  - key: "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    op: "exists"
action:
  risk_profile:
    score_boost: 10
  tags: ["iam-bound"]
```

**Downgrade LOW/MEDIUM findings inside test code:**

```yaml
id: "custom-test-code-noise"
target: "finding"
match:
  - key: "severity"
    op: "in"
    value: ["LOW", "MEDIUM"]
  - key: "location"
    op: "contains"
    value: "test/"
action:
  finding:
    score_factor: 0.1
```

**Suppress a risk-accepted CVE on one package:**

```yaml
id: "custom-accepted-cve"
target: "finding"
match:
  - key: "cve_id"
    op: "eq"
    value: "CVE-2023-37920"
  - key: "package_name"
    op: "eq"
    value: "certifi"
action:
  finding:
    suppress: true
```

**Classify by team naming convention, then relax internal tools:**

```yaml
id: "custom-class-internal-tools"
target: "chart_metadata"
match:
  - key: "name"
    op: "regex"
    value: "^(tool|internal|ops)-"
action:
  tags: ["category:internal-tool"]
---
id: "custom-relax-internal-tools"
target: "finding"
match:
  - key: "tag"
    op: "contains_tag"
    value: "category:internal-tool"
action:
  finding:
    score_factor: 0.5
```

**Reward hardened service accounts (clearing a flag, v2):**

```yaml
id: "custom-sa-hardened"
target: "values"
match:
  - key: "serviceAccount.automount"
    op: "eq"
    value: false
action:
  risk_profile:
    set_flags:
      mountServiceToken: false
```

## Migration notes (v1 → v2)

Everything that worked in v1 keeps working unchanged. New in v2:

- `\.` escapes — **the shipped IAM rules silently never matched in v1**; they
  work now.
- `*` wildcards and numeric indices in key paths.
- `any:` OR blocks combined with the AND `match:` block.
- `in`, `gte`, `lte`, `not_exists` operators; `severity`/`location` finding keys.
- `set_flags` with explicit booleans (v1 `set_flag` could only set `true`).
- `manifest` target with `kind:` filter (raw K8s + `ComposeService`).
- Validation warnings for unknown targets/ops/flags, missing `id`, empty match.
