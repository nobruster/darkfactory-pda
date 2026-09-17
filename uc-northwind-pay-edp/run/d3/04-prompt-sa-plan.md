# 04 · Prompt — SA plan mermaids (`plans/modern.md`)

- Slide: Execute 02–04 (Hands-On **slice a · query** · chip `run/d3/` · **02–04**) — tile 04
- Slice: **A · Query**
- Who: every seat, through **their** agent
- Next: Dig Show Converge + SeamWise, Leave · SeamWise, then [`05-prompt-kits.md`](05-prompt-kits.md) on Execute 05–08

J5 just abstained: dlt / DuckDB / dbt are **not** in the nine-pack notebook.
They live in the SA engagement spec. Read it. **Render the graphs.** Do not
turn a mermaid into an ADR — that is Pass 2 on Execute 05–08.

## Prompt (verbatim)

```text
Read plans/modern.md. Do not change any file.

The solutions architect already drew three mermaid graphs in that file.
Render each one (do not redraw a prettier version; quote the repo):

1. Relationship among legacy, Dark Factory, and modern.
2. Two plants split after the same SFTP raw bytes.
3. Modern runtime flow (the numbered flowchart).

Then answer from those graphs, not from memory:
- What does modern consume that legacy also consumes?
- Where does dlt sit, and what must it not do?
- Which steps on the runtime graph are tonight (Type 01 landing → Gold)
  vs Thursday (Dagster, serve)?
- Is golden-match the Dark Factory?

Do not pick Dagster or FastAPI tonight.
Do not write ADRs yet.
Do not write modern/ product code.
```

## Proof

Three mermaids on screen, from `plans/modern.md` (not invented). Split
plants: `dlt registers` after `modern/landing/` Parquet. Runtime: steps
through golden-match are in scope; Dagster lineage and FastAPI are
**Thursday**. Golden-match is the referee, not the detector.

## If fail

They invent a fourth graph or restack the engines → stop. They start
Dagster because it is on the flowchart → park it. Notebook “already
said dlt” → it did not; J5 abstained. Do not copy last run’s ADRs out
of git history because a mermaid named the stack.
