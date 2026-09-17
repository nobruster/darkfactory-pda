---
id: T-20260827-type-05-lakehouse
title: Type 05 dlt → Gold + golden-match (DF-SOURCE-005 source defect; HALF_UP; HALF_EVEN is MODERN_DEFECT)
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: docs/seams.md
depends_on:
  - T-20260827-type-05-ingest
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/validation/attach_type05.py
  - modern/scripts/run_type05_gold.py
source_note: "ADR 0007–0011; ADR 0003 records HALF_EVEN default; Type 05 contract HALF_UP; do not rewrite expected/"
created: 2026-08-27T12:00:00Z
tags: [type-05, dlt, gold, golden-match, half-up]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 05 ingest leaf authored"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: any
signed_off: false
signed_off_by: (none)
signed_off_at: (none)
accepted: false
accepted_by: (none)
accepted_at: (none)
evidence_refs: []
---

# Type 05 dlt → Gold + golden-match (DF-SOURCE-005 source defect; HALF_UP; HALF_EVEN is MODERN_DEFECT)

> **Why:** The pill is Type 05. Same referee. Do not net the two
> questions. Do not rewrite `expected/` so a `HALF_EVEN` plant goes green.

## Goal

Register Type 05 landing only, Bronze → Silver → Gold, attach
`golden_match.py`.

1. `DF-SOURCE-005` = `CONFIRMED_SOURCE_DEFECT` (declared assessed **0.99**,
   calculated **1.00**). No Gold. Keep 0.99.
2. `rounding-half-up` matches contract **`HALF_UP`**.
3. A plant that applies Python default **`HALF_EVEN`** is
   **`MODERN_DEFECT`**. Fix the plant, not `expected/`.

No Type 05 grain ADR. Frozen trees forbidden. No product execute while
`signed_off: false`.

## Behavior

- **B-1** — dlt registers landing. No semicolon CSV parse in dlt.
- **B-2** — `DF-SOURCE-005` classifies `CONFIRMED_SOURCE_DEFECT`.
- **B-3** — `rounding-half-up` is accepted only under `HALF_UP`.
- **B-4** — `HALF_EVEN` is `MODERN_DEFECT`. Never rewrite `contracts/`
  expected fixtures.
- **B-5** — Same referee, two questions, six codes, no tolerance.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/tasks/T-20260827-type-05-lakehouse.md"
REF="$ROOT/validation/golden-match/golden_match.py"
ATTACH="$ROOT/modern/validation/attach_type05.py"
FINDING="$ROOT/contracts/types/05-merchant-fee-assessment/main/expected-df-source-005-finding.yaml"
LAYOUT="$ROOT/contracts/types/05-merchant-fee-assessment/layout.yaml"
GRAIN="$ROOT/docs/adrs/0009-medallion-grains-and-keys.md"

eval_1() {
  grep -q 'dlt registers' "$SPEC" || return 1
  grep -q 'DF-SOURCE-005' "$SPEC" || return 1
  grep -q 'CONFIRMED_SOURCE_DEFECT' "$SPEC" || return 1
  grep -q 'HALF_UP' "$SPEC" || return 1
  grep -q 'HALF_EVEN' "$SPEC" || return 1
  grep -q 'MODERN_DEFECT' "$SPEC" || return 1
  grep -q 'rounding-half-up' "$SPEC" || return 1
  grep -q 'signed_off: false' "$SPEC" || return 1
  grep -q 'CONFIRMED_SOURCE_DEFECT' "$REF" || return 1
  grep -q 'MODERN_DEFECT' "$REF" || return 1
  grep -q 'rounding_mode: HALF_UP' "$LAYOUT" || return 1
  grep -q 'SOURCE_CONTROL_ASSESSED_FEE_MISMATCH' "$FINDING" || return 1
  grep -q 'A Type 02–05 grain' "$GRAIN" || return 1
  awk '
    BEGIN { sec="" }
    /^---$/ { n++; next }
    n==1 && $0 ~ /^(touches_paths|creates_paths):/ { sec=$1; next }
    n==1 && sec != "" && $0 ~ /^[^[:space:]-]/ { sec="" }
    n==1 && sec != "" && $0 ~ /^[[:space:]]*-[[:space:]]*(legacy|contracts|gen|infra)\// { bad=1 }
    END { exit bad ? 1 : 0 }
  ' "$SPEC" || return 1
}

eval_2() {
  if [[ ! -f "$ATTACH" ]]; then
    grep -q 'signed_off: false' "$SPEC" || return 1
    return 0
  fi
  grep -q 'golden_match' "$ATTACH" || return 1
  grep -q 'DF-SOURCE-005' "$ATTACH" || return 1
  grep -q 'HALF_UP' "$ATTACH" || return 1
  grep -q 'MODERN_DEFECT' "$ATTACH" || return 1
  ! grep -q 'tolerance' "$ATTACH" || return 1
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: DF-SOURCE-005 CONFIRMED_SOURCE_DEFECT; HALF_UP; HALF_EVEN is MODERN_DEFECT
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-3, B-4, B-5]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Attach covers DF-SOURCE-005 and HALF_UP; no tolerance when present
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-3, B-4]
    terminal: true
    expected_duration_sec: 5
```

## Exit Check

```bash
eval_1 && eval_2
```

## Anti-Patterns

- **Don't rewrite `expected/` to match `HALF_EVEN`.** Fix the plant.
- **Don't classify CONFIRMED_LEGACY_DEFECT tonight.** Friday.
- **Don't invent Type 05 Gold for the lie.**

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
