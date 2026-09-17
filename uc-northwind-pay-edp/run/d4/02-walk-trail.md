# 02 · Walk the trail

- Slide: Execute 02 (Hands-On **slice a · trail** · chip `run/d4/` · **02**)
- Slice: **A · Trail**
- Who: every seat, through **their** agent
- Next: Dig Leave · SeamWise, then [`03-place-lanes.md`](03-place-lanes.md) on Execute 03–04

Show first: the week as **one picture**. Then they type. Cite a file per chapter. Do not rebuild the notebook. Do not `catalog_ask` “where does paid live” — they already did Days 1 and 3.

## Prompt (verbatim)

```text
Walk the NorthWind Pay trail. Do not change any file. Do not generate Types 02–05.
Do not recut docs/consensus.md. Do not grep SQL. Do not add a tenth NotebookLM source.

Answer in six chapters. Each chapter: one or two sentences + the file you cited.

1. Requisites and why
   Read docs/brd-type-01-card-settlement.md and docs/tech-spec-type-01-card-settlement.md.
   Why does this plant exist? Why is the contract the judge? Why “no oracle, no build”?
   Money arrives as a file, not an API.

2. Problem and why
   Two plants, same SFTP bytes. Trailer 173.44 vs rows 173.45.
   Cite the BRD lie and docs/adrs/0001-first-write-is-landing-parquet.md plus
   docs/adrs/0005-source-lie-kept-zero-parquet.md.
   Why independence (no Java import; first write is not SFTP)?

3. Decisions taken
   List docs/adrs/ and read docs/seams.md and docs/consensus.md.
   If docs/consensus-lakehouse.md exists, read it; if missing, say so.
   Freeze: legacy/ contracts/ gen/ infra/.
   What did 0001–0005 close (Parquet, five-file, Decimal, privacy at parser, source lie kept)?
   Two signs: ingest, and lakehouse or named gap. What did 0006 park for tonight (rows 8–9)?
   Do not recut any of this.

4. SWE lane (Translator · Tuesday)
   Ingest → landing. Sense → claim → emit. Five-file package.
   Cite docs/adrs/0002-type-01-five-file-package.md and the parser leaf under docs/tasks/.
   Parser may exist; Parquet exists only if the mesh wrote it.

5. DE + analytics lane (Constructor · Wednesday)
   dlt registers only. DuckLake local. Bronze → Silver → Gold.
   Golden-match: two questions, never netted, six codes. “dbt ran” is a log.
   Cite lakehouse papers (0007+ / consensus-lakehouse.md / Gold leaves) or name the gap.

6. Tonight (Orchestrator)
   Same two lanes, now looped. From the trail you just walked — not from memory of a glossary —
   name the four rooms you ask (brain / catalog / papers / judge) and where observations live.
   Eval = a runnable command. Packet = evidence/. Linear moves only packets.
   Remaining types sit on the same two lanes. Type 05 is the pill. Type 06 is Friday.

Then fill right vs wrong (leave the HALF_EVEN row blank until board D):

| Claim | Right | Wrong |
| 173.44 | keep, refuse, zero Parquet | patch Java / expected/ / net with 173.45 |
| First write | modern/landing/ Parquet | SFTP CSV |
| SWE | five-file, privacy at parser, Decimal | port Java, float, dlt parses |
| DE / AE | dlt registers, replay rebuilds Gold | re-parse, “dbt ran” as eval |
| Judge | contracts/ + golden_match.py | grep SQL, chat said OK |
| Dagster | lineage, not parser | the parser |
| Packet | evidence/ before Linear moves | settle on a green log |
```

## Proof

Six citations **in order**. Right/wrong rows 1–7 filled (`HALF_EVEN` still blank). Gold present or named as a gap. No generate. No tenth source.

## If fail

A chapter with no file → re-ask that chapter only. Paid-grain `catalog_ask` as the whole board → stop; that was Wednesday. Missing lakehouse papers → **name the gap**, finish the trail, **do not run 03–08**. Do not start generate on mush.
