---
id: T-20260827-type-03-lakehouse
title: Type 03 dlt → Gold + golden-match (same referee; no new grain ADR)
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: claude
parent: docs/seams.md
depends_on:
  - T-20260827-type-03-ingest
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/validation/attach_type03.py
  - modern/scripts/run_type03_gold.py
source_note: "ADR 0007–0011; ADR 0009 is Type 01 grain only"
created: 2026-08-27T12:00:00Z
tags: [type-03, dlt, gold, golden-match]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 03 ingest leaf authored"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: claude
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:46:51Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:32Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:bd763dd5ae9077fbbff46b8d62bdc937b7a7228259c1f74a271b95f6a4aadbad
accepted_tier: 2
accepted_attempt_id: 96389803-74ba-5d23-92b5-03b3f2ba5026
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:bd763dd5ae9077fbbff46b8d62bdc937b7a7228259c1f74a271b95f6a4aadbad
acceptance_record_digest: sha256:70bf0a3afeb4546a45cf7ede2ff11860d777e99bd312c0c667eed655aad82c32
---

# Type 03 dlt → Gold + golden-match (same referee; no new grain ADR)

## Context

Type 03's lakehouse lane: dlt registers the landing Parquet the ingest leaf
produced, dbt builds Bronze/Silver/Gold at the documented grain, and
golden-match adjudicates. The referee is `validation/golden-match/golden_match.py`
and it is never weakened — no tolerance, ever.

Depends on `T-20260827-type-03-ingest`: without landing Parquet there is
nothing to register.

## Goal

Register Type 03 landing only, Bronze → Silver → Gold, attach
`golden_match.py`. `DF-SOURCE-003` = `CONFIRMED_SOURCE_DEFECT`, keep
**198.49**, no Gold. No Type 03 grain ADR. Frozen trees forbidden.

## Behavior

- **B-1** — dlt registers landing. No `.rem` parse.
- **B-2** — Same referee. `DF-SOURCE-003` is `CONFIRMED_SOURCE_DEFECT`.
- **B-3** — ADR 0009 is not a Type 03 grain. Do not invent dimensions.

## Success Criteria

`eval_3` **executes** the Gold build and reads the row back out of DuckDB, so it
is RED before the work exists and GREEN only when the pipeline actually runs.

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/cvg/tasks/T-20260827-type-03-lakehouse.md"
ATTACH="$ROOT/modern/validation/attach_type03.py"
GOLDSCRIPT="$ROOT/modern/scripts/run_type03_gold.py"

eval_1() {
  grep -q 'golden' "$SPEC" || return 1
  grep -q 'Decimal' "$SPEC" || return 1
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
  test -f "$ATTACH" || return 1
  test -f "$GOLDSCRIPT" || return 1
  ! grep -qE 'from[[:space:]]+legacy|import[[:space:]]+java' "$ATTACH" "$GOLDSCRIPT" || return 1
  ! grep -qE 'tolerance|abs\(.*\)[[:space:]]*<' "$ATTACH" || return 1
}

# EXECUTES the Gold build, then reads the row back. Fails closed when absent.
eval_3() {
  test -f "$GOLDSCRIPT" || return 1
  cd "$ROOT" || return 1
  ./modern/.venv/bin/python "$GOLDSCRIPT" >/dev/null 2>&1 || return 1
  ./modern/.venv/bin/python - <<'PYEOF'
import duckdb, pathlib, sys
db = pathlib.Path.cwd() / "modern/lakehouse/ducklake/northwind_modern.duckdb"
con = duckdb.connect(str(db), read_only=True)
tables = [r[0] for r in con.execute(
    "select table_name from information_schema.tables where table_schema='gold'").fetchall()]
hit = [t for t in tables if "payment_slip_settlement" in t]
assert hit, f"no gold table for type 03: {tables}"
rows = con.execute(f"select * from gold.{hit[0]}").fetchall()
assert rows, f"gold table {hit[0]} is empty"
print("eval_3 OK", hit[0], len(rows), "row(s)")
PYEOF
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: Same referee; DF-SOURCE-003 CONFIRMED_SOURCE_DEFECT; no Type 03 grain ADR
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
  - id: eval_3
    description: EXECUTES the Gold build and reads the row back from DuckDB
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: true
    expected_duration_sec: 120

retry_policy:
  max_iterations: 15
  circuit_breaker_no_progress: 3
  on_terminal_failure: park_with_context

agent_contract:
  version: 2
  read: [intent, behavior, contract, guardrails, operations]
  produce:
    - code
  required_tools: [git, bash]
  timeout_minutes: 45
  sandbox_type: host
  output_artifacts: []
  mcp_dependencies: []
  emit:
    - pass
    - fail
    - retry_with_reason
    - parked_with_context
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

Additive. Revert with `git rm modern/validation/attach_type03.py modern/scripts/run_type03_gold.py`.

---

## Observability Hooks

Watch the Gold row count and the golden-match verdict. Any unexplained
financial delta blocks the release gate.

---

## Anti-Patterns

- **Don't weaken the referee.** No tolerance in `golden_match.py`, ever.
- **Don't rewrite `contracts/**/expected-*`** to make a delta disappear.
- **Don't net the two questions.** Modern-vs-contract and legacy-vs-contract
  are answered separately and every difference gets exactly one code.

---

## Open Questions

(none — ADR 0009 fixes the grain, the contract fixes the money.)

