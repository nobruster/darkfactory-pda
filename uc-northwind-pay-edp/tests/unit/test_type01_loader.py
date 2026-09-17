"""Unit tests for strict Type 01 sanitized CSV validation."""

from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from loader_common import PostgresLoadError
from raw_publisher import PublishedRaw
from type01_loader import (
    PreparedType01Load,
    _parse_csv,
    _validate_prepared_lineage,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = (
    ROOT
    / "contracts"
    / "types"
    / "01-card-settlement"
    / "main"
)
MINIMAL_BATCH = "B202607230000001"
MINIMAL_SOURCE = (
    "NW_CARD_SETTLEMENT_20260723_B202607230000001.dat"
)
MINIMAL_CONTROLS: dict[str, int | str] = {
    "currency": "BRL",
    "detail_count": 2,
    "net_amount": "173.45",
}


def _canonical_text() -> str:
    return (FIXTURES / "expected-sanitized.csv").read_text(
        encoding="utf-8"
    )


class Type01CsvValidationTest(unittest.TestCase):
    """Prove Type 01 lineage, controls, and privacy fail closed."""

    def test_three_approved_csvs_recompute_exact_controls(self) -> None:
        cases = (
            (
                "expected-sanitized.csv",
                MINIMAL_BATCH,
                MINIMAL_SOURCE,
                2,
                Decimal("173.45"),
            ),
            (
                "expected-valid-boundary-sanitized.csv",
                "B202402290000001",
                "NW_CARD_SETTLEMENT_20240229_B202402290000001.dat",
                1,
                Decimal("9999999999.99"),
            ),
            (
                "expected-negative-overpunch-sanitized.csv",
                "B202607230000002",
                "NW_CARD_SETTLEMENT_20260723_B202607230000002.dat",
                1,
                Decimal("-12.34"),
            ),
        )

        for filename, batch_id, source_filename, count, net in cases:
            with self.subTest(filename=filename):
                rows, observed_count, observed_net = _parse_csv(
                    (FIXTURES / filename).read_bytes(),
                    batch_id=batch_id,
                    source_filename=source_filename,
                )
                self.assertEqual(len(rows), count)
                self.assertEqual(observed_count, count)
                self.assertEqual(observed_net, net)

    def test_transport_header_and_empty_data_fail_before_copy(self) -> None:
        canonical = _canonical_text()
        invalid_documents = (
            canonical.replace("\n", "\r\n"),
            canonical.replace(
                "batch_id,source_file,",
                "source_file,batch_id,",
                1,
            ),
            canonical.splitlines()[0] + "\n",
        )

        for content in invalid_documents:
            with self.subTest():
                with self.assertRaises(PostgresLoadError):
                    _parse_csv(
                        content.encode("utf-8"),
                        batch_id=MINIMAL_BATCH,
                        source_filename=MINIMAL_SOURCE,
                    )

    def test_lineage_order_duplicate_and_privacy_fields_fail_closed(
        self,
    ) -> None:
        canonical = _canonical_text()
        contaminated_documents = (
            canonical.replace(MINIMAL_BATCH, "B202607230000099", 1),
            canonical.replace(MINIMAL_SOURCE, "another-source.dat", 1),
            canonical.replace(",2,TXN", ",3,TXN", 1),
            canonical.replace(
                "TXN0000000000002",
                "TXN0000000000001",
                1,
            ),
            canonical.replace(
                "tok_0c5ac34fdde4aa92c6115f09",
                "4111111111111111",
                1,
            ),
            canonical.replace("*******8909", "12345678909", 1),
        )

        for content in contaminated_documents:
            with self.subTest():
                with self.assertRaises(PostgresLoadError):
                    _parse_csv(
                        content.encode("utf-8"),
                        batch_id=MINIMAL_BATCH,
                        source_filename=MINIMAL_SOURCE,
                    )

    def test_amount_movement_and_timestamp_types_are_strict(self) -> None:
        canonical = _canonical_text()
        contaminated_documents = (
            canonical.replace(",123.45,P,", ",123.450,P,", 1),
            canonical.replace(",123.45,P,", ",-123.45,P,", 1),
            canonical.replace(
                "2026-07-23T09:15:30-03:00",
                "2026-07-23T09:15:30",
                1,
            ),
        )

        for content in contaminated_documents:
            with self.subTest():
                with self.assertRaises(PostgresLoadError):
                    _parse_csv(
                        content.encode("utf-8"),
                        batch_id=MINIMAL_BATCH,
                        source_filename=MINIMAL_SOURCE,
                    )

    def test_rejection_never_discloses_contaminated_identifier(self) -> None:
        restricted = "4111111111111111"
        contaminated = _canonical_text().replace(
            "tok_0c5ac34fdde4aa92c6115f09",
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

    def test_commit_boundary_revalidates_complete_raw_lineage(self) -> None:
        csv_bytes = (FIXTURES / "expected-sanitized.csv").read_bytes()
        rows, row_count, net_amount = _parse_csv(
            csv_bytes,
            batch_id=MINIMAL_BATCH,
            source_filename=MINIMAL_SOURCE,
        )
        raw = PublishedRaw(
            batch_id=MINIMAL_BATCH,
            file_type="01",
            filename=MINIMAL_SOURCE,
            sha256="a" * 64,
            size_bytes=338,
            manifest_sha256="b" * 64,
            source_controls=MINIMAL_CONTROLS,
        )
        prepared = PreparedType01Load(
            batch_id=MINIMAL_BATCH,
            raw_filename=MINIMAL_SOURCE,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_count=row_count,
            source_net_amount=format(net_amount, ".2f"),
            csv_filename=MINIMAL_SOURCE.removesuffix(".dat") + ".csv",
            csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
            csv_size_bytes=len(csv_bytes),
            row_count=row_count,
            net_amount=format(net_amount, ".2f"),
            rows=rows,
        )

        _validate_prepared_lineage(prepared, raw=raw)
        for contaminated in (
            replace(prepared, raw_sha256="c" * 64),
            replace(prepared, source_count=1),
            replace(prepared, source_net_amount="173.44"),
            replace(prepared, row_count=1),
            replace(prepared, net_amount="173.44"),
        ):
            with self.subTest(contaminated=contaminated):
                with self.assertRaises(PostgresLoadError):
                    _validate_prepared_lineage(contaminated, raw=raw)


if __name__ == "__main__":
    unittest.main()
