"""Type 06 oracle scores MATCHED consistency, not contract 1.01."""

from __future__ import annotations

import unittest

from type06_oracle import (
    Type06OracleMismatchError,
    compare_post_db_reconciliation,
    compare_rejection,
    compare_sanitized_before_posting,
)


SUCCESS_JAVA = {
    "batch_id": "B202607230000501",
    "csv_sha256": "a" * 64,
    "row_count": 1,
    "original_amount": "67.00",
    "chargeback_amount": "1.00",
    "calculated_amount": "1.00",
    "status": "succeeded",
}
MATCHED_RECON = {
    "batch_id": "B202607230000501",
    "currency": "BRL",
    "source_count": 1,
    "staged_count": 1,
    "applied_count": 1,
    "source_original_amount": "67.00",
    "staged_original_amount": "67.00",
    "applied_original_amount": "67.00",
    "source_chargeback_amount": "1.00",
    "staged_chargeback_amount": "1.00",
    "applied_chargeback_amount": "1.00",
    "source_calculated_amount": "1.00",
    "staged_calculated_amount": "1.00",
    "applied_calculated_amount": "1.00",
    "count_delta": 0,
    "original_amount_delta": "0.00",
    "chargeback_amount_delta": "0.00",
    "calculated_amount_delta": "0.00",
    "reject_count": 0,
    "status": "MATCHED",
}


class Type06OracleTest(unittest.TestCase):
    def test_sanitized_accepts_half_even_one_cent(self) -> None:
        result = compare_sanitized_before_posting(
            "valid-minimal",
            batch_id="B202607230000501",
            java_result=SUCCESS_JAVA,
        )
        self.assertTrue(result.matches)
        self.assertEqual(result.actual["chargeback_amount"], "1.00")

    def test_post_db_accepts_matched_without_contract_cent(self) -> None:
        result = compare_post_db_reconciliation(
            "valid-minimal",
            reconciliation=MATCHED_RECON,
        )
        self.assertTrue(result.matches)
        self.assertEqual(result.actual["source_chargeback_amount"], "1.00")

    def test_malformed_rejection_matches_contract(self) -> None:
        result = compare_rejection(
            "malformed",
            batch_id="B202607230000503",
            java_result={
                "batch_id": "B202607230000503",
                "code": "INVALID_CSV_QUOTING",
                "status": "rejected",
                "csv_file": None,
                "record_number": 2,
            },
        )
        self.assertTrue(result.matches)

    def test_inconsistent_chargeback_is_rejected(self) -> None:
        broken = dict(SUCCESS_JAVA)
        broken["calculated_amount"] = "1.01"
        with self.assertRaises(Type06OracleMismatchError):
            compare_sanitized_before_posting(
                "valid-minimal",
                batch_id="B202607230000501",
                java_result=broken,
            )


if __name__ == "__main__":
    unittest.main()
