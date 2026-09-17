"""Unit tests for Type 02 sanitized CSV validation."""

from __future__ import annotations

import unittest
from pathlib import Path

from loader_common import PostgresLoadError
from type02_loader import _parse_csv


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = (
    ROOT
    / "contracts"
    / "types"
    / "02-instant-payment-events"
    / "main"
)


class Type02CsvValidationTest(unittest.TestCase):
    """Prove independent downstream controls and fail-closed text handling."""

    def test_approved_csv_recomputes_exact_controls(self) -> None:
        controls = _parse_csv(
            (FIXTURES / "expected-sanitized.csv").read_bytes(),
            batch_id="B202607230000101",
            source_filename=(
                "NW_INSTANT_PAYMENT_20260723_"
                "B202607230000101.txt"
            ),
        )

        self.assertEqual(
            controls,
            {
                "currency": "BRL",
                "row_count": 2,
                "credit_amount": "200.00",
                "debit_amount": "26.55",
                "net_amount": "173.45",
                "returned_count": 1,
            },
        )

    def test_formula_description_is_rejected_before_copy(self) -> None:
        contaminated = (
            FIXTURES / "expected-sanitized.csv"
        ).read_text(encoding="utf-8").replace(
            "Invoice 1001",
            "=Invoice 1001",
            1,
        )

        with self.assertRaises(PostgresLoadError):
            _parse_csv(
                contaminated.encode("utf-8"),
                batch_id="B202607230000101",
                source_filename=(
                    "NW_INSTANT_PAYMENT_20260723_"
                    "B202607230000101.txt"
                ),
            )

    def test_event_timestamp_must_resolve_to_source_day(self) -> None:
        contaminated = (
            FIXTURES / "expected-valid-boundary-sanitized.csv"
        ).read_text(encoding="utf-8").replace(
            "2024-02-29T23:59:59Z",
            "2024-03-01T03:00:00Z",
            1,
        )

        with self.assertRaises(PostgresLoadError):
            _parse_csv(
                contaminated.encode("utf-8"),
                batch_id="B202402290000102",
                source_filename=(
                    "NW_INSTANT_PAYMENT_20240229_"
                    "B202402290000102.txt"
                ),
            )


if __name__ == "__main__":
    unittest.main()
