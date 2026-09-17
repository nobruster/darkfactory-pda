---
id: T-20260828-type-06-lakehouse
title: Type 06 dlt → Gold + golden-match (two questions; CONFIRMED_LEGACY_DEFECT stalls)
status: ready
format_version: 3
profile: standard
effort: M
budget_iterations: 15
agent: any
parent: docs/seams-type-06.md
depends_on:
  - T-20260828-type-06-ingest
supersedes: (none)
touches_paths:
  - modern/lakehouse/dlt/registration.py
  - modern/dbt/dbt_project.yml
  - modern/dbt/models/sources.yml
creates_paths:
  - modern/dbt/models/bronze/bronze_merchant_chargeback.sql
  - modern/dbt/models/bronze/bronze_merchant_chargeback_control.sql
  - modern/dbt/models/silver/silver_merchant_chargeback.sql
  - modern/dbt/models/gold/gold_merchant_chargeback_reconciliation.sql
  - modern/validation/attach_type06.py
  - modern/scripts/run_type06_gold.py
source_note: "docs/consensus-type-06.md signed 2026-08-28; ADR 0015; do not rewrite golden_match.py"
created: 2026-08-28T21:00:00Z
tags: [type-06, dlt, gold, golden-match, confirmed-legacy-defect]
owner: Luan Moreno
priority: P1
severity: financial-critical
due_date: (none)
precondition: "Type 06 ingest leaf authored; consensus-type-06 signed"
blocked_reason: (none)
security_class: restricted_synthetic_pii
source_action_item: (none)
tracker_ref: (none)
execution_backend: any
signed_off: true
signed_off_by: luanmorenomaciel
signed_off_at: 2026-08-29T00:11:20Z
accepted: false
accepted_by: (none)
accepted_at: (none)
evidence_refs: []
signed_off_sig: hmac-sha256-v3:d90e2e61:751d7d378db5aa423a8d7be5018b9b74d00e4e7da040b95b796c29a45bfa70fd
---

# Type 06 dlt → Gold + golden-match (two questions; CONFIRMED_LEGACY_DEFECT stalls)

> **Why:** Friday’s pill. Same referee. Do not net the two questions.
> Do not patch Java. Classification is the eval.

## Context

Type 06 dlt → Gold (`docs/seams-type-06.md` seam 2, ADR 0015). Same
referee as Type 01. `CONFIRMED_LEGACY_DEFECT` is tonight’s honest
name when modern matches the contract and legacy does not. Do not
recut `docs/consensus-lakehouse.md`.

## Goal

Register Type 06 landing only, Bronze → Silver → Gold at
`batch_id` + `currency`, attach `golden_match.py` without rewriting
it.

1. Modern Gold for `valid-minimal` matches contract chargeback **1.01**
   `MATCHED`.
2. Ask legacy the same question separately.
3. If modern matches the contract and legacy does not: **one code**
   `CONFIRMED_LEGACY_DEFECT`. Stall the type. Write the packet under
   `evidence/`. Do not patch.
4. If modern is also wrong: `MODERN_DEFECT` — fix the new plant, re-run.
   Still classify legacy if that fact is true.

No product execute while `signed_off: false`. Frozen trees forbidden.

## Behavior

- **B-1** — dlt registers landing. No semicolon CSV parse in dlt.
- **B-2** — Gold table `gold.gold_merchant_chargeback_reconciliation`.
  Grain `batch_id` + `currency`. Contract columns, not Type 01 net.
- **B-3** — Two questions, never netted. Same referee. No tolerance.
- **B-4** — `CONFIRMED_LEGACY_DEFECT` when modern matches contract and
  legacy does not. Stall. Packet. Linear moves after the packet.
- **B-5** — `HALF_EVEN` on this type is `MODERN_DEFECT`. Never rewrite
  `contracts/` expected fixtures or `golden_match.py`.
- **B-6** — `malformed` classified on terminal behavior; zero Gold.

## Success Criteria

```bash
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/tasks/T-20260828-type-06-lakehouse.md"
REF="$ROOT/validation/golden-match/golden_match.py"
ATTACH="$ROOT/modern/validation/attach_type06.py"
RECON="$ROOT/contracts/types/06-merchant-chargeback/reconciliation.yaml"
GOLD="$ROOT/modern/dbt/models/gold/gold_merchant_chargeback_reconciliation.sql"
FACTORY="$ROOT/modern/scripts/factory_e2e.py"

eval_1() {
  grep -q 'dlt registers' "$SPEC" || return 1
  grep -q 'CONFIRMED_LEGACY_DEFECT' "$SPEC" || return 1
  grep -q 'MODERN_DEFECT' "$SPEC" || return 1
  grep -q 'HALF_EVEN' "$SPEC" || return 1
  grep -q 'two questions' "$SPEC" || return 1
  grep -q 'Stall' "$SPEC" || return 1
  grep -q 'signed_off: false' "$SPEC" || return 1
  grep -q '1.01' "$SPEC" || return 1
  grep -q 'CONFIRMED_LEGACY_DEFECT' "$REF" || return 1
  grep -q 'MODERN_DEFECT' "$REF" || return 1
  grep -q 'merchant_chargeback_reconciliation' "$RECON" || return 1
  grep -q 'CONFIRMED_LEGACY_DEFECT' "$FACTORY" || return 1
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
  if [[ ! -f "$ATTACH" ]]; then
    grep -q 'signed_off: false' "$SPEC" || return 1
    return 0
  fi
  test -f "$GOLD" || return 1
  grep -q 'golden_match' "$ATTACH" || return 1
  grep -q 'CONFIRMED_LEGACY_DEFECT' "$ATTACH" || return 1
  grep -q 'HALF_UP' "$ATTACH" || return 1
  ! grep -q 'tolerance' "$ATTACH" || return 1
  grep -q 'applied_chargeback_amount' "$GOLD" || return 1
  grep -q "tag:type_06\\|tags=\\['type_06'\\]" "$GOLD" || grep -q 'type_06' "$GOLD" || return 1
}

eval_3() {
  if [[ ! -f "$ATTACH" ]]; then
    grep -q 'signed_off: false' "$SPEC" || return 1
    return 0
  fi
  python3 "$ATTACH" >/tmp/nwp-type06-attach.json 2>/tmp/nwp-type06-attach.err || true
  PACKET="$ROOT/evidence/modern/B202607230000501/golden-match.json"
  FACTORY_JSON="$ROOT/evidence/factory/type-06.json"
  if [[ -f "$PACKET" ]]; then
    grep -q 'CONFIRMED_LEGACY_DEFECT\|1.01' "$PACKET" || return 1
  fi
  if [[ -f "$FACTORY_JSON" ]]; then
    grep -q 'CONFIRMED_LEGACY_DEFECT' "$FACTORY_JSON" || return 1
  fi
  grep -q 'CONFIRMED_LEGACY_DEFECT' "$ATTACH" || return 1
  return 0
}
```

## Validation Card

```yaml
success_criteria:
  - id: eval_1
    description: Two questions; CONFIRMED_LEGACY_DEFECT stalls; HALF_EVEN is MODERN_DEFECT; freeze fence
    runnable: bash
    check_type: deterministic
    verifies: [B-1, B-3, B-4, B-5]
    terminal: true
    expected_duration_sec: 5
  - id: eval_2
    description: Attach classifies CONFIRMED_LEGACY_DEFECT; Gold has chargeback columns; no tolerance
    runnable: bash
    check_type: deterministic
    verifies: [B-2, B-4, B-6]
    terminal: true
    expected_duration_sec: 5
  - id: eval_3
    description: Present attach/packet names CONFIRMED_LEGACY_DEFECT; does not rewrite the referee
    runnable: bash
    check_type: deterministic
    verifies: [B-3, B-4]
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

(none — additive Type 06 dbt models and attach. Revert those paths.
Never edit frozen trees or `golden_match.py` to go green.)

## Observability Hooks

(none — watch `evidence/modern/B202607230000501/golden-match.json` and
`factory_e2e.py --type 06`. One code. Stall.)

## Anti-Patterns

- **Don't rewrite `expected/` so legacy MATCHED becomes the oracle.**
- **Don't patch Java.** Stall is the success state.
- **Don't net the two questions.**
- **Don't rewrite `golden_match.py`.**
- **Don't invent Type 06 Gold for a refused batch.**

## Do-Not-Touch

- `legacy/`
- `contracts/`
- `gen/`
- `infra/`
- `docs/consensus.md`
- `docs/consensus-lakehouse.md`
- `validation/golden-match/golden_match.py`

## Open Questions

(none — classification table is closed in ADR 0015. The live cent is
observation, not a patch list.)
