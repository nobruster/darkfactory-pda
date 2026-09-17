---
id: T-20260826-type-01-golden-match
title: Attach golden-match to Type 01 modern observations
status: ready
format_version: 3
profile: standard
effort: L
budget_iterations: 15
agent: claude
parent: docs/seams.md
depends_on:
  - T-20260826-type-01-gold
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/validation/attach_type01.py
source_note: "ADR 0011; do not rewrite validation/golden-match/golden_match.py"
created: 2026-08-26T18:00:00Z
tags: [type-01, golden-match]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 01 Gold rebuilds from landing"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: claude
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:57:33Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:10Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:d9df13b69abc6866fbaf80ac96317b12dcdaf4963ea303e8c07d13d0a7511933
accepted_tier: 2
accepted_attempt_id: 81aa0c83-4447-54fc-b322-5ae69ad05152
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:d9df13b69abc6866fbaf80ac96317b12dcdaf4963ea303e8c07d13d0a7511933
acceptance_record_digest: sha256:b7eacd73832bbd8bb2eab80f887e4e988e02b68729d310cff46e5a6282081507
---

# Attach golden-match to Type 01 modern observations

> **Why:** Unresolved golden-match is not Gold. The referee already
> exists. Attach observations. Do not add a tolerance.

## Context

This leaf owns one artifact in the Type 01 steel thread. Legacy is the referee,
never the teacher: the modern side is built from `contracts/` alone. The eval
executes the artifact rather than asserting it exists.

## Goal

Run three cases and write `evidence/modern/`:

1. `valid-minimal` — both questions yes.
2. `DF-SOURCE-001` — `CONFIRMED_SOURCE_DEFECT`, no Gold, keep 173.44.
3. `malformed` — classified terminal, no invented artifacts.

Zero unexplained differences.

## Behavior

- **B-1** — Attach uses `validation/golden-match/golden_match.py` unchanged.
- **B-2** — `valid-minimal` resolved against contract and legacy observation.
- **B-3** — Source lie classified `CONFIRMED_SOURCE_DEFECT`; no Gold file invented.
- **B-4** — Malformed classified; no Parquet / Gold artifacts.

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
d = json.loads((pathlib.Path.cwd()/"evidence/modern/B202607230000001/golden-match.json").read_text())
assert all(d["checks"].values()), d["checks"]
assert d["resolved"] and d["unexplained_count"] == 0, d
print("eval_3 OK golden-match", d["outcome_class"])
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
    description: Attach script uses the referee and adds no tolerance
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Three cases classified; valid-minimal resolved; lie has no Gold
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-3, B-4]
    terminal: true
    expected_duration_sec: 90

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

- **Don't edit the referee.** Don't net the two questions.
- **Don't classify CONFIRMED_LEGACY_DEFECT tonight.** That's Friday.
- **Don't invent Parquet for a refusal.**

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
