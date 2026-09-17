# ADR 0004 — Privacy dies at the parser

- Status: Accepted (Structure). Binding after Consensus.
- Date: 2026-08-25
- Pass: 2 Structure
- Decider: Helena Dias (owner). Unsigned until `docs/consensus.md`.
- Privacy: Priya Shah — privacy finished before any landing row.

## Context

Type 01 raw detail records carry a PAN and a CPF in clear text. On
the live line, Java is the mandatory privacy boundary: tokenize PAN,
keep last4, mask CPF, then publish sanitized CSV. The second plant
must not leak those raw values into landing, logs, evidence, or any
later zone.

The judge is `contracts/types/01-card-settlement/privacy.yaml`, not
inbound policy prose and not Java source.

## Decision

**Privacy dies at the parser.** Clear PAN and CPF do not leave the
parse boundary. Contract transformations apply **before** any
Parquet publication:

| Field | Allowed after parse | Never in landing, logs, evidence, or later zones |
|---|---|---|
| PAN | HMAC token `tok_` + 24 hex; last 4 digits | raw 16 digits |
| CPF | `*******` + last 4 digits | raw 11 digits |

Missing tokenization key fails closed. Evidence may store the raw
SHA-256, never the raw line.

Legacy Java remains the live privacy boundary for CSV. The second
plant does not import that Java to obtain tokens.

## What this is not

How to implement HMAC, where to store the key, or a copy of the Java
tokenizer.

## Consequences

- Schema and writer see only contract-approved fields.
- A landing file that contains a PAN or CPF is a failed batch, not a
  warning.
- Second Brain may teach tokenize / last4 / mask. It does not contain
  the Java parser.

## Evidence

- `contracts/types/01-card-settlement/privacy.yaml`
- `contracts/types/01-card-settlement/README.md` — Java is the live
  privacy boundary
- `docs/tech-spec-type-01-card-settlement.md` R-6, §4
- Second Brain packs 01 and 03 — privacy policy and layout field notes
- `plans/modern.md` — transform prohibited values before Parquet
