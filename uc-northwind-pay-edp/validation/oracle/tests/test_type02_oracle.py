"""Tests proving Type 02 comparisons are contract-driven."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "validation" / "oracle"))

from type02_oracle import (  # noqa: E402
    Type02OracleMismatchError,
    compare_post_db_reconciliation,
    compare_rejection,
    compare_sanitized_before_posting,
)


VALID_RECONCILIATION = {
    "batch_id": "B202607230000101",
    "currency": "BRL",
    "source_count": 2,
    "staged_count": 2,
    "applied_count": 2,
    "source_credit_amount": "200.00",
    "staged_credit_amount": "200.00",
    "applied_credit_amount": "200.00",
    "source_debit_amount": "26.55",
    "staged_debit_amount": "26.55",
    "applied_debit_amount": "26.55",
    "source_net_amount": "173.45",
    "staged_net_amount": "173.45",
    "applied_net_amount": "173.45",
    "source_returned_count": 1,
    "staged_returned_count": 1,
    "applied_returned_count": 1,
    "count_delta": 0,
    "credit_amount_delta": "0.00",
    "debit_amount_delta": "0.00",
    "net_amount_delta": "0.00",
    "returned_count_delta": 0,
    "reject_count": 0,
    "status": "MATCHED",
}


class Type02OracleTest(unittest.TestCase):
    def test_precommit_uses_exact_csv_and_complete_controls(self) -> None:
        result = compare_sanitized_before_posting(
            "valid-minimal",
            batch_id="B202607230000101",
            java_result={
                "batch_id": "B202607230000101",
                "csv_sha256": (
                    "8bd2e4bdb2d7fbea367d5105edae3ff0"
                    "a56fac091ea9b1072af0821a8e25a20a"
                ),
                "row_count": 2,
                "credit_amount": "200.00",
                "debit_amount": "26.55",
                "net_amount": "173.45",
                "returned_count": 1,
                "status": "succeeded",
            },
        )

        self.assertTrue(result.matches)

    def test_precommit_rejects_control_drift(self) -> None:
        with self.assertRaises(Type02OracleMismatchError):
            compare_sanitized_before_posting(
                "valid-minimal",
                batch_id="B202607230000101",
                java_result={
                    "batch_id": "B202607230000101",
                    "csv_sha256": "8bd2e4bdb2d7fbea" + "0" * 48,
                    "row_count": 2,
                    "credit_amount": "200.00",
                    "debit_amount": "26.55",
                    "net_amount": "173.45",
                    "returned_count": 1,
                    "status": "succeeded",
                },
            )

    def test_precommit_rejects_noncanonical_money_without_rounding(self) -> None:
        with self.assertRaises(Type02OracleMismatchError):
            compare_sanitized_before_posting(
                "valid-minimal",
                batch_id="B202607230000101",
                java_result={
                    "batch_id": "B202607230000101",
                    "csv_sha256": (
                        "8bd2e4bdb2d7fbea367d5105edae3ff0"
                        "a56fac091ea9b1072af0821a8e25a20a"
                    ),
                    "row_count": 2,
                    "credit_amount": "200.001",
                    "debit_amount": "26.549",
                    "net_amount": "173.451",
                    "returned_count": 1,
                    "status": "succeeded",
                },
            )

    def test_postgres_comparison_uses_complete_yaml(self) -> None:
        result = compare_post_db_reconciliation(
            "valid-minimal",
            reconciliation=VALID_RECONCILIATION,
        )
        self.assertTrue(result.matches)

        mismatch = dict(VALID_RECONCILIATION)
        mismatch["source_returned_count"] = 0
        with self.assertRaises(Type02OracleMismatchError):
            compare_post_db_reconciliation(
                "valid-minimal",
                reconciliation=mismatch,
            )

    def test_malformed_rejection_compares_record_context(self) -> None:
        result = compare_rejection(
            "malformed",
            batch_id="B202607230000103",
            java_result={
                "batch_id": "B202607230000103",
                "code": "INVALID_FIELD_COUNT",
                "csv_file": None,
                "record_number": 2,
                "status": "rejected",
            },
        )
        self.assertTrue(result.matches)

    def test_dark_factory_compares_all_declared_computed_controls(self) -> None:
        result = compare_rejection(
            "DF-SOURCE-002",
            batch_id="B202607230000105",
            java_result={
                "batch_id": "B202607230000105",
                "code": "SOURCE_CONTROL_NET_MISMATCH",
                "csv_file": None,
                "declared_event_count": 2,
                "computed_event_count": 2,
                "declared_credit_amount": "200.00",
                "computed_credit_amount": "200.00",
                "declared_debit_amount": "26.55",
                "computed_debit_amount": "26.55",
                "declared_net_amount": "173.44",
                "computed_net_amount": "173.45",
                "status": "rejected",
            },
        )
        self.assertTrue(result.matches)
        self.assertNotIn("source_system_role", result.expected)

    def test_unknown_valid_batch_must_reconcile_internally(self) -> None:
        unknown = dict(VALID_RECONCILIATION)
        unknown["batch_id"] = "B202607240000199"
        result = compare_post_db_reconciliation(
            None,
            reconciliation=unknown,
        )
        self.assertIsNone(result.matches)

        unknown["applied_credit_amount"] = "199.99"
        with self.assertRaises(Type02OracleMismatchError):
            compare_post_db_reconciliation(
                None,
                reconciliation=unknown,
            )

    def test_reconciliation_rejects_unexpected_fields(self) -> None:
        unexpected = dict(VALID_RECONCILIATION)
        unexpected["unexpected_field"] = "must-not-be-ignored"
        with self.assertRaises(Type02OracleMismatchError):
            compare_post_db_reconciliation(
                "valid-minimal",
                reconciliation=unexpected,
            )


if __name__ == "__main__":
    unittest.main()
