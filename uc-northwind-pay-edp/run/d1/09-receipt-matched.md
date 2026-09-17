# 09 · Receipt — MATCHED

- Slide: Floor · Execute 05–09 (look-up: MATCHED / Receipt)
- Slice: **B · Plant**
- Who: room
- Next: [`10-tree.md`](10-tree.md)

## Do

Do not look for `evidence/` in the Git sidebar or the editor tree. It is gitignored. Open it in the **terminal** from the repo root:

```bash
cat evidence/B202607230000001/reconciliation.json
```

Then ask the workspace (verbatim):

```text
From the terminal, not from git, read evidence/B202607230000001/reconciliation.json.

Answer, from the file:
1. What is status?
2. What is source_net_amount, applied_net_amount, amount_delta?
3. Why might this folder be missing from the Git sidebar?
4. Did we “fix” 173.44 to get here?

Do not change any file.
Do not edit legacy/.
```

## Proof

```json
"status": "MATCHED"
"source_net_amount": "173.45"
"applied_net_amount": "173.45"
"amount_delta": "0.00"
```

The file decides, not the presenter. A healthy agent says MATCHED, 173.45 / 173.45 / 0.00, gitignored, and **no** — we did not patch 173.44. Valid-minimal rows already agreed.

## If fail

`ls: evidence: No such file or directory` means `make run` did not commit a packet — go back to [`08-prompt-make-run.md`](08-prompt-make-run.md).

Do not “fix” `173.44`. Do not edit frozen `legacy/`.
