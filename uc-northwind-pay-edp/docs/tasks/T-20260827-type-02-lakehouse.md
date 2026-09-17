---
id: T-20260827-type-02-lakehouse
title: Type 02 dlt → Gold + golden-match (same referee; no new grain ADR)
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: docs/seams.md
depends_on:
  - T-20260827-type-02-ingest
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/validation/attach_type02.py
  - modern/scripts/run_type02_gold.py
source_note: "ADR 0007–0011; ADR 0009 is Type 01 grain only; attach golden_match.py"
created: 2026-08-27T12:00:00Z
tags: [type-02, dlt, gold, golden-match]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 02 ingest leaf authored; Type 01 lakehouse sign canonical"
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

# Type 02 dlt → Gold + golden-match (same referee; no new grain ADR)

> **Why:** Same DE lane as Type 01. dlt registers landing only. Replay
> rebuilds Gold. The referee is attached, not rewritten. ADR 0009 is
> not a Type 02 grain.

## Goal

Register Type 02 landing (no re-parse), Bronze → Silver → Gold, attach
`validation/golden-match/golden_match.py`. `valid-minimal` both
questions yes. `DF-SOURCE-002` = `CONFIRMED_SOURCE_DEFECT`, keep
**173.44**, no Gold. Do not invent a Type 02 grain. Do not write frozen
trees. Do not execute product code while `signed_off: false`.

## Behavior

- **B-1** — dlt registers `modern/landing/` Parquet only. No `.txt`
  parse, no tokenize, no net.
- **B-2** — Same referee, two questions never netted, six codes, no
  tolerance. `DF-SOURCE-002` classifies `CONFIRMED_SOURCE_DEFECT`.
- **B-3** — No new grain unless an ADR says so. ADR 0009 is Type 01
  only. Do not read Postgres to compute Gold.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/tasks/T-20260827-type-02-lakehouse.md"
REF="$ROOT/validation/golden-match/golden_match.py"
ATTACH="$ROOT/modern/validation/attach_type02.py"
GRAIN="$ROOT/docs/adrs/0009-medallion-grains-and-keys.md"

eval_1() {
  grep -q 'dlt registers' "$SPEC" || return 1
  grep -q 'CONFIRMED_SOURCE_DEFECT' "$SPEC" || return 1
  grep -q '173.44' "$SPEC" || return 1
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
    description: Same referee; DF-SOURCE-002 CONFIRMED_SOURCE_DEFECT; no Type 02 grain ADR
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-3]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Attach exists only after execute; uses referee with no tolerance
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

## Anti-Patterns

- **Don't re-parse.** Don't rewrite `golden_match.py`. Don't net the two questions.
- **Don't invent Type 02 dimensions.** “dbt ran” is a log, not an eval.

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
