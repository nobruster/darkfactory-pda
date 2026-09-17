"""SQL-only without path must not retrieve the catalog triad."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from retrieve import CANONICAL_QUESTION
from sql_only import SQL_ROOT, answer_from_sql

REPORTING = "reporting.card_settlement_reconciliation"
REFRESH = "reporting.refresh_card_settlement_reconciliation"


class SqlOnlyTests(unittest.TestCase):
    def test_paid_question_does_not_retrieve_catalog_triad(self) -> None:
        self.assertTrue(SQL_ROOT.is_dir(), "legacy/postgres must exist")
        text = answer_from_sql(CANONICAL_QUESTION)
        self.assertIn("WITHOUT ontology", text)
        self.assertIn("Hits for the word 'paid': 0", text)
        self.assertIn("apply_card_settlement", text)
        has_reporting = REPORTING in text
        has_refresh = REFRESH in text
        has_grain = "batch_id" in text and "currency" in text
        self.assertFalse(
            has_reporting and has_refresh and has_grain,
            "SQL-only grep must not assemble the catalog triad",
        )


if __name__ == "__main__":
    unittest.main()
