# TED Transfer Settlement — inbound pack

**Type `04` · `TED_SETTLE04` · `.dat` · mixed widths, inherited returns**

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · net `1000.00` |
| `valid-boundary` | Boundary | accepted |
| `all-returned-zero-net` | Type edge | accepted · net `0.00` |
| `malformed` | Grammar | `INVALID_TRANSPORT` |
| `df-source-004` | Source lie | `SOURCE_CONTROL_NET_MISMATCH` · `999.99` vs `1000.00` |

Estate: [`../estate/`](../estate/README.md).
