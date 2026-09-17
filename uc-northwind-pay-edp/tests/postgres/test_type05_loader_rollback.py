"""Live rollback-only regression for the production Type 05 loader path."""

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
from type05_loader import (  # noqa: E402
    PreparedType05Load,
    _parse_csv,
    commit_type05_batch,
)


PROBE_BATCH = "B202607230009905"
PROBE_SOURCE = f"NW_MERCHANT_FEES_20260723_{PROBE_BATCH}.csv"
AGGREGATE_PROBE_BATCH = "B202607230009915"
AGGREGATE_PROBE_SOURCE = (
    f"NW_MERCHANT_FEES_20260723_{AGGREGATE_PROBE_BATCH}.csv"
)
AGGREGATE_TOTAL = "1999999999999.98"
AGGREGATE_PROBE_CSV = (
    "batch_id,source_file,source_record_number,assessment_id,"
    "merchant_id,merchant_tax_id_masked,fee_code,description,"
    "gross_amount_brl,rate_percent,assessed_fee_brl,"
    "calculated_fee_brl,assessment_date,rounding_mode\n"
    f"{AGGREGATE_PROBE_BATCH},{AGGREGATE_PROBE_SOURCE},2,"
    "FEE2026072309915,MER2026072309915,**********9915,"
    "MAX_FEE,Maximum row one,999999999999.99,100.000,"
    "999999999999.99,999999999999.99,2026-07-23,HALF_UP\n"
    f"{AGGREGATE_PROBE_BATCH},{AGGREGATE_PROBE_SOURCE},3,"
    "FEE2026072319915,MER2026072319915,**********9916,"
    "MAX_FEE,Maximum row two,999999999999.99,100.000,"
    "999999999999.99,999999999999.99,2026-07-23,HALF_UP\n"
).encode("utf-8")


class _IntentionalRollback(Exception):
    """Stop the transaction after all Type 05 assertions have passed."""


class Type05LoaderRollbackTest(unittest.TestCase):
    """Prove COPY and both procedures disappear on oracle rejection."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.configuration = RuntimeConfiguration.load()

    def test_oracle_callback_failure_rolls_back_the_entire_batch(self) -> None:
        canonical = (
            ROOT
            / "contracts"
            / "types"
            / "05-merchant-fee-assessment"
            / "main"
            / "expected-sanitized.csv"
        ).read_text(encoding="utf-8")
        csv_bytes = (
            canonical.replace(
                "B202607230000401",
                PROBE_BATCH,
            )
            .replace(
                "FEE2026072304001",
                "FEE2026072309905",
            )
            .replace(
                "FEE2026072304002",
                "FEE2026072319905",
            )
            .encode("utf-8")
        )
        source_controls: dict[str, int | str] = {
            "assessed_fee": "12.36",
            "calculated_fee": "12.36",
            "currency": "BRL",
            "gross_amount": "1001.00",
            "row_count": 2,
        }
        stage_controls = _parse_csv(
            csv_bytes,
            batch_id=PROBE_BATCH,
            source_filename=PROBE_SOURCE,
        )
        raw = PublishedRaw(
            batch_id=PROBE_BATCH,
            file_type="05",
            filename=PROBE_SOURCE,
            sha256="a" * 64,
            size_bytes=390,
            manifest_sha256="b" * 64,
            source_controls=source_controls,
        )
        prepared = PreparedType05Load(
            batch_id=PROBE_BATCH,
            raw_filename=PROBE_SOURCE,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_controls=source_controls,
            csv_filename=(
                PROBE_SOURCE.removesuffix(".csv") + "_SANITIZED.csv"
            ),
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
            for boundary in ("source", "staged", "applied"):
                self.assertEqual(
                    reconciliation[f"{boundary}_gross_amount"],
                    "1001.00",
                )
                self.assertEqual(
                    reconciliation[f"{boundary}_assessed_fee"],
                    "12.36",
                )
                self.assertEqual(
                    reconciliation[f"{boundary}_calculated_fee"],
                    "12.36",
                )
            self.assertEqual(
                reconciliation["assessment_calculation_delta"],
                "0.00",
            )
            raise _IntentionalRollback

        with self.assertRaises(_IntentionalRollback):
            commit_type05_batch(
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
            "staging.merchant_fee_assessment",
            "legacy.merchant_fee_assessment",
            "reporting.merchant_fee_reconciliation",
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

    def test_batch_aggregate_above_row_cap_reconciles_and_rolls_back(
        self,
    ) -> None:
        source_controls: dict[str, int | str] = {
            "assessed_fee": AGGREGATE_TOTAL,
            "calculated_fee": AGGREGATE_TOTAL,
            "currency": "BRL",
            "gross_amount": AGGREGATE_TOTAL,
            "row_count": 2,
        }
        stage_controls = _parse_csv(
            AGGREGATE_PROBE_CSV,
            batch_id=AGGREGATE_PROBE_BATCH,
            source_filename=AGGREGATE_PROBE_SOURCE,
        )
        self.assertEqual(stage_controls, source_controls)
        raw = PublishedRaw(
            batch_id=AGGREGATE_PROBE_BATCH,
            file_type="05",
            filename=AGGREGATE_PROBE_SOURCE,
            sha256="c" * 64,
            size_bytes=len(AGGREGATE_PROBE_CSV),
            manifest_sha256="d" * 64,
            source_controls=source_controls,
        )
        prepared = PreparedType05Load(
            batch_id=AGGREGATE_PROBE_BATCH,
            raw_filename=AGGREGATE_PROBE_SOURCE,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_controls=source_controls,
            csv_filename=(
                AGGREGATE_PROBE_SOURCE.removesuffix(".csv")
                + "_SANITIZED.csv"
            ),
            csv_sha256=hashlib.sha256(
                AGGREGATE_PROBE_CSV
            ).hexdigest(),
            csv_size_bytes=len(AGGREGATE_PROBE_CSV),
            stage_controls=stage_controls,
            csv_bytes=AGGREGATE_PROBE_CSV,
        )

        with psycopg.connect(
            self.configuration.postgres_dsn
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM control.batches WHERE batch_id = %s",
                    (AGGREGATE_PROBE_BATCH,),
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
            for boundary in ("source", "staged", "applied"):
                self.assertEqual(
                    reconciliation[f"{boundary}_gross_amount"],
                    AGGREGATE_TOTAL,
                )
                self.assertEqual(
                    reconciliation[f"{boundary}_assessed_fee"],
                    AGGREGATE_TOTAL,
                )
                self.assertEqual(
                    reconciliation[f"{boundary}_calculated_fee"],
                    AGGREGATE_TOTAL,
                )
            self.assertEqual(reconciliation["gross_amount_delta"], "0.00")
            self.assertEqual(reconciliation["assessed_fee_delta"], "0.00")
            self.assertEqual(
                reconciliation["calculated_fee_delta"],
                "0.00",
            )
            self.assertEqual(
                reconciliation["assessment_calculation_delta"],
                "0.00",
            )
            raise _IntentionalRollback

        with self.assertRaises(_IntentionalRollback):
            commit_type05_batch(
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
            "staging.merchant_fee_assessment",
            "legacy.merchant_fee_assessment",
            "reporting.merchant_fee_reconciliation",
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
                            (AGGREGATE_PROBE_BATCH,),
                        )
                        self.assertEqual(cursor.fetchone(), (0,))


if __name__ == "__main__":
    unittest.main()
