# Tech-spec — Type 06 merchant chargeback

> Pass 1 Intent draft. Answers `docs/brd-type-06-merchant-chargeback.md`.
> No product code. An unsigned tech-spec is not a license to code.

## 1. The brief, restated

Helena’s estate now includes a sealed Type `06` drop. Ricardo’s
schedule says HALF_UP; the worked example is `67,00` at `1,500`
percent → `1,005` before scale-2. Inbound SQL is a stub. `spec/` is
mail. `contracts/` is the judge. The second plant reads the contract,
never Java. First write is landing Parquet, not SFTP. Same three
seams. Consensus still signs. If legacy disagrees with the contract,
classify — do not patch.

No new facts. That is the BRD in one breath.

### Scope

**In**

- Type 06 merchant chargeback as tonight’s numbered package
  (`valid-minimal` accepted chargeback 1.01; `malformed` refused;
  `legacy-miss` same HALF_UP steel thread, virgin for the loop).
- Same seams: ingest-landing, dlt-gold, orchestrate-serve.
- Restate inbound vs judge vs frozen plant vs observation.

**Out of scope**

- Recutting `docs/consensus.md` or `docs/consensus-lakehouse.md`.
- Rewriting `validation/golden-match/golden_match.py`.
- Editing `legacy/`, `contracts/`, `gen/`, `infra/`.
- Dumping Types `02`–`05` modern packages.
- A new estate, a Dagster product tour, a `factory/` detector folder.
- Type `07`.

## 2. Requirements

Falsifiable. Must / should / could / wont.

### Must

- **R-1 — HALF_UP once.** Chargeback = `original × rate ÷ 100`,
  arbitrary-precision decimal, then round **once** to scale 2 with
  **HALF_UP**. `67.00` at `1.500` percent is `1.005` before scale-2 →
  **1.01**. Python `ROUND_HALF_EVEN` is forbidden here. BRD KPI-1.
- **R-2 — Contract happy path.** `valid-minimal` /
  `B202607230000501` accepted: chargeback **1.01**, calculated
  **1.01**, all deltas `0.00`, status `MATCHED`. Judge:
  `contracts/types/06-merchant-chargeback/main/expected-reconciliation.yaml`.
- **R-3 — Grammar refusal.** `malformed` / `B202607230000503`:
  `INVALID_CSV_QUOTING`, quarantined, **zero** Parquet, **zero**
  business mutation, peers continue. BRD KPI-2.
- **R-4 — Five-file package.** `model → parser → schema → writer →
  handler` under
  `modern/ingestion/src/northwind_pay/types/06-merchant-chargeback/`.
  First write is `modern/landing/` Parquet. Not SFTP. Decimal never
  float. Privacy (CNPJ mask `**********<last4>`) dies at the parser.
- **R-5 — dlt registers landing only.** No semicolon CSV parse in
  dlt. Bronze source-aligned; Silver conserves money; Gold grain
  `batch_id` + `currency` matching
  `reporting.merchant_chargeback_reconciliation`.
- **R-6 — Two questions, never netted.** Attach the existing referee.
  Do not rewrite it. Do not add tolerance.
- **R-7 — Frozen plant.** Zero edits of `legacy/` `contracts/` `gen/`
  `infra/` to make a gate pass. Java is observation, not a teacher.
- **R-8 — Classification is the eval.** If modern matches the
  contract and legacy does not: `CONFIRMED_LEGACY_DEFECT`. Stall the
  type. Do not patch. If modern is also wrong: `MODERN_DEFECT` — fix
  the new plant, re-run. Still classify legacy if that fact is true.
- **R-9 — Packet.** Evidence under `evidence/` (terminal, not Git).
  Linear moves when the packet exists. Chat is not a settle.

### Should

- **S-1 — `legacy-miss` stays virgin** until the loop (`B202607230000504`).
  Pre-flight must not burn it.
- **S-2 — Boundary leap-day** `B200002290000502` / `0.02` accepted
  under the same HALF_UP rule.

### Could

- **C-1 — Dagster lineage** for Type 06 assets. Skip if Dagster is
  not up. ADR 0012: lineage, not a parser.

### Won't

- **W-1** — Recut ingest or lakehouse Consensus.
- **W-2** — Rewrite `expected/` so HALF_EVEN or the live plant goes green.
- **W-3** — Import Java or copy the stub `INSERT SELECT`.
- **W-4** — Empty Type `06` folder. Five files or nothing.
- **W-5** — Types `02`–`05` modern dump. Those leaves stay queued.

## 3. Terminal outcomes

| Scenario | Batch | Contract |
|---|---|---|
| `valid-minimal` | `B202607230000501` | MATCHED chargeback **1.01** |
| `valid-boundary` | `B200002290000502` | MATCHED chargeback **0.02** |
| `malformed` | `B202607230000503` | `INVALID_CSV_QUOTING` · zero output |
| `legacy-miss` | `B202607230000504` | MATCHED chargeback **1.01** (same steel thread) |

Rejection codes come from
`contracts/types/06-merchant-chargeback/layout.yaml`.
`CHARGEBACK_CALCULATION_MISMATCH` when declared chargeback ≠
independent HALF_UP. Source-control mismatches keep the declaration
and refuse.

## 4. Privacy

CNPJ: 14 digits, two Mod11 check digits, then mask
`**********` + last4. Description is validated passthrough. Whole
output scanned for every raw CNPJ before publication. Failure:
`PRIVACY_OUTPUT_VIOLATION`, reject entire batch, no Parquet.

## 5. Open questions (do not block Intent; they block the machine gate)

- What cent the **live** Java plant stored for `B202607230000501`.
  That is Stage 1 observation, not a requirement to copy.
- Whether Dagster is up. Hash skipped if not.

No stack is picked here. Structure names the ADRs. Consensus signs.
Then Task-Spec. Then Bind. Then the loop.
