from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "validation" / "oracle"))

from type01_oracle import (  # noqa: E402
    INTERNALLY_RECONCILED_UNSCORED,
    Type01OracleMismatchError,
    compare_post_db_reconciliation,
    compare_rejection,
    compare_sanitized_before_posting,
    compare_success,
)


VALID_MINIMAL_RECONCILIATION = {
    "batch_id": "B202607230000001",
    "currency": "BRL",
    "source_count": 2,
    "staged_count": 2,
    "applied_count": 2,
    "source_net_amount": "173.45",
    "staged_net_amount": "173.45",
    "applied_net_amount": "173.45",
    "count_delta": 0,
    "amount_delta": "0.00",
    "reject_count": 0,
    "status": "MATCHED",
}


class Type01OracleTest(unittest.TestCase):
    def test_pre_commit_uses_canonical_csv_and_controls(self) -> None:
        result = compare_sanitized_before_posting(
            "valid-minimal",
            batch_id="B202607230000001",
            java_result={
                "batch_id": "B202607230000001",
                "csv_sha256": (
                    "a7db2ed1bfe76ab180bba750bbd4d791"
                    "84d1e118b643a2a0e4d6f0e7f6ec089d"
                ),
                "row_count": 2,
                "net_amount": "173.45",
                "status": "succeeded",
            },
        )

        self.assertTrue(result.matches)
        self.assertEqual(result.expected["row_count"], 2)
        self.assertEqual(result.expected["net_amount"], "173.45")

    def test_pre_commit_rejects_a_runtime_derived_wrong_total(self) -> None:
        with self.assertRaises(Type01OracleMismatchError):
            compare_sanitized_before_posting(
                "valid-minimal",
                batch_id="B202607230000001",
                java_result={
                    "batch_id": "B202607230000001",
                    "csv_sha256": (
                        "a7db2ed1bfe76ab180bba750bbd4d791"
                        "84d1e118b643a2a0e4d6f0e7f6ec089d"
                    ),
                    "row_count": 2,
                    "net_amount": "173.44",
                    "status": "succeeded",
                },
            )

    def test_post_db_compares_the_complete_reconciliation_yaml(self) -> None:
        result = compare_post_db_reconciliation(
            "valid-minimal",
            reconciliation=VALID_MINIMAL_RECONCILIATION,
        )

        self.assertTrue(result.matches)
        self.assertEqual(result.expected, VALID_MINIMAL_RECONCILIATION)

        mismatched = dict(VALID_MINIMAL_RECONCILIATION)
        mismatched["reject_count"] = 1
        with self.assertRaises(Type01OracleMismatchError):
            compare_post_db_reconciliation(
                "valid-minimal",
                reconciliation=mismatched,
            )

    def test_malformed_rejection_compares_safe_record_context(self) -> None:
        result = compare_rejection(
            "malformed",
            batch_id="B202607230000003",
            java_result={
                "batch_id": "B202607230000003",
                "code": "INVALID_OVERPUNCH",
                "csv_file": None,
                "record_number": 2,
                "status": "rejected",
                "transaction_id": "TXN0000000000004",
            },
        )

        self.assertTrue(result.matches)
        self.assertEqual(result.expected["source_record_number"], 2)
        self.assertEqual(
            result.expected["transaction_id"],
            "TXN0000000000004",
        )

    def test_dark_factory_compares_declared_and_computed_controls(self) -> None:
        result = compare_rejection(
            "DF-SOURCE-001",
            batch_id="B202607230000004",
            java_result={
                "batch_id": "B202607230000004",
                "code": "SOURCE_CONTROL_TOTAL_MISMATCH",
                "csv_file": None,
                "declared_detail_count": 2,
                "declared_net_amount": "173.44",
                "computed_detail_count": 2,
                "computed_net_amount": "173.45",
                "status": "rejected",
            },
        )

        self.assertTrue(result.matches)
        self.assertEqual(result.expected["declared_net_amount"], "173.44")
        self.assertEqual(result.actual["computed_net_amount"], "173.45")
        self.assertNotIn("source_system_role", result.expected)
        self.assertNotIn("unrelated_batches_continue", result.expected)

        wrong_diagnosis = {
            "batch_id": "B202607230000004",
            "code": "SOURCE_CONTROL_TOTAL_MISMATCH",
            "csv_file": None,
            "declared_detail_count": 2,
            "declared_net_amount": "173.44",
            "computed_detail_count": 2,
            "status": "rejected",
        }
        wrong_diagnosis["computed_net_amount"] = "173.44"
        with self.assertRaises(Type01OracleMismatchError):
            compare_rejection(
                "DF-SOURCE-001",
                batch_id="B202607230000004",
                java_result=wrong_diagnosis,
            )

    def test_unknown_file_is_internally_reconciled_but_unscored(self) -> None:
        unknown = dict(VALID_MINIMAL_RECONCILIATION)
        unknown["batch_id"] = "B202607240000099"

        result = compare_post_db_reconciliation(
            None,
            reconciliation=unknown,
        )

        self.assertIsNone(result.matches)
        self.assertIsNone(result.expected)
        self.assertEqual(
            result.oracle_status,
            INTERNALLY_RECONCILED_UNSCORED,
        )

    def test_unknown_file_never_hides_an_internal_mismatch(self) -> None:
        unknown = dict(VALID_MINIMAL_RECONCILIATION)
        unknown["batch_id"] = "B202607240000099"
        unknown["applied_count"] = 1

        with self.assertRaises(Type01OracleMismatchError):
            compare_post_db_reconciliation(
                None,
                reconciliation=unknown,
            )

    def test_compatibility_compare_success_is_contract_driven(self) -> None:
        @dataclass
        class Raw:
            batch_id: str

        @dataclass
        class Load:
            batch_id: str
            csv_sha256: str
            row_count: int
            net_amount: str
            reconciliation: dict[str, object]

        result = compare_success(
            "valid-minimal",
            raw=Raw("B202607230000001"),
            load=Load(
                batch_id="B202607230000001",
                csv_sha256=(
                    "a7db2ed1bfe76ab180bba750bbd4d791"
                    "84d1e118b643a2a0e4d6f0e7f6ec089d"
                ),
                row_count=2,
                net_amount="173.45",
                reconciliation=VALID_MINIMAL_RECONCILIATION,
            ),
        )

        self.assertTrue(result.matches)
        self.assertEqual(result.oracle_status, "oracle_matched")


if __name__ == "__main__":
    unittest.main()
