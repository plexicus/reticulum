# Resource Mapping Sources

Reticulum maps your repository through four discoverers. Each one produces
*services* (what findings attach to) and *config units* (what carries a risk
profile). The `source` field in every report tells you which discoverer
produced a unit: `helm`, `k8s` or `compose`.

## Helm charts (`source: helm`)

- **Detected by:** a `Chart.yaml` (case-insensitive) — the chart name comes
  from it, falling back to the directory name if it doesn't parse.
- **Analyzed via:** the rule engine over each candidate values file:
  `values.yaml`, `values-*.yaml`, `values.*.yml`, plus `prod.yaml`,
  `staging.yaml`, `dev.yaml` (sorted; `Chart.yaml`, `Chart.lock` and
  `.helm*` are excluded).
- **Exposure comes from:** `values`/`chart_metadata` rules — ingress flags,
  service types, mesh config, security contexts. Fully user-extensible.

## Raw Kubernetes manifests (`source: k8s`)

- **Detected by:** any YAML document carrying `apiVersion` + `kind` +
  `metadata.name`, outside Helm chart directories. Helm templates are skipped
  (both explicitly and because Go templating isn't valid YAML). Multi-document
  files are supported.
- **Units:** each workload — `Deployment`, `StatefulSet`, `DaemonSet`,
  `ReplicaSet`, `Job`, `CronJob`, `Pod`.
- **Exposure comes from graph tracing**, not string matching:

  1. The workload's pod-template labels are extracted.
  2. Every `Service` whose `spec.selector` is a non-empty subset of those
     labels is connected. `LoadBalancer` (×1.3) and `NodePort` (×1.1) mark
     the workload public.
  3. Every `Ingress` (v1 and legacy backends, including `defaultBackend`) and
     Gateway API `HTTPRoute` referencing a connected Service marks it public
     (×1.3).
  4. Every `NetworkPolicy` whose `podSelector` matches and whose egress
     reaches `0.0.0.0/0` (or is unrestricted) sets `hasInternetEgress`.

  Each connection is recorded as an **exposure path**:

  ```
  Ingress/web-ingress → Service/web-svc → Deployment/web-frontend
  Service/postgres-svc (LoadBalancer) → StatefulSet/postgres-db
  NetworkPolicy/batch-egress egress 0.0.0.0/0 ← Deployment/internal-batch
  ```

  Paths appear in the CLI output, in `riskProfile.exposurePaths` in the JSON
  report, and as edges in the `--graph` Mermaid output. This is the
  traceability core: not "this looks public" but *why* and *through what*.

- **Rules:** `manifest`-target rules run on the workload document **and**
  every connected Service/Ingress/HTTPRoute/NetworkPolicy document, so you
  can write YAML detections over raw manifests (see the shipped
  `rules/manifest/k8s-security.yaml`).

## docker-compose (`source: compose`)

- **Detected by:** `docker-compose.yml`, `docker-compose.yaml`,
  `compose.yml`, `compose.yaml` — each entry under `services:`.
- **Exposure comes from published ports**, with real-world semantics:
  - `"8080:80"` → public (binds all interfaces) — exposure path
    `Compose/web publishes 8080→80`
  - `"127.0.0.1:5432:5432"` / `host_ip: 127.0.0.1` → **not** public
  - `"80"` (container-only) → not public
  - long syntax (`published/target/host_ip`) supported
- **Security context:** `privileged: true` (+20), `network_mode: host`
  (×1.5), dangerous `cap_add` entries like `SYS_ADMIN` (+15).
- **Rules:** each service is also evaluated by `manifest` rules as a
  synthetic document of `kind: ComposeService`.
- **Attribution:** services with a `build:` context attach findings from that
  context directory. Image-only services (e.g. `image: postgres:14`)
  deliberately do **not** claim repository files.

## Dockerfiles (services)

Every `Dockerfile`, `Dockerfile.<name>` or `<name>.Dockerfile` (ignoring
`.dockerignore`) defines a service — the entity findings attach to and the
unit of reporting. Naming:

| File | Service id |
|---|---|
| `apps/web/Dockerfile` | `web` (directory name) |
| `Dockerfile.worker` | `worker` |
| `auth.Dockerfile` | `auth` |

## Linking

Services link to the best-scoring config unit:

| Signal | Points |
|---|---|
| Service id equals unit name (case-insensitive) | +100 |
| Unit path inside service directory, or vice versa (component-wise) | +80 |
| Unit's `values.yaml` mentions the service id | +60 |

Units discovered by the K8s/compose sources that created their own service
entries arrive pre-linked.

## Roadmap

Sources under consideration: Kustomize overlays, Terraform (cloud exposure:
security groups, load balancers), CloudFormation, Nomad job specs. The
`manifest` rule target and `SourceKind` are designed to absorb new sources
without breaking existing reports.
