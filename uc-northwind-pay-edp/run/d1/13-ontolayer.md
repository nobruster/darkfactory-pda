# 13 · OntoLayer — the plant, without then with

- Slide: DIG · Show · OntoLayer · the map, then Hands-On Execute 13
- Slice: **E · Graph**
- Who: instructor first, then every seat through **their** agent
- Next: [`14-converge.md`](14-converge.md)

The graph is **live Postgres** (tables, columns, procedures). It is not Converge, not Task-Spec, not the week map. Do not ask it what a kit is.

**First: why this graph exists.** Then the paid contrast. Then dives. Do not skip the without.

---

## Why ontology (verbatim) — read the folder, not the catalog

Paste one. Wait. These three are **not** `catalog_ask`. The agent reads `ontology/README.md`.

**W1 — what an ontology is here**

```text
Read ontology/README.md.
In three sentences: what is this ontology? What does it crawl? What does it not do (no SQL against live money, not the use case)?
Do not change any file.
```

Proof: Graph over live NorthWind Pay Postgres after `make deploy`. Schemas, tables, columns, FKs, views, routines. It does not write the plant. It does not run SQL against business tables.

**W2 — what OntoLayer is**

```text
Read ontology/README.md.
What is OntoLayer, and how does this repo’s ontology/ folder relate to it?
Do not change any file.
```

Proof: OntoLayer is the upstream crawler (sibling). `ontology/` here vendors that Postgres path and adds stored routines so “paid” is meaning, not DDL.

**W3 — why not just grep SQL**

```text
Why do we ask the graph instead of grepping legacy/postgres?
What should be different about the answer with the graph vs without it?
Do not change any file.
```

Proof: Without = guess joins, invent grain. With = retrieve grain, keys, which procedure writes reporting. That contrast is the value.

---

**Then the plant.** One contrast. Then dives. Do not skip the without. Write the contrast on the board before you go deeper.

---

## Contrast (required) — same question, two passes

```text
Where does “paid” live for Type 01 card settlement?
Name the reporting table, the grain (keys), and which procedure writes that table.
Do not guess joins. Do not invent a grain.
```

### Pass A — without the graph

Staff deterministic baseline (SQL grep, no graph):

```bash
make ontology-ask-sql
```

Agent (may read SQL, must not use the catalog):

```text
Where does “paid” live for Type 01 card settlement?
Name the reporting table, the grain (keys), and which procedure writes that table.
Do not guess joins. Do not invent a grain.

You may read legacy/postgres SQL.
Do not use ontology/.
Do not use MCP.
Do not change any file.
```

Typical misses — leave them on the board:

| Guess | Why it is wrong |
|---|---|
| `staging.card_settlement` is paid | Staging is COPY. Not applied money. |
| `legacy.apply_card_settlement_batch` writes reporting | It writes `legacy.card_settlement`. |
| Grain is `transaction_id` / a row in the file | Reporting is **batch + currency**. |

### Pass B — with the graph

Staff, if MCP is not wired:

```bash
make ontology
make ontology-ask
```

Agent with MCP:

```text
Where does “paid” live for Type 01 card settlement?
Name the reporting table, the grain (keys), and which procedure writes that table.
Do not guess joins. Do not invent a grain.

Use the northwind-ontology MCP tools (catalog_ask).
Do not grep SQL.
Do not change any file.
```

### Proof (must match the catalog)

| Fact | From the graph |
|---|---|
| Paid is observed on | `reporting.card_settlement_reconciliation` |
| Grain | `batch_id`, `currency` |
| Paid facts | `applied_net_amount`, `status`, `applied_count` |
| Writes that table | `reporting.refresh_card_settlement_reconciliation` |
| Applies money | `legacy.apply_card_settlement_batch` → `legacy.card_settlement` |
| Not paid | `staging.card_settlement` |

Board: **without guessed; with retrieved.** Then the dives.

---

## Dives (with the graph only)

Paste one. Wait. Then the next. Still Type 01. Still no SQL against live money.

**D1 — staging is not paid**

```text
Is staging.card_settlement paid money for Type 01?
If not, which table is the applied money, and which procedure writes it?
Use catalog_ask. Do not change any file.
```

Proof: **No.** Applied money is `legacy.card_settlement`, written by `legacy.apply_card_settlement_batch`. Staging is COPY.

**D2 — apply vs refresh**

```text
For Type 01, which procedure applies money, and which procedure writes the reporting reconciliation table?
Name both. Do not mix them.
Use catalog_ask. Do not change any file.
```

Proof: apply → `legacy.apply_card_settlement_batch`. Reporting → `reporting.refresh_card_settlement_reconciliation`.

**D3 — grain**

```text
What is the grain of reporting.card_settlement_reconciliation?
Name the keys. Do not invent transaction_id.
Use catalog_ask. Do not change any file.
```

Proof: `batch_id`, `currency`. One row per batch per currency.

**D4 — the four schemas (whole plant)**

```text
Read ontology/README.md. Which four schemas does the crawl include?
Do not invent a fifth. Do not change any file.
```

Proof: `control`, `staging`, `legacy`, `reporting`.

Do **not** ask the graph: “what is Converge?”, “what is Task-Spec?”, “how do I Capture?”. Those are Slice F. The catalog will search routine names and lie politely.

---

## Wire MCP (once per laptop)

```json
{
  "mcpServers": {
    "northwind-ontology": {
      "command": "legacy/runner/.venv/bin/python",
      "args": ["ontology/scripts/mcp_server.py"],
      "cwd": "<repo root>"
    }
  }
}
```

`make ontology-mcp` is the same server in the foreground. Tools: `catalog_search`, `catalog_get`, `catalog_ask`. Read-only.

---

## If fail

| What happened | What you do |
|---|---|
| `Catalog graph missing` | `make deploy && make ontology`. Do not invent the graph. |
| Agent uses ontology on Pass A | Stop. Repeat Pass A. |
| Agent still greps SQL on Pass B | Instructor runs `make ontology-ask`. |
| Agent asks the graph what Converge is | Stop. That is Slice F. The graph is Postgres. |

Do not start Capture until the without/with line is on the board. Do not write `modern/`.
