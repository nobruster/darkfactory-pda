# 11 · Pass 5 — Task-Spec

- Slide: Execute 11 (Hands-On **slice e · leaf** · chip **11**) after Task-Spec Show + the separate kit
- Slice: **E · Task-Spec**
- Who: instructor authors the first leaf in public, then every seat
- Next: Task-Mesh (Show only — no file), then Debrief · In hand, then [`12-research.md`](12-research.md)

Skip this beat if Consensus is unsigned (Execute 11 stays dark). No eval, no build. `signed_off` starts **false**. No product code tonight.

## Prompt (verbatim)

```text
You are Pass 5 Tasking on NorthWind Pay.
Author one Type 01 leaf for ingest → landing (parser or writer — one leaf).
Write it under docs/tasks/.
The eval must be runnable.

The leaf must require:
- Exact Decimal
- Privacy at parse (PAN token + last4, CPF mask)
- Deterministic Parquet under modern/landing/ (when the mesh later runs)
- No write to frozen folders

Do not write modern/ product code tonight.
Do not change frozen folders.
```

```bash
mkdir -p docs/tasks
cvg tasking --draft --json
```

If `cvg` wrote under `cvg/docs/`, move the leaf into `docs/tasks/`. If `cvg` errors, the agent still writes the leaf — do not debug the CLI.

## Proof

A Task-Spec exists under `docs/tasks/`. It has an eval. `signed_off` is false. No `modern/` required tonight.

## If fail

No eval → tear it up. Do not Loop. Task-Mesh is Show — internals, not a license to write Parquet.
