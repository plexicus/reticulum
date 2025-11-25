# Reticulum Rule Engine Documentation

## Overview
The Reticulum Rule Engine allows DevSecOps teams to define custom prioritization and suppression logic using YAML rules. Rules can match against Helm chart metadata, values, or vulnerability findings.

## Rule Targets

### 1. `chart_metadata`
Matches against Chart.yaml properties (name, path).

**Use Cases:**
- Classify services by name patterns (auth, db, monitoring)
- Boost priority for critical services

**Available Match Keys:**
- `name`: Chart name
- `path`: Chart directory path

**Example:**
```yaml
target: "chart_metadata"
match:
  - key: "name"
    op: "regex"
    value: ".*(auth|keycloak).*"
```

### 2. `values`
Matches against values.yaml configuration.

**Use Cases:**
- Detect exposure mechanisms (Ingress, Istio)
- Detect security misconfigurations (privileged, RBAC)
- Identify technology stack (database type, framework)

**Available Match Keys:**
- Any dot-notation path in values.yaml (e.g., `ingress.enabled`, `database.type`)

**Example:**
```yaml
target: "values"
match:
  - key: "database.type"
    op: "eq"
    value: "postgres"
```

### 3. `finding`
Matches against vulnerability findings from SARIF.

**Use Cases:**
- Suppress vulnerabilities for unused dependencies
- Reduce severity based on service context

**Available Match Keys:**
- `package_name`: Package name from Trivy (e.g., `mysql-connector`)
- `cve_id`: CVE or rule ID (e.g., `CVE-2023-1234`)
- `tag`: Check if Chart has a specific tag (use `op: contains_tag`)

**Example:**
```yaml
target: "finding"
match:
  - key: "package_name"
    op: "contains"
    value: "mysql"
  - key: "tag"
    op: "contains_tag"
    value: "tech:postgres"
```

## Match Operators

- `eq`: Exact match
- `neq`: Not equal
- `contains`: String contains
- `regex`: Regular expression match
- `exists`: Key exists in YAML
- `gt`: Greater than (numbers)
- `lt`: Less than (numbers)
- `contains_tag`: Check if Chart has a tag (only for `finding` target)

## Actions

### Risk Profile Actions
```yaml
action:
  risk_profile:
    set_flag: "isPublic"        # Set boolean flag
    score_multiplier: 1.3       # Multiply score
    score_boost: 20             # Add points
```

**How Priority Works:**
Priority is automatically calculated from the final score:
- Score ≥ 90 → P0_BLEEDING
- Score ≥ 70 → P1_CRITICAL
- Score ≥ 50 → P2_HIGH
- Score ≥ 30 → P3_MEDIUM
- Score < 30 → P4_LOW

Use `score_boost` and `score_multiplier` to influence priority.

### Finding Actions
```yaml
action:
  finding:
    suppress: true              # Completely suppress finding
    score_factor: 0.1           # Reduce score to 10%
```

### Tagging
```yaml
action:
  tags: ["category:auth", "tech:postgres"]
```

Tags are applied to Charts and can be used by `finding` rules via `contains_tag`.

## Rule Evaluation Flow

1. **Chart Analysis Phase**
   - `chart_metadata` rules evaluate against Chart.yaml
   - `values` rules evaluate against values.yaml
   - Tags are applied to Chart
   - Risk profile flags and score modifiers are accumulated

2. **Finding Analysis Phase** (during SARIF processing)
   - For each vulnerability finding:
     - `finding` rules evaluate
     - If `suppress: true`, finding is discarded
     - If `score_factor` is set, base score is modified
     - Modified finding is scored using Chart's risk profile

## Valid Use Cases & Examples

### 1. Service Classification
```yaml
id: "class-auth"
target: "chart_metadata"
match:
  - key: "name"
    op: "regex"
    value: ".*(auth|keycloak).*"
action:
  risk_profile:
    score_boost: 20
  tags: ["category:auth"]
```

### 2. Exposure Detection
```yaml
id: "exposure-ingress"
target: "values"
match:
  - key: "ingress.enabled"
    op: "eq"
    value: true
action:
  risk_profile:
    set_flag: "isPublic"
    score_multiplier: 1.3
```

### 3. Internal Service Scoring (Default)
```yaml
id: "scoring-internal"
target: "values"
match:
  - key: "service.type"
    op: "eq"
    value: "ClusterIP"
action:
  risk_profile:
    score_multiplier: 0.5  # Reduce score by 50% for internal services
```

### 4. Context-Based Severity Reduction
```yaml
id: "reduce-monitoring-severity"
target: "finding"
match:
  - key: "tag"
    op: "contains_tag"
    value: "category:monitoring"
action:
  finding:
    score_factor: 0.3  # Reduce to 30% for monitoring tools
```

## Important Notes

### ServiceAccount Automount
The `harden-sa-automount` rule only matches when `serviceAccount.automount` is **explicitly set to true** in `values.yaml`. It does not match if the field is missing, even though Kubernetes defaults to true. This is by design to detect explicit misconfigurations.

### Code-Level Dependencies
Reticulum analyzes `values.yaml` and `Chart.yaml`, not application source code. Rules relying on deep code inspection (e.g., "is this library actually used?") are not supported directly, but can be approximated using tags and service classification.

## Rule Directory Structure

```
rules/
├── exposure/          # Public exposure detection
│   ├── ingress.yaml
│   ├── istio.yaml
│   ├── istio-nested.yaml
│   ├── gateway-api.yaml
│   ├── ambassador.yaml
│   └── loadbalancer.yaml
├── security/          # Security misconfigurations
│   ├── privileged.yaml
│   ├── rbac.yaml
│   └── service-account.yaml
├── scoring/           # Score modifiers and classification
│   ├── auth-services.yaml
│   ├── databases.yaml
│   ├── monitoring.yaml
│   ├── monitoring-findings.yaml
│   └── internal.yaml
└── custom/            # User-defined rules (override defaults)
```

**Loading Order:** exposure → security → scoring → custom

Rules in `custom/` are loaded last and can override default behavior.
