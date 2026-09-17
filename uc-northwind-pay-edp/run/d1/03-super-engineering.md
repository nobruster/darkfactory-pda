# 03 · Workspace — CMUX, ORCA, Super Engineering, or BYO

- Slide: Craft · Execute 01–04
- Slice: **A · Seat**
- Who: room
- Next: [`04-machine-four.md`](04-machine-four.md)

The workspace is **generic**. Super Engineering is the house default. **CMUX**, **ORCA**, or any seat that can **edit files and run shell** also sits. The gates are graded, not the vendor.

Point it at **DeepSeek** through OpenRouter (beat 02). Then prove the LLM answers.

## Do

1. Open a workspace: Super Engineering, CMUX, ORCA, or BYO.
2. Attach the OpenRouter key. Select DeepSeek.
3. Ping the model. Verbatim:

```text
Reply with exactly: seat-ok
Do not change any file.
Do not run a command.
```

4. If the workspace can run shell, a second ping (verbatim):

```text
What is your working directory? Print the repo root if you can see it.
Do not change any file.
```

## Proof

- The model returns `seat-ok`.
- A workspace that can run shell names a directory. If it cannot run shell yet, that waits for beat 04–05. Do not stall.

## If fail

Oh My Pi + the OpenRouter key is enough to chat. A missing CMUX / ORCA / Super Engineering install is not a stop. Do not debug a workspace for 80 people. Continue to machine four.
