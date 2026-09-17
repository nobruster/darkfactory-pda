---
id: T-20260827-type-03-ingest
title: Type 03 ingest → landing (five-file package; zero Parquet on DF-SOURCE-003)
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: docs/seams.md
depends_on: []
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement/model.py
  - modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement/parser.py
  - modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement/schema.py
  - modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement/writer.py
  - modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement/handler.py
source_note: "ADR 0001–0005, 0002 five-file; contracts/types/03-payment-slip-settlement/; keep DF-SOURCE-003 198.49"
created: 2026-08-27T12:00:00Z
tags: [type-03, ingest, landing]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "docs/consensus.md signed; Type 01 seam 1 unchanged"
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

# Type 03 ingest → landing (five-file package; zero Parquet on DF-SOURCE-003)

> **Why:** Same SWE lane as Type 01. 240-byte paired `A`/`B` lots are
> type-specific. Keep declared **198.49**. Do not create an empty type folder.

## Goal

Author (and later execute) one Type 03 five-file package so
`valid-minimal` may emit `modern/landing/` Parquet and `DF-SOURCE-003`
emits **zero** Parquet (`SOURCE_CONTROL_NET_MISMATCH`). Decimal. Privacy
at the parser. Frozen trees forbidden. No product files while
`signed_off: false`.

## Behavior

- **B-1** — Same as Type 01: five-file, Decimal, privacy at parse,
  landing Parquet not SFTP, lie refused with zero Parquet.
- **B-2** — Type-specific: `PAYSLIPSET03` `.rem`, 240-byte paired
  segments; `DF-SOURCE-003` / `B202607230000205` declares net **198.49**
  vs rows **198.50**.
- **B-3** — No Java import. No empty `03-payment-slip-settlement/` folder.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/tasks/T-20260827-type-03-ingest.md"
FINDING="$ROOT/contracts/types/03-payment-slip-settlement/main/expected-df-source-003-finding.yaml"
PKG="$ROOT/modern/ingestion/src/northwind_pay/types/03-payment-slip-settlement"

eval_1() {
  grep -q 'five-file' "$SPEC" || return 1
  grep -q 'modern/landing/' "$SPEC" || return 1
  grep -q '198.49' "$SPEC" || return 1
  grep -q 'zero Parquet' "$SPEC" || return 1
  grep -q 'Decimal' "$SPEC" || return 1
  grep -q 'signed_off: false' "$SPEC" || return 1
  grep -q 'SOURCE_CONTROL_NET_MISMATCH' "$FINDING" || return 1
  grep -q '198.49' "$FINDING" || return 1
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
  if [[ ! -d "$PKG" ]]; then
    grep -q 'signed_off: false' "$SPEC" || return 1
    return 0
  fi
  for f in model.py parser.py schema.py writer.py handler.py; do
    test -f "$PKG/$f" || return 1
  done
  ! grep -qE 'from[[:space:]]+legacy|import[[:space:]]+java' "$PKG"/*.py || return 1
  grep -q 'Decimal' "$PKG/parser.py" || return 1
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: Leaf names five-file landing, keep 198.49 zero Parquet, freeze fence
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Absent package allowed only while unsigned; present package is five-file Decimal no Java
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-3]
    terminal: true
    expected_duration_sec: 5
```

## Exit Check

```bash
eval_1 && eval_2
```

## Anti-Patterns

- **Don't pair segments in Dagster.** Don't repair 198.49. Don't create an empty type folder.

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
