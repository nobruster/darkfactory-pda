# 02 · Prompt — BRD + tech-spec

- Slide: Execute 01–02 (Hands-On **slice a · recap**) — tile 02
- Slice: **A · Recap**
- Who: every seat, through **their** agent
- Next: Stage lecture (SWE Role · java2py · The translator · First write · Why a file · Five-file package). Then Craft Shows, then [`03-prompt-harness.md`](03-prompt-harness.md) on Execute 03–04.

Why a file **is** the ingest seam (`sense → claim → emit`). No extra beat.

Do not rerun Pass 0–1. The agent **reads**. Map: [`docs/README.md`](../../docs/README.md).

## Prompt (verbatim)

```text
Read docs/README.md, then docs/brd-type-01-card-settlement.md and docs/tech-spec-type-01-card-settlement.md.
Do not change any file.

Restate, from the files:
1. Who asked, and what is out of scope?
2. The lie — trailer vs rows.
3. Inbound vs judge.
4. What the second plant must not do (first write is not SFTP; no Java import).
5. Did Intent pick DuckDB, dbt, or a lakehouse? If yes, name that as a smell.

If a file is missing, say so. Do not invent a BRD.
```

## Proof

Helena. Type `01` steel thread. Trailer **173.44** vs rows **173.45**. `spec/` inbound. `contracts/` judge. First write later, not SFTP. No stack. No `modern/`.

## If fail

Missing files → Second Brain + `spec/` still exist. Name the gap. Continue. Do not start Structure around an empty brief.
