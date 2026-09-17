# ADR 0007 — dlt registers landing only

- Status: Accepted (Structure). Binding after `docs/consensus-lakehouse.md`.
- Date: 2026-08-26
- Pass: 2 Structure (Day 3 Constructor)
- Decider: Helena Dias (owner). Unparks ADR 0006 row 3.
- Seat: Constructor (DE + analytics)

## Context

Landing Parquet is already the first write of the second plant (ADR 0001).
Privacy and Decimal already died at the parser (ADR 0003, 0004). A
2026-06-09 sync sketched a second reader and a medallion path; that
sketch is mail, not a stack. ADR 0006 parked the exact dlt role until
tonight.

If dlt parses raw bytes, tokenizes PAN, or computes a net, Constructor
owns money and grammar that Translator already closed. That is a
wrong seam.

## Decision

**dlt registers `modern/landing/` Parquet.** It does not re-parse. It
does not own money. It does not own privacy. It does not invent a
column the writer did not publish.

What dlt may do:

- discover published Type 01 Parquet under `modern/landing/`
- load those files into the local DuckLake / DuckDB catalog
- carry the writer's per-batch control manifest as its own table so
  Gold can compare a source-owned declaration without re-deriving it

What dlt must not do:

- read SFTP `raw/incoming` or any `.dat`
- tokenize, mask, or scan for PAN / CPF
- sum details into a net
- "fix" trailer **173.44**
- write Gold

A batch that emitted **zero** Parquet (ADR 0005) is not registered.
Absence is the terminal, not an empty table that looks like Gold.

## What this is not

A dlt version pin, a pipeline name, or a cloud loader. How to call
`pipeline.run` is implementation.

## Consequences

- Seam 2 starts at immutable landing, never at raw bytes.
- Gold cannot obtain a net that landing did not already compute.
- dlt state lives in disposable local runtime, not in `legacy/`.

## Evidence

- `docs/adrs/0006-later-nights-parked.md` row 3
- `docs/seams.md` seam 2 consumes landing; must not re-parse
- `plans/modern.md` Milestone 2 — "registers landing; does not re-parse"
- Second Brain pack 01 architecture: parser → sanitized Parquet →
  Bronze / Silver / Gold. The notebook does **not** contain the word
  dlt; this ADR is the decision, not inbound mail.
