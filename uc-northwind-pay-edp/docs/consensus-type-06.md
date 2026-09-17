# Consensus — Type 06 merchant chargeback

Pass 4. The barrier. Papers live in `docs/`, not `cvg/docs/`.
Do **not** recut `docs/consensus.md` or `docs/consensus-lakehouse.md`.
Those signs stay canonical for Type 01 ingest and Type 01 lakehouse.

**Signed.** This plan is the right thing to build. The machine may
take Pass 5 (Type 06 ingest → landing leaf and Type 06 dlt → Gold
leaf). The eval is the judge of done. The eval includes
**classification**, not only “it loaded.”

- Date: 2026-08-28
- Author of ADRs / seams: Grok seat (Night 5 Dark Factory)
- Signed by: **Luan Moreno, Agentic Lead**
- Verdict: **canonical for Type 06**
- Steel thread tonight: Type 06 ingest → landing → Gold (ADR 0014–0015,
  `docs/seams-type-06.md`)
- Fictional brief owner (Helena Dias) remains in the BRD; this barrier
  is signed by the Agentic Lead.

## What this sign authorizes

Full Pass 5–8 on Type `06` only. Bind still fences `legacy/`,
`contracts/`, `gen/`, `infra/`. Mesh may write the Type 06 five-file
package, landing, dlt registration for type `06`, Type 06 dbt models,
and `evidence/` packets. Mesh may **not** rewrite the referee, recut
prior Consensus, or dump Types `02`–`05`.

No sign on this file → no loop. This is the sign.

## Contradiction walked (mail vs inbound vs judge vs live plant)

- Ricardo (2026-07-18): `67,00` at `1,500` percent is `1,005` before
  scale-2; round HALF_UP once; ignore “normal.”
- Inbound procedure dump is a stub `INSERT SELECT`. Not an oracle.
- Judge (`contracts/`): chargeback **1.01**, `MATCHED`,
  `rounding_mode: HALF_UP`. `malformed` = `INVALID_CSV_QUOTING`.
- Python default `HALF_EVEN` would emit **1.00** from `1.005`. That is
  `MODERN_DEFECT` if the new plant does it. Fix the plant, not
  `expected/`.
- If the **live** Java / procs MATCHED a different cent than **1.01**,
  that is `CONFIRMED_LEGACY_DEFECT`. Stall. Do not patch Java.

Keep **1.01**. Classify. Do not manufacture agreement.

## Objections (default-to-refuted)

| ID | Objection | Disposition |
|---|---|---|
| C-06-1 | Type 06 was a refused cut on `docs/seams.md`. | **ACCEPTED** — owner: Luan Moreno. That refusal was “not in that drop.” The kit is in `spec/` tonight. New paper `docs/seams-type-06.md`. Do not recut Night 2 seams. |
| C-06-2 | Author and reviewer are the same seat. | **ACCEPTED** — owner: Luan Moreno. Same as Night 2 C-1. Dated signature on this file is the barrier. Does not block this sign. |
| C-06-3 | Inbound SQL looks like the apply path; copy it. | **FIXED** in ADR 0014: read the contract, never Java, never the stub. |
| C-06-4 | `1.005` “normally” rounds to `1.00`. | **FIXED** in ADR 0014 / R-1: HALF_UP once → **1.01**. `HALF_EVEN` is `MODERN_DEFECT`. |
| C-06-5 | If legacy already MATCHED, ship it. | **FIXED** in ADR 0015: two questions, never netted. Legacy MATCHED against itself is not the contract. |
| C-06-6 | Patch Java / expected / golden_match to go green. | **FIXED** by Bind (`legacy/` `contracts/` `gen/` `infra/` frozen) and ADR 0015. Stall is success. |
| C-06-7 | While we are here, dump Types 02–05. | **ACCEPTED** — owner: Luan Moreno. Thursday queued those leaves unsigned. Tonight is Type 06 only. |
| C-06-8 | Stand up Dagster so the graph looks busy. | **ACCEPTED** — ADR 0012. Skip hash if not up. |

No objection remains unresolved. None of them is a license to code
before this sign. This sign **is** the license for Pass 5–8 on Type 06.

## Open questions (do not block the sign; they block the machine gate)

- Stage 1: has legacy actually run `B202607230000501`, and what cent
  did it store? Observation. Not a patch list.
- `B202607230000504` stays virgin until the loop.
- Type 01 Gold / loop packet may be missing on a fresh worktree —
  **name the gap**; still run Type 06.

## Gate

Owner signed 2026-08-28. Pass 5 may author leaves with
`signed_off: false`. Bind stamps before product execute. Mesh runs.
Watch the eval, not the keystrokes.
