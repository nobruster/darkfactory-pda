# ADR 0011 — Golden-match keys; two questions never netted

- Status: Accepted (Structure). Binding after `docs/consensus-lakehouse.md`.
- Date: 2026-08-26
- Pass: 2 Structure (Day 3 Constructor)
- Decider: Helena Dias (owner). Unparks ADR 0006 row 7.
- Seat: Constructor (DE + analytics)

## Context

`validation/golden-match/golden_match.py` already exists. It has no
tolerance member. The week **attaches** observations; it does not
rewrite the referee for slack. Paid grain is `batch_id` + `currency`.
Record grain for sanitized rows is `batch_id` + `source_record_number`
(physical record number).

A source lie makes "match legacy" and "match contract" differ. Netting
those into one green check hides the class.

## Decision

**Keys**

| Compare | Key | Artifact |
|---|---|---|
| Record | `batch_id` + `source_record_number` | landing / Bronze vs `expected-sanitized.csv` |
| Aggregate (paid) | `batch_id` + `currency` | Gold vs contract recon **and** vs legacy observation |
| Rejection | `batch_id` | terminal status + code; **zero** Parquet / Gold |

**Two questions, never netted**

1. Did modern match **legacy observation**?
2. Did modern match the **contract** / independent expectation?

**Six codes** (exactly one per difference):

| Code | Tonight |
|---|---|
| `CONFIRMED_SOURCE_DEFECT` | `DF-SOURCE-001` / trailer **173.44** vs rows **173.45**. Keep 173.44. No Gold. |
| `CONFIRMED_LEGACY_DEFECT` | **Friday.** Do not hunt it tonight. |
| `MODERN_DEFECT` | Fix the plant, not the expected. |
| `APPROVED_BEHAVIOR_CHANGE` | Named, signed, rare (e.g. independent rejection-code vocabulary). |
| `CONTRACT_AMBIGUITY` | Escalate. Do not code a guess. |
| `UNRESOLVED` | Not shippable. Not servable. Failed night. |

`valid-minimal`: both questions **yes**. `malformed`: classified
terminal, no invented artifacts. Unexplained financial difference
blocks Gold.

Do **not** edit `validation/golden-match/golden_match.py` to add a
tolerance.

## What this is not

A new referee. A serve API. A Type 05 rounding compare.

## Consequences

- Evidence packet lives under `evidence/modern/` (gitignored).
- A green dbt run with `UNRESOLVED` is a failed day.
- Constructor does not copy Java totals into Gold to go green.

## Evidence

- `docs/adrs/0006-later-nights-parked.md` row 7
- `validation/golden-match/golden_match.py` — two questions, six codes,
  no tolerance
- `plans/modern.md` Milestone 3
- `contracts/types/01-card-settlement/main/expected-reconciliation.yaml`
- Second Brain pack 08 + Marina 2026-07-14: keep their number, refuse
