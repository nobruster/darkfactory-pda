---
id: T-20260827-type-04-ingest
title: Type 04 ingest → landing (five-file package; zero Parquet on DF-SOURCE-004)
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
  - modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement/model.py
  - modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement/parser.py
  - modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement/schema.py
  - modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement/writer.py
  - modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement/handler.py
source_note: "ADR 0001–0005, 0002 five-file; contracts/types/04-ted-transfer-settlement/; keep DF-SOURCE-004 999.99"
created: 2026-08-27T12:00:00Z
tags: [type-04, ingest, landing]
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

# Type 04 ingest → landing (five-file package; zero Parquet on DF-SOURCE-004)

> **Why:** Same SWE lane as Type 01. `.dat` is not enough to pick this
> parser (Type 01 is overpunch card). Keep declared **999.99**.

## Goal

Author (and later execute) one Type 04 five-file package so
`valid-minimal` may emit `modern/landing/` Parquet and `DF-SOURCE-004`
emits **zero** Parquet (`SOURCE_CONTROL_NET_MISMATCH`). Decimal. Privacy
at the parser. Frozen trees forbidden. No empty type folder. No product
files while `signed_off: false`.

## Behavior

- **B-1** — Same as Type 01: five-file, Decimal, privacy at parse,
  landing Parquet not SFTP, lie refused with zero Parquet.
- **B-2** — Type-specific: `TED_SETTLE04` heterogeneous fixed-width
  `H/D/R/T`; `DF-SOURCE-004` / `B202607230000305` declares net **999.99**
  vs rows **1000.00**.
- **B-3** — No Java import. No empty `04-ted-transfer-settlement/` folder.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/tasks/T-20260827-type-04-ingest.md"
FINDING="$ROOT/contracts/types/04-ted-transfer-settlement/main/expected-df-source-004-finding.yaml"
PKG="$ROOT/modern/ingestion/src/northwind_pay/types/04-ted-transfer-settlement"

eval_1() {
  grep -q 'five-file' "$SPEC" || return 1
  grep -q 'modern/landing/' "$SPEC" || return 1
  grep -q '999.99' "$SPEC" || return 1
  grep -q 'zero Parquet' "$SPEC" || return 1
  grep -q 'Decimal' "$SPEC" || return 1
  grep -q 'signed_off: false' "$SPEC" || return 1
  grep -q 'SOURCE_CONTROL_NET_MISMATCH' "$FINDING" || return 1
  grep -q '999.99' "$FINDING" || return 1
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
    description: Leaf names five-file landing, keep 999.99 zero Parquet, freeze fence
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

- **Don't dispatch Type 04 because the extension is `.dat`.** Type 01 is a different `.dat`.
- **Don't repair 999.99.** Don't create an empty type folder.

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
