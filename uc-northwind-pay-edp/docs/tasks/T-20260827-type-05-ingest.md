---
id: T-20260827-type-05-ingest
title: Type 05 ingest → landing (five-file; HALF_UP at parser; zero Parquet on DF-SOURCE-005)
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
  - modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment/model.py
  - modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment/parser.py
  - modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment/schema.py
  - modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment/writer.py
  - modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment/handler.py
source_note: "ADR 0001–0005, 0003 Decimal; contracts/types/05-merchant-fee-assessment/; HALF_UP; keep DF-SOURCE-005 0.99"
created: 2026-08-27T12:00:00Z
tags: [type-05, ingest, landing, half-up]
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

# Type 05 ingest → landing (five-file; HALF_UP at parser; zero Parquet on DF-SOURCE-005)

> **Why:** Same SWE lane as Type 01. Locale CSV and `HALF_UP` are
> type-specific. Keep declared assessed **0.99**. Do not rewrite
> `expected/`. Do not create an empty Type 05 package.

## Goal

Author (and later execute) one Type 05 five-file package so
`valid-minimal` and `rounding-half-up` may emit `modern/landing/`
Parquet, fee = `gross × rate ÷ 100` rounded once with **`HALF_UP`**,
and `DF-SOURCE-005` emits **zero** Parquet
(`SOURCE_CONTROL_ASSESSED_FEE_MISMATCH`). Frozen trees forbidden. No
product files while `signed_off: false`.

## Behavior

- **B-1** — Same as Type 01: five-file, Decimal never float, privacy at
  parse, landing Parquet not SFTP.
- **B-2** — Type-specific: semicolon CSV, decimal comma; **`HALF_UP`**
  at the parser (Python default `HALF_EVEN` is forbidden here).
- **B-3** — `DF-SOURCE-005` / `B202607230000405` source assessed **0.99**
  vs calculated **1.00**. Keep 0.99. Refuse. Zero Parquet. Do not rewrite
  `contracts/` `expected/`.
- **B-4** — No empty `05-merchant-fee-assessment/` folder. No Java import.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/tasks/T-20260827-type-05-ingest.md"
FINDING="$ROOT/contracts/types/05-merchant-fee-assessment/main/expected-df-source-005-finding.yaml"
LAYOUT="$ROOT/contracts/types/05-merchant-fee-assessment/layout.yaml"
PKG="$ROOT/modern/ingestion/src/northwind_pay/types/05-merchant-fee-assessment"

eval_1() {
  grep -q 'five-file' "$SPEC" || return 1
  grep -q 'modern/landing/' "$SPEC" || return 1
  grep -q 'HALF_UP' "$SPEC" || return 1
  grep -q 'HALF_EVEN' "$SPEC" || return 1
  grep -q 'DF-SOURCE-005' "$SPEC" || return 1
  grep -q '0.99' "$SPEC" || return 1
  grep -q 'zero Parquet' "$SPEC" || return 1
  grep -q 'signed_off: false' "$SPEC" || return 1
  grep -q 'rounding_mode: HALF_UP' "$LAYOUT" || return 1
  grep -q 'SOURCE_CONTROL_ASSESSED_FEE_MISMATCH' "$FINDING" || return 1
  grep -q '0.99' "$FINDING" || return 1
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
    test ! -d "$PKG" || return 1
    return 0
  fi
  for f in model.py parser.py schema.py writer.py handler.py; do
    test -f "$PKG/$f" || return 1
  done
  grep -q 'HALF_UP' "$PKG/parser.py" || return 1
  ! grep -qE 'from[[:space:]]+legacy|import[[:space:]]+java' "$PKG"/*.py || return 1
  grep -q 'Decimal' "$PKG/parser.py" || return 1
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: HALF_UP at parser; DF-SOURCE-005 keep 0.99 zero Parquet; freeze fence
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-3]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: No empty Type 05 folder while unsigned; present parser is HALF_UP Decimal
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-4]
    terminal: true
    expected_duration_sec: 5
```

## Exit Check

```bash
eval_1 && eval_2
```

## Anti-Patterns

- **Don't rewrite `expected/` to match `HALF_EVEN`.** That is `MODERN_DEFECT` on the lakehouse leaf.
- **Don't create an empty Type 05 package.** Five files or nothing.
- **Don't repair 0.99.**

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `validation/golden-match/golden_match.py`
