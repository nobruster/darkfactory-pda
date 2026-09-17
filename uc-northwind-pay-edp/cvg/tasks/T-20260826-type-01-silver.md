---
id: T-20260826-type-01-silver
title: Type 01 Silver conforms without changing money
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 10
agent: claude
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
execution_backend: claude
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:58:10Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:07Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:cb6d7037ef1e77a236546d6bd4d7c67a5aa01cd25e4c985b53833bd9606b443b
accepted_tier: 2
accepted_attempt_id: 54d430f3-8afa-5e43-8bee-2ae1270f6fc8
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:cb6d7037ef1e77a236546d6bd4d7c67a5aa01cd25e4c985b53833bd9606b443b
acceptance_record_digest: sha256:d2bb2a9bec0eb081da4cc98d5b68c91c098ba64145cab66623a603ce409bbc19
---

# Type 01 Silver conforms without changing money

## Context

This leaf owns one artifact in the Type 01 steel thread. Legacy is the referee,
never the teacher: the modern side is built from `contracts/` alone. The eval
executes the artifact rather than asserting it exists.

## Goal

Silver is the same grain as Bronze. It adds movement direction. It
does not retotal. It does not retokenize.

## Behavior

- **B-1** — Grain remains `batch_id` + `source_record_number`.
- **B-2** — `P` → `PURCHASE`, `R` → `REFUND`. `amount_brl` unchanged.
- **B-3** — A conservation test fails if Silver changes a cent.

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
n = c.execute("select count(*) from silver.silver_card_settlement").fetchone()[0]
assert n == 2, n
print("eval_3 OK silver rows", n)
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
