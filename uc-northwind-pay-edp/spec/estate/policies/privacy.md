# NorthWind Pay — restricted data in settlement files

Internal policy, 2026-06-16. Applies to every type in this drop.

## May exist in the raw file

PAN, CPF, CNPJ, account numbers, holder names, free-text descriptions
that the source chose to send.

## Must not exist after sanitize

Those values in the clear, in any CSV, Parquet, log, evidence packet,
ticket, or warehouse table, unless a type policy names an **approved
transform** (token, last4, mask).

## Rules that do not waive

- Fail closed if a tokenization key is missing.
- Scan the entire candidate output before publish.
- A leak stalls the type. There is no “just this demo.”

See the 16 Jun privacy meeting. Type packs add the field-level detail.
