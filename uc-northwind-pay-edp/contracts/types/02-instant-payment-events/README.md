# 02 - Instant Payment Events

Status: approved for Type 02 implementation

This synthetic contract models PIX-like instant-payment settlement events without claiming an undocumented production layout.

## Why this layout exists

Unlike 01, this type is not positional. It is a UTF-8 pipe-delimited event file with escaped delimiters, explicit timezone offsets, variable document types, and conditional return fields. It forces the processor to select a different parser strategy.

## Detection

- Filename pattern: `^NW_INSTANT_PAYMENT_[0-9]{8}_B[0-9]{15}\.txt$`
- Header type code: `PIX_EVENTS01`
- Layout version: `001`
- Encoding: UTF-8
- Line ending: LF
- Final newline: exactly one LF
- Record order: one header, one or more events, one trailer
- Parser selection: manifest type, filename, header code, layout version, date,
  and batch ID must agree; the `.txt` extension is not sufficient.

## Processing route

1. Publish the raw file through the local SFTP raw zone.
2. Parse and validate the pipe-delimited event records.
3. Tokenize payer and payee documents and retain only masked forms.
4. Convert credit/debit direction into a signed exact amount.
5. Publish sanitized CSV through SFTP.
6. Load `staging.instant_payment_event`.
7. Run `legacy.apply_instant_payment_batch(batch_id)`.
8. Run `reporting.refresh_instant_payment_reconciliation(batch_id)`.

The database transaction is not successful until source, staging, and
operational count, credit, debit, net, and returned-event controls all match
the approved oracle.

## Five canonical outcomes

| Scenario | Batch | Purpose | Expected result |
|---|---|---|---|
| `valid-minimal` | `B202607230000101` | Credit plus returned debit, CPF/CNPJ role variants, and escaped pipe. | Exact CSV and `MATCHED` reconciliation. |
| `valid-boundary` | `B202402290000102` | Leap day, UTC `Z`, and minimum positive BRL amount. | Exact CSV and `MATCHED` reconciliation. |
| `escaped-content` | `B202607230000104` | NFC UTF-8, comma, escaped pipe, and escaped backslash. | Exact quoted CSV and `MATCHED` reconciliation. |
| `malformed` | `B202607230000103` | One unescaped pipe creates a 14-field event. | `INVALID_FIELD_COUNT`; affected batch only is quarantined. |
| `DF-SOURCE-002` | `B202607230000105` | Source trailer declares BRL 173.44 while its events compute BRL 173.45. | `SOURCE_CONTROL_NET_MISMATCH`; no CSV or business mutation. |

The fifth case is the Dark Factory proof. The observed raw delivery is the
system-of-record output, while the executable contract is the source of
correctness. Java and a later read-only PostgreSQL diagnostic must independently
recompute BRL `173.45`; that evidence isolates the defect to the simulated source
without silently weakening the contract.

## Contract files

- `layout.yaml`: delimiter, escaping, record variants, and conditional fields.
- `privacy.yaml`: CPF/CNPJ tokenization and masking.
- `csv.yaml`: sanitized event schema.
- `reconciliation.yaml`: credit, debit, net, and status controls.
- `main/`: canonical raw inputs, exact sanitized CSV/reconciliation oracles, and
  safe rejection/finding oracles for all five outcomes.

## Safety decisions fixed by this contract

- The parser is a single-pass escape-aware lexer. Only `\|` and `\\` are
  legal, and decoding happens exactly once.
- UTF-8 decoding is strict; BOM, CR, blank records, missing final LF, unknown
  escapes, and trailing backslashes are rejected. Source files are limited to
  10,000 events, 512 bytes per physical record, and 5,200,000 bytes in total.
- Timestamps use whole seconds with an explicit offset, preserve their
  validated source spelling, and must land on the header date in
  `America/Sao_Paulo`.
- Money uses exact decimal arithmetic. Event amounts are strictly positive in
  the source; direction applies the CSV sign exactly once.
- CPF/CNPJ values must pass length and Mod-11 validation. Their raw digits, the
  decoded description, tokens, and masks never enter logs or evidence.
- Description is non-empty NFC text of at most 80 Unicode code points and
  rejects controls, bidi controls, spreadsheet-formula prefixes, and
  document/PAN-like digit runs.
- A failure publishes no partial CSV and cannot mutate Type 02 business rows.
