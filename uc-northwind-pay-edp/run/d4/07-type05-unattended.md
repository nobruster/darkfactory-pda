# 07 · Type 05 unattended

- Slide: Execute 07–08 (Hands-On **slice d · pill**) — tile 07
- Slice: **D · Pill**
- Who: instructor binds, **leaves the table**, then the room looks up
- Next: [`08-half-up.md`](08-half-up.md) on the **same board**

Type `05` is a real type, then a pill. Same movie as Type 01’s lie: `DF-SOURCE-005` = `CONFIRMED_SOURCE_DEFECT`. Do not walk `rounding-half-up` on this tile.

Inbound: [`spec/type-05-merchant-fee-assessment/`](../../spec/type-05-merchant-fee-assessment/README.md). Brain pack **07**.

## Prompt (verbatim)

```text
Bind Type 05. Hand the inbound pack. Walk away.

The eval is the judge. When the loop returns, look up:
1. make run TYPE=05 SCENARIO=valid-minimal — classified, packet on disk.
2. make run TYPE=05 SCENARIO=malformed — classified. No invented artifacts.
3. make run TYPE=05 SCENARIO=DF-SOURCE-005 — CONFIRMED_SOURCE_DEFECT. Keep the declaration. Refuse.
   (uppercase DF-SOURCE-005 — lowercase df-source-005 is not a registered scenario)

Do not implement rounding-half-up on this tile.
Do not change expected/.
Do not patch Java.
Do not open Type 06.
```

## Proof

Look up `evidence/B202607230000405/final-status.json`:
`status: quarantined` · `code: SOURCE_CONTROL_ASSESSED_FEE_MISMATCH`
(declared assessed 0.99 vs calculated 1.00). That refusal **is**
`CONFIRMED_SOURCE_DEFECT` in golden-match language. The JSON will **not**
say `CONFIRMED_SOURCE_DEFECT` — do not hunt for that string. Frozen
`legacy/` untouched.

## If fail

Narrating the keystrokes → not unattended. Rewriting expected → **stop**. Missing Type 05 leaves → go back to [`04-generate-queue.md`](04-generate-queue.md).
