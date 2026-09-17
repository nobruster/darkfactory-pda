---
id: T-20260825-type-01-landing-parser
title: Parse Type 01 card settlement into Decimal, privacy-safe records for landing
status: ready
format_version: 3
profile: standard
effort: S
budget_iterations: 15
agent: any
parent: docs/seams.md
depends_on: []
supersedes: (none)
touches_paths: []
creates_paths:
  - modern/ingestion/src/northwind_pay/types/01-card-settlement/parser.py
source_note: "docs/consensus.md signed 2026-08-25 by Luan Moreno, Agentic Lead; ADR 0003–0005; seams.md ingest→landing claim leg"
created: 2026-08-25T23:00:00Z
tags: [type-01, ingest, landing, parser]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "docs/consensus.md records canonical sign; do not execute product code until this leaf is gated"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: any
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-28T01:36:09Z
accepted: false
accepted_by: (none)
accepted_at: (none)
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:d239b1dba1cc6089a2d7c64dff66405ce5139450ee25617adbed69f6dbe80ccc
---

# Parse Type 01 card settlement into Decimal, privacy-safe records for landing

> **Why:** Privacy dies at the parser. Money is Decimal. The first modern write
> (when the mesh later runs) is deterministic Parquet under `modern/landing/`,
> never SFTP. This leaf is the Type 01 **claim** leg, not the lakehouse.

---

## Goal

Author and later execute one Type 01 **parser** that reads the same raw
`.dat` bytes as the live line, decodes signed overpunch as exact Decimal
(scale 2), tokenizes PAN (`tok_` + 24 hex) and keeps last4, masks CPF as
`*******` + last4, **before** any landing publication, and yields **no**
parquet-ready rows when the source lie keeps **173.44**. Do not write
`legacy/`, `contracts/`, `gen/`, or `infra/`. Do not write `modern/`
product code while this leaf is only authored (`signed_off: false`).

---

## Context

Steel thread: Type 01 ingest → landing (`docs/seams.md` seam 1, claim
leg). Judge: `contracts/types/01-card-settlement/`. Consensus signed
2026-08-25 by Luan Moreno, Agentic Lead. Keep 173.44. Java is
observation only — do not import it.

---

## Behavior

- **B-1** — GIVEN a Type 01 detail amount encoded as signed overpunch
  WHEN the parser decodes money THEN the value is exact Decimal scale 2,
  never binary float. Example: `00000001234E` → `123.45`.
- **B-2** — GIVEN a Type 01 detail with clear PAN and CPF WHEN the
  parser finishes THEN PAN is `tok_` + 24 lowercase hex plus last4, CPF
  is `*******` + last4, and neither raw value appears in landing, logs,
  or evidence.
- **B-3** — GIVEN an accepted Type 01 batch (`valid-minimal`, net
  173.45) WHEN the mesh later runs THEN the writer may emit deterministic
  Parquet under `modern/landing/` from these records. GIVEN
  `df-source-001` / trailer **173.44** vs rows **173.45** WHEN the
  parser refuses THEN zero Parquet rows are produced for that batch.
- **B-4** — GIVEN this leaf WHEN any file is written THEN the path is
  not under `legacy/`, `contracts/`, `gen/`, or `infra/`.

---

## Success Criteria

Each criterion is a runnable bash function returning 0 (pass) or non-zero (fail).
Each MUST be terminal (deterministic, idempotent, non-flaky).

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/tasks/T-20260825-type-01-landing-parser.md"
LAYOUT="$ROOT/contracts/types/01-card-settlement/layout.yaml"
PRIVACY="$ROOT/contracts/types/01-card-settlement/privacy.yaml"
CONSENSUS="$ROOT/docs/consensus.md"
PARSER="$ROOT/modern/ingestion/src/northwind_pay/types/01-card-settlement/parser.py"

# eval-1: Decimal at parse is the contract and this leaf
eval_1() {
  grep -q 'decimal_scale: 2' "$LAYOUT" || return 1
  grep -q '00000001234E' "$LAYOUT" || return 1
  grep -q '123.45' "$LAYOUT" || return 1
  grep -q 'Decimal' "$SPEC" || return 1
  grep -q 'never binary float' "$SPEC" || return 1
}

# eval-2: Privacy dies at parse (PAN token + last4, CPF mask)
eval_2() {
  grep -q 'tok_' "$PRIVACY" || return 1
  grep -q "output_format: last_4_digits" "$PRIVACY" || return 1
  grep -Fq '*******' "$PRIVACY" || return 1
  grep -q 'PAN' "$SPEC" || return 1
  grep -q 'CPF' "$SPEC" || return 1
}

# eval-3: Landing Parquet destination + freeze fence + signed consensus
eval_3() {
  grep -q 'modern/landing/' "$SPEC" || return 1
  grep -q '173.44' "$SPEC" || return 1
  grep -q 'zero Parquet' "$SPEC" || return 1
  grep -q 'Luan Moreno' "$CONSENSUS" || return 1
  grep -q 'canonical' "$CONSENSUS" || return 1
  grep -q 'signed_off: false' "$SPEC" || return 1
  awk '
    BEGIN { sec="" }
    /^---$/ { n++; next }
    n==1 && $0 ~ /^(touches_paths|creates_paths):/ { sec=$1; next }
    n==1 && sec != "" && $0 ~ /^[^[:space:]-]/ { sec="" }
    n==1 && sec != "" && $0 ~ /^[[:space:]]*-[[:space:]]*(legacy|contracts|gen|infra)\// { bad=1 }
    END { exit bad ? 1 : 0 }
  ' "$SPEC" || return 1
}

# eval-4: When the parser exists (mesh later), Decimal + no Java + no float money.
# Tonight parser.py is absent — that is not a skip; the leaf is not executed yet.
# Absence passes only while signed_off is false. Presence must satisfy the gate.
eval_4() {
  if [[ ! -f "$PARSER" ]]; then
    grep -q 'signed_off: false' "$SPEC" || return 1
    test ! -d "$ROOT/modern/ingestion" || test ! -f "$PARSER" || return 1
    return 0
  fi
  grep -q 'Decimal' "$PARSER" || return 1
  ! grep -qE 'from[[:space:]]+legacy|import[[:space:]]+java|legacy\.processor' "$PARSER" || return 1
  ! grep -qE 'float\(|np\.float|dtype=float' "$PARSER" || return 1
  grep -qE 'tok_|last4|last_4' "$PARSER" || return 1
}
```

---

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: Type 01 money is Decimal scale 2; this leaf forbids binary float
    runnable: bash
    check_type: deterministic
    verifies: [B-1]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Contract and leaf require PAN tok_+last4 and CPF mask at parse
    runnable: bash
    check_type: deterministic
    verifies: [B-2]
    terminal: true
    expected_duration_sec: 5
  - id: eval_3
    description: Leaf names modern/landing Parquet, keep 173.44 zero Parquet, no frozen writes
    runnable: bash
    check_type: deterministic
    verifies: [B-3, B-4]
    terminal: true
    expected_duration_sec: 5
  - id: eval_4
    description: Absent parser is allowed only while unsigned; present parser is Decimal, private, no Java
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-2, B-4]
    terminal: true
    expected_duration_sec: 5

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

---

## Exit Check

```bash
eval_1 && eval_2 && eval_3 && eval_4
```

---

## Rollback Plan

(none — this task is append-only. Tonight it only adds this spec under
`docs/tasks/`. If a later execution writes `parser.py`, revert that path
with `git checkout --` / `git rm` on `modern/ingestion/.../parser.py`.
Never revert frozen trees to "fix" a gate.)

---

## Observability Hooks

(none — no runtime observability required tonight. When the mesh later
runs, watch landing parquet SHA-256 and refuse `SOURCE_CONTROL_TOTAL_MISMATCH`
with zero Parquet.)

---

## Anti-Patterns

- **Don't import Java or `legacy/processor`.** The second plant reads raw
  bytes and `contracts/`. Java is observation only.
- **Don't take sanitized CSV as input.** Legacy CSV is comparison
  evidence, never a modern source.
- **Don't write Parquet to SFTP.** First modern write is
  `modern/landing/`. Mixing destinations is a failed day.
- **Don't use float for money.** One cent is the class. Decimal only.
- **Don't repair 173.44.** Keep the declaration. Refuse. Zero Parquet.
- **Don't write `modern/` product code while `signed_off` is false.**
  Authoring this leaf is not executing it.
- **Don't pick a lakehouse in this leaf.** dlt / DuckDB / dbt are Day 3
  (ADR 0006).
- **Don't hand-edit `signed_off*`.** Only `taskspec gate --stamp`.

---

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `legacy/processor/src`

---

## Open Questions

(none — this task is fully specified. Python packaging remains parked
in ADR 0006 and must not be smuggled in as a stack pick.)
