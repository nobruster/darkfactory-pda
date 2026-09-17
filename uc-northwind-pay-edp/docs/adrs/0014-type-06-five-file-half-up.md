# ADR 0014 — Type 06 is a numbered five-file package; HALF_UP at the parser

- Status: Accepted (Structure). Binding after `docs/consensus-type-06.md`.
- Date: 2026-08-28
- Pass: 2 Structure (Day 5 Dark Factory)
- Decider: Helena Dias (owner). Unsigned until `docs/consensus-type-06.md`.
- Seat: Dark Factory

## Context

Type 06 arrived tonight as a sealed CSV pack. ADR 0002 defined the
five-file unit for Type 01. ADR 0003 forbids binary float and records
that Python’s default is `ROUND_HALF_EVEN`. Type 05 taught `HALF_UP`
as a Thursday pill; Type 06 is a **new numbered package**, not a copy
of that plant. Inbound mail says “same commercial rounding as merchant
fees” and “not normal language.” The judge is
`contracts/types/06-merchant-chargeback/layout.yaml`:
`rounding_mode: HALF_UP`.

`docs/seams.md` listed Type 06 as a refused cut because it was not in
that drop. That refusal is historical. Tonight the kit is in `spec/`.

## Decision

Type 06 implementation unit:

`model → parser → schema → writer → handler`

under `modern/ingestion/src/northwind_pay/types/06-merchant-chargeback/`.

| Rule | Owner |
|---|---|
| Semicolon CSV, quoted description, decimal comma, `dd/MM/yyyy` | parser |
| `original × rate ÷ 100`, Decimal, **HALF_UP** once to scale 2 | parser |
| CNPJ Mod11 then `**********<last4>` | parser |
| Independent calculated amount vs declared chargeback | parser / writer |
| Deterministic Parquet + manifest last | writer / common publish |
| Compose one batch | handler |

First write remains `modern/landing/` Parquet (ADR 0001). Not SFTP.
Not a Java import. Not a widening of the Type 01 package. Not a dump
of Types `02`–`05`.

Worked example the contract already names: `67.00 × 1.500 ÷ 100 =
1.005` → HALF_UP **1.01**. A modern plant that emits `1.00` is
`MODERN_DEFECT`.

## What this is not

A Type 05 folder copy. A new estate. A rounding-mode library debate.
Permission to rewrite `expected/` so `HALF_EVEN` goes green.

## Consequences

- Pass 3 rides the existing three seams.
- Pass 5 ingest leaf binds to this unit.
- Empty `06-merchant-chargeback/` is forbidden. Five files or nothing.

## Evidence

- `docs/brd-type-06-merchant-chargeback.md`
- `docs/tech-spec-type-06-merchant-chargeback.md` R-1, R-4
- `contracts/types/06-merchant-chargeback/layout.yaml`
- ADR 0001, 0002, 0003, 0004
