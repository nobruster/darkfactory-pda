# 04 · Pipeline Smoke Test

- Slide: Execute 04 (Hands-On **slice d · smoke** · chip `run/d5/` · **04**)
- Slice: **D · Smoke**
- Who: instructor first, then seats
- Next: [`05-type06-converge.md`](05-type06-converge.md)

Smoke the **Type 01** pipeline that already exists. First write is landing. dlt registers only. Gold rebuilds from landing. Golden-match still both questions true.

Dagster is **lineage, not a parser** (ADR 0012). Thursday skipped the hash because Dagster was not up. **It is up now**, in its own environment (`modern/orchestration/`), and every asset shells out to `modern/scripts/plant_steps.py` — it owns no layout and no money rule. Materialise it; do not turn it into a product tour. Do not write FastAPI on this tile (ADR 0013 is signed; this beat is smoke, not serve).

## Prompt (verbatim)

```text
Do not recut docs/consensus.md or docs/consensus-lakehouse.md.
Do not rewrite validation/golden-match/golden_match.py.
Do not move parsing into a Dagster asset.
Do not write FastAPI.
Do not generate Types 02–06.

Smoke Type 01 from landing (terminal, not Git):

1. Confirm evidence/B202607230000001/reconciliation.json is MATCHED 173.45. If it is, do not make run TYPE=01 SCENARIO=valid-minimal.
2. Confirm modern/landing/B202607230000001/*.parquet exists.
3. Optional replay (does not recut signs): from repo root, with modern/.venv (pyarrow 25 — the venv that wrote landing; modern/lakehouse/.venv has pyarrow 22 and will raise PublicationError),
   modern/.venv/bin/python modern/scripts/run_type01_gold.py
   then read-only: Gold row B202607230000001 / BRL / 173.45 / MATCHED.
4. Confirm evidence/modern/B202607230000001/golden-match.json — both questions true.
5. Confirm evidence/loop/T-20260825-type-01-landing-parser.json still says eval exit 0, classification accepted. Its Dagster skip note is Thursday's record; do not rewrite it.
6. Materialise the lineage and record the Gold hash:
   cd modern/orchestration && .venv/bin/dagster asset materialize --select '*' -m definitions
   If Dagster will not come up, say so out loud and skip the hash. Do not fake it.

Parsing stays in modern/ingestion/.../01-card-settlement/parser.py. It does not move into the orchestrator.
```

## Proof

Landing present. Gold MATCHED 173.45 (after replay or from disk). Both questions true. Six Dagster assets materialised, or the outage named. Parser path unchanged.

## If fail

Replay red → **do not patch Java**. Name the gap. Do not proceed to invent Type 06 Gold from Postgres. Missing landing → Night 3 emit, not a Dagster asset.
