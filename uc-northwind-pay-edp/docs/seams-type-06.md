# Seams — Type 06 rides the existing three cuts

Pass 3 Decompose (Day 5 Dark Factory). Type `06` is a **new numbered
package**, not a new estate. Do not recut `docs/seams.md` (Night 2/3
historical). Do not copy `assurance` / `foundation` / `models`.

Papers: `docs/brd-type-06-merchant-chargeback.md`,
`docs/tech-spec-type-06-merchant-chargeback.md`, ADR 0014–0015.

## Vocabulary (unchanged)

Seam = handoff. Swimlane = one owning seat. Leg = ordered observable
capability. Java vs Python is not a seam.

## Seam list (Type 06 on the same cuts)

### 1. Ingest → landing

| | |
|---|---|
| **Seam** | Type 06 raw CSV → sanitized landing |
| **Swimlane** | Translator (SWE) — tonight the factory executes it |
| **Consumes** | Same raw bytes + checksum the live line already reads. Judge: `contracts/types/06-merchant-chargeback/` |
| **Produces** | Accepted: atomic Parquet + readiness manifest in `modern/landing/`. Refused: **zero Parquet**, stable code |
| **Write surface** | Type 06 five-file package (ADR 0014) and `modern/landing/` |
| **Must not write** | `legacy/`, `contracts/`, `gen/`, `infra/`, SFTP `csv/outgoing`, Gold |

**Legs:** sense (identity, checksum, replay) → claim (semicolon CSV,
Decimal HALF_UP, CNPJ mask, independent controls) → emit (`valid-minimal`
chargeback 1.01; `malformed` `INVALID_CSV_QUOTING` zero Parquet).

### 2. dlt → Gold

| | |
|---|---|
| **Seam** | Immutable Type 06 landing → governed Gold |
| **Swimlane** | Constructor (DE + analytics) |
| **Consumes** | `modern/landing/` Parquet already published. Does **not** re-parse CSV |
| **Produces** | Bronze → Silver → Gold at Type 06 grains (ADR 0015); golden-match attached |
| **Write surface** | dlt register-only for type `06`, dbt models tagged `type_06`, `evidence/modern/` |
| **Must not write** | Raw files, Type 06 parser grammar, frozen plant, the referee |

**Legs:** register → medallion → match (two questions, never netted).

### 3. Orchestrate + serve

Unchanged. Dagster is lineage, not a parser (ADR 0012). Skip the gold
hash if Dagster is not up. Do not stand it up to look busy.

## Refused cuts (tonight)

- Java vs Python
- CSV-as-input to dlt
- SFTP as modern destination
- Recutting Night 2 ingest Consensus or Night 3 lakehouse sign
- Dumping Types `02`–`05` modern packages
- Patching `legacy/` so Stage 6 goes green
- A lakehouse named as a new estate

## Handoff rule

One owner per seam. No sign on `docs/consensus-type-06.md` → no loop.
`legacy-miss` / `B202607230000504` stays virgin until the loop.
