# Tech-spec — Type 01 card settlement

> Pass 1 Intent draft. Answers `docs/brd-type-01-card-settlement.md`.
> No product code. No stack. No ADRs. Brief-in, spec-out.
> An unsigned tech-spec is not a license to code.

## 1. The brief, restated

### Problem restated

Helena Dias asked to rebuild the five live settlement files **beside**
Java, not instead of it. Overnight files land; Type 01 is the steel
thread; types 02–05 exist in the drop; Type 06 is not in the drop.
Done is accepted, refused, or a **kept source lie**. Trailer **173.44**
vs rows **173.45** — keep the declaration, refuse the batch. Inbound
prose does not outrank the contract. First write of the second plant is
**later**, and is **not SFTP**. Do not pick a stack.

No new facts. That is the BRD in one breath.

### Scope

**In**

- Type 01 card settlement as tonight’s steel thread (`valid-minimal`
  accepted net 173.45 on 2 record; `df-source-001` lie kept).
- Name types 02–05 as present in the drop, not as tonight’s build.
- Restate inbound vs judge vs frozen plant vs observation.

**Out of scope**

- Type 06 (0 file of type 06 in this drop).
- Replacing Java or editing the live line.
- Picking a stack, writing ADRs, cutting seams, creating `modern/`.
- Rewriting 173.44 to 173.45.

## 2. Requirements

Falsifiable. Must / should / could / wont. Traced to BRD KPIs.

### Must

- **R-1 — Keep the lie.** On Type 01 `df-source-001` / batch
  `B202607230000004`, the declared trailer net stays **173.44** (BRL)
  and the independently summed details stay **173.45** (BRL). The
  second plant must **not** write 173.45 into the trailer. Current:
  source declares 173.44 vs rows 173.45 → Target: declaration kept,
  batch refused. Input: that one batch, 2 record. BRD KPI-2.
- **R-2 — Refuse a control mismatch.** When declared net ≠ computed
  net, the outcome is `SOURCE_CONTROL_TOTAL_MISMATCH`, status
  quarantined, **0** sanitized row, **0** business mutation, quarantine
  scope = that 1 batch, unrelated batches continue. Current: Marina
  will not send a “corrected” file → Target: refuse, do not patch.
  Comparator: declared amount **less than** computed amount by 0.01
  BRL on this fixture. BRD KPI-2.
- **R-3 — Type 01 steel thread.** `valid-minimal` is accepted: net
  **173.45** BRL, **2 record**, amount delta **0.00**, status MATCHED,
  privacy holds, tolerances are **0**. Current: drop already names
  this happy path → Target: any later plant matches that oracle, not
  a rewritten trailer. BRD KPI-1.
- **R-4 — Three done outcomes.** Every Type 01 sample in the drop ends
  in exactly 1 of: accepted (sanitized + recon match oracle), refused
  (stable code, 0 CSV row, 0 business row, peers continue), or kept
  source lie (classified, never repaired). At least 1 sample of each
  of those three roles exists in the drop (`valid-minimal`,
  `malformed`, `df-source-001`).
- **R-5 — Inbound does not outrank the judge.** `spec/` is mail.
  `contracts/` is the judge. When Marina says “settlement total” and
  the layout says “net amount,” the contract still wins. **0** edits
  of `contracts/` to match a meeting noun.
- **R-6 — Frozen plant.** Nothing in `legacy/`, `contracts/`, `gen/`,
  or `infra/` is edited to make a later gate pass. At least 4 frozen
  trees named. Java is not replaced. The second plant does not import
  Java to invent an answer.
- **R-7 — First write of the second plant is later, and is not SFTP.**
  Current: 0 files of a second plant on this tree tonight → Target:
  first write happens after Consensus, and that first write is **not**
  an SFTP drop. BRD KPI-3.
- **R-8 — Types in the drop.** Exactly 5 live types are in this drop
  (`01`–`05`). Type 01 is the steel thread (1 type tonight). Types
  02–05 exist (4 types later). Type 06 count in this drop = **0**.

### Should

- **R-9 — Same shape of lie on 02–05.** Keep each type’s declared
  number; refuse the batch. Not tonight’s eval; at least 1 lie sample
  per later type is already in the drop (BRD pack 08). Could wait
  until that night.

### Could

- **R-10 — Ops vocabulary note.** Record that trailer bytes 16–30 are
  “net amount” in the layout and “settlement total” in ops mail, as
  an owned open question — not as a silent default.

### Wont

- **W-1 — No Type 06.** Do not open Type 06. **0** Type 06 packs in
  this drop. A sixth file arrives as its own pack later.
- **W-2 — No stack tonight.** Do not pick a warehouse engine, a
  transform tool, a lakehouse, or any serving layer. Stack is not an
  answer at Intent. Owner preference in a 2026-06-09 sketch is mail;
  revisit only after Consensus.
- **W-3 — No ADRs, no seams, no `modern/`.** Pass 2–8 are not tonight.
  Do not cut seams. Do not create `modern/`.
- **W-4 — No repair of 173.44.** Do not “correct” the trailer.

### Success metrics

Traced to BRD KPIs. Current → target.

| Metric | Current | Target | BRD KPI |
|---|---|---|---|
| Steel thread named | Type 01 `valid-minimal` net 173.45, 2 record, MATCHED | later plant matches that oracle without rewriting the source | KPI-1 |
| Lie kept | trailer 173.44 vs rows 173.45 | declaration kept; batch refused; 0 sanitized row | KPI-2 |
| Altitude | unsigned BRD + this draft | 0 product files tonight; first second-plant write later, not SFTP | KPI-3 |

### Data named

The **source records** the engagement acts on are overnight Type 01
card-settlement files (`CRD_SETTLE01`, `.dat`, one header, detail
records, one trailer), plus the four other live types in the drop
(instant payment, payment slip, TED, merchant fees) as named later
threads. Inputs the second plant **reads** are those raw files and
their checksums — the same bytes the live line already reads — not
Java internals. Type 06 is not among the source records in this drop.

## 3. Truth roles on this tree

| Role | On this tree |
|---|---|
| **Inbound** | `spec/` — mail, meetings, layouts, samples. Contradictions allowed. `cover.md` is mail, not the judge. |
| **Judge / source of correctness** | `contracts/` — signed layouts and oracles. Outranks inbound prose and outranks code. |
| **Frozen plant** | `legacy/`, `gen/`, `infra/` — and `contracts/` with them. Do not write. Java stays the live privacy boundary. |
| **Source of observation** | Immutable SFTP bytes, hashes, manifests, database observations, and per-run `evidence/`. Gitignored; open in the terminal. MATCHED or it did not happen. |
| **System of record** | The simulated source owns its raw file and declared controls; committed applied tables own applied legacy state. A source of record may still emit 173.44 vs 173.45. |
| **Executable Git contract** | Versioned YAML, schemas, fixtures, tests — the currently approved expectation. No implementation silently redefines it. |

Inbound vs judge vs frozen plant must all three be named. They are.

## 4. What the second plant must not do

- **Must not** replace Java or call Java to produce the second answer.
- **Must not** edit `legacy/`, `contracts/`, `gen/`, or `infra/` to go
  green.
- **Must not** repair 173.44. Keep the declaration. Refuse the batch.
- **Must not** treat `spec/` as the contract.
- **Must not** write its first artifact as an SFTP drop. The first
  write of the second plant is **later**, and is **not SFTP**.
- **Must not** exist on the tree tonight. Do not create `modern/`.
- **Must not** open Type 06.
- **Must not** pick a stack at Intent (no warehouse, no transform
  tool, no lakehouse named as a decision).

Helena is not sending a parser or permission to edit the live line.
Rafael does not want the new team reading Java “to go faster.”

## 5. Open questions

Open assumptions. Each has an owner. No silent defaults. Stack is not
an answer. Dated 2026-08-25.

- question: "When is the second plant’s first write, and what artifact
  is it — later, and not SFTP, but which night?"
  owner: Helena Dias
  default (not a decision): after Consensus; not tonight
  blocks: Pass 2 calendar only
- question: "Which word does reporting speak for trailer bytes 16–30 —
  layout ‘net amount’ or ops ‘settlement total’ — without letting
  inbound outrank `contracts/`?"
  owner: Marina Alves
  default (not a decision): layout noun for the field; ops noun may
  appear in prose; the judge is still `contracts/`
  blocks: vocabulary in later ADRs, not tonight’s code
- question: "The 2026-06-09 sync sketched a second reader and a
  medallion path. That is mail. What, if anything, is owner preference
  for Pass 3 — recorded as preference, not as Intent?"
  owner: Helena Dias
  default (not a decision): **no stack at Pass 1**; revisit only after
  Consensus
  blocks: nothing tonight

No blocker gap is left `pending`. None of these block tonight’s
altitude. Pass 2 must not consume this draft as canonical.

## Sign-off

- **Owner/decider:** Helena Dias, Partner Integration — verdict: pending
- **Date:** (unset — draft; owner writes canonical + ISO date after review)
