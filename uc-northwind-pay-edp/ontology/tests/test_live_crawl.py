"""Opt-in live crawl. Skips when Postgres is down."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from settings import settings


def _postgres_up() -> bool:
    try:
        import psycopg2

        conn = psycopg2.connect(settings.dsn())
        conn.close()
        return True
    except Exception:
        return False


@unittest.skipUnless(_postgres_up(), "Postgres is down — run make deploy")
class LiveCrawlTests(unittest.TestCase):
    def test_four_schemas_and_apply_card_settlement(self) -> None:
        from pipeline import crawl_sync

        with tempfile.TemporaryDirectory() as tmp:
            graph = crawl_sync(Path(tmp))
        schemas = set(graph["schemas"])
        self.assertTrue(
            {"control", "staging", "legacy", "reporting"}.issubset(schemas),
            f"missing plant schemas in {schemas}",
        )
        names = set(graph["summary"]["routine_names"])
        self.assertIn("legacy.apply_card_settlement_batch", names)


if __name__ == "__main__":
    unittest.main()
