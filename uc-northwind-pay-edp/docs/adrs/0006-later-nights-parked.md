# ADR 0006 — Later-night questions parked (no lakehouse tonight)

- Status: Parked
- Date: 2026-08-25
- Pass: 2 Structure
- Decider: Helena Dias (owner). Revisit only after Consensus.

## Context

`plans/modern.md` lists ten questions with no binding answer on this
tree. Structure must close **landing facts** (ADRs 0001–0005) and
**park** the rest with an owner. A 2026-06-09 sync sketched a second
reader and a medallion path. That sketch is **mail**, not a stack
decision. Intent W-2 forbids picking a warehouse, transform tool, or
lakehouse at this altitude.

## Decision

Do **not** pick DuckDB, dlt, dbt, DuckLake, Dagster, or FastAPI in
Pass 2. The following stay parked. A parked row is not a silent
default.

| # | Question | Status | Owner | Opens |
|---|---|---|---|---|
| 1 | Python version, packaging tool, validation libraries | Parked | Helena Dias | after Consensus, before Milestone 1 |
| 2 | Canonical Parquet schema, compression, ordering, partitioning, metadata | Parked (destination closed in 0001) | Helena Dias | with Milestone 1 |
| 3 | Exact dlt loading or registration role | Parked | Helena Dias | Day 3 |
| 4 | DuckLake storage and catalog placement | Parked | Helena Dias | Day 3 |
| 5 | Bronze, Silver, and Gold grains and keys | Parked | Helena Dias | Day 3 |
| 6 | Rule allocation between ingestion and dbt | Parked | Helena Dias | Day 3 |
| 7 | Record and aggregate keys for golden-match | Parked | Helena Dias | Day 3 |
| 8 | Dagster asset, partition, retry, backfill | Parked | Helena Dias | Day 4 |
| 9 | First read-only FastAPI endpoint and MCP tools | Parked | Helena Dias | Day 4 |
| 10 | Whether any later CI surface is in scope | Parked; default remains **no** | Helena Dias | not this week |

Also parked (from Intent, not a stack):

- **Trailer noun** — layout `net amount` vs ops `settlement total`.
  Owner: Marina Alves. Judge remains `contracts/`. Does not block
  landing.
- **Which night the first write lands on disk** — after Consensus;
  not this Structure beat. Owner: Helena Dias.

## What this is not

A preference for Parquet / Bronze / Silver / Gold as a technology
choice. Medallion nouns in mail do not authorize a lakehouse ADR.

## Consequences

- Decompose (Pass 3) cuts **ingest → landing** only.
- Day 3 may unpark rows 3–7. Day 4 may unpark rows 8–9.
- Copying last run’s stack ADRs out of git history is forbidden.

## Evidence

- `docs/tech-spec-type-01-card-settlement.md` W-2, §5
- `plans/modern.md` — Design decisions, questions 1–10
- Second Brain pack 01 / cover.md — not sending a lakehouse model
- `docs/README.md` — rows 8–9 / orchestrate + remaining types are Day 4; landing Parquet is Days 2–3
