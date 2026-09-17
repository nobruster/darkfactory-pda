---
id: T-20260826-type-01-dlt-register
title: Register Type 01 landing Parquet through dlt (no re-parse)
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 10
agent: claude
parent: docs/seams.md
depends_on:
  - T-20260826-type-01-landing-emit
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/lakehouse/dlt/registration.py
source_note: "docs/consensus-lakehouse.md; ADR 0007, 0008"
created: 2026-08-26T18:00:00Z
tags: [type-01, dlt, register]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "landing Parquet exists for valid-minimal"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: claude
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:57:59Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:03Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:54a764a63e8ac440c6fdccb9dda68ab814f4077dbe3851f883273a4ef997ee6e
accepted_tier: 2
accepted_attempt_id: b531aa05-40fd-5932-a713-67a31a2b4fbf
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:54a764a63e8ac440c6fdccb9dda68ab814f4077dbe3851f883273a4ef997ee6e
acceptance_record_digest: sha256:c3228f378c34f58850a348ef40291e655c449648bb78456b565c2c3c20d4628f
---

# Register Type 01 landing Parquet through dlt (no re-parse)

> **Why:** Seam 2 starts at immutable landing. If dlt parses bytes or
> computes a net, the seam is wrong.

## Context

This leaf owns one artifact in the Type 01 steel thread. Legacy is the referee,
never the teacher: the modern side is built from `contracts/` alone. The eval
executes the artifact rather than asserting it exists.

## Goal

dlt registers published Type 01 Parquet into local DuckDB. It does not
re-parse `.dat`. It does not tokenize. It does not own money.

## Behavior

- **B-1** — GIVEN landing Parquet WHEN register runs THEN DuckDB holds
  `landing.card_settlement` and `landing.card_settlement_control`.
- **B-2** — GIVEN the dlt module WHEN inspected THEN it does not read
  raw `.dat`, does not HMAC, does not decode overpunch.
- **B-3** — GIVEN a refused batch with zero Parquet WHEN register runs
  THEN that batch is not invented as Gold-ready rows.

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
n = c.execute("select count(*) from landing.card_settlement").fetchone()[0]
assert n == 2, n
print("eval_3 OK landing rows", n)
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
    description: dlt module registers landing and does not parse raw
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Type 01 landing rows appear in local DuckDB after register
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-3]
    terminal: true
    expected_duration_sec: 60

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
- `validation/golden-match/golden_match.py`

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
