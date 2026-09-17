# Pack 01 — The estate (inbound)

Customer drop for the whole engagement. Type packs may contradict it.
Mail is not the contract. Do not invent Java.



---

## Source: `spec/estate/README.md`

# Estate — the customer, not a type

Shared inbound for the whole engagement. Type packs do not repeat the
kick-off. They may contradict it.

| Path | What it is |
|---|---|
| [`cover.md`](cover.md) | Who they are, what they want, what done means |
| [`meetings/`](meetings/) | Kick-off through the controls walk-through |
| [`mail/`](mail/) | The share-folder drop and the cent that will not die |
| [`policies/`](policies/) | Privacy, and how they talk about rounding |

Fictional NorthWind Pay / partner voices. Not a second `contracts/`.


---

## Source: `spec/estate/cover.md`

# Cover — NorthWind Pay settlement modernization

**From:** Helena Dias, Partner Integration  
**To:** the modernization team  
**Date:** 2026-06-24  
**Request:** rebuild the five live settlement files beside the current Java
line. Do not replace Java. Do not “fix” source totals.

NorthWind Pay already runs five file types through SFTP → Java 21 →
sanitized CSV → PostgreSQL. We need a second, independent
implementation that reads **this drop**, not the Java, and still
reaches the same terminal outcomes.

## What we are sending

- This estate folder (how we work, what we decided, what we argue about)
- One inbound pack per live type: `01` card, `02` instant payment,
  `03` payment slip, `04` TED, `05` merchant fees
- Raw samples, what sanitized output must look like, and the refusals
- One source-owned lie per type. Keep the declaration. Compute the
  truth. Refuse the batch.

We are **not** sending a parser, a lakehouse model, or permission to
edit the live line.

## Done means

For every accepted sample: sanitized rows and reconciliation match the
oracle, privacy holds, tolerances are zero.  
For every refusal: stable code, no CSV, no business rows, peers
continue.  
For every source lie: classified as a source defect, never repaired.

Type `06` is out of scope for this drop. If a sixth file appears, it
will arrive as its own pack.


---

## Source: `spec/estate/mail/2026-06-24-share-folder-drop.md`

# Fwd: NW Pay — settlement drop (please don’t lose the checksums)

**From:** Helena Dias `<helena.dias@partner.example>`  
**Date:** 2026-06-24 18:41 −03  
**To:** modernization@  

Hi —

Folder is up. Five types. Please start from `estate/cover.md` before you
open a `.dat`.

Rafael dumped the tables the way they come out of SSMS. If a column
looks unused, it probably is — ask him before you model it.

Checksums sit next to the raw files. If a sidecar is missing, stop.
We will not adjudicate a file we cannot hash.

Helena


---

## Source: `spec/estate/mail/2026-07-14-the-cent-that-will-not-die.md`

# Re: that trailer again

**From:** Marina Alves `<marina.alves@northwindpay.example>`  
**Date:** 2026-07-14 09:12 −03  
**To:** Helena Dias  
**Cc:** Rafael Costa

Helena —

I am not sending another “corrected” file.

Card settlement `B202607230000004` still declares **173.44**. Our
details add to **173.45**. Same shape on PIX, slips, TED, and the fee
file (that one lies about the assessed fee: **0.99** vs **1.00**).

If your new plant quietly writes 173.45 into the trailer we will
have nothing to show the source. Keep their number. Refuse the
batch. That is the whole point.

Marina


---

## Source: `spec/estate/meetings/2026-06-02-kick-off.md`

# NorthWind Pay — modernization kick-off

**Date:** 2026-06-02  
**Type:** Kick-off  
**Source:** Google Meet recording (internal)  
**Confidence:** 0.91

## Attendees

| Name | Role | Organization |
|---|---|---|
| Helena Dias | Partner Integration | requesting side |
| Marina Alves | Settlement Ops | NorthWind Pay |
| Rafael Costa | Legacy Platform | NorthWind Pay |
| Priya Shah | Privacy | NorthWind Pay |

## Executive Summary

Sixteen-week parallel modernization of the five live settlement files.
Java stays the privacy boundary on the current line. The new plant
reads this drop and the signed contracts. NorthWind keeps SFTP and
PCI-adjacent bytes inside its own roles.

## Key Decisions

| # | Decision | Owner | Status | Rationale |
|---|---|---|---|---|
| D1 | Java is not replaced | Rafael | Approved | Live line stays the oracle |
| D2 | Five types only in this drop | Helena | Approved | A sixth file is a later pack |
| D3 | Source totals are never rewritten | Marina | Approved | The lie is evidence |
| D4 | Privacy is finished before any CSV | Priya | Approved | Loader must not see a PAN |

## Action Items

- [x] Helena: drop the share folder (Due: 2026-06-24)
- [ ] Rafael: walk each type’s insert proc (Due: rolling)
- [ ] Priya: written privacy policy in the drop (Due: 2026-06-16)

## Open Questions

| # | Question | Owner | Priority |
|---|---|---|---|
| Q1 | Who owns Type 05 rounding language in ops email vs the fee schedule? | Marina | P1 |

## Implicit Signals

Rafael does not want the new team reading Java “to go faster.” Marina
is tired of explaining the same one-cent trailer.


---

## Source: `spec/estate/meetings/2026-06-09-file-decomposition.md`

# File decomposition — Java stays, you rebuild beside it

**Date:** 2026-06-09  
**Type:** Tech Sync  
**Confidence:** 0.88

## Attendees

Helena Dias · Rafael Costa · Marina Alves

## Executive Summary

The live path remains SFTP raw → Java sanitize → SFTP csv → COPY →
procedures → reporting. The modernization plant is a second reader of
the **same raw bytes**. It must not call Java and must not reuse the
stored procedures to invent an answer.

## Key Decisions

| # | Decision | Owner | Status |
|---|---|---|---|
| D1 | One handler per type, five files: model, parser, schema, writer, handler | Helena | Approved |
| D2 | Exact Decimal. No float money. | Rafael | Approved |
| D3 | Quarantine is batch-scoped | Marina | Approved |

## Architecture

```text
customer drop (this folder)
  → understand / decide
  → independent parser
  → sanitized Parquet
  → Bronze / Silver / Gold
  → compare to expected/ and to a live legacy observation
```

## Open Questions

| # | Question | Context |
|---|---|---|
| Q1 | Do unused columns on Rafael’s table dumps belong in Gold? | He said “most of those were for a report that died.” |


---

## Source: `spec/estate/meetings/2026-06-16-privacy-boundary.md`

# Privacy boundary

**Date:** 2026-06-16  
**Type:** Decision Meeting  
**Confidence:** 0.93

## Attendees

Priya Shah · Rafael Costa · Helena Dias

## Executive Summary

Restricted values die at Java on the live line and must die at the
modern parser before any Parquet or Gold. Tokens are HMAC, fail-closed.
Clear PAN, CPF, CNPJ, and account numbers are prohibited in CSV, logs,
evidence, and the warehouse.

## Key Decisions

| # | Decision | Status |
|---|---|---|
| D1 | Whole-output scan before publish | Approved |
| D2 | Type 01 PAN = token + last4; CPF = seven stars + last4 | Approved |
| D3 | Types 02–04 tokenize documents / accounts; Type 05 masks CNPJ | Approved |
| D4 | A privacy miss stalls the type. No waiver. | Approved |

## Implicit Signals

Priya will fail a demo that prints a “harmless” CPF in an exception.
Rafael asked whether the new plant can “just call our tokenizer.”
Denied — independence.


---

## Source: `spec/estate/meetings/2026-06-23-async-handoff.md`

# Async handoff — share folder is live

**Date:** 2026-06-23  
**Type:** Async Handoff  
**Source:** mail from Helena Dias  
**Confidence:** 0.86

## Attendees

*N/A — asynchronous. Helena asked for a walk-through the week of 2026-06-30.*

## Executive Summary

Five type folders plus this estate are in the share. Each type has a
vendor-ish layout, a table dump, at least one insert proc, samples, and
expected outs. Helena flagged Type 05 rounding and Type 01’s two procs
as “worth a live hour.”

## Action Items

- [ ] Modernization team: read cover + policies before any type
- [ ] Rafael: be on the 30 Jun card walk-through
- [ ] Marina: bring the trailer that still says 173.44

## Open Questions

| # | Question | Context |
|---|---|---|
| Q1 | Which insert proc is current on card settlement? | Two dates in the folder |
| Q2 | Is “normal rounding” in ops mail HALF_UP or banker’s? | Type 05 only |


---

## Source: `spec/estate/meetings/2026-07-07-controls-walkthrough.md`

# Controls walk-through

**Date:** 2026-07-07  
**Type:** Tech Sync  
**Confidence:** 0.84

## Attendees

Marina Alves · Rafael Costa · Helena Dias

## Executive Summary

Every type has source-owned trailer or manifest controls. The plant
must recompute them. A one-cent miss is a quarantine, not a patch.
Marina walked the five source-lie files. Rafael confirmed Java already
refuses all five on the live line.

## Key Decisions

| # | Decision | Status |
|---|---|---|
| D1 | Zero tolerance on count and money deltas | Approved |
| D2 | Source lie keeps the published declaration | Approved |
| D3 | Vocabulary in Gold follows the layout names, not ops slang | Proposed — Helena to write down |

## Implicit Signals

Marina still says “settlement total” for Type 01 trailer net.
Rafael says “assessed” and “calculated” for Type 05 and gets annoyed
when email says “the fee.” The room will trip on nouns unless someone
writes an ADR.


---

## Source: `spec/estate/policies/privacy.md`

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


---

## Source: `spec/estate/policies/rounding-and-controls.md`

# Rounding and controls

Ops note. Not a substitute for each type’s layout.

- Money is exact decimal. Two fractional digits unless a layout says
  otherwise.
- **Do not** use binary float. **Do not** use a language default
  rounding unless the type says so.
- Type 05 is percentage fees. The fee schedule (in that pack) is
  `HALF_UP` at the cent. Ops mail that says “normal rounding” is
  **not** a contract.
- Source-owned trailers and manifests are declarations. Independently
  recompute. A one-cent miss is quarantine.
- Tolerances are zero.

If two documents disagree, write down which one you believed. Do not
average them.
