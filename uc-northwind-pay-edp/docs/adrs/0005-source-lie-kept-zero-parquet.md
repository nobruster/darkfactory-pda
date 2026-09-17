# ADR 0005 — Source lie keeps 173.44; refuse; zero Parquet

- Status: Accepted (Structure). Binding after Consensus.
- Date: 2026-08-25
- Pass: 2 Structure
- Decider: Helena Dias (owner). Unsigned until `docs/consensus.md`.
- Ops: Marina Alves — do not fix totals.

## Context

The source can lie. Type 01 `df-source-001` / batch `B202607230000004`
declares trailer net **173.44** (layout bytes 16–30, field
`net_amount_brl`) while independently summed details are **173.45**.
Finding: `SOURCE_CONTROL_TOTAL_MISMATCH`.

Marina, 2026-07-14: she will not send a “corrected” file. If the new
plant writes 173.45 into the trailer, ops has nothing to show the
source. Keep their number. Refuse the batch.

Inbound may say “settlement total.” The layout and the contract say
**net amount**. The contract wins (R-5). The noun is parked, not
patched (ADR 0006).

## Decision

1. **Keep the declaration.** Trailer 173.44 stays 173.44. The second
   plant must not write 173.45 into the trailer or any control field.
2. **Refuse the batch.** Terminal is quarantined,
   `SOURCE_CONTROL_TOTAL_MISMATCH`, scope = that one batch, peers
   continue. Not a crash.
3. **Zero Parquet.** No landing file, no sanitized rows, no business
   mutation for that batch. Refusal is an expected terminal, not
   missing data.

Happy path remains `valid-minimal`: net 173.45, two records, MATCHED,
`amount_delta` 0.00, privacy holds.

## What this is not

How the parser detects the mismatch, or a repair job that “corrects”
the source.

## Consequences

- Evidence for a refused lie records declared vs computed amounts and
  the finding code. It does not invent Parquet, dlt, or Gold artifacts.
- The same **shape** of lie on types 02–05 is later (R-9), not this
  steel thread.

## Evidence

- `docs/tech-spec-type-01-card-settlement.md` R-1, R-2, R-4, W-4
- `contracts/types/01-card-settlement/README.md` — DF-SOURCE-001
- `spec/type-01-card-settlement/README.md` — declared 173.44, computed
  173.45
- Second Brain pack 08 and Marina mail 2026-07-14
- `plans/modern.md` — no Parquet for rejected source or malformed batches
