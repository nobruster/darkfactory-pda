"""Type 01 emit: happy Parquet, source lie keeps 173.44 with zero Parquet."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "modern" / "ingestion" / "src"))

os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")

from northwind_pay.emit import emit_scenario  # noqa: E402


class Type01EmitTest(unittest.TestCase):
    def test_valid_minimal_publishes_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            landing = Path(directory)
            outcome = emit_scenario("valid-minimal", landing_root=landing)
        self.assertEqual(outcome["status"], "succeeded")
        self.assertIsNotNone(outcome["parquet_sha256"])
        self.assertEqual(outcome["record_count"], 2)

    def test_source_lie_emits_zero_parquet_and_keeps_173_44(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            landing = Path(directory)
            outcome = emit_scenario("df-source-001", landing_root=landing)
            parquet = list(landing.rglob("*.parquet"))
        self.assertEqual(outcome["status"], "quarantined")
        self.assertEqual(outcome["code"], "SOURCE_CONTROL_TOTAL_MISMATCH")
        self.assertIsNone(outcome["parquet_sha256"])
        self.assertEqual(outcome["controls"]["declared_net_amount"], "173.44")
        self.assertEqual(outcome["controls"]["computed_net_amount"], "173.45")
        self.assertEqual(parquet, [])

    def test_malformed_is_quarantined_without_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            landing = Path(directory)
            outcome = emit_scenario("malformed", landing_root=landing)
        self.assertEqual(outcome["status"], "quarantined")
        self.assertEqual(outcome["code"], "INVALID_OVERPUNCH")
        self.assertEqual(outcome["batch_id"], "B202607230000003")
        self.assertIsNone(outcome["parquet_sha256"])


if __name__ == "__main__":
    unittest.main()
