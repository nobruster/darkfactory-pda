# 07 · Pass 3 — Decompose (seam 2)

- Slide: Execute 05–08 (Hands-On **slice b · barrier**) — tile 07
- Slice: **B · Barrier**
- Who: instructor cuts in public, room copies
- Next: [`08-consensus.md`](08-consensus.md)

SeamWise already taught on the side kit. This beat **updates** `docs/seams.md` seam 2. Do not rewrite seam 1. Do not write Task-Specs yet.

## Do

| Seam | Owner | When |
|---|---|---|
| Ingest → landing | Translator | **signed Tuesday** — do not recut |
| **dlt → Gold** | **Constructor** | **tonight’s legs** |
| Orchestrate + serve | Orchestrator | Day 4 |

## Prompt (verbatim)

```text
You are Pass 3 Decompose on NorthWind Pay.
Steel thread tonight is Type 01 dlt → Gold.
Update docs/seams.md seam 2 only.
Name: seam, swimlane, leg. One owner per handoff.

Seam 2 legs (ordered):
1. Register — dlt registers modern/landing/ Parquet. No re-parse.
2. Medallion — Bronze → Silver → Gold. Grains from tonight’s ADRs.
3. Match — attach validation/golden-match/golden_match.py. Two questions. No tolerance.

Do not recut seam 1.
Do not task Types 02–05.
Do not write Task-Specs.
Do not write product code.
Do not change frozen folders.
```

## Proof

`docs/seams.md` seam 2 has three legs. Constructor owns the write surface. Translator does not write Gold. Type `01` is the only lane for leaves tonight.

## If fail

They cut “Java vs Python” or “ingest vs lakehouse” as a new estate → stop. Bronze / Silver / Gold are **legs**, not new seams. Recutting seam 1 → stop.
