# 10 · Execute — Type 01 landing Parquet

- Slide: Execute 10–12 (Hands-On **slice d · gold** · chip **10–12**) — tile 10
- Slice: **D · Gold**
- Who: instructor first, then every seat through **their** agent
- Next: [`11-lakehouse.md`](11-lakehouse.md) on the **same board**

Order is mandatory. **Landing before dlt.** If Parquet already exists for `valid-minimal`, prove it and skip emit. Frozen folders stay frozen.

## Prompt (verbatim)

```text
Run the signed Type 01 emit leaves (schema / writer / handler) so landing exists.
Use the same raw bytes as the live line (valid-minimal).
Do not import Java.
Do not write legacy/, contracts/, gen/, or infra/.

Proof I will look up:
1. modern/landing/ has deterministic Parquet + readiness for valid-minimal (net 173.45 shape).
2. df-source-001 / trailer 173.44 vs rows 173.45 → zero Parquet, stable finding. Keep 173.44.
3. No file at legacy/processor/PWNED.txt. No SFTP csv/outgoing write.

If landing already exists and matches the ADR, say so and stop emit.
Do not start dlt until this proof holds.
```

## Proof

`modern/landing/` exists for the happy batch. Source lie emits **zero** Parquet. Bind still on.

## If fail

Emit fails → **stop**. dlt has nothing to register. Do not “register raw.” Do not copy Java CSV into landing.

`modern/ingestion/src/northwind_pay/types/01-card-settlement/` is **not** an importable Python package (hyphen + leading digit). Load `parser.py` / `handler.py` by file path and register the module in `sys.modules` **before** `dataclass` runs. Do not rename the ADR 0002 path. Parser may already exist with `signed_off: false` — finish schema / writer / handler; do not recut the parser to make Gold easier.
