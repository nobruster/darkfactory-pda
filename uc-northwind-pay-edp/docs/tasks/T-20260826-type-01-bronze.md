---
id: T-20260826-type-01-bronze
title: Type 01 Bronze is source-aligned to landing
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 10
agent: any
parent: docs/seams.md
depends_on:
  - T-20260826-type-01-dlt-register
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/dbt/models/bronze/bronze_card_settlement.sql
  - modern/dbt/models/bronze/bronze_card_settlement_control.sql
source_note: "ADR 0009 Bronze grain; ADR 0010 no retokenize"
created: 2026-08-26T18:00:00Z
tags: [type-01, bronze, dbt]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "dlt has registered Type 01 landing"
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

# Type 01 Bronze is source-aligned to landing

## Goal

Bronze types landing. Grain is `batch_id` + `source_record_number`.
No re-parse. No PAN/CPF transform.

## Behavior

- **B-1** — Grain is one movement per (`batch_id`, `source_record_number`).
- **B-2** — `amount_brl` is decimal(18,2). `card_token` matches `tok_` + 24 hex.
- **B-3** — SQL does not read `postgres`, `legacy.`, or `.dat`.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
B="$ROOT/modern/dbt/models/bronze/bronze_card_settlement.sql"
C="$ROOT/modern/dbt/models/bronze/bronze_card_settlement_control.sql"

eval_1() {
  test -f "$B" && test -f "$C" || return 1
  grep -q 'source_record_number' "$B" || return 1
  grep -q 'decimal(18, 2)' "$B" || return 1
  ! grep -qiE 'postgres|legacy\\.|tokenize|overpunch|\\.dat' "$B" "$C" || return 1
}

eval_2() {
  test -f "$ROOT/modern/dbt/tests/assert_type01_no_clear_pan_in_bronze.sql" || return 1
  test -f "$ROOT/modern/dbt/tests/assert_type01_bronze_grain.sql" || return 1
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: Bronze SQL is source-aligned and does not re-parse
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-3]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Bronze grain and privacy tests exist
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
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
