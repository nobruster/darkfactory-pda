# 15 · Pass 0 — Capture (write a real BRD)

- Slide: DIG · Show · Converge · the spine, then Hands-On Execute 14–16
- Slice: **F · Spine**
- Who: every seat, through **their** agent, gated by `cvg`
- Next: [`16-intent.md`](16-intent.md)

This is the document the rest of the week reads. Make it good. The owner voice is Helena’s drop. The facts come from the **Second Brain** and `spec/` — not from grepping Java, not from a stack preference.

`cvg capture` **validates** an artifact that already exists. The agent drafts. A green draft token is not Consensus.

If `cvg` is not on the path, still write the file. Gate it when the CLI sits (beat 14).

---

## What a good BRD looks like tonight

Write `docs/brd-type-01-card-settlement.md` with these headings, in this order:

1. **Who asked, and what is out of scope** — Helena; rebuild beside Java; Type 06 not here; do not fix totals.
2. **What lands** — overnight files, Type 01 steel thread, five live types named, first write of the second plant later.
3. **What “done” means** — accepted batch, refusal, source lie. Keep the declaration.
4. **The lie** — trailer **173.44**, rows **173.45**. Same shape on PIX / slips / TED / fees. Refuse. Do not patch.
5. **Inbound vs judge** — `spec/` is mail. `contracts/` is the judge. Inbound prose does not outrank the contract.
6. **What we will not do tonight** — no stack, no ADRs, no seams, no `modern/`.

Provenance: every number cites a source (NotebookLM retrieval or a `spec/` path).

---

## Prompt (verbatim)

```text
You are Pass 0 Capture on NorthWind Pay. Human-led. No product code.

Draft docs/brd-type-01-card-settlement.md from:
- the Second Brain (NotebookLM — what it actually retrieved)
- spec/estate/ (mail, not the contract)
- spec/type-01-card-settlement/ inbound notes and samples
- spec/README.md for the five live types

Use these headings, in order:
1. Who asked, and what is out of scope
2. What lands
3. What “done” means
4. The lie
5. Inbound vs judge
6. What we will not do tonight

The BRD must say, in the owner's voice:
- Helena asked to rebuild beside Java
- Type 01 is tonight’s steel thread; types 02–05 exist; Type 06 is not in the drop
- done = accepted, refused, or a kept source lie
- trailer 173.44 vs rows 173.45 — keep the lie, refuse the batch
- first modern write is later; do not pick a stack

Inbound prose does not outrank contracts/.
Do not write modern/.
Do not write ADRs.
Do not cut seams.
Do not “fix” 173.44.
```

Then gate it:

```bash
mkdir -p docs
cvg capture --draft docs/brd-type-01-card-settlement.md --json
```

If the brief is empty or the do-nothing test is tolerable — **kill it cheaply**. That is a result.

```bash
cvg capture --no-go docs/no-go-type-01.md --json
```

## Proof

The file exists. The room can restate the six headings without the file open. `CHECK_BRD=DRAFT_OK` or `CHECK_BRD=NOGO_OK` if `cvg` sits. No parser.

## If fail

Repair the BRD (scope, the lie, provenance). Do not start Intent around a red Capture. If `cvg` is missing, the written BRD still counts — gate it when the CLI sits.
