"""Crawl live Postgres into an EntityStore, then a JSON graph. No OpenSearch."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from connectors import get_connector
from entities import EntityStore
from settings import REPO_ROOT, settings

logger = logging.getLogger(__name__)

SOURCE_SHA = "189b245efe3301c09727529eca47d8094b313d72"


def store_to_graph(store: EntityStore, schemas: tuple[str, ...]) -> dict[str, Any]:
    tables = [
        {
            "id": t.id,
            "schema": t.schema_name,
            "name": t.name,
            "qualified_name": t.qualified_name,
            "column_count": t.column_count,
            "columns_preview": t.columns_preview,
            "description": t.description,
        }
        for t in store.tables
    ]
    columns = [
        {
            "id": c.id,
            "table": c.table_name,
            "name": c.name,
            "qualified_name": c.qualified_name,
            "data_type": c.data_type,
            "description": c.description,
        }
        for c in store.columns
    ]
    relationships = [
        {
            "id": r.id,
            "from_table": r.from_table,
            "from_column": r.from_column,
            "to_table": r.to_table,
            "to_column": r.to_column,
            "relation_type": r.relation_type,
        }
        for r in store.relationships
    ]
    views = [
        {
            "id": v.id,
            "schema": v.schema_name,
            "name": v.name,
            "qualified_name": v.qualified_name,
            "column_names": v.column_names,
            "referenced_tables": v.referenced_tables,
            "description": v.description,
        }
        for v in store.views
    ]
    routines = [
        {
            "id": p.id,
            "schema": p.schema_name,
            "name": p.name,
            "qualified_name": p.qualified_name,
            "kind": p.kind,
            "language": p.language,
            "arguments": p.arguments,
            "referenced_relations": p.referenced_relations,
            "description": p.description,
        }
        for p in store.procedures
    ]
    present_schemas = sorted(
        {t.schema_name for t in store.tables if t.schema_name}
        | {p.schema_name for p in store.procedures if p.schema_name}
        | {v.schema_name for v in store.views if v.schema_name}
    )
    return {
        "source": {
            "ontolayer_sha": SOURCE_SHA,
            "connector": "postgres",
            "requested_schemas": list(schemas),
        },
        "schemas": present_schemas,
        "tables": tables,
        "columns": columns,
        "relationships": relationships,
        "views": views,
        "routines": routines,
        "summary": {
            "schema_count": len(present_schemas),
            "table_count": len(tables),
            "column_count": len(columns),
            "relationship_count": len(relationships),
            "view_count": len(views),
            "routine_count": len(routines),
            "routine_names": [p["qualified_name"] for p in routines],
        },
    }


def graph_to_html(graph: dict[str, Any]) -> str:
    summary = graph.get("summary", {})
    schemas = ", ".join(graph.get("schemas") or [])
    routines = "\n".join(
        f"<li><code>{name}</code></li>"
        for name in summary.get("routine_names") or []
    ) or "<li><em>none</em></li>"
    example = _paid_example(graph)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>NorthWind Pay ontology</title>
<style>
  body {{ font: 16px/1.45 system-ui, sans-serif; background:#0b0b0e; color:#eaedf2;
         max-width: 720px; margin: 48px auto; padding: 0 24px; }}
  h1 {{ font-weight: 600; }}
  code {{ color: #8ae4f2; }}
  .k {{ color: #6e7a8c; text-transform: uppercase; letter-spacing: .12em; font-size: 12px; }}
  ul {{ padding-left: 1.2em; }}
</style>
</head>
<body>
  <p class="k">grant crawl · read-only</p>
  <h1>NorthWind Pay as a catalog</h1>
  <p>Four plant schemas: <code>{schemas or "—"}</code>.</p>
  <p>
    <b>{summary.get("table_count", 0)}</b> tables ·
    <b>{summary.get("routine_count", 0)}</b> routines ·
    <b>{summary.get("relationship_count", 0)}</b> foreign keys.
  </p>
  <h2>Routines</h2>
  <ul>{routines}</ul>
  <p>{example}</p>
  <p class="k">this is a graph over live postgres. it does not write the plant.</p>
</body>
</html>
"""


def _paid_example(graph: dict[str, Any]) -> str:
    tables = {t.get("qualified_name") for t in graph.get("tables") or []}
    routines = {r.get("qualified_name") for r in graph.get("routines") or []}
    recon = "reporting.card_settlement_reconciliation"
    refresh = "reporting.refresh_card_settlement_reconciliation"
    apply_fn = "legacy.apply_card_settlement_batch"
    if recon in tables and refresh in routines and apply_fn in routines:
        return (
            f'<b>paid</b> lives on <code>{recon}</code> (grain <code>batch_id</code>, '
            f'<code>currency</code>), written by <code>{refresh}</code>. '
            f'<code>{apply_fn}</code> writes applied money onto '
            f'<code>legacy.card_settlement</code>.'
        )
    return "Open <code>graph.json</code> for tables, columns, FKs, and routines."


def write_graph(graph: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    graph_path = output_dir / "graph.json"
    html_path = output_dir / "index.html"
    summary_path = output_dir / "summary.txt"
    graph_path.write_text(json.dumps(graph, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    html_path.write_text(graph_to_html(graph), encoding="utf-8")
    summary = graph["summary"]
    lines = [
        f"schemas: {', '.join(graph['schemas'])}",
        f"tables: {summary['table_count']}",
        f"routines: {summary['routine_count']}",
        "routine names:",
        *[f"  - {name}" for name in summary["routine_names"]],
    ]
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return graph_path


async def crawl(output_dir: Path | None = None) -> dict[str, Any]:
    dsn = settings.dsn()
    schemas = settings.schema_names()
    connector = get_connector(
        "postgres",
        connection_string=dsn,
        schema_filter=",".join(schemas),
        definition_sql_max_chars=settings.definition_sql_max_chars,
    )
    ok = await connector.fetch()
    if not ok:
        raise RuntimeError(
            "Catalog crawl failed. Run `make deploy` and confirm `make status` is healthy."
        )
    result = connector.process()
    store = result.entity_store
    if store is None:
        raise RuntimeError("Connector returned no entity store.")
    graph = store_to_graph(store, result.schemas or schemas)
    dest = output_dir or (REPO_ROOT / "ontology" / "output")
    write_graph(graph, dest)
    connector.close()
    return graph


def crawl_sync(output_dir: Path | None = None) -> dict[str, Any]:
    return asyncio.run(crawl(output_dir))
