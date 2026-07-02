# Scoring — The Math

Reticulum turns a scanner's flat severity into a **contextual risk score**.
This page documents the exact algorithm, so every number in a report can be
reproduced by hand.

## 1. Base severity (0–100)

Each SARIF finding gets a base severity on the CVSS-like 0–10 scale,
resolved in this order:

1. `properties.security-severity` (string, float or integer; clamped to 0–10)
2. The rule's `defaultConfiguration.level` via the level map below
3. The result's `level` via the same map
4. Fallback: `5.0`

| level | severity |
|---|---|
| `critical`, `crit`, `blocker` | 10.0 |
| `high`, `error`, `severe` | 7.5 |
| `medium`, `moderate`, `warning`, `major` | 5.0 |
| `low`, `minor`, `info` | 2.5 |

`base_score = severity × 10` → 0–100.

## 2. Finding rules

`finding`-target rules run first and may:

- **suppress** the finding (it disappears from every output), or
- multiply the base score by a **score_factor** (e.g. `0.3` for monitoring
  tools).

## 3. Contextual transformation

The owning unit's RiskProfile — built in Phase 2 by exposure analysis — then
transforms the (possibly adjusted) base score:

```text
score = base_score
score = score × m₁ × m₂ × …        # all multipliers, in rule order
score = score + b₁ + b₂ + …        # all boosts
score = score − 10                  # only if no fix is available
final = clamp(score, 0, 100)
```

Notes:

- **Multipliers** come from exposure rules (`1.3` ingress, `1.1` NodePort,
  `1.5` hostNetwork, `0.5` ClusterIP-only, `0.1` monitoring…). They compound.
- **Boosts** come from threat context (`+20` privileged, `+15` dangerous
  capabilities, `+10` IAM binding, `+20` auth service…).
- **Fixability**: findings with no available patch get −10 — they are less
  *actionable*, not less real. Fixability is evaluated per finding and never
  mutates the shared profile.

## 4. Priority

| Priority | Score | Meaning | Action |
|---|---|---|---|
| **P0_BLEEDING** | 90–100 | Critical public exposure | Fix immediately |
| **P1_CRITICAL** | 70–89 | High risk, potential breach | Fix within 24h |
| **P2_HIGH** | 50–69 | Moderate risk | Fix next sprint |
| **P3_MEDIUM** | 30–49 | Internal / mitigated | Backlog |
| **P4_LOW** | 0–29 | Informational | Monitor |

## Worked examples

All three examples share one CVE: **CVE-2023-37920, severity 9.8 → base 98**.

### a) Public, privileged admin API

Rules fired: ingress (×1.3), LoadBalancer (×1.3), privileged (+20),
automount (+5). Fix available.

```text
98 × 1.3 × 1.3 = 165.62
165.62 + 20 + 5 = 190.62
clamp → 100                        ⇒ P0_BLEEDING
```

### b) Internal worker (ClusterIP only)

Rules fired: internal scoring (×0.5). Fix available.

```text
98 × 0.5 = 49                      ⇒ P3_MEDIUM
```

Same CVE, 51-point difference — that's the point of context.

### c) Internal service, no fix available

A 6.5 finding (base 65) on a ClusterIP service, no patched version:

```text
65 × 0.5 = 32.5
32.5 − 10 = 22.5 → 22              ⇒ P4_LOW
```

### `baseRiskScore` in reports

Each unit's `riskProfile.baseRiskScore` answers "what would a hypothetical
severity-50 finding score here?" — i.e. the algorithm above applied to 50.
It makes profiles comparable at a glance without any findings.
