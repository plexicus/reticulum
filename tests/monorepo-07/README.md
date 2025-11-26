# Monorepo 07: Rule Validation Sandbox

This monorepo is a minimal environment designed for **systematic testing and validation** of Reticulum's rule engine.

Unlike other monorepos that simulate real-world scenarios, this repository is intended to be modified to trigger specific rules one by one or in combination to verify their behavior.

## Structure

- **Service:** `auth-api` (Generic Helm chart)
- **Chart:** `charts/test-app`
- **Values:** `charts/test-app/values.yaml`

## Usage for Testing

To test a specific rule, modify `charts/test-app/values.yaml` to match the rule's criteria.

### Example: Testing `exposure-ingress-enabled`

1.  **Modify `values.yaml`:**
    ```yaml
    ingress:
      enabled: true  # <--- Triggers the rule
      hosts:
        - host: api.example.com
    ```

2.  **Run Reticulum:**
    ```bash
    ../../run_tools.sh .
    ../../reticulum -p . -s trivy.sarif
    ```

3.  **Verify Output:**
    Confirm that the `exposure-ingress-enabled` rule appears in the "Rules Applied" list and that the score is boosted accordingly.

## Validated Rules

This repository has been used to validate:
- `scoring-internal` (Default behavior)
- `class-auth` (Service name matching)
- `exposure-ingress-enabled` (Ingress detection)
- `exposure-service-lb` (LoadBalancer detection)
- `security-privileged` (Privileged container detection)
- `harden-sa-automount` (ServiceAccount token mounting)
