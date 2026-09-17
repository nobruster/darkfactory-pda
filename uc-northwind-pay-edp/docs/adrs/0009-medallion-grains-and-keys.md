# ADR 0009 — Bronze, Silver, and Gold grains and keys

- Status: Accepted (Structure). Binding after `docs/consensus-lakehouse.md`.
- Date: 2026-08-26
- Pass: 2 Structure (Day 3 Constructor)
- Decider: Helena Dias (owner). Unparks ADR 0006 row 5.
- Seat: Constructor (DE + analytics)

## Context

Medallion nouns appear in the 2026-06-09 architecture sketch (Second
Brain pack 01). That sketch is **mail, not a grain**. OntoLayer names
the legacy paid grain: `reporting.card_settlement_reconciliation`
keyed by `batch_id` + `currency`. The contract report relation is the
same (`contracts/types/01-card-settlement/reconciliation.yaml`).
`chargeback_flag` is dead; do not put it in Gold (Type 01 walk-through).

## Decision

Type 01 medallion grains tonight:

| Zone | Grain | Keys | Meaning |
|---|---|---|---|
| **Bronze** | one source-aligned movement | `batch_id` + `source_record_number` | Typed landing. Minimal reinterpretation. Privacy-safe columns only. |
| **Bronze control** | one control row per batch | `batch_id` | Source-owned declaration **and** independently computed totals, as the writer published them. |
| **Silver** | one conformed movement | `batch_id` + `source_record_number` | Same money as Bronze. Adds settled direction (`PURCHASE` / `REFUND`) and a parsed instant. Does not retotal. |
| **Gold** | one governed reconciliation | `batch_id` + `currency` | The number that may later be served. Same grain as legacy paid. |

Column semantics on Gold match the contract report:

- `source_*` — declaration (trailer), even when it is later a lie
- `staged_*` — Bronze totals
- `applied_*` — Silver totals
- `count_delta` / `amount_delta` — applied minus source
- `status` — `MATCHED` or `MISMATCHED`
- `reject_count` — constant `0` on an accepted landing batch (the
  lie never reaches Gold)

Accepted Type 01 happy path (`valid-minimal`): net **173.45**, two
records, `amount_delta` **0.00**, `MATCHED`.

A source-lie batch emits zero Parquet (ADR 0005). It has **no** Bronze
row, **no** Gold row. Classification lives on the terminal, not on a
repaired recon.

## What this is not

A star schema. A Type 02–05 grain. A FastAPI resource. Agents do not
invent dimensions to look busy.

## Consequences

- Golden-match compares Gold to the contract recon and to a live
  legacy observation **at this grain**.
- Silver that changes a cent is a failed layer, not a "clean-up."
- Unused dump columns (`chargeback_flag`) stay out of Gold.

## Evidence

- `docs/adrs/0006-later-nights-parked.md` row 5
- OntoLayer / `make ontology-ask` — paid table, grain, procedure
- `contracts/types/01-card-settlement/reconciliation.yaml`
- Second Brain pack 01 architecture (mail) + pack 03 walk-through
  (`chargeback_flag` dead)
