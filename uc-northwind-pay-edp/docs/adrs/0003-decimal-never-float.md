# ADR 0003 — Decimal, never float

- Status: Accepted (Structure). Binding after Consensus.
- Date: 2026-08-25
- Pass: 2 Structure
- Decider: Helena Dias (owner). Unsigned until `docs/consensus.md`.

## Context

Type 01 money is signed overpunch, scale 2, currency BRL. The steel
thread happy path is net **173.45** on two records, `amount_delta`
**0.00**, status MATCHED. The source lie is a **one-cent** trailer
mismatch (173.44 vs 173.45). Binary floating point cannot hold those
cents as facts.

The contract tolerances are zero. Python’s default rounding is
`ROUND_HALF_EVEN`; Type 05 forbids that default. That fact is
recorded here so money never silently uses float or banker’s rounding
on Type 01 either.

## Decision

All financial amounts in the second plant are exact **decimal** values
at the contract scale. Never binary floating point (`float`, IEEE-754)
for money, controls, or reconciliation.

Type 01 scale is **2**. Comparisons are exact. There is no tolerance
band.

## What this is not

A rounding-mode library choice, a Type 05 `HALF_UP` implementation,
or a lakehouse numeric type. Type 05 rounding is Day 4.

## Consequences

- Landing Parquet money columns are decimal, not float.
- Independent sums of details are decimal. Trailer declared net is
  decimal. The lie is visible as 0.01, not as noise.
- A float in a money path is a failed gate, not a style note.

## Evidence

- `contracts/types/01-card-settlement/layout.yaml` — overpunch
  `decimal_scale: 2`; example `00000001234E` → `123.45`
- `contracts/types/01-card-settlement/reconciliation.yaml` —
  `amount_delta: "0.00"`
- `docs/tech-spec-type-01-card-settlement.md` R-1, R-3
- `plans/modern.md` — Decimal, never binary floating point
- OntoLayer / `make ontology-ask` — paid facts include
  `applied_net_amount` on `reporting.card_settlement_reconciliation`
