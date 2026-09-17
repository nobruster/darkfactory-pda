---
id: T-20260826-type-01-landing-emit
title: Emit Type 01 landing Parquet for valid-minimal; zero Parquet on the lie
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
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
execution_backend: any
signed_off: false
signed_off_by: (none)
signed_off_at: (none)
accepted: false
accepted_by: (none)
accepted_at: (none)
evidence_refs: []
---

# Emit Type 01 landing Parquet for valid-minimal; zero Parquet on the lie

> **Why:** Constructor consumes landing. If Parquet is missing, the first
> incident is emit, not a re-parse. The lie keeps **173.44** and writes
> nothing.

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

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/tasks/T-20260826-type-01-landing-emit.md"
HANDLER="$ROOT/modern/ingestion/src/northwind_pay/types/01-card-settlement/handler.py"
WRITER="$ROOT/modern/ingestion/src/northwind_pay/types/01-card-settlement/writer.py"
CONSENSUS="$ROOT/docs/consensus-lakehouse.md"
LANDING="$ROOT/modern/landing"

eval_1() {
  test -f "$HANDLER" || return 1
  test -f "$WRITER" || return 1
  grep -q 'decimal128' "$WRITER" || return 1
  grep -q 'modern/landing' "$SPEC" || return 1
  grep -q 'Luan Moreno' "$CONSENSUS" || return 1
}

eval_2() {
  python3 - "$ROOT" <<'PY'
import os, sys
from pathlib import Path
root = Path(sys.argv[1])
os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")
sys.path.insert(0, str(root / "modern/ingestion/src"))
from northwind_pay.emit import emit_scenario
landing = root / "modern" / "landing"
happy = emit_scenario("valid-minimal", landing_root=landing)
assert happy["status"] == "succeeded", happy
assert happy["parquet_sha256"]
assert list(landing.rglob("*.parquet")), "missing parquet"
lie = emit_scenario("df-source-001", landing_root=landing)
assert lie["status"] == "quarantined", lie
assert lie["code"] == "SOURCE_CONTROL_TOTAL_MISMATCH"
assert lie.get("parquet_sha256") in (None, "")
assert not list(landing.rglob("*B202607230000004*.parquet"))
assert "173.44" in str(lie.get("controls"))
print("emit ok")
PY
}

eval_3() {
  test ! -f "$ROOT/legacy/processor/PWNED.txt" || return 1
  awk '
    BEGIN { sec="" }
    /^---$/ { n++; next }
    n==1 && $0 ~ /^(touches_paths|creates_paths):/ { sec=$1; next }
    n==1 && sec != "" && $0 ~ /^[^[:space:]-]/ { sec="" }
    n==1 && sec != "" && $0 ~ /^[[:space:]]*-[[:space:]]*(legacy|contracts|gen|infra)\// { bad=1 }
    END { exit bad ? 1 : 0 }
  ' "$SPEC"
}
```

## Validation Card

```yaml
success_criteria:
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
