"""Live rollback-only regression for the production Type 01 loader path."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[2]
for module_directory in (
    ROOT / "legacy" / "runner",
    ROOT / "legacy" / "publisher",
    ROOT / "legacy" / "postgres",
):
    sys.path.insert(0, str(module_directory))

from config import RuntimeConfiguration  # noqa: E402
from raw_publisher import PublishedRaw  # noqa: E402
from type01_loader import (  # noqa: E402
    PreparedType01Load,
    _parse_csv,
    commit_type01_batch,
)


PROBE_BATCH = "B202607230009901"
PROBE_SOURCE = f"NW_CARD_SETTLEMENT_20260723_{PROBE_BATCH}.dat"


class _IntentionalRollback(Exception):
    """Stop the transaction after all Type 01 assertions have passed."""


class Type01LoaderRollbackTest(unittest.TestCase):
    """Prove COPY and both procedures disappear on oracle rejection."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.configuration = RuntimeConfiguration.load()

    def test_oracle_callback_failure_rolls_back_the_entire_batch(self) -> None:
        canonical = (
            ROOT
            / "contracts"
            / "types"
            / "01-card-settlement"
            / "main"
            / "expected-sanitized.csv"
        ).read_text(encoding="utf-8")
        csv_bytes = (
            canonical.replace(
                "B202607230000001",
                PROBE_BATCH,
            )
            .replace(
                "TXN0000000000001",
                "TXN0000000009901",
            )
            .replace(
                "TXN0000000000002",
                "TXN0000000009902",
            )
            .encode("utf-8")
        )
        rows, row_count, net_amount = _parse_csv(
            csv_bytes,
            batch_id=PROBE_BATCH,
            source_filename=PROBE_SOURCE,
        )
        source_controls: dict[str, int | str] = {
            "currency": "BRL",
            "detail_count": 2,
            "net_amount": "173.45",
        }
        raw = PublishedRaw(
            batch_id=PROBE_BATCH,
            file_type="01",
            filename=PROBE_SOURCE,
            sha256="a" * 64,
            size_bytes=338,
            manifest_sha256="b" * 64,
            source_controls=source_controls,
        )
        prepared = PreparedType01Load(
            batch_id=PROBE_BATCH,
            raw_filename=PROBE_SOURCE,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_count=2,
            source_net_amount="173.45",
            csv_filename=PROBE_SOURCE.removesuffix(".dat") + ".csv",
            csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
            csv_size_bytes=len(csv_bytes),
            row_count=row_count,
            net_amount=format(net_amount, ".2f"),
            rows=rows,
        )

        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM control.batches WHERE batch_id = %s",
                    (PROBE_BATCH,),
                )
                self.assertEqual(cursor.fetchone(), (0,))

        def reject_after_assertions(
            reconciliation: object,
        ) -> None:
            self.assertIsInstance(reconciliation, dict)
            assert isinstance(reconciliation, dict)
            self.assertEqual(
                reconciliation,
                {
                    "batch_id": PROBE_BATCH,
                    "currency": "BRL",
                    "source_count": 2,
                    "staged_count": 2,
                    "applied_count": 2,
                    "source_net_amount": "173.45",
                    "staged_net_amount": "173.45",
                    "applied_net_amount": "173.45",
                    "count_delta": 0,
                    "amount_delta": "0.00",
                    "reject_count": 0,
                    "status": "MATCHED",
                },
            )
            raise _IntentionalRollback

        with self.assertRaises(_IntentionalRollback):
            commit_type01_batch(
                prepared,
                raw=raw,
                configuration=self.configuration,
                reconciliation_validator=reject_after_assertions,
            )

        checks = (
            "control.batches",
            "control.files",
            "control.loads",
            "control.procedure_runs",
            "staging.card_settlement",
            "legacy.card_settlement",
            "reporting.card_settlement_reconciliation",
        )
        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                for table in checks:
                    with self.subTest(table=table):
                        cursor.execute(
                            f"SELECT count(*) FROM {table} "
                            "WHERE batch_id = %s",
                            (PROBE_BATCH,),
                        )
                        self.assertEqual(cursor.fetchone(), (0,))


if __name__ == "__main__":
    unittest.main()
