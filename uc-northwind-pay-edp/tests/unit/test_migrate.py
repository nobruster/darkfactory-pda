"""Unit tests for the versioned PostgreSQL migration runner."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from migrate import MigrationError, discover_migrations


class DiscoverMigrationsTest(unittest.TestCase):
    """Validate ordering and immutable migration identity."""

    def test_discovers_global_order_across_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "migrations").mkdir()
            (root / "procedures").mkdir()
            first = root / "migrations" / "001_base.sql"
            second = root / "procedures" / "002_functions.sql"
            first.write_text("\\set ON_ERROR_STOP on\nSELECT 1;\n")
            second.write_text("SELECT 2;\n")

            migrations = discover_migrations(root)

            self.assertEqual(("001", "002"), tuple(
                migration.version for migration in migrations
            ))
            self.assertNotIn("\\set", migrations[0].sql)
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                migrations[0].sha256,
            )

    def test_duplicate_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "migrations").mkdir()
            (root / "procedures").mkdir()
            (root / "migrations" / "001_base.sql").write_text("SELECT 1;\n")
            (root / "procedures" / "001_again.sql").write_text("SELECT 2;\n")

            with self.assertRaisesRegex(
                MigrationError,
                "Duplicate PostgreSQL migration versions: 001",
            ):
                discover_migrations(root)

    def test_unversioned_sql_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "migrations").mkdir()
            (root / "procedures").mkdir()
            (root / "migrations" / "base.sql").write_text("SELECT 1;\n")

            with self.assertRaisesRegex(
                MigrationError,
                "Migration filename is not versioned",
            ):
                discover_migrations(root)


if __name__ == "__main__":
    unittest.main()
