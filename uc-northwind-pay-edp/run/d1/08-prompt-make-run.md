# 08 · Prompt — make run

- Slide: Floor · Execute 05–09
- Slice: **B · Plant**
- Who: every seat, through **their** agent
- Next: [`09-receipt-matched.md`](09-receipt-matched.md)

## Prompt (verbatim)

```text
Run make run TYPE=01 SCENARIO=valid-minimal.
Do not edit legacy/, contracts/, gen/, or infra/.
```

## Proof

Batch `B202607230000001` **succeeded**. Then, in the **terminal** (not the Git panel):

```bash
ls evidence/B202607230000001
```

`evidence/` is in `.gitignore` and created `0700`. The editor tree will hide it. That does not mean the run failed.

## If fail

If the runner says `Immutable evidence already exists` — the first run already wrote the packet. Skip to [`09-receipt-matched.md`](09-receipt-matched.md). Do not clean unless you need a **repeat**.

Repeat of the same canonical batch needs a clean runtime:

```bash
make clean CONFIRM=clean-runtime && make deploy
```

Then retry this prompt. Do not walk Type `05`. Do not invent `modern/`.
