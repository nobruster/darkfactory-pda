# 06 · Specs + OntoLayer

- Slide: Execute 05–06 (Hands-On **slice c · query**) — tile 06
- Slice: **C · Query**
- Who: every seat, through **their** agent + MCP
- Next: Dig Show Converge + Seamwise, then [`07-prompt-kits.md`](07-prompt-kits.md) on Execute 07–10

Show first. Same question without, then with. Mail is not the judge. MCP `catalog_ask` first.

## Prompt 1 — specs (verbatim)

```text
Read docs/tech-spec-type-01-card-settlement.md and spec/type-01-card-settlement/README.md.
You may read contracts/types/01-card-settlement/README.md as the judge.
Do not change any file.
Do not create modern/.

Answer:
1. What will we build (five-file package, first write)?
2. What must we not do (Java import, CSV-as-input, SFTP as modern destination, dlt, Type 06)?
3. Which document wins if inbound prose disagrees with contracts/?
```

## Prompt 2 — graph (verbatim)

```text
Where does “paid” live for Type 01?
Name the reporting table, the grain, and which procedure writes that table.
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
| Build | `model → parser → schema → writer → handler` → `modern/landing/` Parquet |
| Not | Java import, SFTP CSV as modern input, dlt tonight |
| Judge | `contracts/` |
| Paid | `reporting.card_settlement_reconciliation` · grain `batch_id + currency` |

## If fail

Graph down → `make deploy && make ontology`. Do not guess joins. Specs missing → name the gap; do not invent a stack.
