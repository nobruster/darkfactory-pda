"""Unit: pg_proc fixture rows become ProcedureEntity. No live database."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from connectors.postgres import _relations_mentioned
from connectors.routines import procedure_entities_from_rows, truncate_sql
from settings import Settings


class ProcedureMappingTests(unittest.TestCase):
    def test_maps_function_and_procedure_kinds(self) -> None:
        rows = [
            (
                "legacy",
                "apply_card_settlement_batch",
                "p_batch_id text",
                "plpgsql",
                "f",
                "CREATE FUNCTION legacy.apply_card_settlement_batch(p_batch_id text) ...",
            ),
            (
                "control",
                "register_batch",
                "p_batch_id text",
                "plpgsql",
                "p",
                "CREATE PROCEDURE control.register_batch(p_batch_id text) ...",
            ),
        ]
        edges = {
            ("legacy", "apply_card_settlement_batch"): [
                "legacy.card_settlement",
                "reporting.card_settlement_reconciliation",
            ]
        }
        entities = procedure_entities_from_rows(rows, edges)
        self.assertEqual(len(entities), 2)
        apply_fn = entities[0]
        self.assertEqual(apply_fn.schema_name, "legacy")
        self.assertEqual(apply_fn.name, "apply_card_settlement_batch")
        self.assertEqual(apply_fn.qualified_name, "legacy.apply_card_settlement_batch")
        self.assertEqual(apply_fn.kind, "function")
        self.assertEqual(apply_fn.language, "plpgsql")
        self.assertEqual(
            apply_fn.referenced_relations,
            ["legacy.card_settlement", "reporting.card_settlement_reconciliation"],
        )
        self.assertEqual(entities[1].kind, "procedure")
        self.assertEqual(entities[1].qualified_name, "control.register_batch")

    def test_truncates_huge_definitions(self) -> None:
        body = "x" * 200
        cut = truncate_sql(body, 50)
        self.assertTrue(cut.endswith("-- [truncated]"))
        self.assertLessEqual(len(cut), 50)

    def test_mentions_known_relations_in_sql(self) -> None:
        sql = "INSERT INTO reporting.card_settlement_reconciliation SELECT * FROM legacy.card_settlement"
        found = _relations_mentioned(
            sql,
            [
                "legacy.card_settlement",
                "reporting.card_settlement_reconciliation",
                "control.batches",
            ],
        )
        self.assertEqual(
            found,
            [
                "legacy.card_settlement",
                "reporting.card_settlement_reconciliation",
            ],
        )

    def test_schema_filter_never_defaults_public(self) -> None:
        empty = Settings(postgres_schema_filter="")
        self.assertEqual(
            empty.schema_names(),
            ("control", "staging", "legacy", "reporting"),
        )
        public_only = Settings(postgres_schema_filter="public")
        self.assertEqual(
            public_only.schema_names(),
            ("control", "staging", "legacy", "reporting"),
        )


if __name__ == "__main__":
    unittest.main()
