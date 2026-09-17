# ADR 0010 — Rule split: parser owns privacy and Decimal; dbt does not retokenize

- Status: Accepted (Structure). Binding after `docs/consensus-lakehouse.md`.
- Date: 2026-08-26
- Pass: 2 Structure (Day 3 Constructor)
- Decider: Helena Dias (owner). Unparks ADR 0006 row 6.
- Privacy: Priya Shah — privacy finished before any landing row.
- Seat: Constructor (DE + analytics)

## Context

ADR 0003: money is Decimal, never float. ADR 0004: PAN token + last4
and CPF `*******` + last4 die at the parser, before Parquet. The
five-file package owns Type 01 grammar (ADR 0002). dbt is a later
zone. If dbt re-parses overpunch or HMAC-tokenizes, privacy has a
second death and the seam is wrong.

## Decision

**Rule allocation:**

| Rule | Owner | Must not |
|---|---|---|
| Transport, overpunch, Decimal scale 2 | Type 01 parser | dbt, dlt |
| PAN HMAC token + last4; CPF mask | Type 01 parser | dbt, dlt, Gold |
| Independent control sum vs trailer | Type 01 parser / writer | dbt "fixing" 173.44 |
| Source-aligned typing of landing columns | Bronze | re-parse `.dat` |
| Conformed direction / timestamps | Silver | change money |
| Governed recon at paid grain | Gold | read Postgres to invent the number |
| Two-question compare, six codes | `validation/golden-match/golden_match.py` | a dbt test that nets the questions |

dbt may **assert** that Bronze has no 16-digit PAN and that Silver
conserves Bronze totals. Those are gates, not new privacy transforms.

Missing tokenization key still fails closed at parse.

## What this is not

How HMAC is coded, a dbt package name, or a Type 05 `HALF_UP` rule.
Type 05 rounding stays Thursday.

## Consequences

- A dbt model that calls `tokenize` or `decode_overpunch` is a failed
  review, not a helper.
- Gold evidence must not contain clear PAN or CPF (Priya).
- Parser already refused the lie; dbt never sees those bytes.

## Evidence

- `docs/adrs/0003-decimal-never-float.md`
- `docs/adrs/0004-privacy-dies-at-the-parser.md`
- `docs/adrs/0006-later-nights-parked.md` row 6
- `contracts/types/01-card-settlement/privacy.yaml`
- Second Brain pack 01 privacy boundary: restricted values die at the
  modern parser **before any Parquet or Gold**
