"""Minimal MCP stdio server over the catalog graph.

Implements initialize / tools/list / tools/call / ping.
Does not execute SQL. Reads ontology/output/graph.json.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from retrieve import (
    CANONICAL_QUESTION,
    catalog_ask,
    catalog_get,
    catalog_search,
    format_ask,
    load_graph,
)

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "northwind-ontology"
SERVER_VERSION = "0.1.0"

TOOLS = [
    {
        "name": "catalog_search",
        "description": (
            "Search the NorthWind Pay catalog graph for tables and routines. "
            "Read-only. Does not run SQL."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Name or keyword (e.g. paid, card_settlement, apply)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "catalog_get",
        "description": (
            "Get one table (with columns) or one routine (with referenced relations) "
            "by qualified_name such as reporting.card_settlement_reconciliation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "qualified_name": {
                    "type": "string",
                    "description": "schema.name (table or routine)",
                },
            },
            "required": ["qualified_name"],
        },
    },
    {
        "name": "catalog_ask",
        "description": (
            "Ask the catalog a business question. Use this for the Day 1 contrast query: "
            + CANONICAL_QUESTION
            + " Retrieves grain and writers from the graph. Never guesses."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Natural-language question"},
            },
            "required": ["question"],
        },
    },
]


def _text_result(payload: Any) -> dict[str, Any]:
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
    return {"content": [{"type": "text", "text": text}]}


def dispatch_tool(name: str, arguments: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    if name == "catalog_search":
        return _text_result(catalog_search(graph, str(arguments.get("query") or "")))
    if name == "catalog_get":
        return _text_result(catalog_get(graph, str(arguments.get("qualified_name") or "")))
    if name == "catalog_ask":
        asked = catalog_ask(graph, str(arguments.get("question") or ""))
        return _text_result({"structured": asked, "prose": format_ask(asked)})
    raise ValueError(f"Unknown tool: {name}")


def handle(message: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") or {}

    if method == "notifications/initialized" or method == "notifications/cancelled":
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        try:
            result = dispatch_tool(str(params.get("name") or ""), params.get("arguments") or {}, graph)
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            }

    if msg_id is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def _read_stdio_message(buf) -> dict[str, Any] | None:
    """MCP stdio uses LSP-style Content-Length framing."""
    headers: dict[str, str] = {}
    while True:
        line = buf.readline()
        if line == b"":
            return None
        if line in (b"\n", b"\r\n"):
            break
        try:
            decoded = line.decode("utf-8")
        except UnicodeDecodeError:
            return None
        if ":" not in decoded:
            continue
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length") or "0")
    if length <= 0:
        return None
    body = buf.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _write_stdio_message(buf, message: dict[str, Any]) -> None:
    body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    buf.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    buf.write(body)
    buf.flush()


def serve_stdio(graph: dict[str, Any] | None = None) -> None:
    catalog = graph if graph is not None else load_graph()
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        try:
            message = _read_stdio_message(stdin)
        except (json.JSONDecodeError, ValueError):
            continue
        if message is None:
            return
        reply = handle(message, catalog)
        if reply is None:
            continue
        _write_stdio_message(stdout, reply)
