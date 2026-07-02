# Audit Report — D → Rust Migration

This document lists every defect found in the original D (dlang) implementation
during the migration audit, and how the Rust port addresses each one.
Behavioral parity with the D binary was verified against `tests/monorepo-01..07`
(scan-only mode) and a synthetic Trivy SARIF fixture
(`tests/fixtures/synthetic-trivy.sarif`, full mode incl. enriched SARIF output).
The only intentional output differences are the ones documented below.

## Bugs fixed

### 1. NaN score corruption from uninitialized rule fields (critical)
`rules/model.d` declared `float scoreMultiplier` / `float scoreFactor`, whose
default value in D is `float.nan`.

- `engine.d:292` guarded with `scoreFactor != 0.0` — true for NaN — so any
  `finding`-target rule **without** an explicit `score_factor` (e.g. a
  suppress-only or tag-only rule) multiplied the finding score by NaN, and
  `cast(int)(NaN)` is undefined behavior.
- `engine.d:463` guarded with `scoreMultiplier != 1.0` — also true for NaN — so
  a `values`/`chart_metadata` rule whose action had no `risk_profile` block (or
  one without `score_multiplier`) pushed NaN into the multiplier list,
  corrupting every score for that chart.

**Fix:** `Option<f32>` in `src/rules/mod.rs`; absent means "no effect".
Regression test: `finding_rule_without_score_factor_leaves_score_intact`.

### 2. Per-finding state leaking into the shared chart profile (high)
`ingestor.d:271` executed `risk.hasFix = fixable` on the **chart's shared**
`RiskProfile` before scoring each finding. Consequences:

- The fixability of whichever finding was processed *last* stuck permanently to
  the chart, so the `baseRiskScore` in the JSON report depended on SARIF result
  order (observed: payment-go reported 15 instead of 25 because its last
  finding had no fix).

**Fix:** `calculate_score_with_fix(base, has_fix)` takes fixability as an
argument; the profile is never mutated during ingestion
(`src/ingestor.rs`, test `no_fix_penalty_does_not_mutate_profile`).

### 3. Crash on SARIF results without `ruleId` (high)
`ingestor.d:92` (`extractSeverity`) read `result["ruleId"].str` unconditionally
while the caller treated `ruleId` as optional. A SARIF result lacking `ruleId`
(valid per spec — `rule.id` can live elsewhere) threw and aborted the run.
Same pattern for `r["id"]` on rule entries.

**Fix:** all JSON access is `Option`-chained (`src/ingestor.rs`,
test `severity_missing_rule_id_does_not_panic`).

### 4. `security-severity` type handling (medium)
`extractSeverity` only accepted string and float JSON types for
`properties.security-severity`. GitHub/Trivy may emit it as an integer (e.g.
`8`), which silently fell through to a wrong severity. An unparseable string
crashed the whole run (`to!float` throw).

**Fix:** string, float and integer accepted; unparseable strings fall through
to the next strategy instead of crashing
(test `severity_from_security_severity_property`).

### 5. Rules only loadable from the current working directory (medium)
`app.d:223` looked for `rules/exposure` etc. relative to CWD only. Running the
binary from any other directory silently loaded **zero rules**, producing
neutral scores with no warning.

**Fix:** `--rules <dir>` flag; fallback order CWD → executable directory; an
explicit warning is printed when no rules directory is found (`src/main.rs`).

### 6. String-prefix path matching false positives (medium)
`ingestor.d` used string `startsWith` to decide whether a finding path is
inside a service directory, so `/repo/app-extra/file.py` matched service
`/repo/app`. Same issue in the resolution strategy checks.

**Fix:** component-wise `Path::starts_with`
(test `path_starts_with_is_component_wise`).

### 7. `RiskProfile.reset()` did not clear `appliedRuleIds` (low)
`model.d:118` reset all flags and score lists but left `appliedRuleIds`
populated. Any chart analyzed twice would accumulate duplicate rule IDs in the
report.

**Fix:** reset restores the full default state
(test `reset_clears_applied_rules`).

### 8. Shared charts analyzed once per service (low)
`app.d:242` iterated services and analyzed `s.chart` without deduplication;
two services linked to the same chart re-ran the full analysis per service.
Because of bug 7 (`reset()` not clearing `appliedRuleIds`), each re-run
appended a duplicate set of rule IDs to the report, besides duplicating log
output and work.

**Fix:** charts are deduplicated before exposure analysis (`src/main.rs`).

### 9. `"HelmVinked"` typo in JSON report (low, output change)
`model.d:167` emitted `"type": "HelmVinked"` for chart-linked services.
Nothing in the repo consumed the typo (checked `analyze_results.py`).

**Fix:** emits `"HelmLinked"`. **This is an intentional output change** —
external consumers matching on the typo must update.

### 10. Swallowed errors via `catch (Throwable)` (code quality)
The D code caught `Throwable` (including assertion failures / fatal errors) in
9 places, often with an empty body, hiding real failures (e.g. values-file
enumeration errors in `analyzer.d:53`).

**Fix:** Rust `Result` handling everywhere; genuinely ignorable conditions are
explicit (`filter_map(Result::ok)`), parse failures are reported to the user.

## Intentional behavior differences

- **`type: "HelmLinked"`** instead of `"HelmVinked"` (bug 9).
- **`baseRiskScore` no longer depends on SARIF result order** (bug 2).
- **Deterministic rule ordering:** rule files load in sorted path order, so
  `appliedRuleIds` has a stable order; D depended on filesystem enumeration
  order. Same set, possibly different order (observed in monorepo-07).
- **Duplicate `mountServiceToken` flag semantics kept:** rules can only set
  flags to `true` (as in D). The `harden-sa-automount` rule relies on the
  default already being `true`; changing this is out of scope.

## Parity verification

| Check | Result |
|---|---|
| `--scan-only` JSON, monorepo-01..07 | identical flags/scores/rule IDs (order note above) |
| Full run + synthetic SARIF, monorepo-06 | identical `baseScore`, `reticulumScore`, `priority`, `severity` per finding |
| Enriched SARIF `properties.reticulum` | identical for all 4 results |
| `cargo test` | 29/29 pass |
| `cargo clippy --all-targets -- -D warnings` | clean |
