---
id: T-20260827-orchestrate-type-01
title: Dagster lineage on closed Type 01 — parsing does not move into the orchestrator
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 10
agent: claude
parent: docs/seams.md
depends_on:
  - T-20260826-type-01-golden-match
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/orchestrate/definitions.py
source_note: "ADR 0012 unparks 0006 row 8; seams.md seam 3; skip Gold hash if Dagster is not up"
created: 2026-08-27T12:00:00Z
tags: [orchestrate, dagster, type-01, lineage]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 01 Gold closed; ADR 0012 accepted; do not stand up Dagster to look busy"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: claude
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:58:20Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:12Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:c82a725950013b96d9021d123d375a31d75ca5500d011f21dfc71e91ad88d3b8
accepted_tier: 2
accepted_attempt_id: 43128cdc-20ed-5014-9af6-e7351b245c4d
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:c82a725950013b96d9021d123d375a31d75ca5500d011f21dfc71e91ad88d3b8
acceptance_record_digest: sha256:e3b042dd587740acb30673242f38e83caf2be4b4a218a46532e53bf4ce3b8feb
---

# Dagster lineage on closed Type 01 — parsing does not move into the orchestrator

> **Why:** Seam 3 is lineage and serve, not a second parser. Type 01
> Gold already exists. Skip the hash compare if Dagster is not up.

## Context

This leaf owns one artifact in the Type 01 steel thread. Legacy is the referee,
never the teacher: the modern side is built from `contracts/` alone. The eval
executes the artifact rather than asserting it exists.

## Goal

Declare Dagster assets that replay closed Type 01 emit → register →
Bronze → Silver → Gold → golden-match from immutable landing. Parsing
does not move into the orchestrator. Do not write frozen trees. Do not
create an empty orchestrate package to look busy. `signed_off` starts
false.

## Behavior

- **B-1** — Dagster is lineage (ADR 0012). It may partition by
  `batch_id`, retry, and backfill from `modern/landing/`.
- **B-2** — It must not read raw `.dat`, tokenize, decode overpunch,
  or own money.
- **B-3** — If Dagster is not installed / not up, skip the Gold-hash
  compare and pass. Do not stand up Dagster to look busy.
- **B-4** — If Dagster is up, replayed Gold for `B202607230000001`
  matches the existing Type 01 packet (applied_net `173.45`,
  `MATCHED`). Lie batch stays absent.

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
import pathlib
defs = pathlib.Path.cwd()/"modern/orchestration/definitions.py"
src = defs.read_text()
for a in ("legacy_ground_truth","landing_parquet","lakehouse_registered",
          "gold_reconciliation","golden_match_verdict","gold_hash"):
    assert f"def {a}(" in src, a
assert "plant_steps.py" in src or "STEPS" in src, "assets must shell out, not parse"
print("eval_3 OK six lineage assets")
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
    description: ADR 0012 lineage-not-parser; freeze fence; unsigned
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Skip Gold hash if Dagster is not up; definitions must not parse raw
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-3, B-4]
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

## Anti-Patterns

- **Don't parse Type 01 in Dagster.** Translator owns grammar.
- **Don't stand up Dagster to look busy.** Skip the hash.
- **Don't serve unresolved Gold** (ADR 0013). That is not this leaf's write.

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
- `modern/ingestion/src/northwind_pay/types/01-card-settlement/parser.py`

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
