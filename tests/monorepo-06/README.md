# Monorepo 06: Contextual Prioritization Demo

This monorepo demonstrates Reticulum's core value proposition: **Contextual Prioritization**.

It contains multiple services with varying levels of exposure and security configurations. The goal is to show that a vulnerability in a public-facing, privileged service is prioritized much higher than the same (or worse) vulnerability in a locked-down internal service.

## Architecture

| Service | Type | Exposure | Security Context | Risk Profile |
|---------|------|----------|------------------|--------------|
| **admin-api** | Python/Flask | **Public** (Ingress + LB) | **Privileged**, SA Automount | 🔴 **CRITICAL** |
| **internal-worker** | Python/Celery | Internal (ClusterIP) | Non-root, No Caps | 🟢 **LOW** |
| **payment-go** | Go | Internal (ClusterIP) | Non-root, No Caps | 🟢 **LOW** |
| **postgres-db** | PostgreSQL | Internal (ClusterIP) | Standard | 🟡 **MEDIUM** |

## Expected Behavior

### 1. admin-api (Escalation)
- **Input:** Medium severity vulnerabilities (e.g., CVE-2025-50181).
- **Reticulum Action:** Escalates to **P0_BLEEDING** or **P1_CRITICAL**.
- **Reason:** Public exposure + Privileged container means any compromise could be catastrophic.

### 2. internal-worker (De-prioritization)
- **Input:** High severity vulnerabilities (e.g., Command Injection).
- **Reticulum Action:** De-prioritizes to **P3_MEDIUM** or **P4_LOW**.
- **Reason:** Service is internal-only and runs as non-root. The blast radius is contained.

### 3. payment-go (De-prioritization)
- **Input:** SQL Injection vulnerability.
- **Reticulum Action:** De-prioritizes to **P4_LOW**.
- **Reason:** Internal service context reduces the immediate exploitability from external attackers.

## Running the Demo

1. **Generate Data:**
   ```bash
   ../../run_tools.sh .
   ```

2. **Run Reticulum:**
   ```bash
   ../../reticulum -p . -s trivy.sarif
   ```

3. **Observe Results:**
   Check the output to see `admin-api` with a high Reticulum score (e.g., 100) and `internal-worker` with a significantly lower score (e.g., 37), despite having potentially more severe raw vulnerabilities.
