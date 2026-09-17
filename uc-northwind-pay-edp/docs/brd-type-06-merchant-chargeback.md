# BRD — Type 06 merchant chargeback (sealed drop)

> Pass 0 Capture. Owner’s voice. No product code. No stack.
> Facts from `spec/type-06-merchant-chargeback/` inbound. This is mail
> compiled into a brief. It is not `contracts/`. The judge outranks
> every paragraph here.

## 1. Who asked, and what is out of scope

A sealed Type `06` pack arrived tonight. It is **not** in Thursday’s
Second Brain zip. Helena Dias still owns the estate brief; Ricardo
Mendes (2026-07-18) sent the chargeback fee schedule.

Do **not** replace Java. Do **not** edit `legacy/`, `contracts/`,
`gen/`, or `infra/` so a number agrees. Do **not** recut
`docs/consensus.md` or `docs/consensus-lakehouse.md`. Do **not** dump
Types `02`–`05` modern packages on this tile.

Helena is the decider on this brief. Consensus still signs before any
loop.

## 2. What lands (inbound is messy on purpose)

Overnight CSV, not an API. Filename shape
`NW_MERCHANT_CHARGEBACK_YYYYMMDD_B###############.csv`. Code
`MER_CHGBK06`, layout `001`. UTF-8 NFC, LF, semicolon, decimal comma,
`dd/MM/yyyy`, description always quoted.

Inbound pack (`spec/type-06-merchant-chargeback/inbound/`):

| Artifact | What it says | What it is |
|---|---|---|
| `merchant-chargeback-layout.md` | Chargeback = `original × rate ÷ 100`, round **once** HALF_UP (0.005 → 0.01). Header exact. | Mail. Layout sketch. |
| `2026-07-18-chargeback-schedule.md` | Same commercial rounding as merchant fees. Worked example: `67,00` at `1,500` percent is `1,005` before scale-2. Believe the schedule, not “normal” language from the call. | Mail. Ricardo. |
| `merchant-chargeback-table-definitions.txt` | `staging.merchant_chargeback` dump. | Mail. Incomplete. |
| `usp_apply_merchant_chargeback.sql` | `INSERT INTO legacy.merchant_chargeback SELECT * FROM staging…` | Mail. Incomplete. Not the live procedure. |

Four samples sit next to checksums. No source-manifest sidecar in the
share. If a checksum is missing, stop.

| Sample | Role | What the pack already says |
|---|---|---|
| `valid-minimal` | Happy | accepted · chargeback `1.01` |
| `valid-boundary` | Leap day / exact 2 cents | accepted |
| `malformed` | Grammar | `INVALID_CSV_QUOTING` |
| `legacy-miss` | Same HALF_UP steel thread | accepted · chargeback `1.01` |

The first write of the **second** plant for this type is **later**,
after Consensus. It is **not** SFTP. Do not pick a new estate. Type
`06` is a new numbered package on the same three seams.

## 3. What “done” means

Done is classified evidence, not a green parser.

- **Accepted sample** — sanitized rows and reconciliation match the
  **contract** oracle, privacy holds, tolerances are zero. Contract
  happy path: chargeback **1.01** BRL, `MATCHED`.
- **Refusal** — stable code, no sanitized CSV, no business rows, peers
  continue. Malformed is `INVALID_CSV_QUOTING`.
- **A disagreement is named.** Two questions, never netted: does
  modern match the contract? does legacy match the contract? Exactly
  one code per difference. Chat is not a settle.

The inbound SQL dump is not an oracle. `contracts/types/06-merchant-chargeback/`
is the judge.

## 4. KPIs

- **KPI-1 — Contract amount.** `valid-minimal` / `B202607230000501`:
  independently calculated HALF_UP chargeback is **1.01**. Not
  banker’s rounding. Not “normal.”
- **KPI-2 — Grammar refusal.** `malformed` / `B202607230000503`:
  `INVALID_CSV_QUOTING`, zero output, peers continue.
- **KPI-3 — Same seams.** Ingest → landing Parquet; dlt registers
  landing only; Gold at paid grain. Not a sixth estate.
- **KPI-4 — Frozen plant.** Zero edits of `legacy/` `contracts/`
  `gen/` `infra/` to manufacture agreement.
- **KPI-5 — Packet.** Evidence under `evidence/` (terminal, not Git).
  Linear moves when the packet exists.

## 5. Contradictions walked (mail vs inbound vs judge)

- Ricardo: “same commercial rounding as merchant fees”; “believe the
  schedule, not ‘normal’ language.” Python default is `HALF_EVEN`.
  Judge: `rounding_mode: HALF_UP`.
- Worked example `1,005` before scale-2. HALF_UP once → **1.01**.
  A plant that emits **1.00** is wrong relative to the contract.
- Inbound procedure is a stub `INSERT SELECT`. Live Java / procs are
  observation only. Do not copy them for the answer.
- Pack README and contract both name chargeback **1.01**. That is the
  oracle. If the live plant MATCHED a different cent, that fact is
  classified later — it is not a license to rewrite `expected/`.

Keep the contract number. Do not patch the plant you already trusted.
