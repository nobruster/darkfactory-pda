---
id: T-20260827-type-05-lakehouse
title: Type 05 dlt → Gold + golden-match (DF-SOURCE-005 source defect; HALF_UP; HALF_EVEN is MODERN_DEFECT)
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: claude
parent: docs/seams.md
depends_on:
  - T-20260827-type-05-ingest
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/validation/attach_type05.py
  - modern/scripts/run_type05_gold.py
source_note: "ADR 0007–0011; ADR 0003 records HALF_EVEN default; Type 05 contract HALF_UP; do not rewrite expected/"
created: 2026-08-27T12:00:00Z
tags: [type-05, dlt, gold, golden-match, half-up]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 05 ingest leaf authored"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: claude
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:46:27Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:38Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:e327f7be21a9cc4dfb0513e62bed23d357a8d0597cd9595924b4013ff49ef586
accepted_tier: 2
accepted_attempt_id: e8c57f12-9bfb-5c45-b8f3-5ee3bdcbb5e5
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:e327f7be21a9cc4dfb0513e62bed23d357a8d0597cd9595924b4013ff49ef586
acceptance_record_digest: sha256:14d779524f8b5e9ea9164583dd184c7e4275ba25c3306c761af2215656fb0afc
---

# Type 05 dlt → Gold + golden-match (DF-SOURCE-005 source defect; HALF_UP; HALF_EVEN is MODERN_DEFECT)

> **Why:** The pill is Type 05. Same referee. Do not net the two
> questions. Do not rewrite `expected/` so a `HALF_EVEN` plant goes green.

## Context

Type 05's lakehouse lane: dlt registers the landing Parquet the ingest leaf
produced, dbt builds Bronze/Silver/Gold at the documented grain, and
golden-match adjudicates. The referee is `validation/golden-match/golden_match.py`
and it is never weakened — no tolerance, ever.

Depends on `T-20260827-type-05-ingest`: without landing Parquet there is
nothing to register.

## Goal

Register Type 05 landing only, Bronze → Silver → Gold, attach
`golden_match.py`.

1. `DF-SOURCE-005` = `CONFIRMED_SOURCE_DEFECT` (declared assessed **0.99**,
   calculated **1.00**). No Gold. Keep 0.99.
2. `rounding-half-up` matches contract **`HALF_UP`**.
3. A plant that applies Python default **`HALF_EVEN`** is
   **`MODERN_DEFECT`**. Fix the plant, not `expected/`.

No Type 05 grain ADR. Frozen trees forbidden. No product execute while
`signed_off: false`.

## Behavior

- **B-1** — dlt registers landing. No semicolon CSV parse in dlt.
- **B-2** — `DF-SOURCE-005` classifies `CONFIRMED_SOURCE_DEFECT`.
- **B-3** — `rounding-half-up` is accepted only under `HALF_UP`.
- **B-4** — `HALF_EVEN` is `MODERN_DEFECT`. Never rewrite `contracts/`
  expected fixtures.
- **B-5** — Same referee, two questions, six codes, no tolerance.

## Success Criteria

`eval_3` **executes** the Gold build and reads the row back out of DuckDB, so it
is RED before the work exists and GREEN only when the pipeline actually runs.

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/cvg/tasks/T-20260827-type-05-lakehouse.md"
ATTACH="$ROOT/modern/validation/attach_type05.py"
GOLDSCRIPT="$ROOT/modern/scripts/run_type05_gold.py"

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
hit = [t for t in tables if "merchant_fee" in t]
assert hit, f"no gold table for type 05: {tables}"
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
    description: DF-SOURCE-005 CONFIRMED_SOURCE_DEFECT; HALF_UP; HALF_EVEN is MODERN_DEFECT
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-3, B-4, B-5]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Attach covers DF-SOURCE-005 and HALF_UP; no tolerance when present
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-3, B-4]
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

## Rollback Plan

Additive. Revert with `git rm modern/validation/attach_type05.py modern/scripts/run_type05_gold.py`.

---

## Observability Hooks

Watch the Gold row count and the golden-match verdict. Any unexplained
financial delta blocks the release gate.

---

## Open Questions

(none — ADR 0009 fixes the grain, the contract fixes the money.)

---

## Anti-Patterns

- **Don't rewrite `expected/` to match `HALF_EVEN`.** Fix the plant.
- **Don't classify CONFIRMED_LEGACY_DEFECT tonight.** Friday.
- **Don't invent Type 05 Gold for the lie.**

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
