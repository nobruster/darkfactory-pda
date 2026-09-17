# ADR 0002 — Type 01 five-file package is the unit

- Status: Accepted (Structure). Binding after Consensus.
- Date: 2026-08-25
- Pass: 2 Structure
- Decider: Helena Dias (owner). Unsigned until `docs/consensus.md`.

## Context

The second plant must reach the same terminal outcomes as the live
line without importing Java or reading PL/pgSQL to invent an answer.
The steel thread is Type 01 card settlement (`CRD_SETTLE01`). Types
02–05 exist in the drop and are later slices. Type 06 is not in the
drop.

## Decision

The implementation unit for Type 01 is one **five-file package**:

`model → parser → schema → writer → handler`

That package owns Type 01 grammar, privacy, money, and terminal
outcome. Shared mechanics (checksum, quarantine, provenance) may live
beside it. Type-specific rules do not.

Inputs are the **same raw bytes and checksums** the live line already
reads — not Java internals, not sanitized CSV, not PostgreSQL.

Types 02–05 each get their own package later. Do not pre-seed empty
type folders.

## What this is not

How those five files are coded, which Python version they use, or a
port of `legacy/processor/src`.

## Consequences

- Pass 3 cuts ingest → landing against this unit.
- Pass 5 Task-Spec leaves bind to this unit, not to a lakehouse.
- A later type is a new package, not a widening of Type 01.

## Evidence

- `docs/tech-spec-type-01-card-settlement.md` R-3, R-6, R-8, §4
- `plans/modern.md` — `model.py` / `parser.py` / `schema.py` /
  `writer.py` / `handler.py`
- `spec/type-01-card-settlement/README.md` — do not open Java for the
  answer
- Second Brain pack 02 — five live types; Type 06 absent
