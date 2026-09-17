# ADR 0015 — Type 06 Gold grain; two questions; stall on legacy miss

- Status: Accepted (Structure). Binding after `docs/consensus-type-06.md`.
- Date: 2026-08-28
- Pass: 2 Structure (Day 5 Dark Factory)
- Decider: Helena Dias (owner). Unsigned until `docs/consensus-type-06.md`.
- Seat: Dark Factory

## Context

ADR 0009 closed Type 01 medallion grains. It is **not** a Type 06
grain. ADR 0011 named six golden-match codes and parked
`CONFIRMED_LEGACY_DEFECT` for Friday. ADR 0007: dlt registers landing
only. The Type 06 contract paid relation is
`reporting.merchant_chargeback_reconciliation`, grain `batch_id` +
`currency`.

The point of tonight is that the **legacy plant** can disagree with
the contract. Repair is never. A stalled type with one honest code is
a success state.

## Decision

Type 06 medallion grains:

| Zone | Grain | Keys |
|---|---|---|
| **Bronze** | one source-aligned chargeback | `batch_id` + `source_record_number` |
| **Bronze control** | one control row per batch | `batch_id` |
| **Silver** | same grain as Bronze; money conserved | `batch_id` + `source_record_number` |
| **Gold** | one governed reconciliation | `batch_id` + `currency` |

Gold columns match the Type 06 contract report (`source_*` /
`staged_*` / `applied_*` for original, chargeback, calculated;
deltas; `status`; `reject_count`). dlt does not parse CSV. dbt does
not retokenize or re-round.

**Two questions, never netted** (same referee, ADR 0011):

1. Does **modern** match the contract?
2. Does **legacy** match the contract?

| modern | legacy | code | what we do |
|---|---|---|---|
| ✗ | ✓ | `MODERN_DEFECT` | fix the new plant, re-run |
| ✓ | ✗ | `CONFIRMED_LEGACY_DEFECT` | write it down, **stall** |
| both ✗ vs declaration, ✓ vs each other | `CONFIRMED_SOURCE_DEFECT` | keep the wrong number |

Do **not** edit `legacy/`. Do **not** rewrite
`contracts/**/expected-*`. Do **not** add tolerance to
`validation/golden-match/golden_match.py`. Gold stays blocked on
unresolved. The packet lives under `evidence/` (gitignored).

`malformed` is classified on terminal behavior: status, stable code,
zero Parquet, zero mutation. Do not invent empty rows.

## What this is not

A Type 01 Gold copy with renamed columns guessed from Java. A license
to net the two questions into one green check. A `factory/` detector
product.

## Consequences

- Lakehouse leaf evals include the **classification**, not only “it
  loaded.”
- `factory_e2e.py --type 06` is the stage printer. It builds nothing.
- Linear moves when the packet exists.

## Evidence

- `contracts/types/06-merchant-chargeback/reconciliation.yaml`
- ADR 0007, 0009, 0011
- `plans/dark-factory.md` §7 Day 5 red pill
- `validation/golden-match/golden_match.py` — six codes, no tolerance
