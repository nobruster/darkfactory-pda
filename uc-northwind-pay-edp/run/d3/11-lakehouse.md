# 11 · Execute — dlt register → Bronze → Silver → Gold

- Slide: Execute 10–12 (Hands-On **slice d · gold**) — tile 11
- Slice: **D · Gold**
- Who: instructor first, then every seat
- Next: [`12-golden-match.md`](12-golden-match.md) on the **same board**

dlt **registers** landing. It does not parse bytes. It does not compute a net. Gold grain is the ADR. Postgres is **observation**, not an input to Gold.

There is no `make dlt` on this tree. Follow tonight’s ADRs and `plans/modern.md` Milestones 2–3. Local DuckLake / DuckDB only.

## Prompt (verbatim)

```text
Run the Type 01 register + Bronze + Silver + Gold leaves, in that order.

Rules:
- dlt registers modern/landing/ only. If it re-parses raw or tokenizes PAN, stop.
- DuckLake / DuckDB is local.
- Bronze is source-aligned to landing. Silver is the conformed grain from the ADR. Gold is the number that may later be served.
- Do not read PostgreSQL to compute Gold.
- Do not rewrite privacy in dbt.
- Do not stand up Dagster.

Look up: Gold rebuilds from landing on a clean local run. Grain tests pass.
```

## Proof

Landing is registered. Bronze / Silver / Gold exist for Type 01. Grain matches the ADR. No Java net copied into Gold.

## If fail

dlt parses or owns money → **stop**. Seam is wrong. Green dbt with no grain test → tear it up. Do not proceed to golden-match.

Do not put `modern/lakehouse/` on `sys.path` and `from dlt.registration import …` — that **shadows** the pip `dlt` library. Keep `modern/lakehouse/dlt/registration.py`; import it as `registration`. The pip package is `import dlt` **inside** `register()`.
