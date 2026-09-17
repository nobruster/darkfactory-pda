"""Catalog ask: the Day 1 paid question is retrieved, not guessed."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp_stdio import handle
from retrieve import (
    CANONICAL_QUESTION,
    catalog_ask,
    catalog_get,
    format_ask,
    graph_path,
    load_graph,
)


def _fixture_graph() -> dict:
    return {
        "tables": [
            {
                "qualified_name": "reporting.card_settlement_reconciliation",
                "schema": "reporting",
                "columns_preview": "batch_id, currency, applied_net_amount",
                "description": "",
            },
            {
                "qualified_name": "legacy.card_settlement",
                "schema": "legacy",
                "columns_preview": "batch_id, amount_brl",
                "description": "",
            },
            {
                "qualified_name": "staging.card_settlement",
                "schema": "staging",
                "columns_preview": "batch_id, amount_brl",
                "description": "",
            },
        ],
        "columns": [
            {"table": "reporting.card_settlement_reconciliation", "qualified_name": "reporting.card_settlement_reconciliation.batch_id", "name": "batch_id", "data_type": "text"},
            {"table": "reporting.card_settlement_reconciliation", "qualified_name": "reporting.card_settlement_reconciliation.currency", "name": "currency", "data_type": "text"},
            {"table": "reporting.card_settlement_reconciliation", "qualified_name": "reporting.card_settlement_reconciliation.applied_net_amount", "name": "applied_net_amount", "data_type": "numeric"},
            {"table": "reporting.card_settlement_reconciliation", "qualified_name": "reporting.card_settlement_reconciliation.status", "name": "status", "data_type": "text"},
        ],
        "routines": [
            {
                "qualified_name": "legacy.apply_card_settlement_batch",
                "kind": "function",
                "language": "plpgsql",
                "arguments": "p_batch_id text",
                "referenced_relations": ["legacy.card_settlement", "staging.card_settlement"],
            },
            {
                "qualified_name": "reporting.refresh_card_settlement_reconciliation",
                "kind": "function",
                "language": "plpgsql",
                "arguments": "p_batch_id text",
                "referenced_relations": [
                    "reporting.card_settlement_reconciliation",
                    "legacy.card_settlement",
                ],
            },
        ],
    }


class RetrieveTests(unittest.TestCase):
    def test_canonical_paid_question_names_grain_and_writer(self) -> None:
        result = catalog_ask(_fixture_graph(), CANONICAL_QUESTION)
        self.assertEqual(result["mode"], "paid-type01")
        self.assertEqual(result["reporting_table"], "reporting.card_settlement_reconciliation")
        self.assertEqual(result["grain"], ["batch_id", "currency"])
        self.assertEqual(
            result["writes_reporting"],
            "reporting.refresh_card_settlement_reconciliation",
        )
        self.assertEqual(result["applies_money"], "legacy.apply_card_settlement_batch")
        self.assertIn("staging.card_settlement", result["not_paid"])
        prose = format_ask(result)
        self.assertIn("reporting.card_settlement_reconciliation", prose)
        self.assertIn("batch_id", prose)
        self.assertNotIn("guess", prose.lower())

    def test_mcp_tools_call_catalog_ask(self) -> None:
        graph = _fixture_graph()
        listed = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, graph)
        names = [t["name"] for t in listed["result"]["tools"]]
        self.assertEqual(names, ["catalog_search", "catalog_get", "catalog_ask"])
        called = handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "catalog_ask",
                    "arguments": {"question": CANONICAL_QUESTION},
                },
            },
            graph,
        )
        text = called["result"]["content"][0]["text"]
        self.assertIn("reporting.refresh_card_settlement_reconciliation", text)
        self.assertIn("batch_id", text)

    def test_get_missing(self) -> None:
        got = catalog_get(_fixture_graph(), "reporting.does_not_exist")
        self.assertEqual(got["kind"], "missing")


@unittest.skipUnless(graph_path().is_file(), "no crawled graph")
class LiveRetrieveTests(unittest.TestCase):
    def test_live_graph_answers_canonical_question(self) -> None:
        result = catalog_ask(load_graph(), CANONICAL_QUESTION)
        self.assertEqual(result.get("reporting_table"), "reporting.card_settlement_reconciliation")
        self.assertEqual(result.get("grain"), ["batch_id", "currency"])
        self.assertEqual(
            result.get("writes_reporting"),
            "reporting.refresh_card_settlement_reconciliation",
        )


if __name__ == "__main__":
    unittest.main()
