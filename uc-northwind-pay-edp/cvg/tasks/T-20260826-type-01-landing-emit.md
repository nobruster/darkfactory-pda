---
id: T-20260826-type-01-landing-emit
title: Emit Type 01 landing Parquet for valid-minimal; zero Parquet on the lie
status: ready
format_version: 3
profile: standard
effort: L
budget_iterations: 15
agent: claude
parent: docs/seams.md
depends_on:
  - T-20260825-type-01-landing-parser
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/ingestion/src/northwind_pay/types/01-card-settlement/model.py
  - modern/ingestion/src/northwind_pay/types/01-card-settlement/schema.py
  - modern/ingestion/src/northwind_pay/types/01-card-settlement/writer.py
  - modern/ingestion/src/northwind_pay/types/01-card-settlement/handler.py
  - modern/ingestion/src/northwind_pay/common/parquet.py
  - modern/ingestion/src/northwind_pay/emit.py
source_note: "docs/consensus-lakehouse.md signed 2026-08-26; ADR 0001, 0002, 0005; seams.md ingest emit leg"
created: 2026-08-26T18:00:00Z
tags: [type-01, landing, emit, parquet]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "docs/consensus-lakehouse.md records canonical lakehouse sign"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: claude
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:57:11Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:01Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:b3c732d700ab9c005762f1f2af2c6e0832be77698ee3a6474dd356eb6c27fbcb
accepted_tier: 2
accepted_attempt_id: a6be0ee5-8ae4-5832-a18a-dbec584ea971
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:b3c732d700ab9c005762f1f2af2c6e0832be77698ee3a6474dd356eb6c27fbcb
acceptance_record_digest: sha256:f2c9585bd75fee73e68e966b5b65ba7a0d53d5784ff6236d025d0108917e4757
---

# Emit Type 01 landing Parquet for valid-minimal; zero Parquet on the lie

> **Why:** Constructor consumes landing. If Parquet is missing, the first
> incident is emit, not a re-parse. The lie keeps **173.44** and writes
> nothing.

## Context

This leaf owns one artifact in the Type 01 steel thread. Legacy is the referee,
never the teacher: the modern side is built from `contracts/` alone. The eval
executes the artifact rather than asserting it exists.

## Goal

Finish the Type 01 five-file package (`schema` / `writer` / `handler`)
so `valid-minimal` publishes deterministic Parquet under
`modern/landing/` (net 173.45 shape) and `df-source-001` emits **zero**
Parquet. Do not write `legacy/`, `contracts/`, `gen/`, or `infra/`.

## Behavior

- **B-1** — GIVEN `valid-minimal` raw bytes WHEN emit runs THEN Parquet
  + readiness manifest land atomically under `modern/landing/`. Money
  is decimal128 scale 2. Columns match the sanitized CSV contract.
- **B-2** — GIVEN `df-source-001` (trailer 173.44 vs rows 173.45) WHEN
  emit runs THEN zero Parquet, stable finding
  `SOURCE_CONTROL_TOTAL_MISMATCH`. Keep 173.44.
- **B-3** — GIVEN malformed Type 01 WHEN emit runs THEN classified
  terminal, no invented Parquet.
- **B-4** — GIVEN this leaf WHEN any file is written THEN the path is
  not under `legacy/`, `contracts/`, `gen/`, or `infra/`. No
  `legacy/processor/PWNED.txt`. No SFTP `csv/outgoing`.

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
import json, pathlib
m = json.loads((pathlib.Path.cwd()/"modern/landing/B202607230000001/parquet-manifest.json").read_text())
assert m["computed_net_amount"] == "173.45", m
assert m["record_count"] == 2, m
print("eval_3 OK landing", m["parquet_sha256"][:12])
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
    description: Handler and writer exist; Decimal parquet; lakehouse sign present
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: valid-minimal publishes Parquet; df-source-001 zero Parquet keep 173.44
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-3]
    terminal: true
    expected_duration_sec: 30
  - id: eval_3
    description: Frozen trees and PWNED.txt are not in scope
    runnable: bash
    check_type: deterministic
    verifies: [B-4]
    terminal: true
    expected_duration_sec: 5

retry_policy:
  max_iterations: 15
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

## Anti-Patterns

- **Don't import Java.** Don't copy CSV into landing.
- **Don't repair 173.44.** Don't register raw.
- **Don't write frozen trees.**

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
