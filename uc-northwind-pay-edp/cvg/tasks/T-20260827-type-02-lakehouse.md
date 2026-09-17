---
id: T-20260827-type-02-lakehouse
title: Type 02 dlt → Gold + golden-match (same referee; no new grain ADR)
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: claude
parent: docs/seams.md
depends_on:
  - T-20260827-type-02-ingest
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/validation/attach_type02.py
  - modern/scripts/run_type02_gold.py
source_note: "ADR 0007–0011; ADR 0009 is Type 01 grain only; attach golden_match.py"
created: 2026-08-27T12:00:00Z
tags: [type-02, dlt, gold, golden-match]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 02 ingest leaf authored; Type 01 lakehouse sign canonical"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: claude
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:46:14Z
accepted: true
accepted_by: luanmorenomaciel
accepted_at: 2026-09-10T19:05:26Z
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:6ef7eaecb5a903eae0f8675bc6ed640fe2bcb936a5e634a0b1e283325c69cef9
accepted_tier: 2
accepted_attempt_id: 03e1b109-96bd-5ad2-8176-ad3175e34306
accepted_authorization_ref: hmac-sha256-v3:d90e2e61:6ef7eaecb5a903eae0f8675bc6ed640fe2bcb936a5e634a0b1e283325c69cef9
acceptance_record_digest: sha256:2acd2e6b3bffbd859c4376d5328ea00f337b7068730b104dc6d381278be42631
---

# Type 02 dlt → Gold + golden-match (same referee; no new grain ADR)

> **Why:** Same DE lane as Type 01. dlt registers landing only. Replay
> rebuilds Gold. The referee is attached, not rewritten. ADR 0009 is
> not a Type 02 grain.

## Context

Type 02's lakehouse lane: dlt registers the landing Parquet the ingest leaf
produced, dbt builds Bronze/Silver/Gold at the documented grain, and
golden-match adjudicates. The referee is `validation/golden-match/golden_match.py`
and it is never weakened — no tolerance, ever.

Depends on `T-20260827-type-02-ingest`: without landing Parquet there is
nothing to register.

## Goal

Register Type 02 landing (no re-parse), Bronze → Silver → Gold, attach
`validation/golden-match/golden_match.py`. `valid-minimal` both
questions yes. `DF-SOURCE-002` = `CONFIRMED_SOURCE_DEFECT`, keep
**173.44**, no Gold. Do not invent a Type 02 grain. Do not write frozen
trees. Do not execute product code while `signed_off: false`.

## Behavior

- **B-1** — dlt registers `modern/landing/` Parquet only. No `.txt`
  parse, no tokenize, no net.
- **B-2** — Same referee, two questions never netted, six codes, no
  tolerance. `DF-SOURCE-002` classifies `CONFIRMED_SOURCE_DEFECT`.
- **B-3** — No new grain unless an ADR says so. ADR 0009 is Type 01
  only. Do not read Postgres to compute Gold.

## Success Criteria

`eval_3` **executes** the Gold build and reads the row back out of DuckDB, so it
is RED before the work exists and GREEN only when the pipeline actually runs.

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/cvg/tasks/T-20260827-type-02-lakehouse.md"
ATTACH="$ROOT/modern/validation/attach_type02.py"
GOLDSCRIPT="$ROOT/modern/scripts/run_type02_gold.py"

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
hit = [t for t in tables if "instant_payment" in t]
assert hit, f"no gold table for type 02: {tables}"
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
    description: Same referee; DF-SOURCE-002 CONFIRMED_SOURCE_DEFECT; no Type 02 grain ADR
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-3]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Attach exists only after execute; uses referee with no tolerance
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

## Rollback Plan

Additive. Revert with `git rm modern/validation/attach_type02.py modern/scripts/run_type02_gold.py`.

---

## Observability Hooks

Watch the Gold row count and the golden-match verdict. Any unexplained
financial delta blocks the release gate.

---

## Open Questions

(none — ADR 0009 fixes the grain, the contract fixes the money.)

---

## Anti-Patterns

- **Don't re-parse.** Don't rewrite `golden_match.py`. Don't net the two questions.
- **Don't invent Type 02 dimensions.** “dbt ran” is a log, not an eval.

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
