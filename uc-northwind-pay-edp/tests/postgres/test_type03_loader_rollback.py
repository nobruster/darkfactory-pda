"""Live rollback-only regression for the production Type 03 loader path."""

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
from type03_loader import (  # noqa: E402
    PreparedType03Load,
    _parse_csv,
    commit_type03_batch,
)


PROBE_BATCH = "B202607230009903"
PROBE_SOURCE = f"NW_PAYMENT_SLIP_20260723_{PROBE_BATCH}.rem"


class _IntentionalRollback(Exception):
    """Stop the transaction after all Type 03 assertions have passed."""


class Type03LoaderRollbackTest(unittest.TestCase):
    """Prove COPY and both procedures disappear on oracle rejection."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.configuration = RuntimeConfiguration.load()

    def test_oracle_callback_failure_rolls_back_the_entire_batch(self) -> None:
        canonical = (
            ROOT
            / "contracts"
            / "types"
            / "03-payment-slip-settlement"
            / "main"
            / "expected-sanitized.csv"
        ).read_text(encoding="utf-8")
        csv_bytes = (
            canonical.replace(
                "B202607230000201",
                PROBE_BATCH,
            )
            .replace(
                "PSL0000000000001",
                "PSL0000000009903",
            )
            .replace(
                "PSL0000000000002",
                "PSL0000000009904",
            )
            .encode("utf-8")
        )
        source_controls: dict[str, int | str] = {
            "currency": "BRL",
            "discount_amount": "5.00",
            "face_amount": "200.00",
            "fee_amount": "3.50",
            "logical_count": 2,
            "lot_count": 1,
            "net_amount": "198.50",
            "orphan_segment_count": 0,
            "physical_record_count": 8,
        }
        stage_controls = _parse_csv(
            csv_bytes,
            batch_id=PROBE_BATCH,
            source_filename=PROBE_SOURCE,
            expected_lot_count=1,
            expected_physical_record_count=8,
        )
        raw = PublishedRaw(
            batch_id=PROBE_BATCH,
            file_type="03",
            filename=PROBE_SOURCE,
            sha256="a" * 64,
            size_bytes=1936,
            manifest_sha256="b" * 64,
            source_controls=source_controls,
        )
        prepared = PreparedType03Load(
            batch_id=PROBE_BATCH,
            raw_filename=PROBE_SOURCE,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_controls=source_controls,
            csv_filename=PROBE_SOURCE.removesuffix(".rem") + ".csv",
            csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
            csv_size_bytes=len(csv_bytes),
            stage_controls=stage_controls,
            csv_bytes=csv_bytes,
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
            self.assertEqual(reconciliation["status"], "MATCHED")
            self.assertEqual(reconciliation["source_count"], 2)
            self.assertEqual(reconciliation["staged_count"], 2)
            self.assertEqual(reconciliation["applied_count"], 2)
            self.assertEqual(
                reconciliation["applied_face_amount"],
                "200.00",
            )
            self.assertEqual(
                reconciliation["applied_discount_amount"],
                "5.00",
            )
            self.assertEqual(
                reconciliation["applied_fee_amount"],
                "3.50",
            )
            self.assertEqual(
                reconciliation["applied_net_amount"],
                "198.50",
            )
            self.assertEqual(
                reconciliation["applied_orphan_segment_count"],
                0,
            )
            raise _IntentionalRollback

        with self.assertRaises(_IntentionalRollback):
            commit_type03_batch(
                prepared,
                raw=raw,
                configuration=self.configuration,
                reconciliation_validator=reject_after_assertions,
            )

        checks = (
            ("control.batches", "batch_id"),
            ("control.files", "batch_id"),
            ("control.loads", "batch_id"),
            ("control.procedure_runs", "batch_id"),
            ("staging.payment_slip_settlement", "batch_id"),
            ("legacy.payment_slip_settlement", "batch_id"),
            (
                "reporting.payment_slip_settlement_reconciliation",
                "batch_id",
            ),
        )
        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                for table, column in checks:
                    with self.subTest(table=table):
                        cursor.execute(
                            f"SELECT count(*) FROM {table} "
                            f"WHERE {column} = %s",
                            (PROBE_BATCH,),
                        )
                        self.assertEqual(cursor.fetchone(), (0,))


if __name__ == "__main__":
    unittest.main()
