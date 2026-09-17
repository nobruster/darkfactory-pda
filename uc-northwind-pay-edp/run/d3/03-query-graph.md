# 03 · Specs + OntoLayer

- Slide: Execute 02–04 (Hands-On **slice a · query**) — tile 03
- Slice: **A · Query**
- Who: every seat, through **their** agent + MCP
- Next: [`04-prompt-sa-plan.md`](04-prompt-sa-plan.md) on the **same board**

Show first. Same paid question without, then with. Mail is not the judge. MCP `catalog_ask` first.

## Prompt 1 — specs (verbatim)

```text
Read docs/adrs/0006-later-nights-parked.md, docs/seams.md, spec/type-01-card-settlement/README.md, and contracts/types/01-card-settlement/README.md as the judge.
Do not change any file.
Do not create modern/.

Answer:
1. What does Constructor consume tonight (landing) and what must it not do (re-parse, own money)?
2. Which 0006 rows open tonight (3–7) vs Thursday (8–9)?
3. Which document wins if inbound prose disagrees with contracts/?
```

## Prompt 2 — graph (verbatim)

```text
Where does “paid” live for Type 01?
Name the reporting table, the grain, and which procedure writes that table.
What grain and keys would dlt register from landing (do not guess joins)?
Use the northwind-ontology MCP tools (catalog_ask) or say to run make ontology-ask.
Do not grep SQL.
Do not change any file.
```

Staff, if MCP is down:

```bash
make ontology-ask-sql
make ontology-ask
```

## Proof

| Ask | A healthy answer |
|---|---|
| Consume | `modern/landing/` Parquet. dlt **registers**. No re-parse |
| 0006 | Rows **3–7** tonight. **8–9** Dagster/serve = Day 4 |
| Judge | `contracts/` |
| Paid | `reporting.card_settlement_reconciliation` · grain `batch_id + currency` · `reporting.refresh_card_settlement_reconciliation` |

Without ontology: 0 SQL hits for the word “paid”. That contrast is the lesson.

## If fail

Graph down → `make deploy && make ontology` **on this checkout only**.
Compose `northwind-pay-legacy` (port 2222 / 54329) is **one plant**. Do
not `make deploy` from a worktree while `main` is up — remap
`COMPOSE_PROJECT_NAME` and ports in `.env`, or stop `main` first. Do
not guess joins. Do not treat staging as paid.
