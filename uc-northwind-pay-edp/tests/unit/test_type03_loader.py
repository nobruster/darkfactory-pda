"""Unit tests for strict Type 03 sanitized CSV validation."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from loader_common import PostgresLoadError
from raw_publisher import PublishedRaw
from type03_loader import (
    PreparedType03Load,
    _parse_csv,
    _validate_prepared_lineage,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = (
    ROOT
    / "contracts"
    / "types"
    / "03-payment-slip-settlement"
    / "main"
)
MINIMAL_BATCH = "B202607230000201"
MINIMAL_SOURCE = (
    "NW_PAYMENT_SLIP_20260723_B202607230000201.rem"
)
MINIMAL_CONTROLS: dict[str, int | str] = {
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
MINIMAL_STAGE_CONTROLS: dict[str, int | str] = {
    "currency": "BRL",
    "discount_amount": "5.00",
    "face_amount": "200.00",
    "fee_amount": "3.50",
    "net_amount": "198.50",
    "orphan_segment_count": 0,
    "row_count": 2,
}


def _parse(
    filename: str,
    *,
    batch_id: str,
    source_filename: str,
    lot_count: int,
    physical_record_count: int,
) -> dict[str, int | str]:
    return _parse_csv(
        (FIXTURES / filename).read_bytes(),
        batch_id=batch_id,
        source_filename=source_filename,
        expected_lot_count=lot_count,
        expected_physical_record_count=physical_record_count,
    )


class Type03CsvValidationTest(unittest.TestCase):
    """Prove paired-record lineage, controls, and privacy fail closed."""

    def test_valid_minimal_recomputes_exact_controls(self) -> None:
        self.assertEqual(
            _parse(
                "expected-sanitized.csv",
                batch_id=MINIMAL_BATCH,
                source_filename=MINIMAL_SOURCE,
                lot_count=1,
                physical_record_count=8,
            ),
            MINIMAL_STAGE_CONTROLS,
        )

    def test_valid_boundary_preserves_exact_decimal_limits(self) -> None:
        controls = _parse(
            "expected-valid-boundary-sanitized.csv",
            batch_id="B202402290000202",
            source_filename=(
                "NW_PAYMENT_SLIP_20240229_B202402290000202.rem"
            ),
            lot_count=1,
            physical_record_count=6,
        )

        self.assertEqual(controls["row_count"], 1)
        self.assertEqual(
            controls["face_amount"],
            "9999999999999.99",
        )
        self.assertEqual(
            controls["net_amount"],
            "9999999999999.99",
        )

    def test_multi_lot_accounts_for_lot_trailer_and_next_header(self) -> None:
        controls = _parse(
            "expected-multi-lot-sanitized.csv",
            batch_id="B202607230000204",
            source_filename=(
                "NW_PAYMENT_SLIP_20260723_B202607230000204.rem"
            ),
            lot_count=2,
            physical_record_count=10,
        )

        self.assertEqual(controls, MINIMAL_STAGE_CONTROLS)

    def test_extra_csv_field_is_rejected_before_copy(self) -> None:
        canonical = (FIXTURES / "expected-sanitized.csv").read_text(
            encoding="utf-8"
        )
        lines = canonical.splitlines()
        contaminated = "\n".join(
            (f"{lines[0]},unexpected", f"{lines[1]},secret", *lines[2:])
        ) + "\n"

        with self.assertRaises(PostgresLoadError):
            _parse_csv(
                contaminated.encode("utf-8"),
                batch_id=MINIMAL_BATCH,
                source_filename=MINIMAL_SOURCE,
            )

    def test_noncanonical_money_and_physical_order_are_rejected(self) -> None:
        canonical = (FIXTURES / "expected-sanitized.csv").read_text(
            encoding="utf-8"
        )
        contaminated_values = (
            canonical.replace(",150.00,5.00,", ",0150.00,5.00,", 1),
            canonical.replace(",3,4,000001,", ",4,5,000001,", 1),
        )

        for contaminated in contaminated_values:
            with self.subTest():
                with self.assertRaises(PostgresLoadError):
                    _parse_csv(
                        contaminated.encode("utf-8"),
                        batch_id=MINIMAL_BATCH,
                        source_filename=MINIMAL_SOURCE,
                    )

    def test_rejection_does_not_disclose_restricted_value(self) -> None:
        restricted = "111111111111111111111111111111111111111111111111"
        canonical = (FIXTURES / "expected-sanitized.csv").read_text(
            encoding="utf-8"
        )
        contaminated = canonical.replace(
            "payref_b9880c406eb74a9e6d753799",
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

    def test_commit_boundary_revalidates_bytes_and_all_stage_controls(
        self,
    ) -> None:
        csv_bytes = (FIXTURES / "expected-sanitized.csv").read_bytes()
        raw = PublishedRaw(
            batch_id=MINIMAL_BATCH,
            file_type="03",
            filename=MINIMAL_SOURCE,
            sha256="a" * 64,
            size_bytes=1936,
            manifest_sha256="b" * 64,
            source_controls=MINIMAL_CONTROLS,
        )
        prepared = PreparedType03Load(
            batch_id=MINIMAL_BATCH,
            raw_filename=MINIMAL_SOURCE,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_controls=MINIMAL_CONTROLS,
            csv_filename=MINIMAL_SOURCE.removesuffix(".rem") + ".csv",
            csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
            csv_size_bytes=len(csv_bytes),
            stage_controls=MINIMAL_STAGE_CONTROLS,
            csv_bytes=csv_bytes,
        )
        _validate_prepared_lineage(prepared, raw=raw)

        contaminated_controls = {
            **MINIMAL_STAGE_CONTROLS,
            "face_amount": "199.99",
        }
        contaminated = PreparedType03Load(
            batch_id=prepared.batch_id,
            raw_filename=prepared.raw_filename,
            raw_sha256=prepared.raw_sha256,
            raw_manifest_sha256=prepared.raw_manifest_sha256,
            source_controls=prepared.source_controls,
            csv_filename=prepared.csv_filename,
            csv_sha256=prepared.csv_sha256,
            csv_size_bytes=prepared.csv_size_bytes,
            stage_controls=contaminated_controls,
            csv_bytes=prepared.csv_bytes,
        )
        with self.assertRaises(PostgresLoadError):
            _validate_prepared_lineage(contaminated, raw=raw)


if __name__ == "__main__":
    unittest.main()
