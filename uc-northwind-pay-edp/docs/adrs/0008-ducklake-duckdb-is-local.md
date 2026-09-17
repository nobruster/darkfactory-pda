# ADR 0008 — DuckLake / DuckDB is local

- Status: Accepted (Structure). Binding after `docs/consensus-lakehouse.md`.
- Date: 2026-08-26
- Pass: 2 Structure (Day 3 Constructor)
- Decider: Helena Dias (owner). Unparks ADR 0006 row 4.
- Seat: Constructor (DE + analytics)

## Context

The second plant must rebuild approved Gold from landing on a clean
local run (`plans/modern.md` Milestone 2). Intent forbade picking a
cloud warehouse at landing altitude. ADR 0006 parked catalog
placement until tonight.

PostgreSQL on this tree is the **legacy observation environment**.
Reading it to compute Gold would make the second plant a copy of the
first.

## Decision

**DuckLake / DuckDB is local.** The catalog and the database file live
under `modern/lakehouse/` in this working tree. They are rebuilt from
immutable landing Parquet. They are not a warehouse copy, not a
replica of `northwind_legacy`, and not a system of record.

- Path: `modern/lakehouse/ducklake/` (gitignored, disposable).
- Rebuild: register landing, then dbt. Delete the file and repeat —
  Gold must come back the same.
- Postgres, Java CSV, and `evidence/B…/reconciliation.json` remain
  **observation only**. They never feed a dbt model.

## What this is not

A cloud DuckLake, MotherDuck, or a production catalog. Serving and
Dagster stay parked (ADR 0006 rows 8–9).

## Consequences

- A missing DuckDB file is not data loss. Landing is the durable
  artifact.
- CI is still out of scope (ADR 0006 row 10).
- Constructor does not open a warehouse ticket to finish tonight.

## Evidence

- `docs/adrs/0006-later-nights-parked.md` row 4
- `plans/modern.md` — local DuckLake and DuckDB; legacy PostgreSQL is
  observation only
- `docs/CONTEXT.md` — paid lives on `reporting.card_settlement_reconciliation`
  as a **legacy** fact, not as a modern input
