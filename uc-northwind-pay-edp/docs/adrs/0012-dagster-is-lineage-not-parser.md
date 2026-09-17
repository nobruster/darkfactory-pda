# ADR 0012 — Dagster is lineage, not a parser

- Status: Accepted (Structure). Binding after ingest and lakehouse signs.
- Date: 2026-08-27
- Pass: 2 Structure (Day 4 Orchestrator)
- Decider: Helena Dias (owner). Unparks ADR 0006 row 8.
- Seat: Orchestrator

## Context

ADR 0006 parked Dagster asset, partition, retry, and backfill until
Day 4. Type 01 Gold is closed: landing Parquet, local DuckLake, Bronze
→ Silver → Gold, golden-match attached. Seam 3 consumes approved Gold.
If Dagster parses Type 01 `.dat`, the orchestrator owns grammar that
Translator already closed.

## Decision

**Dagster is lineage on closed Type 01.** It may declare assets,
partitions, retry, and backfill so a clean local replay rebuilds Gold
from immutable landing. Parsing does not move into the orchestrator.

What Dagster may do:

- materialize already-authored Type 01 emit → register → B/S/G → match
- partition by `batch_id`
- retry a failed materialize without changing money rules
- backfill from `modern/landing/` (not from SFTP raw)

What Dagster must not do:

- read SFTP `raw/incoming` or any `.dat` / `.txt` / `.rem` / `.csv` source
- tokenize, mask, decode overpunch, or round `HALF_UP`
- invent Gold when landing emitted zero Parquet
- rewrite `validation/golden-match/golden_match.py`

A missing Dagster install is not a failed leaf. Skip the Gold-hash
compare if Dagster is not up. Do not stand up Dagster to look busy.

## What this is not

A Type 02–05 parser. A FastAPI. A CI surface (ADR 0006 row 10 stays
parked). A recut of ADR 0001–0011. ADR 0006 remains the park record.

## Consequences

- Orchestrator leaf `T-20260827-orchestrate-type-01` binds here.
- Translator still owns ingest → landing. Constructor still owns
  dlt → Gold.
- Types 02–05 do not wait on Dagster to be tasked.

## Evidence

- `docs/adrs/0006-later-nights-parked.md` row 8
- `docs/seams.md` seam 3 — orchestrator does not parse Type 01
- `plans/modern.md` — Dagster is lineage, not the parser
