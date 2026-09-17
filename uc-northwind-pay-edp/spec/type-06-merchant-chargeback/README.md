# Merchant Chargeback Adjustment — inbound pack

**Type `06` · `MER_CHGBK06` · `.csv` · semicolon, decimal comma, `HALF_UP`**

Same shape as Types `01`–`05`. This is a new numbered package in the
customer drop. Brain packs cover `01`–`05` only.

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · chargeback `1.01` |
| `valid-boundary` | Leap day / exact 2 cents | accepted |
| `malformed` | Grammar | `INVALID_CSV_QUOTING` |
| `legacy-miss` | Same HALF_UP steel thread | accepted · chargeback `1.01` |

Estate: [`../estate/`](../estate/README.md).
