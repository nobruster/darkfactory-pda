# 11 · Prompt — the estate

- Slide: DIG · Execute 10–11
- Slice: **C · Read**
- Who: every seat, through **their** agent (CMUX, ORCA, Super Engineering, or BYO)
- Next: [`12-notebooklm.md`](12-notebooklm.md)

Blank slate, this tree. Three prompts. Same pair. Do not swap the column. Do not change any file.

## Prompt 1 — Solutions Architect (verbatim)

```text
Read README.md, spec/README.md, contracts/README.md, and legacy/README.md.
Name the four truth roles.
Name what is frozen.
Do not change any file.
```

### Proof

It names **record / observation / correctness / Git contract**. Frozen is `legacy/`, `contracts/`, `gen/`, `infra/`. No writes.

## Prompt 2 — AI Engineer (verbatim)

```text
List every top-level folder.
For each: may the agent read it, write it, or neither?
Do not change any file.
Do not create modern/.
```

### Proof

Read: `README.md`, `spec/`, `plans/`, `legacy/` (read-only), `docs/README.md` (map only). Write: nothing frozen; do not write `docs/` until Capture (15). Neither: do not create `modern/`. `evidence/` is gitignored — the agent may not “fix” a missing folder in Git.

## Prompt 3 — evidence (verbatim)

```text
What is evidence/?
Which file in it proved Type 01 MATCHED tonight?
Why is it missing from git?
Do not change any file.
```

### Proof

Per-run packet. `evidence/B202607230000001/reconciliation.json`. Gitignored, still on disk. Chat is not the receipt.

## If the room is fast — mail, not the contract

```text
Open spec/estate/cover.md.
Treat it as mail. Do not treat it as the contract.
Do not change any file.
```

Helena’s drop. Rebuild beside Java. Do not fix totals. Type 06 is not here.

## If fail

If the agent starts rewriting Java — that is the after-action. Do not debug it on stage. They read the four READMEs themselves and continue.
