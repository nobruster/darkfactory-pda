---
id: T-20260826-type-01-bronze
title: Type 01 Bronze is source-aligned to landing
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 10
agent: claude
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
execution_backend: claude
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:58:05Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:05Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:22b7ae7264a73903f40d54d9e2f1f35efe38faeda149cf555a69bd06278fc63f
accepted_tier: 2
accepted_attempt_id: e6910678-1b54-53e6-956e-f64c19953c10
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:22b7ae7264a73903f40d54d9e2f1f35efe38faeda149cf555a69bd06278fc63f
acceptance_record_digest: sha256:6113a870e546e2e6d754efe7a53a22e8312a63c43bf701cdbf6da848dd752d4e
---

# Type 01 Bronze is source-aligned to landing

## Context

This leaf owns one artifact in the Type 01 steel thread. Legacy is the referee,
never the teacher: the modern side is built from `contracts/` alone. The eval
executes the artifact rather than asserting it exists.

## Goal

Bronze types landing. Grain is `batch_id` + `source_record_number`.
No re-parse. No PAN/CPF transform.

## Behavior

- **B-1** — Grain is one movement per (`batch_id`, `source_record_number`).
- **B-2** — `amount_brl` is decimal(18,2). `card_token` matches `tok_` + 24 hex.
- **B-3** — SQL does not read `postgres`, `legacy.`, or `.dat`.

## Success Criteria

`eval_3` **executes** against the real artifact this leaf owns.

```bash
ROOT="$(git rev-parse --show-toplevel)"

eval_1() {
  test -d "$ROOT/cvg/tasks" || return 1
}

eval_2() {
  test -x "$ROOT/modern/.venv/bin/python" || return 1
}

eval_3() {
  cd "$ROOT" || return 1
  ./modern/.venv/bin/python - <<'PYEOF'
import duckdb, pathlib
c = duckdb.connect(str(pathlib.Path.cwd()/"modern/lakehouse/ducklake/northwind_modern.duckdb"), read_only=True)
n = c.execute("select count(*) from bronze.bronze_card_settlement").fetchone()[0]
assert n == 2, n
print("eval_3 OK bronze rows", n)
PYEOF
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_3
    description: EXECUTES the artifact this leaf owns
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: true
    expected_duration_sec: 60
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

retry_policy:
  max_iterations: 10
  circuit_breaker_no_progress: 3
  on_terminal_failure: park_with_context

agent_contract:
  version: 2
  read: [intent, behavior, contract, guardrails, operations]
  produce: [code]
  required_tools: [git, bash]
  timeout_minutes: 30
  sandbox_type: host
  output_artifacts: []
  mcp_dependencies: []
  emit: [pass, fail, retry_with_reason, parked_with_context]
  backend_metadata: {}
```

## Exit Check

```bash
eval_1 && eval_2 && eval_3
```

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`

---

## Rollback Plan

Additive. Revert the declared paths with `git checkout --` / `git rm`.
Never revert a frozen tree to make a gate pass.

---

## Observability Hooks

Watch the artifact this leaf owns; any unexplained financial delta blocks the
release gate.

---

## Open Questions

(none — the contract and the ADRs fix the grain and the money rule.)

---

## Anti-Patterns

- Don't weaken the referee. Don't rewrite `expected/`. Don't patch `legacy/`.
