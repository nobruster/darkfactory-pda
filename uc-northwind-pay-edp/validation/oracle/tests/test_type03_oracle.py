"""Tests proving Type 03 comparisons are independent and contract-driven."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "validation" / "oracle"))

from type03_oracle import (  # noqa: E402
    Type03OracleMismatchError,
    compare_post_db_reconciliation,
    compare_rejection,
    compare_sanitized_before_posting,
)


VALID_RECONCILIATION: dict[str, object] = {
    "batch_id": "B202607230000201",
    "currency": "BRL",
    "source_count": 2,
    "staged_count": 2,
    "applied_count": 2,
    "source_face_amount": "200.00",
    "staged_face_amount": "200.00",
    "applied_face_amount": "200.00",
    "source_discount_amount": "5.00",
    "staged_discount_amount": "5.00",
    "applied_discount_amount": "5.00",
    "source_fee_amount": "3.50",
    "staged_fee_amount": "3.50",
    "applied_fee_amount": "3.50",
    "source_net_amount": "198.50",
    "staged_net_amount": "198.50",
    "applied_net_amount": "198.50",
    "source_orphan_segment_count": 0,
    "staged_orphan_segment_count": 0,
    "applied_orphan_segment_count": 0,
    "count_delta": 0,
    "face_amount_delta": "0.00",
    "discount_amount_delta": "0.00",
    "fee_amount_delta": "0.00",
    "net_amount_delta": "0.00",
    "orphan_segment_count_delta": 0,
    "reject_count": 0,
    "status": "MATCHED",
}


class Type03OracleTest(unittest.TestCase):
    """Exercise canonical, drift, Dark Factory, and unseen-batch paths."""

    def test_precommit_uses_exact_csv_and_all_controls(self) -> None:
        result = compare_sanitized_before_posting(
            "valid-minimal",
            batch_id="B202607230000201",
            java_result={
                "batch_id": "B202607230000201",
                "csv_sha256": (
                    "a108607f7d32017a954efce8ee35124d"
                    "42429bb7a85a38ef58f700087fd4b941"
                ),
                "row_count": 2,
                "face_amount": "200.00",
                "discount_amount": "5.00",
                "fee_amount": "3.50",
                "net_amount": "198.50",
                "orphan_segment_count": 0,
                "status": "succeeded",
            },
        )
        self.assertTrue(result.matches)

    def test_postgres_comparison_rejects_one_control_drift(self) -> None:
        result = compare_post_db_reconciliation(
            "valid-minimal",
            reconciliation=VALID_RECONCILIATION,
        )
        self.assertTrue(result.matches)

        mismatch = dict(VALID_RECONCILIATION)
        mismatch["applied_fee_amount"] = "3.49"
        with self.assertRaises(Type03OracleMismatchError):
            compare_post_db_reconciliation(
                "valid-minimal",
                reconciliation=mismatch,
            )

    def test_malformed_rejection_includes_pair_record_context(self) -> None:
        result = compare_rejection(
            "malformed",
            batch_id="B202607230000203",
            java_result={
                "batch_id": "B202607230000203",
                "code": "SEGMENT_PAIR_MISMATCH",
                "csv_file": None,
                "record_number": 4,
                "status": "rejected",
            },
        )
        self.assertTrue(result.matches)

    def test_dark_factory_compares_declared_and_computed_controls(self) -> None:
        result = compare_rejection(
            "DF-SOURCE-003",
            batch_id="B202607230000205",
            java_result={
                "batch_id": "B202607230000205",
                "code": "SOURCE_CONTROL_NET_MISMATCH",
                "csv_file": None,
                "declared_lot_count": 1,
                "computed_lot_count": 1,
                "declared_physical_record_count": 8,
                "computed_physical_record_count": 8,
                "declared_logical_count": 2,
                "computed_logical_count": 2,
                "declared_face_amount": "200.00",
                "computed_face_amount": "200.00",
                "declared_discount_amount": "5.00",
                "computed_discount_amount": "5.00",
                "declared_fee_amount": "3.50",
                "computed_fee_amount": "3.50",
                "declared_net_amount": "198.49",
                "computed_net_amount": "198.50",
                "computed_orphan_segment_count": 0,
                "status": "rejected",
            },
        )
        self.assertTrue(result.matches)
        self.assertNotIn("source_system_role", result.expected)

    def test_unknown_valid_batch_must_reconcile_internally(self) -> None:
        unknown = dict(VALID_RECONCILIATION)
        unknown["batch_id"] = "B202607240000299"
        result = compare_post_db_reconciliation(
            None,
            reconciliation=unknown,
        )
        self.assertIsNone(result.matches)

        unknown["orphan_segment_count_delta"] = 1
        with self.assertRaises(Type03OracleMismatchError):
            compare_post_db_reconciliation(
                None,
                reconciliation=unknown,
            )


if __name__ == "__main__":
    unittest.main()
