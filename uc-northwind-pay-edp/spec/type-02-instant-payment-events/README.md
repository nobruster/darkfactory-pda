# Instant Payment Events — inbound pack

**Type `02` · `PIX_EVENTS01` · `.txt` · UTF-8 pipes, escapes, offsets**

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · net `173.45` |
| `valid-boundary` | Boundary | accepted |
| `escaped-content` | Type edge | accepted |
| `malformed` | Grammar | `INVALID_FIELD_COUNT` |
| `df-source-002` | Source lie | `SOURCE_CONTROL_NET_MISMATCH` · `173.44` vs `173.45` |

Estate: [`../estate/`](../estate/README.md).
