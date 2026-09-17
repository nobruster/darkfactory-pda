---
id: T-20260828-type-06-ingest
title: Type 06 ingest → landing (five-file; HALF_UP at parser; 1.01; malformed zero Parquet)
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: docs/seams-type-06.md
depends_on: []
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/ingestion/src/northwind_pay/types/06-merchant-chargeback/model.py
  - modern/ingestion/src/northwind_pay/types/06-merchant-chargeback/parser.py
  - modern/ingestion/src/northwind_pay/types/06-merchant-chargeback/schema.py
  - modern/ingestion/src/northwind_pay/types/06-merchant-chargeback/writer.py
  - modern/ingestion/src/northwind_pay/types/06-merchant-chargeback/handler.py
source_note: "docs/consensus-type-06.md signed 2026-08-28; ADR 0014; contracts/types/06-merchant-chargeback/; HALF_UP 1.01"
created: 2026-08-28T21:00:00Z
tags: [type-06, ingest, landing, half-up]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "docs/consensus-type-06.md signed; do not recut docs/consensus.md"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: any
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:11:17Z
accepted: false
accepted_by: (none)
accepted_at: (none)
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:7f9dcd880aa589500f355abe5836e5ecb176d60fbcb822ff7601742548729a48
---

# Type 06 ingest → landing (five-file; HALF_UP at parser; 1.01; malformed zero Parquet)

> **Why:** Sealed Type 06. Same SWE lane as Type 01. Locale CSV and
> `HALF_UP` are type-specific. Contract chargeback is **1.01**. Do not
> import Java. Do not create an empty Type 06 package.

## Context

Steel thread tonight: Type 06 ingest → landing (`docs/seams-type-06.md`
seam 1). Judge: `contracts/types/06-merchant-chargeback/`. Consensus
signed 2026-08-28 by Luan Moreno, Agentic Lead. HALF_UP **1.01**. Java
is observation only — do not import it.

## Goal

Author (and after Bind, execute) one Type 06 five-file package so
`valid-minimal` may emit `modern/landing/` Parquet, chargeback =
`original × rate ÷ 100` rounded once with **`HALF_UP`** (**1.01** on
`67.00` at `1.500` percent), and `malformed` emits **zero** Parquet
(`INVALID_CSV_QUOTING`). Frozen trees forbidden. No product files
while `signed_off: false`.

## Behavior

- **B-1** — Same as Type 01: five-file, Decimal never float, privacy at
  parse (CNPJ `**********<last4>`), landing Parquet not SFTP.
- **B-2** — Type-specific: semicolon CSV, decimal comma; **`HALF_UP`**
  at the parser (Python default `HALF_EVEN` is forbidden here).
- **B-3** — `valid-minimal` / `B202607230000501` calculated chargeback
  **1.01**. Not **1.00**.
- **B-4** — `malformed` / `B202607230000503` → `INVALID_CSV_QUOTING`,
  zero Parquet.
- **B-5** — No empty `06-merchant-chargeback/` folder. No Java import.
  Do not dump Types `02`–`05`.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/tasks/T-20260828-type-06-ingest.md"
LAYOUT="$ROOT/contracts/types/06-merchant-chargeback/layout.yaml"
RECON="$ROOT/contracts/types/06-merchant-chargeback/main/expected-reconciliation.yaml"
REJECT="$ROOT/contracts/types/06-merchant-chargeback/main/expected-malformed-rejection.yaml"
PKG="$ROOT/modern/ingestion/src/northwind_pay/types/06-merchant-chargeback"

eval_1() {
  grep -q 'five-file' "$SPEC" || return 1
  grep -q 'modern/landing/' "$SPEC" || return 1
  grep -q 'HALF_UP' "$SPEC" || return 1
  grep -q 'HALF_EVEN' "$SPEC" || return 1
  grep -q '1.01' "$SPEC" || return 1
  grep -q 'INVALID_CSV_QUOTING' "$SPEC" || return 1
  grep -q 'zero Parquet' "$SPEC" || return 1
  grep -q 'signed_off: false' "$SPEC" || return 1
  grep -q 'CONFIRMED_LEGACY_DEFECT' "$SPEC" || return 1
  grep -q 'rounding_mode: HALF_UP' "$LAYOUT" || return 1
  grep -q '1.01' "$RECON" || return 1
  grep -q 'INVALID_CSV_QUOTING' "$REJECT" || return 1
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
  grep -q 'ROUND_HALF_UP\|HALF_UP' "$PKG/parser.py" || return 1
  ! grep -qE 'from[[:space:]]+legacy|import[[:space:]]+java' "$PKG"/*.py || return 1
  grep -q 'Decimal' "$PKG/parser.py" || return 1
  ! grep -q 'ROUND_HALF_EVEN' "$PKG/parser.py" || return 1
}

eval_3() {
  if [[ ! -f "$PKG/handler.py" ]]; then
    grep -q 'signed_off: false' "$SPEC" || return 1
    return 0
  fi
  PYBIN="$ROOT/modern/.venv/bin/python"
  if [[ ! -x "$PYBIN" ]]; then
    PYBIN="$(command -v python3)"
  fi
  PYTHONPATH="$ROOT/modern/ingestion/src${PYTHONPATH:+:$PYTHONPATH}" "$PYBIN" - <<'PY' || return 1
import importlib.util, sys, tempfile
from pathlib import Path
pkg = Path("modern/ingestion/src/northwind_pay/types/06-merchant-chargeback/handler.py")
spec = importlib.util.spec_from_file_location("nwp_t06_handler", pkg)
mod = importlib.util.module_from_spec(spec)
sys.modules["nwp_t06_handler"] = mod
spec.loader.exec_module(mod)
raw = Path("spec/type-06-merchant-chargeback/samples/valid-minimal.csv")
with tempfile.TemporaryDirectory() as tmp:
    out = mod.process(raw, landing_root=Path(tmp))
assert out.status == "succeeded", out
assert str(out.controls.get("computed_chargeback_amount")) == "1.01", out.controls
assert out.parquet_sha256
mal = Path("spec/type-06-merchant-chargeback/samples/malformed.csv")
with tempfile.TemporaryDirectory() as tmp:
    out = mod.process(mal, landing_root=Path(tmp))
assert out.status == "quarantined", out
assert out.code == "INVALID_CSV_QUOTING", out
assert out.parquet_sha256 is None
PY
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: HALF_UP at parser; contract 1.01; malformed zero Parquet; classification named; freeze fence
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-3, B-4]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: No empty Type 06 folder while unsigned; present parser is HALF_UP Decimal not HALF_EVEN
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-5]
    terminal: true
    expected_duration_sec: 5
  - id: eval_3
    description: Present handler emits 1.01 HALF_UP Parquet and quarantines malformed with zero Parquet
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-3, B-4]
    terminal: true
    expected_duration_sec: 30

retry_policy:
  max_iterations: 15
  circuit_breaker_no_progress: 3
  on_terminal_failure: park_with_context

agent_contract:
  version: 2
  read: [intent, behavior, contract, guardrails, operations]
  produce:
    - code
    - tests
  required_tools: [git, bash]
  timeout_minutes: 30
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

(none — additive. If a later execution writes the Type 06 five-file
package, revert those five paths. Never revert frozen trees to "fix"
a gate.)

## Observability Hooks

(none — watch landing Parquet SHA-256 and refuse `INVALID_CSV_QUOTING`
with zero Parquet. Classification of a live-plant miss is the
lakehouse leaf.)

## Anti-Patterns

- **Don't rewrite `expected/` to match `HALF_EVEN`.** That is `MODERN_DEFECT`.
- **Don't create an empty Type 06 package.** Five files or nothing.
- **Don't copy Types 02–05 packages onto this tile.**
- **Don't patch Java so the cent agrees.** If modern matches 1.01 and
  legacy does not, the lakehouse leaf classifies `CONFIRMED_LEGACY_DEFECT`.

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `docs/consensus.md`
- `docs/consensus-lakehouse.md`
- `validation/golden-match/golden_match.py`

## Open Questions

(none — this task is fully specified. The live Java cent is Stage 1
observation on the lakehouse leaf, not a parser input.)
