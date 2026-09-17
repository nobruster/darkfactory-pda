# Payment Slip Settlement — inbound pack

**Type `03` · `PAYSLIPSET03` · `.rem` · 240-byte pairs, lots**

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · net `198.50` |
| `valid-boundary` | Boundary | accepted |
| `multi-lot` | Type edge | accepted |
| `malformed` | Grammar | `SEGMENT_PAIR_MISMATCH` |
| `df-source-003` | Source lie | `SOURCE_CONTROL_NET_MISMATCH` · `198.49` vs `198.50` |

Estate: [`../estate/`](../estate/README.md).
