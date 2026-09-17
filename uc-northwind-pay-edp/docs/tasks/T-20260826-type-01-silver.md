---
id: T-20260826-type-01-silver
title: Type 01 Silver conforms without changing money
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 10
agent: any
parent: docs/seams.md
depends_on:
  - T-20260826-type-01-bronze
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/dbt/models/silver/silver_card_settlement.sql
source_note: "ADR 0009 Silver grain; ADR 0010 conservation"
created: 2026-08-26T18:00:00Z
tags: [type-01, silver, dbt]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 01 Bronze model exists"
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

# Type 01 Silver conforms without changing money

## Goal

Silver is the same grain as Bronze. It adds movement direction. It
does not retotal. It does not retokenize.

## Behavior

- **B-1** — Grain remains `batch_id` + `source_record_number`.
- **B-2** — `P` → `PURCHASE`, `R` → `REFUND`. `amount_brl` unchanged.
- **B-3** — A conservation test fails if Silver changes a cent.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
S="$ROOT/modern/dbt/models/silver/silver_card_settlement.sql"

eval_1() {
  test -f "$S" || return 1
  grep -q 'PURCHASE' "$S" || return 1
  grep -q 'REFUND' "$S" || return 1
  grep -q 'amount_brl' "$S" || return 1
  ! grep -qiE 'postgres|tokenize|overpunch' "$S" || return 1
}

eval_2() {
  test -f "$ROOT/modern/dbt/tests/assert_type01_silver_preserves_bronze_totals.sql" || return 1
  grep -q 'conserves_totals' "$ROOT/modern/dbt/tests/assert_type01_silver_preserves_bronze_totals.sql" || return 1
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: Silver SQL conforms direction and keeps amount_brl
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Conservation test exists
    runnable: bash
    check_type: deterministic
    verifies: [B-3]
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
