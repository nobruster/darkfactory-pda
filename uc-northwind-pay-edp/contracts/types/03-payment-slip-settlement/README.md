# 03 - Payment Slip Settlement

Status: approved for implementation

This synthetic contract models payment-slip settlement using a CNAB-inspired
multi-segment format. It does not claim production fidelity.

## Why this layout exists

Every physical record is exactly 240 US-ASCII bytes followed by CRLF. One
logical settlement is assembled from two adjacent records: financial segment
`A` and beneficiary segment `B`. Lots add a second control level. Together,
these rules exercise byte-preserving SFTP transport, visible filler validation,
record pairing, privacy transformation, and independent control arithmetic.

## Detection and dispatch

- Filename: `^NW_PAYMENT_SLIP_[0-9]{8}_B[0-9]{15}\.rem$`
- Header type code: `PAYSLIPSET03`
- Layout version: `001`
- Encoding: strict US-ASCII
- Record length: 240 bytes excluding CRLF
- Sequence: `H (L (A B)+ T)+ Z`

The manifest type, filename date and batch, header code and layout, every
embedded batch ID, and the header sequence must agree. The `.rem` extension
alone never selects this parser.

## Processing route

1. Preserve and validate the exact source bytes published through SFTP.
2. Validate file, lot, field, filler, document, sequence, and pairing rules in
   the declared rejection order.
3. Independently calculate logical count, face, discount, fee, and net controls.
4. Join each adjacent `A` and `B` pair into one logical settlement.
5. Tokenize payment reference, beneficiary, and bank-account data using three
   separate fail-closed HMAC keys; mask validated CPF/CNPJ values.
6. Scan the complete CSV for every prohibited raw value before publication.
7. Load `staging.payment_slip_settlement`, apply the operational procedure, and
   reconcile source, staged, and applied controls with zero tolerance.

## Canonical outcomes

| Scenario | Batch | Expected result |
|---|---|---|
| `valid-minimal` | `B202607230000201` | accepted |
| `valid-boundary` | `B202402290000202` | accepted |
| `malformed` | `B202607230000203` | `SEGMENT_PAIR_MISMATCH` |
| `multi-lot` | `B202607230000204` | accepted |
| `DF-SOURCE-003` | `B202607230000205` | `SOURCE_CONTROL_NET_MISMATCH` |

`DF-SOURCE-003` is structurally and arithmetically valid through every lot
trailer, but its file trailer declares BRL `198.49` instead of the independently
computed BRL `198.50`. The affected batch is quarantined before CSV publication
or PostgreSQL business mutation.

## Contract files

- `layout.yaml`: exact transport, six record variants, field constraints,
  pairing, bounds, and rejection precedence.
- `privacy.yaml`: three independent token domains, CPF/CNPJ masking, whole
  output scanning, and privacy-safe failures.
- `csv.yaml`: exact normalized row generated from each complete pair.
- `reconciliation.yaml`: complete source, staged, applied, delta, replay, and
  uniqueness semantics.
- `main/`: three accepted truth sets, one isolated structural rejection, and
  one source-only Dark Factory finding.
