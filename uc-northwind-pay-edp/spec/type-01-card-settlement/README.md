# Card Settlement Detail — inbound pack

**Type `01` · `CRD_SETTLE01` · `.dat` · ISO-8859-1 fixed width, COBOL overpunch**

What we mailed. Start at `inbound/`, hash `samples/`, adjudicate with
`expected/`. Do not open Java for the answer.

| Folder | Contents |
|---|---|
| [`inbound/`](inbound/) | Layout rev 3, table dump, two dated procs, walk-through, ops noun |
| [`samples/`](samples/) | Five raw files + SHA-256 |
| [`expected/`](expected/) | Sanitized + recon for accepted; refusals for malformed and the lie |

| Sample | Role | Expected |
|---|---|---|
| `valid-minimal` | Happy | accepted · net `173.45` |
| `valid-boundary` | Boundary | accepted |
| `negative-overpunch` | Type edge | accepted · net `-12.34` |
| `malformed` | Grammar | `INVALID_OVERPUNCH` |
| `df-source-001` | Source lie | `SOURCE_CONTROL_TOTAL_MISMATCH` · declared `173.44` · computed `173.45` |

Estate context: [`../estate/`](../estate/README.md).
