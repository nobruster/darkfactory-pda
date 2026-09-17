# 05 · Boot

- Slide: Floor · Execute 05–09
- Slice: **B · Plant**
- Who: room
- Next: [`06-prompt-readme.md`](06-prompt-readme.md)

## Do

```bash
git clone <this-repo>
cd uc-northwind-pay-edp
git checkout main
make init
make deploy
```

Then, in the **same workspace** as beat 03 (CMUX, ORCA, Super Engineering, or BYO), ping the LLM again. Verbatim:

```text
Reply with exactly: boot-ok
What directory are you in?
Do not change any file.
```

The workspace should now see the clone. If it does not, open the folder in the workspace and ping once more.

## Proof

Compose is up. Not MATCHED yet. The model returns `boot-ok`. The working directory is the repo root.

## If fail

Same stop as machine four if Docker/Make/Python died. A workspace that will not open the folder is not a stop — they run 06–09 from the terminal. Do not run the README prompt against a missing clone.
