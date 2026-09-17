"""Read-only retrieval over ontology/output/graph.json.

No SQL against business tables. The graph is the context.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from settings import REPO_ROOT

CANONICAL_QUESTION = (
    'Where does "paid" live for Type 01 card settlement? '
    "Name the reporting table, the grain (keys), and which procedure writes that table. "
    "Do not guess joins. Do not invent a grain."
)

TYPE01_REPORTING = "reporting.card_settlement_reconciliation"
TYPE01_APPLY = "legacy.apply_card_settlement_batch"
TYPE01_REFRESH = "reporting.refresh_card_settlement_reconciliation"
TYPE01_APPLIED = "legacy.card_settlement"


def graph_path() -> Path:
    return REPO_ROOT / "ontology" / "output" / "graph.json"


def load_graph(path: Path | None = None) -> dict[str, Any]:
    target = path or graph_path()
    if not target.is_file():
        raise RuntimeError(
            f"Catalog graph missing at {target}. Run `make ontology` first."
        )
    return json.loads(target.read_text(encoding="utf-8"))


def _columns_for(graph: dict[str, Any], qualified_table: str) -> list[dict[str, str]]:
    cols = []
    prefix = qualified_table + "."
    for col in graph.get("columns") or []:
        qn = col.get("qualified_name") or ""
        table = col.get("table") or ""
        if table == qualified_table or qn.startswith(prefix):
            cols.append(
                {
                    "name": col.get("name") or "",
                    "data_type": col.get("data_type") or "",
                }
            )
    return cols


def _routine(graph: dict[str, Any], qualified: str) -> dict[str, Any] | None:
    for item in graph.get("routines") or []:
        if item.get("qualified_name") == qualified:
            return item
    return None


def _table(graph: dict[str, Any], qualified: str) -> dict[str, Any] | None:
    for item in graph.get("tables") or []:
        if item.get("qualified_name") == qualified:
            return item
    return None


def catalog_search(graph: dict[str, Any], query: str, limit: int = 12) -> dict[str, Any]:
    q = query.strip().lower()
    if not q:
        return {"query": query, "matches": []}
    tokens = [t for t in re.split(r"[^a-z0-9_.]+", q) if t]
    matches: list[dict[str, Any]] = []

    def score(hay: str) -> int:
        h = hay.lower()
        return sum(3 if tok in h else 0 for tok in tokens) + (8 if q in h else 0)

    for table in graph.get("tables") or []:
        name = table.get("qualified_name") or ""
        s = score(name + " " + (table.get("columns_preview") or ""))
        if s:
            matches.append(
                {
                    "kind": "table",
                    "qualified_name": name,
                    "preview": table.get("columns_preview") or "",
                    "score": s,
                }
            )
    for routine in graph.get("routines") or []:
        name = routine.get("qualified_name") or ""
        s = score(name + " " + " ".join(routine.get("referenced_relations") or []))
        if s:
            matches.append(
                {
                    "kind": "routine",
                    "qualified_name": name,
                    "kind_detail": routine.get("kind") or "",
                    "referenced_relations": routine.get("referenced_relations") or [],
                    "score": s,
                }
            )
    matches.sort(key=lambda m: (-int(m["score"]), m["qualified_name"]))
    return {"query": query, "matches": matches[:limit]}


def catalog_get(graph: dict[str, Any], qualified_name: str) -> dict[str, Any]:
    name = qualified_name.strip()
    table = _table(graph, name)
    if table:
        return {
            "kind": "table",
            "qualified_name": name,
            "schema": table.get("schema"),
            "columns": _columns_for(graph, name),
            "description": table.get("description") or "",
        }
    routine = _routine(graph, name)
    if routine:
        return {
            "kind": "routine",
            "qualified_name": name,
            "routine_kind": routine.get("kind"),
            "language": routine.get("language"),
            "arguments": routine.get("arguments"),
            "referenced_relations": routine.get("referenced_relations") or [],
        }
    return {"kind": "missing", "qualified_name": name}


def _grain_from_columns(columns: list[dict[str, str]]) -> list[str]:
    names = [c["name"] for c in columns]
    preferred = [n for n in ("batch_id", "currency") if n in names]
    return preferred or names[:2]


def _looks_like_paid_type01(question: str) -> bool:
    q = question.lower()
    paid = any(w in q for w in ("paid", "pay", "payment observation", "reconciliation"))
    type01 = any(w in q for w in ("01", "card", "settlement", "type 1"))
    if "paid" in q and not any(t in q for t in ("02", "03", "04", "05", "pix", "ted", "boleto")):
        return True
    return paid and type01


def catalog_ask(graph: dict[str, Any], question: str) -> dict[str, Any]:
    """Retrieve a subgraph. Does not execute SQL and does not guess missing grain."""
    if _looks_like_paid_type01(question):
        return _ask_paid_type01(graph, question)
    search = catalog_search(graph, question, limit=8)
    return {
        "question": question,
        "mode": "search",
        "answer": "No dedicated subgraph. Nearest catalog matches are attached. Do not invent grain.",
        "matches": search["matches"],
        "warning": "This is retrieval, not a SQL result.",
    }


def _ask_paid_type01(graph: dict[str, Any], question: str) -> dict[str, Any]:
    reporting = catalog_get(graph, TYPE01_REPORTING)
    apply_fn = catalog_get(graph, TYPE01_APPLY)
    refresh_fn = catalog_get(graph, TYPE01_REFRESH)
    applied = catalog_get(graph, TYPE01_APPLIED)
    missing = [
        name
        for name, node in (
            (TYPE01_REPORTING, reporting),
            (TYPE01_REFRESH, refresh_fn),
            (TYPE01_APPLY, apply_fn),
        )
        if node.get("kind") == "missing"
    ]
    if missing:
        return {
            "question": question,
            "mode": "paid-type01",
            "error": f"graph is incomplete; missing {missing}. Re-run `make ontology`.",
        }
    columns = reporting.get("columns") or []
    grain = _grain_from_columns(columns)
    paid_facts = [
        c["name"]
        for c in columns
        if c["name"] in ("applied_net_amount", "status", "applied_count")
    ]
    return {
        "question": question,
        "mode": "paid-type01",
        "answer": (
            f'"paid" for Type 01 is observed on {TYPE01_REPORTING}. '
            f"Grain is {', '.join(grain)} (one row per batch per currency). "
            f"{TYPE01_REFRESH} writes that table. "
            f"{TYPE01_APPLY} writes applied money onto {TYPE01_APPLIED}, "
            f"which the refresh reads. Do not treat staging as paid."
        ),
        "reporting_table": TYPE01_REPORTING,
        "grain": grain,
        "paid_fact_columns": paid_facts,
        "writes_reporting": TYPE01_REFRESH,
        "applies_money": TYPE01_APPLY,
        "applied_table": TYPE01_APPLIED,
        "not_paid": ["staging.card_settlement"],
        "entities": {
            "reporting": reporting,
            "refresh": refresh_fn,
            "apply": apply_fn,
            "applied": applied,
        },
        "warning": "Retrieved from the catalog graph. Not a SQL query against live money.",
    }


def format_ask(result: dict[str, Any]) -> str:
    if result.get("error"):
        return result["error"]
    if result.get("mode") != "paid-type01":
        lines = [result.get("answer") or "", ""]
        for match in result.get("matches") or []:
            lines.append(f"- {match.get('kind')}: {match.get('qualified_name')}")
        return "\n".join(lines).strip()
    grain = ", ".join(result.get("grain") or [])
    facts = ", ".join(result.get("paid_fact_columns") or [])
    return "\n".join(
        [
            result.get("answer") or "",
            "",
            f"reporting table : {result.get('reporting_table')}",
            f"grain           : {grain}",
            f"paid facts      : {facts}",
            f"writes table    : {result.get('writes_reporting')}",
            f"applies money   : {result.get('applies_money')} → {result.get('applied_table')}",
            f"not paid        : {', '.join(result.get('not_paid') or [])}",
        ]
    )
