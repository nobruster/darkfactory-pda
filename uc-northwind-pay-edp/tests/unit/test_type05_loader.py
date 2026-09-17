"""Unit tests for strict Type 05 sanitized CSV validation."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from loader_common import PostgresLoadError
from raw_publisher import PublishedRaw
from type05_loader import (
    PreparedType05Load,
    _parse_csv,
    _validate_prepared_lineage,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = (
    ROOT
    / "contracts"
    / "types"
    / "05-merchant-fee-assessment"
    / "main"
)
MINIMAL_BATCH = "B202607230000401"
MINIMAL_SOURCE = (
    "NW_MERCHANT_FEES_20260723_B202607230000401.csv"
)
MINIMAL_CONTROLS: dict[str, int | str] = {
    "assessed_fee": "12.36",
    "calculated_fee": "12.36",
    "currency": "BRL",
    "gross_amount": "1001.00",
    "row_count": 2,
}
AGGREGATE_BATCH = "B202607230000405"
AGGREGATE_SOURCE = (
    "NW_MERCHANT_FEES_20260723_B202607230000405.csv"
)
AGGREGATE_TOTAL = "1999999999999.98"
AGGREGATE_CSV = (
    "batch_id,source_file,source_record_number,assessment_id,"
    "merchant_id,merchant_tax_id_masked,fee_code,description,"
    "gross_amount_brl,rate_percent,assessed_fee_brl,"
    "calculated_fee_brl,assessment_date,rounding_mode\n"
    f"{AGGREGATE_BATCH},{AGGREGATE_SOURCE},2,"
    "FEE2026072300405,MER2026072300405,**********0405,"
    "MAX_FEE,Maximum row one,999999999999.99,100.000,"
    "999999999999.99,999999999999.99,2026-07-23,HALF_UP\n"
    f"{AGGREGATE_BATCH},{AGGREGATE_SOURCE},3,"
    "FEE2026072310405,MER2026072310405,**********1405,"
    "MAX_FEE,Maximum row two,999999999999.99,100.000,"
    "999999999999.99,999999999999.99,2026-07-23,HALF_UP\n"
).encode("utf-8")


class Type05CsvValidationTest(unittest.TestCase):
    """Prove NFC, canonical decimals, HALF_UP, and privacy fail closed."""

    def test_two_valid_maximum_rows_may_exceed_the_per_row_cap(self) -> None:
        self.assertEqual(
            _parse_csv(
                AGGREGATE_CSV,
                batch_id=AGGREGATE_BATCH,
                source_filename=AGGREGATE_SOURCE,
            ),
            {
                "assessed_fee": AGGREGATE_TOTAL,
                "calculated_fee": AGGREGATE_TOTAL,
                "currency": "BRL",
                "gross_amount": AGGREGATE_TOTAL,
                "row_count": 2,
            },
        )

    def test_three_approved_csvs_recompute_exact_controls(self) -> None:
        cases = (
            (
                "expected-sanitized.csv",
                MINIMAL_BATCH,
                MINIMAL_SOURCE,
                MINIMAL_CONTROLS,
            ),
            (
                "expected-valid-boundary-sanitized.csv",
                "B200002290000402",
                (
                    "NW_MERCHANT_FEES_20000229_"
                    "B200002290000402.csv"
                ),
                {
                    "assessed_fee": "999999999999.99",
                    "calculated_fee": "999999999999.99",
                    "currency": "BRL",
                    "gross_amount": "999999999999.99",
                    "row_count": 1,
                },
            ),
            (
                "expected-rounding-half-up-sanitized.csv",
                "B202607230000404",
                (
                    "NW_MERCHANT_FEES_20260723_"
                    "B202607230000404.csv"
                ),
                {
                    "assessed_fee": "0.04",
                    "calculated_fee": "0.04",
                    "currency": "BRL",
                    "gross_amount": "3.50",
                    "row_count": 2,
                },
            ),
        )
        for filename, batch_id, source_filename, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(
                    _parse_csv(
                        (FIXTURES / filename).read_bytes(),
                        batch_id=batch_id,
                        source_filename=source_filename,
                    ),
                    expected,
                )

    def test_half_up_ties_and_canonical_decimals_are_enforced(self) -> None:
        canonical = (
            FIXTURES / "expected-rounding-half-up-sanitized.csv"
        ).read_text(encoding="utf-8")
        cases = (
            canonical.replace(",0.01,0.01,", ",0.00,0.00,", 1),
            canonical.replace(",1.00,0.500,", ",01.00,0.500,", 1),
            canonical.replace(",1.00,0.500,", ",1.00,00.500,", 1),
        )
        for contaminated in cases:
            with self.subTest():
                with self.assertRaises(PostgresLoadError):
                    _parse_csv(
                        contaminated.encode("utf-8"),
                        batch_id="B202607230000404",
                        source_filename=(
                            "NW_MERCHANT_FEES_20260723_"
                            "B202607230000404.csv"
                        ),
                    )

    def test_nfc_description_formula_digit_run_and_quote_mode_reject(
        self,
    ) -> None:
        canonical = (FIXTURES / "expected-sanitized.csv").read_text(
            encoding="utf-8"
        )
        cases = (
            canonical.replace(
                "Arredondamento mínimo",
                "Arredondamento mi\u0301nimo",
                1,
            ),
            canonical.replace(
                "Arredondamento mínimo",
                "=SUM(A1:A2)",
                1,
            ),
            canonical.replace(
                "Arredondamento mínimo",
                "Pedido 12345678901",
                1,
            ),
            canonical.replace(
                "Arredondamento mínimo",
                '"Arredondamento mínimo"',
                1,
            ),
        )
        for contaminated in cases:
            with self.subTest():
                with self.assertRaises(PostgresLoadError):
                    _parse_csv(
                        contaminated.encode("utf-8"),
                        batch_id=MINIMAL_BATCH,
                        source_filename=MINIMAL_SOURCE,
                    )

    def test_rejection_does_not_disclose_contaminated_description(self) -> None:
        restricted = "12345678901234"
        canonical = (FIXTURES / "expected-sanitized.csv").read_text(
            encoding="utf-8"
        )
        contaminated = canonical.replace(
            "Arredondamento mínimo",
            restricted,
            1,
        )
        with self.assertRaises(PostgresLoadError) as raised:
            _parse_csv(
                contaminated.encode("utf-8"),
                batch_id=MINIMAL_BATCH,
                source_filename=MINIMAL_SOURCE,
            )
        self.assertNotIn(restricted, str(raised.exception))

    def test_commit_boundary_revalidates_bytes_and_all_controls(self) -> None:
        csv_bytes = (FIXTURES / "expected-sanitized.csv").read_bytes()
        raw = PublishedRaw(
            batch_id=MINIMAL_BATCH,
            file_type="05",
            filename=MINIMAL_SOURCE,
            sha256="a" * 64,
            size_bytes=390,
            manifest_sha256="b" * 64,
            source_controls=MINIMAL_CONTROLS,
        )
        prepared = PreparedType05Load(
            batch_id=MINIMAL_BATCH,
            raw_filename=MINIMAL_SOURCE,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_controls=MINIMAL_CONTROLS,
            csv_filename=(
                MINIMAL_SOURCE.removesuffix(".csv") + "_SANITIZED.csv"
            ),
            csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
            csv_size_bytes=len(csv_bytes),
            stage_controls=MINIMAL_CONTROLS,
            csv_bytes=csv_bytes,
        )
        _validate_prepared_lineage(prepared, raw=raw)

        contaminated = PreparedType05Load(
            batch_id=prepared.batch_id,
            raw_filename=prepared.raw_filename,
            raw_sha256=prepared.raw_sha256,
            raw_manifest_sha256=prepared.raw_manifest_sha256,
            source_controls=prepared.source_controls,
            csv_filename=prepared.csv_filename,
            csv_sha256=prepared.csv_sha256,
            csv_size_bytes=prepared.csv_size_bytes,
            stage_controls={
                **MINIMAL_CONTROLS,
                "calculated_fee": "12.35",
            },
            csv_bytes=prepared.csv_bytes,
        )
        with self.assertRaises(PostgresLoadError):
            _validate_prepared_lineage(contaminated, raw=raw)


if __name__ == "__main__":
    unittest.main()
