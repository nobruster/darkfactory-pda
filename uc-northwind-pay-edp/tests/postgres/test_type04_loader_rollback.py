"""Live rollback-only regression for the production Type 04 loader path."""

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
from type04_loader import (  # noqa: E402
    PreparedType04Load,
    _parse_csv,
    commit_type04_batch,
)


PROBE_BATCH = "B202607230009904"
PROBE_SOURCE = f"NW_TED_SETTLEMENT_20260723_{PROBE_BATCH}.dat"


class _IntentionalRollback(Exception):
    """Stop the transaction after all Type 04 assertions have passed."""


class Type04LoaderRollbackTest(unittest.TestCase):
    """Prove COPY and both procedures disappear on oracle rejection."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.configuration = RuntimeConfiguration.load()

    def test_oracle_callback_failure_rolls_back_the_entire_batch(self) -> None:
        canonical = (
            ROOT
            / "contracts"
            / "types"
            / "04-ted-transfer-settlement"
            / "main"
            / "expected-sanitized.csv"
        ).read_text(encoding="utf-8")
        csv_bytes = (
            canonical.replace(
                "B202607230000301",
                PROBE_BATCH,
            )
            .replace(
                "TED2026072300301",
                "TED2026072309904",
            )
            .replace(
                "TED2026072301301",
                "TED2026072319904",
            )
            .replace(
                "RET2026072300301",
                "RET2026072309904",
            )
            .encode("utf-8")
        )
        source_controls: dict[str, int | str] = {
            "currency": "BRL",
            "gross_amount": "1250.00",
            "net_amount": "1000.00",
            "return_amount": "-250.00",
            "return_count": 1,
            "transfer_count": 2,
        }
        stage_controls = _parse_csv(
            csv_bytes,
            batch_id=PROBE_BATCH,
            source_filename=PROBE_SOURCE,
        )
        raw = PublishedRaw(
            batch_id=PROBE_BATCH,
            file_type="04",
            filename=PROBE_SOURCE,
            sha256="a" * 64,
            size_bytes=563,
            manifest_sha256="b" * 64,
            source_controls=source_controls,
        )
        prepared = PreparedType04Load(
            batch_id=PROBE_BATCH,
            raw_filename=PROBE_SOURCE,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_controls=source_controls,
            csv_filename=PROBE_SOURCE.removesuffix(".dat") + ".csv",
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
            self.assertEqual(reconciliation["source_transfer_count"], 2)
            self.assertEqual(reconciliation["staged_transfer_count"], 2)
            self.assertEqual(reconciliation["applied_transfer_count"], 2)
            self.assertEqual(reconciliation["source_return_count"], 1)
            self.assertEqual(reconciliation["staged_return_count"], 1)
            self.assertEqual(reconciliation["applied_return_count"], 1)
            self.assertEqual(
                reconciliation["applied_gross_amount"],
                "1250.00",
            )
            self.assertEqual(
                reconciliation["applied_return_amount"],
                "-250.00",
            )
            self.assertEqual(
                reconciliation["applied_net_amount"],
                "1000.00",
            )
            raise _IntentionalRollback

        with self.assertRaises(_IntentionalRollback):
            commit_type04_batch(
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
            "staging.ted_transfer_movement",
            "legacy.ted_transfer_movement",
            "reporting.ted_transfer_reconciliation",
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
