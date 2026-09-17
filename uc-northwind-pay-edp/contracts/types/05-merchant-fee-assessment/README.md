# 05 - Merchant Fee Assessment

Status: approved for implementation

This synthetic contract assesses merchant fees from gross values and percentage
rates without claiming production fidelity.

## Why this layout exists

The source is strict UTF-8/NFC semicolon-delimited text with decimal commas,
`dd/MM/yyyy` dates, mandatory quoted descriptions, embedded delimiters and
quotes, and exact `HALF_UP` percentage rounding. It exercises a locale-aware
parser and arithmetic boundary that the other four contracts do not.

## Detection and transport

- Filename: `^NW_MERCHANT_FEES_[0-9]{8}_B[0-9]{15}\.csv$`
- Exact header is fixed in `layout.yaml`
- Encoding: strict UTF-8, NFC already normalized, no BOM
- Line ending: exact LF, including exactly one final LF
- Delimiter: semicolon; quote: double quote; escaped quote: doubled quote
- Detail rows: exactly ten fields, description quoted, other fields unquoted
- Bounds: 10,000 details, 512 bytes per physical line, 5,130,138 bytes per file

Manifest type, layout, filename date and batch, every row batch and business
date, raw hash, and source controls must agree. The `.csv` extension alone never
selects this parser.

## Processing route

1. Preserve strict source bytes and source-owned controls through SFTP.
2. Parse with a single-pass quote-aware lexer; reject multiline or ambiguous
   quoting instead of relying on permissive CSV defaults.
3. Validate canonical decimal-comma lexemes, CNPJ Mod-11 digits, identifiers,
   descriptions, dates, and uniqueness.
4. Calculate every fee as `gross × rate ÷ 100`, then round once to scale two
   with `HALF_UP`; binary floating point is forbidden.
5. Compare parsed and calculated aggregates with all source manifest controls.
6. Mask each CNPJ, produce deterministic normalized CSV, and scan the complete
   output for every raw CNPJ before publication.
7. Load `staging.merchant_fee_assessment`, apply both procedures, and reconcile
   source, staged, and applied count, gross, assessed, and calculated controls.

## Five canonical outcomes

| Scenario | Batch | Expected result |
|---|---|---|
| `valid-minimal` | `B202607230000401` | accepted |
| `valid-boundary` | `B200002290000402` | accepted |
| `malformed` | `B202607230000403` | `INVALID_CSV_QUOTING` |
| `rounding-half-up` | `B202607230000404` | accepted |
| `DF-SOURCE-005` | `B202607230000405` | `SOURCE_CONTROL_ASSESSED_FEE_MISMATCH` |

`DF-SOURCE-005` has a valid raw row whose assessed and independently calculated
fee are both BRL `1.00`. Only the source-owned manifest declares BRL `0.99`.
The hash-stable raw observation and independent downstream calculation isolate
the defect to the simulated source system of record. The batch is quarantined
before CSV publication or PostgreSQL business mutation; unrelated batches
continue.

## Contract files

- `layout.yaml`: strict transport, CSV grammar, locale decimals, dates,
  identifiers, CNPJ validation, source controls, bounds, and rejection order.
- `privacy.yaml`: CNPJ masking, validated description passthrough, privacy-safe
  failures, and whole-output scanning.
- `csv.yaml`: deterministic normalized CSV and database staging shape.
- `reconciliation.yaml`: source, stage, applied, delta, replay, and uniqueness
  semantics.
- `main/`: three accepted truth sets, one isolated quoting rejection, and one
  source-only Dark Factory finding.
