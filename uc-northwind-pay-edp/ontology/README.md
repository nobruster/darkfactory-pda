# Ontology — catalog crawl over the live plant

This is the graph over NorthWind Pay Postgres after `make deploy`. It is **not** the use case. It does not write the plant.

OntoLayer (sibling repo) already crawls tables, columns, FKs, and views. This folder vendors that Postgres path, then adds stored routines so a grant room can see **meaning** (`legacy.apply_*` writes `reporting.*_reconciliation`) rather than DDL.

OpenSearch and LLM enrichment stay later seams. **MCP is in this folder:** stdio over `graph.json`, read-only. Day 1 asks the same question without the graph, then with it.

## Connect

Reuse the plant. Do not add a second Postgres.

```text
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=54329
POSTGRES_DB=northwind_legacy
POSTGRES_ADMIN_USER=northwind_admin
POSTGRES_SCHEMA_FILTER=control,staging,legacy,reporting
```

The crawler uses the **admin** DSN so `pg_get_functiondef` works, then opens a **read-only** session. The loader role is for `COPY` + execute, not for showing the ontology.

If `make deploy` has not made Postgres healthy, the crawl fails closed.

## Show

```bash
make deploy
make ontology
```

Writes gitignored artifacts:

| File | What |
|---|---|
| `ontology/output/graph.json` | schemas, tables, columns, FKs, views, routines, routine→table edges |
| `ontology/output/summary.txt` | counts and routine names |
| `ontology/output/index.html` | one-pager for the grant room |

Stdout prints the four schemas, table count, routine names, and one example of the form *paid lives on `reporting.*_reconciliation`, written by `legacy.apply_*`*.

Speak the real routine count. Do not invent 300 procedures.

## Ask (MCP)

The catalog is a context source. It does not run SQL against live money.

```bash
make ontology          # crawl if needed
make ontology-ask      # Day 1 question, stdout (with graph)
make ontology-ask-sql  # same question, legacy/postgres grep only (without)
make ontology-mcp      # stdio MCP server
```

The **one** Floor question (verbatim, both passes):

```text
Where does “paid” live for Type 01 card settlement?
Name the reporting table, the grain (keys), and which procedure writes that table.
Do not guess joins. Do not invent a grain.
```

| Pass | How | What should happen |
|---|---|---|
| Without | Agent may read `legacy/postgres` SQL. No `ontology/`, no MCP | Greps DDL, guesses joins, invents grain |
| With | `catalog_ask` via MCP, or `make ontology-ask` | Retrieves `reporting.card_settlement_reconciliation`, grain `batch_id`+`currency`, writer `reporting.refresh_card_settlement_reconciliation` |

MCP tools (read-only): `catalog_search`, `catalog_get`, `catalog_ask`.

Wire the agent:

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

Staff beat: [`run/d1/13-ontolayer.md`](../run/d1/13-ontolayer.md).

## Freeze

- Read-only crawl. Never write `legacy/`, `contracts/`, `gen/`, `infra/`.
- Do not alter frozen SQL or grants to make the crawler happier.
- Empty or `public` schema filter is replaced by the four plant schemas.

## Tests

```bash
make test-ontology
```

Unit tests map `pg_proc` fixture rows with no database. The live smoke skips when Postgres is down; after `make deploy` it asserts the four schemas and `legacy.apply_card_settlement_batch`.

See [`SOURCE.md`](SOURCE.md) for the OntoLayer SHA and keep/drop list.
