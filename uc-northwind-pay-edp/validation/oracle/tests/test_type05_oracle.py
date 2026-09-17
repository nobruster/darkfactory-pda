"""Tests proving Type 05 comparisons are independent and contract-driven."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "validation" / "oracle"))

from type05_oracle import (  # noqa: E402
    Type05OracleMismatchError,
    compare_post_db_reconciliation,
    compare_rejection,
    compare_sanitized_before_posting,
)


VALID_RECONCILIATION: dict[str, object] = {
    "batch_id": "B202607230000401",
    "currency": "BRL",
    "source_count": 2,
    "staged_count": 2,
    "applied_count": 2,
    "source_gross_amount": "1001.00",
    "staged_gross_amount": "1001.00",
    "applied_gross_amount": "1001.00",
    "source_assessed_fee": "12.36",
    "staged_assessed_fee": "12.36",
    "applied_assessed_fee": "12.36",
    "source_calculated_fee": "12.36",
    "staged_calculated_fee": "12.36",
    "applied_calculated_fee": "12.36",
    "count_delta": 0,
    "gross_amount_delta": "0.00",
    "assessed_fee_delta": "0.00",
    "calculated_fee_delta": "0.00",
    "assessment_calculation_delta": "0.00",
    "reject_count": 0,
    "status": "MATCHED",
}


class Type05OracleTest(unittest.TestCase):
    """Exercise canonical, drift, Dark Factory, and unseen-batch paths."""

    def test_precommit_uses_exact_csv_and_fee_controls(self) -> None:
        result = compare_sanitized_before_posting(
            "valid-minimal",
            batch_id="B202607230000401",
            java_result={
                "batch_id": "B202607230000401",
                "csv_sha256": (
                    "cc13c6fa4ea028b7b7cbfaaf5b755a09"
                    "cd8edcc424739515429388bd15978c48"
                ),
                "row_count": 2,
                "gross_amount": "1001.00",
                "assessed_fee": "12.36",
                "calculated_fee": "12.36",
                "status": "succeeded",
            },
        )
        self.assertTrue(result.matches)

    def test_postgres_comparison_rejects_calculation_drift(self) -> None:
        result = compare_post_db_reconciliation(
            "valid-minimal",
            reconciliation=VALID_RECONCILIATION,
        )
        self.assertTrue(result.matches)

        mismatch = dict(VALID_RECONCILIATION)
        mismatch["applied_calculated_fee"] = "12.35"
        with self.assertRaises(Type05OracleMismatchError):
            compare_post_db_reconciliation(
                "valid-minimal",
                reconciliation=mismatch,
            )

    def test_malformed_rejection_compares_physical_record(self) -> None:
        result = compare_rejection(
            "malformed",
            batch_id="B202607230000403",
            java_result={
                "batch_id": "B202607230000403",
                "code": "INVALID_CSV_QUOTING",
                "csv_file": None,
                "record_number": 2,
                "status": "rejected",
            },
        )
        self.assertTrue(result.matches)

    def test_dark_factory_compares_external_source_controls(self) -> None:
        result = compare_rejection(
            "DF-SOURCE-005",
            batch_id="B202607230000405",
            java_result={
                "batch_id": "B202607230000405",
                "code": "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
                "csv_file": None,
                "declared_row_count": 1,
                "computed_row_count": 1,
                "declared_gross_amount": "100.00",
                "computed_gross_amount": "100.00",
                "declared_assessed_fee": "0.99",
                "computed_assessed_fee": "1.00",
                "declared_calculated_fee": "1.00",
                "computed_calculated_fee": "1.00",
                "status": "rejected",
            },
        )
        self.assertTrue(result.matches)
        self.assertNotIn("source_system_role", result.expected)

    def test_unknown_valid_batch_must_reconcile_internally(self) -> None:
        unknown = dict(VALID_RECONCILIATION)
        unknown["batch_id"] = "B202607240000499"
        result = compare_post_db_reconciliation(
            None,
            reconciliation=unknown,
        )
        self.assertIsNone(result.matches)

        unknown["assessment_calculation_delta"] = "0.01"
        with self.assertRaises(Type05OracleMismatchError):
            compare_post_db_reconciliation(
                None,
                reconciliation=unknown,
            )


if __name__ == "__main__":
    unittest.main()
