# 01 - Card Settlement Detail

Status: approved for Type 01 implementation

This is a deliberately synthetic contract. It reproduces representative legacy risks without claiming to be an undocumented NorthWind Pay production layout.

## Business purpose

The file settles card purchases and refunds for merchants in BRL. Raw detail records contain a PAN and CPF in clear text. Java is the mandatory privacy boundary: it must tokenize the PAN, retain only its last four digits, mask the CPF, and publish sanitized CSV.

## Detection

- Filename pattern: `^NW_CARD_SETTLEMENT_[0-9]{8}_B[0-9]{15}\.dat$`
- Header type code: `CRD_SETTLE01`
- Layout version: `001`
- Encoding: ISO-8859-1
- Line ending: LF
- Blank lines: forbidden
- Record order: one header, one or more details, one trailer

The filename date, header date, trailer date, and date portion of the batch ID must agree.

## Approved first example

- Filename: `NW_CARD_SETTLEMENT_20260723_B202607230000001.dat`
- Batch ID: `B202607230000001`
- Detail records: 2
- Currency: BRL
- Source total: BRL 173.45
- Expected rejects: 0

## Processing route

1. Publish the raw file, checksum, and manifest to SFTP `raw/incoming/`.
2. Intake validates and claims the batch in `raw/processing/`.
3. Java parses and sanitizes the detail records.
4. Java publishes sanitized CSV to SFTP `csv/outgoing/`.
5. The loader copies CSV into `staging.card_settlement`.
6. `legacy.apply_card_settlement_batch(batch_id)` applies operational results.
7. `reporting.refresh_card_settlement_reconciliation(batch_id)` produces the reconciliation.

## Contract files

- `layout.yaml`: fixed-width records, overpunch rules, and `canonical_rejection_codes`.
- `privacy.yaml`: PAN and CPF transformations and prohibited outputs.
- `csv.yaml`: exact sanitized CSV schema and formatting.
- `reconciliation.yaml`: database route, controls, and zero-tolerance comparisons.
- `main/`: canonical valid, boundary, negative, malformed, sanitized, and reconciliation fixtures.

The canonical set also includes the `DF-SOURCE-001` source-system defect, its
expected batch-scoped finding, exact valid-boundary and negative-overpunch CSV
outputs and reconciliations, and the expected malformed rejection. The Dark
Factory fixture declares BRL 173.44 while its independently parsed details total
BRL 173.45; downstream code must detect and quarantine it without weakening the
contract.

## Step 1 gate

The gate passes when the raw fixtures in `main/` can be transformed manually into the exact sanitized values and reconciliation described by this package, without relying on unstated rules.
