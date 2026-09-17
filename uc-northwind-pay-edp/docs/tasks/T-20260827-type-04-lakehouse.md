---
id: T-20260827-type-04-lakehouse
title: Type 04 dlt → Gold + golden-match (same referee; no new grain ADR)
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: docs/seams.md
depends_on:
  - T-20260827-type-04-ingest
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/validation/attach_type04.py
  - modern/scripts/run_type04_gold.py
source_note: "ADR 0007–0011; ADR 0009 is Type 01 grain only"
created: 2026-08-27T12:00:00Z
tags: [type-04, dlt, gold, golden-match]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 04 ingest leaf authored"
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

# Type 04 dlt → Gold + golden-match (same referee; no new grain ADR)

## Goal

Register Type 04 landing only, Bronze → Silver → Gold, attach
`golden_match.py`. `DF-SOURCE-004` = `CONFIRMED_SOURCE_DEFECT`, keep
**999.99**, no Gold. No Type 04 grain ADR. Frozen trees forbidden.

## Behavior

- **B-1** — dlt registers landing. No TED `.dat` parse.
- **B-2** — Same referee. `DF-SOURCE-004` is `CONFIRMED_SOURCE_DEFECT`.
- **B-3** — ADR 0009 is not a Type 04 grain.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/tasks/T-20260827-type-04-lakehouse.md"
REF="$ROOT/validation/golden-match/golden_match.py"
ATTACH="$ROOT/modern/validation/attach_type04.py"
GRAIN="$ROOT/docs/adrs/0009-medallion-grains-and-keys.md"

eval_1() {
  grep -q 'dlt registers' "$SPEC" || return 1
  grep -q 'CONFIRMED_SOURCE_DEFECT' "$SPEC" || return 1
  grep -q '999.99' "$SPEC" || return 1
  grep -q 'signed_off: false' "$SPEC" || return 1
  grep -q 'CONFIRMED_SOURCE_DEFECT' "$REF" || return 1
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
  ! grep -q 'tolerance' "$ATTACH" || return 1
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: Same referee; DF-SOURCE-004 CONFIRMED_SOURCE_DEFECT; no Type 04 grain ADR
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-3]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Attach uses referee with no tolerance when present
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: true
    expected_duration_sec: 5
```

## Exit Check

```bash
eval_1 && eval_2
```

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
