# 04 - TED Transfer Settlement

Status: approved for implementation

This synthetic contract models successful interbank transfers and full returns.
It uses heterogeneous fixed-width records and exact CRLF transport semantics;
it does not claim production fidelity.

## Why this layout exists

The four record variants have different byte lengths. A transfer marked `RT`
requires one immediately following full-return record, while `OK` forbids one.
Amount sign and magnitude are separate fields. This exercises conditional
record structure, inherited movement context, signed controls, exact local-time
interpretation, and byte-level SFTP validation.

## Detection and dispatch

- Filename: `^NW_TED_SETTLEMENT_[0-9]{8}_B[0-9]{15}\.dat$`
- Header code: `TED_SETTLE04`
- Layout version: `001`
- Encoding: strict US-ASCII
- Line ending: exact CRLF after every record
- Record lengths excluding CRLF: `H=56`, `D=162`, `R=91`, `T=82`
- Sequence: `H (D | D R)+ T`, with the branch selected by `D.status_code`

Manifest identity, filename date and batch, header code and layout, trailer date
and batch, and raw bytes must agree. The `.dat` extension alone never selects
this parser.

## Processing route

1. Preserve and validate exact source bytes through SFTP.
2. Parse each transfer and attach a required full return immediately after `RT`.
3. Independently calculate transfer/return counts and gross, returned, and net
   values before trusting the trailer.
4. Validate CPF/CNPJ values, tokenize payer and beneficiary accounts with a
   dedicated fail-closed HMAC key, and mask tax IDs.
5. Convert São Paulo local timestamps to explicit-offset CSV timestamps.
6. Scan the complete CSV for every prohibited raw value before publication.
7. Load `staging.ted_transfer_movement`, apply the operational procedure, and
   reconcile source, staged, and applied controls with zero tolerance.

## Canonical outcomes

| Scenario | Batch | Expected result |
|---|---|---|
| `valid-minimal` | `B202607230000301` | accepted |
| `valid-boundary` | `B200002290000302` | accepted |
| `malformed` | `B202607230000303` | `INVALID_TRANSPORT` |
| `all-returned-zero-net` | `B202607230000304` | accepted |
| `DF-SOURCE-004` | `B202607230000305` | `SOURCE_CONTROL_NET_MISMATCH` |

`DF-SOURCE-004` is structurally valid and correctly declares counts, gross, and
returned values, but its trailer declares BRL `999.99` rather than the
independently computed BRL `1000.00`. It is quarantined before CSV publication
or PostgreSQL business mutation.

## Contract files

- `layout.yaml`: exact heterogeneous records, conditional linkage, timestamp
  semantics, validation order, bounds, and rejection codes.
- `privacy.yaml`: account tokenization, CPF/CNPJ masking, name protection,
  whole-output scanning, and privacy-safe failures.
- `csv.yaml`: exact normalized movement rows and inherited return context.
- `reconciliation.yaml`: complete source, staged, applied, delta, replay, and
  uniqueness semantics.
- `main/`: three accepted truth sets, one isolated transport rejection, and one
  source-only Dark Factory finding.
