"""Live rollback-only regression for the production Type 02 loader path.

Type 02 was the only implemented type without this proof. Its loader runs the
same COPY-apply-reconcile-commit transaction as the others, so the same question
has to be answered for it: when the oracle rejects at the reconciliation
boundary, does *everything* disappear — staging rows, operational rows, the
reporting row, and every control-plane record?
"""

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
from type02_loader import (  # noqa: E402
    PreparedType02Load,
    _parse_csv,
    commit_type02_batch,
)


PROBE_BATCH = "B202607230009902"
PROBE_SOURCE = f"NW_INSTANT_PAYMENT_20260723_{PROBE_BATCH}.txt"
CANONICAL_BATCH = "B202607230000101"
CANONICAL_SOURCE = f"NW_INSTANT_PAYMENT_20260723_{CANONICAL_BATCH}.txt"


class _IntentionalRollback(Exception):
    """Stop the transaction after all Type 02 assertions have passed."""


class Type02LoaderRollbackTest(unittest.TestCase):
    """Prove COPY and both procedures disappear on oracle rejection."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.configuration = RuntimeConfiguration.load()

    def test_oracle_callback_failure_rolls_back_the_entire_batch(self) -> None:
        canonical = (
            ROOT
            / "contracts"
            / "types"
            / "02-instant-payment-events"
            / "main"
            / "expected-sanitized.csv"
        ).read_text(encoding="utf-8")
        # Rewrite every identity the schema treats as unique so the probe can
        # never collide with the canonical batch, which must stay untouched.
        csv_bytes = (
            canonical.replace(CANONICAL_BATCH, PROBE_BATCH)
            .replace(CANONICAL_SOURCE, PROBE_SOURCE)
            .replace(
                "E2026072300000000000000000000001",
                "E2026072300000000000000000009901",
            )
            .replace(
                "E2026072300000000000000000000002",
                "E2026072300000000000000000009902",
            )
            .replace("PIXTXN0000000001", "PIXTXN0000009901")
            .replace("PIXTXN0000000002", "PIXTXN0000009902")
            .encode("utf-8")
        )
        source_controls: dict[str, int | str] = {
            "credit_amount": "200.00",
            "currency": "BRL",
            "debit_amount": "26.55",
            "event_count": 2,
            "net_amount": "173.45",
        }
        stage_controls = _parse_csv(
            csv_bytes,
            batch_id=PROBE_BATCH,
            source_filename=PROBE_SOURCE,
        )
        raw = PublishedRaw(
            batch_id=PROBE_BATCH,
            file_type="02",
            filename=PROBE_SOURCE,
            sha256="a" * 64,
            size_bytes=len(csv_bytes),
            manifest_sha256="b" * 64,
            source_controls=source_controls,
        )
        prepared = PreparedType02Load(
            batch_id=PROBE_BATCH,
            raw_filename=PROBE_SOURCE,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_controls=source_controls,
            csv_filename=PROBE_SOURCE.removesuffix(".txt") + ".csv",
            csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
            csv_size_bytes=len(csv_bytes),
            stage_controls=stage_controls,
            csv_bytes=csv_bytes,
        )

        with psycopg.connect(self.configuration.postgres_dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM control.batches WHERE batch_id = %s",
                    (PROBE_BATCH,),
                )
                self.assertEqual(cursor.fetchone(), (0,))

        def reject_after_assertions(reconciliation: object) -> None:
            # The reconciliation must be fully correct at the moment of refusal.
            # A rollback proof is only meaningful if the work being discarded
            # was real.
            self.assertIsInstance(reconciliation, dict)
            assert isinstance(reconciliation, dict)
            self.assertEqual(reconciliation["status"], "MATCHED")
            self.assertEqual(reconciliation["source_count"], 2)
            self.assertEqual(reconciliation["staged_count"], 2)
            self.assertEqual(reconciliation["applied_count"], 2)
            self.assertEqual(reconciliation["applied_credit_amount"], "200.00")
            self.assertEqual(reconciliation["applied_debit_amount"], "26.55")
            self.assertEqual(reconciliation["applied_net_amount"], "173.45")
            self.assertEqual(reconciliation["applied_returned_count"], 1)
            raise _IntentionalRollback

        with self.assertRaises(_IntentionalRollback):
            commit_type02_batch(
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
            ("staging.instant_payment_event", "batch_id"),
            ("legacy.instant_payment_event", "batch_id"),
            ("reporting.instant_payment_reconciliation", "batch_id"),
        )
        with psycopg.connect(self.configuration.postgres_dsn) as connection:
            with connection.cursor() as cursor:
                for table, column in checks:
                    with self.subTest(table=table):
                        cursor.execute(
                            f"SELECT count(*) FROM {table} WHERE {column} = %s",
                            (PROBE_BATCH,),
                        )
                        self.assertEqual(cursor.fetchone(), (0,))


if __name__ == "__main__":
    unittest.main()
