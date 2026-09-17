# Merchant Fee Assessment — inbound pack

**Type `05` · `MER_FEESET05` · `.csv` · semicolon, decimal comma, `HALF_UP`**

Same shape as Types `01`–`04`. The old numbered `01-`…`07-` tree is
gone; this is the customer drop.

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · assessed `12.36` |
| `valid-boundary` | Boundary | accepted |
| `rounding-half-up` | Type edge | accepted · assessed `0.04` on `3.50` |
| `malformed` | Grammar | `INVALID_CSV_QUOTING` |
| `df-source-005` | Source lie | `SOURCE_CONTROL_ASSESSED_FEE_MISMATCH` · declared `0.99` · computed `1.00` |

**Small red pill.** Python default is `HALF_EVEN`. Ops mail says
“normal rounding.” This type is **`HALF_UP`**. `rounding-half-up`
(`0.04` on `3.50`) is the proof. Trust the schedule and `expected/`,
not the language default. That is a preview of Day 5: something you
already trusted can be wrong.

Estate: [`../estate/`](../estate/README.md).
