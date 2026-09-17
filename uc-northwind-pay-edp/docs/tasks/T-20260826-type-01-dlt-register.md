---
id: T-20260826-type-01-dlt-register
title: Register Type 01 landing Parquet through dlt (no re-parse)
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 10
agent: any
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
execution_backend: any
signed_off: false
signed_off_by: (none)
signed_off_at: (none)
accepted: false
accepted_by: (none)
accepted_at: (none)
evidence_refs: []
---

# Register Type 01 landing Parquet through dlt (no re-parse)

> **Why:** Seam 2 starts at immutable landing. If dlt parses bytes or
> computes a net, the seam is wrong.

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

```bash
ROOT="$(git rev-parse --show-toplevel)"
REG="$ROOT/modern/lakehouse/dlt/registration.py"

eval_1() {
  test -f "$REG" || return 1
  grep -q 'dlt' "$REG" || return 1
  ! grep -qE '\\.dat|decode_overpunch|tokenize_pan|HMAC' "$REG" || return 1
}

eval_2() {
  python3 - "$ROOT" <<'PY'
import os, sys
from pathlib import Path
root = Path(sys.argv[1])
os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")
sys.path.insert(0, str(root / "modern/ingestion/src"))
sys.path.insert(0, str(root / "modern/lakehouse/dlt"))
from northwind_pay.emit import emit_scenario
from registration import register
landing = root / "modern" / "landing"
emit_scenario("valid-minimal", landing_root=landing)
db = root / "modern/lakehouse/ducklake/northwind_modern.duckdb"
result = register("01", landing_root=landing, database=db)
assert result.row_count >= 2, result
assert result.table == "card_settlement"
import duckdb
con = duckdb.connect(str(db), read_only=True)
n = con.execute("select count(*) from landing.card_settlement").fetchone()[0]
assert n >= 2, n
print("register ok", result)
PY
}
```

## Validation Card

```yaml
success_criteria:
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
- `validation/golden-match/golden_match.py`
