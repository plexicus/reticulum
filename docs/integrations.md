# Integrations

Reticulum consumes standard SARIF, so any scanner that emits SARIF works.
These are the tested paths.

## Trivy (containers, dependencies, IaC)

```bash
# Filesystem scan of a repo
trivy fs --format sarif --output trivy.sarif .

# Analyze with Reticulum
reticulum -p . -s trivy.sarif -o report.json --graph exposure.mmd
```

Reticulum reads Trivy's `security-severity`, `trivy:packageName` (used by
`package_name` finding rules) and `trivy:fixedVersion` (drives the
actionability modifier).

## Semgrep (SAST)

```bash
semgrep scan --sarif --output semgrep.sarif .
reticulum -p . -s semgrep.sarif -o report.json
```

Semgrep reports CWD-relative paths; Reticulum's path resolution handles both
repo-relative and CWD-relative layouts, plus absolute paths from containerized
runs.

## GitHub Actions

```yaml
name: contextual-security
on: [pull_request]

jobs:
  reticulum:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Scan with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          format: sarif
          output: trivy.sarif

      - name: Build Reticulum
        run: |
          docker build -t reticulum https://github.com/plexicus/reticulum.git

      - name: Prioritize
        run: |
          docker run --rm -v "$PWD:/data" reticulum \
            -p /data -s /data/trivy.sarif \
            -o /data/report.json \
            --sarif-output /data/enriched.sarif \
            --graph /data/exposure.mmd

      # Upload the ENRICHED sarif: code-scanning alerts now carry
      # properties.reticulum.{score, priority, serviceId, exposure}
      - name: Upload to code scanning
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: enriched.sarif

      - name: Exposure graph in the job summary
        run: |
          echo '```mermaid' >> "$GITHUB_STEP_SUMMARY"
          cat exposure.mmd  >> "$GITHUB_STEP_SUMMARY"
          echo '```'        >> "$GITHUB_STEP_SUMMARY"
```

## Gating on priority

`report.json` is designed for automation. Example: fail the build on any
P0/P1 finding:

```bash
reticulum -p . -s trivy.sarif -o report.json
jq -e '[.services[].findings[]? | select(.priority | test("P0|P1"))] | length == 0' \
  report.json || { echo "P0/P1 findings present"; exit 1; }
```

## Enriched SARIF

`--sarif-output` writes the input SARIF back with one added property per
matched result:

```json
"properties": {
  "reticulum": {
    "score": 100,
    "priority": "P0_BLEEDING",
    "serviceId": "admin-api",
    "exposure": "Public"
  }
}
```

Downstream SARIF consumers (GitHub code scanning, DefectDojo, SonarQube
importers) keep working — they just gain context.

## Exposure graph

`--graph exposure.mmd` writes a Mermaid flowchart. Render it anywhere Mermaid
runs: GitHub READMEs and PR comments, GitLab, Obsidian, `mmdc` for SVG/PNG:

```bash
npx -y @mermaid-js/mermaid-cli -i exposure.mmd -o exposure.svg
```

## Suppressions as code

Risk acceptance lives in `rules/custom/` — reviewed, versioned, diffable:

```yaml
id: "accept-CVE-2023-4863-on-thumbnailer"
target: "finding"
match:
  - key: "cve_id"
    op: "eq"
    value: "CVE-2023-4863"
  - key: "package_name"
    op: "eq"
    value: "libwebp"
action:
  finding:
    suppress: true
```
