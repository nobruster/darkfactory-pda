"""Tests proving Type 04 comparisons are independent and contract-driven."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "validation" / "oracle"))

from type04_oracle import (  # noqa: E402
    Type04OracleMismatchError,
    compare_post_db_reconciliation,
    compare_rejection,
    compare_sanitized_before_posting,
)


VALID_RECONCILIATION: dict[str, object] = {
    "batch_id": "B202607230000301",
    "currency": "BRL",
    "source_transfer_count": 2,
    "staged_transfer_count": 2,
    "applied_transfer_count": 2,
    "source_return_count": 1,
    "staged_return_count": 1,
    "applied_return_count": 1,
    "source_gross_amount": "1250.00",
    "staged_gross_amount": "1250.00",
    "applied_gross_amount": "1250.00",
    "source_return_amount": "-250.00",
    "staged_return_amount": "-250.00",
    "applied_return_amount": "-250.00",
    "source_net_amount": "1000.00",
    "staged_net_amount": "1000.00",
    "applied_net_amount": "1000.00",
    "transfer_count_delta": 0,
    "return_count_delta": 0,
    "gross_amount_delta": "0.00",
    "return_amount_delta": "0.00",
    "net_amount_delta": "0.00",
    "reject_count": 0,
    "status": "MATCHED",
}


class Type04OracleTest(unittest.TestCase):
    """Exercise canonical, drift, Dark Factory, and unseen-batch paths."""

    def test_precommit_uses_exact_csv_and_signed_controls(self) -> None:
        result = compare_sanitized_before_posting(
            "valid-minimal",
            batch_id="B202607230000301",
            java_result={
                "batch_id": "B202607230000301",
                "csv_sha256": (
                    "96ac52ddfc186df6b9e0814767ee2176"
                    "da0740b9944c7dc1d19e82024e875619"
                ),
                "row_count": 3,
                "transfer_count": 2,
                "return_count": 1,
                "gross_amount": "1250.00",
                "return_amount": "-250.00",
                "net_amount": "1000.00",
                "status": "succeeded",
            },
        )
        self.assertTrue(result.matches)

    def test_postgres_comparison_rejects_return_drift(self) -> None:
        result = compare_post_db_reconciliation(
            "valid-minimal",
            reconciliation=VALID_RECONCILIATION,
        )
        self.assertTrue(result.matches)

        mismatch = dict(VALID_RECONCILIATION)
        mismatch["staged_return_amount"] = "-249.99"
        with self.assertRaises(Type04OracleMismatchError):
            compare_post_db_reconciliation(
                "valid-minimal",
                reconciliation=mismatch,
            )

    def test_malformed_transport_rejection_matches(self) -> None:
        result = compare_rejection(
            "malformed",
            batch_id="B202607230000303",
            java_result={
                "batch_id": "B202607230000303",
                "code": "INVALID_TRANSPORT",
                "csv_file": None,
                "status": "rejected",
            },
        )
        self.assertTrue(result.matches)

    def test_dark_factory_compares_all_source_controls(self) -> None:
        result = compare_rejection(
            "DF-SOURCE-004",
            batch_id="B202607230000305",
            java_result={
                "batch_id": "B202607230000305",
                "code": "SOURCE_CONTROL_NET_MISMATCH",
                "csv_file": None,
                "declared_transfer_count": 2,
                "computed_transfer_count": 2,
                "declared_return_count": 1,
                "computed_return_count": 1,
                "declared_gross_amount": "1250.00",
                "computed_gross_amount": "1250.00",
                "declared_return_amount": "-250.00",
                "computed_return_amount": "-250.00",
                "declared_net_amount": "999.99",
                "computed_net_amount": "1000.00",
                "status": "rejected",
            },
        )
        self.assertTrue(result.matches)
        self.assertNotIn("source_system_role", result.expected)

    def test_unknown_valid_batch_must_reconcile_internally(self) -> None:
        unknown = dict(VALID_RECONCILIATION)
        unknown["batch_id"] = "B202607240000399"
        result = compare_post_db_reconciliation(
            None,
            reconciliation=unknown,
        )
        self.assertIsNone(result.matches)

        unknown["return_count_delta"] = 1
        with self.assertRaises(Type04OracleMismatchError):
            compare_post_db_reconciliation(
                None,
                reconciliation=unknown,
            )


if __name__ == "__main__":
    unittest.main()
