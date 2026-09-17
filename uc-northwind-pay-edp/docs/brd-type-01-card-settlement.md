# BRD — Type 01 card settlement (Helena’s drop)

> Pass 0 Capture draft. Owner’s voice. No product code. No stack.
> Facts from the Second Brain (packs 00, 01, 02, 03, 08) and `spec/` inbound.
> This is mail compiled into a brief. It is not `contracts/`.

## 1. Who asked, and what is out of scope

Helena Dias, Partner Integration, asked on 2026-06-24 to rebuild the five
live settlement files **beside** the current Java line. Do not replace
Java. Do not “fix” source totals.

*(Second Brain pack 01 / `spec/estate/cover.md`; kick-off
`spec/estate/meetings/2026-06-02-kick-off.md` — D1 Java is not replaced.)*

**Out of scope for this drop**

- Type `06`. It is not in the share. If a sixth file appears, it arrives
  as its own pack. *(cover.md; `spec/README.md`; Second Brain pack 00,
  02.)*
- A parser, a lakehouse model, or permission to edit the live line.
  Helena is not sending those. *(cover.md.)*
- Rewriting source totals so a trailer matches the rows. Marina: keep
  their number. *(cover.md; `spec/estate/mail/2026-07-14-the-cent-that-will-not-die.md`.)*

Helena is the decider on this brief.

## 2. What lands

Overnight files, not an API. A batch lands on SFTP. Type `01` card
settlement is **tonight’s steel thread**. Types `02` instant payment
(PIX), `03` payment slip, `04` TED, and `05` merchant fees **exist in
this drop** so later nights can ask them. They are not tonight’s build.

*(Second Brain packs 00 and 02; `spec/README.md`; cover.md five types;
`spec/type-01-card-settlement/README.md`.)*

Type `01` arrives as `CRD_SETTLE01`, `.dat`, ISO-8859-1 fixed width,
COBOL overpunch. Filename shape
`NW_CARD_SETTLEMENT_YYYYMMDD_B###############.dat`. One header, details,
one trailer. *(Second Brain pack 03 /
`spec/type-01-card-settlement/inbound/card-settlement-layout-rev3.md`.)*

Five Type `01` samples sit next to checksums. If a sidecar is missing,
stop. *(Helena mail `spec/estate/mail/2026-06-24-share-folder-drop.md`;
type pack `samples/`.)*

| Sample | Role | What the pack already says |
|---|---|---|
| `valid-minimal` | Happy | accepted · net `173.45` (measured — `spec/type-01-card-settlement/README.md`) |
| `valid-boundary` | Boundary | accepted |
| `negative-overpunch` | Type edge | accepted · net `-12.34` (measured — same README) |
| `malformed` | Grammar | `INVALID_OVERPUNCH` |
| `df-source-001` | Source lie | declared `173.44` · computed `173.45` (measured — same README) |

The first write of the **second** plant is **later**. It is not tonight.
Do not pick a stack. Helena did not send a lakehouse. The 2026-06-09
sync sketched a second reader of the same raw bytes; that sketch is
mail, not a technology decision for Capture.

*(cover.md “not sending a parser, a lakehouse model”;
`spec/estate/meetings/2026-06-09-file-decomposition.md`; `spec/README.md`
Day 1: no parser, no `modern/`.)*

## 3. What “done” means

Done is three terminal outcomes, not a green parser. Helena:

- **Accepted sample** — sanitized rows and reconciliation match the
  oracle, privacy holds, tolerances are zero.
- **Refusal** — stable code, no CSV, no business rows, peers continue.
- **Source lie** — classified as a source defect, **never repaired**.
  Keep the declaration. Compute the truth. Refuse the batch.

*(cover.md “Done means”; Second Brain pack 01.)*

Type `01` happy path the drop already names: `valid-minimal`, net
`173.45` (measured — type README; inbound expected recon
`spec/type-01-card-settlement/expected/valid-minimal.reconciliation.yaml`
status `MATCHED`, `amount_delta` `0.00`).

Marina: quarantine is batch-scoped. One bad batch does not stop the
line. *(kick-off D3; type expected finding `quarantine_scope: batch`.)*

## 4. The lie

The source **can** lie. Keep the declaration. Refuse the batch. Do not
patch it.

Type `01` steel thread of the lie: trailer field (layout bytes 16–30,
**net amount** in the PDF; Marina still says **settlement total**)
declares **173.44** while the details add to **173.45**.

- Declared `173.44` (measured — Marina mail 2026-07-14; type README
  `df-source-001`; expected finding
  `spec/type-01-card-settlement/expected/df-source-001.finding.yaml`
  `declared_net_amount: "173.44"`).
- Computed `173.45` (measured — same three sources
  `computed_net_amount: "173.45"`).
- Finding the drop already names: `SOURCE_CONTROL_TOTAL_MISMATCH`.
- Batch Marina named: `B202607230000004` (measured — mail 2026-07-14;
  expected finding `batch_id: B202607230000004`).
- No CSV. No business mutation. Peers continue.

Marina, 2026-07-14: she is not sending another “corrected” file. If the
new plant quietly writes `173.45` into the trailer, ops has nothing to
show the source. Keep their number. Refuse the batch. That is the whole
point.

*(Second Brain pack 08; `spec/estate/mail/2026-07-14-the-cent-that-will-not-die.md`;
`spec/type-01-card-settlement/inbound/2026-07-02-settlement-total.md`;
layout rev 3 trailer 16–30.)*

Same **shape** on the other live types in this drop (keep their number,
refuse):

| Type | Declares | Rows add to |
|---|---|---|
| `02` PIX | **173.44** | **173.45** |
| `03` slips | **198.49** | **198.50** |
| `04` TED | **999.99** | **1000.00** |
| `05` fees | **0.99** assessed | **1.00** |

(measured — Second Brain pack 08 / Marina mail.) Those types exist; they
are not tonight’s steel thread.

Do not rewrite `173.44` to `173.45`.

## 5. Inbound vs judge

`spec/` is how the customer **arrives** — mail, meetings, policies,
layouts, samples. Messy on purpose. Contradictions are allowed in
inbound prose. `cover.md` is mail. It is not the contract.

`contracts/` is the **judge** once installed — signed layouts and
oracles. When inbound and the contract disagree, inbound does **not**
outrank the contract. We do not “fix” `contracts/` because a meeting
used the wrong noun (Marina’s “settlement total” vs layout “net
amount”).

*( `spec/README.md` “This folder vs the brain vs contracts/”; Second
Brain pack 00: mail is not the judge; pack 03 walk-through 2026-06-30
open question on the noun.)*

The Second Brain is queryable memory of inbound prose. It does not
contain `contracts/` or Java. Capture used it for owner voice and the
lie in prose. The judge remains `contracts/`.

## 6. What we will not do tonight

Tonight is Pass 0 Capture. Human-led. No product code.

We will not:

- Pick DuckDB, dbt, a lakehouse, Parquet, or any stack.
- Write ADRs (Pass 2).
- Cut seams (Pass 3).
- Run Consensus, Task-Spec, Bind, or the Loop (Passes 4–8).
- Create `modern/`.
- Open Type `06`.
- Repair `173.44`.
- Replace Java or edit the live line.
- Treat this unsigned draft as a license to code.

The first write of the second plant is **later**, and it is **not
SFTP**. Do not pick a stack.

---

## Executive summary

Helena asked to rebuild five settlement files beside Java, not instead
of it. Tonight’s steel thread is Type 01; 02–05 exist; 06 is not in the
drop. Done is accepted, refused, or a kept source lie. Trailer 173.44
vs rows 173.45 — keep the lie. First modern write is later; no stack.

## Problem

Partners still fire overnight files at a live Java line and then argue
about a one-cent trailer. Helena’s 2026-06-24 drop (measured) asks for a
second plant that reads **this folder**, not the Java, and still reaches
the same terminal outcomes. Marina will not send another “corrected”
file: card settlement batch `B202607230000004` (measured) still
declares **173.44** (measured) while details add to **173.45**
(measured). If a new plant quietly writes 173.45 (measured) into the
trailer, ops has nothing to show the source.

The pain is not “Java is old.” The pain is a source-owned lie that must
stay visible, plus a drop that is mail rather than a parser.
Type 01 (measured) is the steel thread; types 02–05 (measured) share
the same one-cent shape in this drop. Type 06 (measured) is not here.

**If we build nothing:** the live line keeps settling, and the
modernization team still has no owner brief that names the lie, the
judge, and the fence. Capture would have failed its only job. That cost
is not tolerable for tonight; this brief exists instead of a no-go
record.

## Goals & KPIs

- **KPI-1 — steel thread named.** Type 01 `valid-minimal` already
  states accepted net `173.45` (measured — type README) as the happy
  path the rest of the week can point at.
- **KPI-2 — the lie kept.** `df-source-001` stays declared `173.44`
  vs computed `173.45` (measured) and is refused, not patched.
- **KPI-3 — altitude held.** Tonight ends at a BRD + later a tech-spec.
  Zero product files. First write of the second plant → later (desired).

## Scope

**In:**
- Compile Helena’s Type 01 ask into this BRD (Pass 0), from the Second
  Brain and `spec/` inbound.
- Name types 02–05 as in-the-drop, not tonight’s steel thread.
- Name the Type 01 lie (173.44 vs 173.45) and the three done outcomes:
  accepted, refused, kept source lie.

**Out:**
- Type 06.
- Replacing Java or editing the live line.
- Picking a stack, writing ADRs, cutting seams, creating `modern/`.
- Rewriting a source trailer to go green.

**Undecided:**
- When the second plant’s first write happens (after Consensus; not
  tonight). Owned below.

## Definition of success

Helena can point at this brief and say: five types named, 06 out, Type
01 is the thread, done is accepted / refused / kept lie, 173.44 vs
173.45 is kept, inbound is not the judge, and nobody picked a stack
tonight.

## Stakeholders

- **Helena Dias, Partner Integration — owner and decider.** Asked for
  the rebuild beside Java. Breaks ties on this brief.
- **Marina Alves, Settlement Ops** — feels the trailer; will not send a
  corrected file; owns “do not fix totals.”
- **Rafael Costa, Legacy Platform** — live Java line; does not want the
  new team reading Java “to go faster.”
- **Priya Shah, Privacy** — privacy finished before any CSV.

## Risks

Pre-mortem: it is six months from now, this shipped, and it failed —
what killed it?

- **The second plant “fixes” 173.44 to 173.45.** Not accepted. Marina
  already wrote the refusal. Capture records the lie as a requirement
  for Intent.
- **Inbound prose treated as the contract** (settlement total vs net
  amount). Not accepted. `spec/` is mail; `contracts/` is the judge.
- **Tonight’s agent writes `modern/` or picks a lakehouse because a
  2026-06-09 sketch mentioned Parquet.** Not accepted. That sketch is
  mail. Stack is out of Capture.
- **Unsigned brief treated as license to code.** Accepted as a process
  risk only if we stop: verdict stays pending until Helena marks
  canonical. Pass 1 must not consume an unsigned brief as if it were
  signed.

## Constraints

- Do not replace Java (Helena, Rafael — kick-off D1).
- Do not rewrite source totals (Helena cover; Marina D3).
- Type 06 is a later pack (Helena D2).
- Privacy before any CSV (Priya D4).
- No product code tonight. First modern write is later.
- Inbound does not outrank `contracts/`.

A lakehouse named in a meeting is a **preference in the mail**, not a
constraint here. Recorded as an open question for later passes. Not a
Capture decision.

## Open questions

- question: "When does the second plant’s first write happen, and what
  is its first artifact — later, and not SFTP, but the exact night is
  not Helena’s cover letter?"
  owner: Helena Dias
  blocks: Pass 2+ schedule, not tonight’s BRD
- question: "Ops noun ‘settlement total’ vs layout ‘net amount’ for
  trailer bytes 16–30 — which word does reporting speak, without letting
  inbound outrank the contract?"
  owner: Marina Alves
  blocks: vocabulary in Intent; not a license to edit contracts/
- question: "2026-06-09 sync sketched Parquet / Bronze / Silver / Gold
  as a second reader. Owner preference for later passes only — Capture
  must not pick it."
  owner: Helena Dias
  blocks: nothing tonight; revisit after Consensus, not here

## Source

- Second Brain packs `00-how-this-notebook-thinks.md`, `01-estate.md`,
  `02-five-types.md`, `03-type-01-inbound.md`, `08-the-lie.md`
  (compiled from `spec/`; NotebookLM cannot read overpunch `.dat`).
- `spec/estate/cover.md` (Helena, 2026-06-24).
- `spec/estate/mail/2026-06-24-share-folder-drop.md`.
- `spec/estate/mail/2026-07-14-the-cent-that-will-not-die.md` (Marina).
- `spec/estate/meetings/2026-06-02-kick-off.md`.
- `spec/estate/meetings/2026-06-09-file-decomposition.md` (mail, not a
  stack decision).
- `spec/type-01-card-settlement/README.md` and inbound layout /
  walk-through / Marina 2026-07-02 note.
- `spec/type-01-card-settlement/expected/valid-minimal.reconciliation.yaml`
  and `df-source-001.finding.yaml`.
- `spec/README.md` (five live types; inbound vs judge; Type 06 not here).

Captured 2026-08-25. Pass 0. Human-led.

## Sign-off

- **Owner/decider:** Helena Dias, Partner Integration — verdict: pending
- **Date:** (unset — draft; owner writes canonical + ISO date after review)
