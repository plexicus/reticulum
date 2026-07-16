# monorepo-10 — env selector + path allowlist/denylist (H77)

Exercises the `--env` precedence selector and the `--include`/`--exclude`
path allowlist added for H77.

- `charts/internal-api` has divergent per-environment values: the base
  `values.yaml` keeps ingress disabled, `values-dev.yaml` turns it on,
  `values-prod.yaml` keeps it off. With no `--env` flag, reticulum unions
  every overlay (today's default, back-compat) so `internal-api` is
  reported public. With `--env prod`, only the base + prod overlay are
  analyzed, so `internal-api` is reported internal.
- `examples/decoy-workload.yaml` is a privileged raw K8s Deployment that
  lives outside the real deployment topology. Without a filter it is
  discovered like any other manifest; with `--exclude examples/**` it is
  skipped entirely and never contributes a service to the report.
