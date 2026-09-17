# 01 · Prompt — Recap disk

- Slide: Recap · closed, Recap · papers (talk; **no** Hands-On badge)
- Slice: **Recap**
- Who: every seat, through **their** agent — if they missed Tuesday, they type this
- Next: Floor Shows (Second Brain, OntoLayer + specs), then [`02-query-brain.md`](02-query-brain.md) on Execute 02–04

Do not rerun Pass 0–1 or ingest 2–4. The agent **reads**. Map: [`docs/README.md`](../../docs/README.md).

## Prompt (verbatim)

```text
Do not change any file.
Read docs/README.md, docs/consensus.md, docs/adrs/0006-later-nights-parked.md, and docs/seams.md.
List docs/tasks/ and modern/ (terminal, not Git).

From the files, not from memory:
1. Who signed ingest → landing, and what must we keep (173.44)?
2. What did ADRs 0001–0005 close? What did 0006 park for tonight?
3. How many Task-Specs exist? What is signed_off on the parser leaf?
4. Does modern/landing/ Parquet exist? What modern file does exist?
5. Which seam is tonight (dlt → Gold)? Which seams wait until Thursday?

Do not make run unless evidence/B202607230000001/reconciliation.json is missing.
Do not write any file.
Do not unpark 0006 yet.
```

## Proof

1. **Luan Moreno, Agentic Lead** · **173.44** kept.
2. Landing facts closed. **0006** parks dlt / DuckLake / B-S-G grains / rule split / golden-match keys (rows 3–7).
3. **One** leaf · parser · `signed_off: false`.
4. **No** `modern/landing/`. Parser at `modern/ingestion/.../parser.py`.
5. Seam **2** tonight. Seam 3 (orchestrate + Type 05) is Thursday.

## If fail

Missing papers → name the gap; continue. Missing MATCHED packet → [`../d1/05-boot.md`](../d1/05-boot.md) then [`../d1/08-prompt-make-run.md`](../d1/08-prompt-make-run.md). Do not share Compose (`northwind-pay-legacy`, port 2222). Do not start Structure around an empty recap.
