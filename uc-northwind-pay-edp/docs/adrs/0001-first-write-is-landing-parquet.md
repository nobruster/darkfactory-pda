# ADR 0001 — First write is landing Parquet, not SFTP

- Status: Accepted (Structure). Binding after Consensus.
- Date: 2026-08-25
- Pass: 2 Structure
- Decider: Helena Dias (owner). Unsigned until `docs/consensus.md`.

## Context

Two plants read the same SFTP raw drop. Legacy’s first write is already
CSV on `csv/outgoing`. Intent (R-7) requires the second plant’s first
write to be later and **not SFTP**. Mixing those destinations is a
failed day.

## Decision

The second plant’s first artifact is **sanitized Parquet in
`modern/landing/`**, plus a readiness manifest, published atomically.

It is **not** an SFTP drop. It is **not** a rewrite of `csv/outgoing`.
It is **not** a lakehouse table. dlt, DuckLake, dbt, and serving are
not this decision (see ADR 0006).

The write happens **after Consensus**. This ADR does not create
`modern/`.

## What this is not

How to serialize Parquet, which library to use, or how to layout
directories beyond the named zone `modern/landing/`.

## Consequences

- Accepted Type 01 batches may emit landing Parquet after the sign.
- Refused and source-lie batches emit **zero** Parquet (ADR 0005).
- Golden-match later compares landing (and Gold) to `contracts/` and
  to legacy observation. Legacy CSV remains comparison evidence only.

## Evidence

- `docs/tech-spec-type-01-card-settlement.md` R-7, §4
- `docs/README.md` — first write after the sign is landing Parquet
- `plans/modern.md` — landing zone is not SFTP
- Second Brain pack 01 — Helena is not sending a lakehouse; rebuild
  beside Java
