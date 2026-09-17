# ADR 0013 — FastAPI / MCP serve only read-only approved Gold

- Status: Accepted (Structure). Binding after ingest and lakehouse signs.
- Date: 2026-08-27
- Pass: 2 Structure (Day 4 Orchestrator)
- Decider: Helena Dias (owner). Unparks ADR 0006 row 9.
- Seat: Orchestrator

## Context

ADR 0006 parked the first read-only FastAPI endpoint and MCP tools
until Day 4. Paid grain for Type 01 is `batch_id` + `currency`.
Unresolved golden-match is not Gold. Serving a lie, a stub, or
Postgres as if it were modern Gold would hide the class.

## Decision

**FastAPI and MCP are read-only over approved Gold.** They may expose
Type 01 `gold.gold_card_settlement_reconciliation` rows whose packet
is resolved with `unexplained_count` 0. They must not write landing,
must not parse raw, and must not serve `UNRESOLVED` or
`CONFIRMED_SOURCE_DEFECT` batches as paid.

What serving may do:

- GET approved Type 01 Gold at grain `batch_id` + `currency`
- MCP tools that read the same approved rows

What serving must not do:

- POST / mutate Gold, landing, or frozen trees
- read `reporting.card_settlement_reconciliation` to invent the number
- expose restricted raw PAN / CPF
- stand in for Dagster lineage (ADR 0012)

Absence of a FastAPI process is allowed. Do not create an empty
serving package to look busy.

## What this is not

A public API. A Type 06 serve. A CI surface (row 10 stays parked,
default **no**). A recut of ADR 0006.

## Consequences

- Unresolved Gold is not servable.
- ADR 0006 remains the park record.

## Evidence

- `docs/adrs/0006-later-nights-parked.md` row 9
- `docs/seams.md` seam 3 — read-only serve of approved Gold only
- `docs/adrs/0011-golden-match-keys-two-questions.md` — UNRESOLVED
  is not shippable
