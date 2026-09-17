"""Type 06 emit: happy Parquet HALF_UP 1.01; malformed zero Parquet."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDLER = (
    REPO_ROOT
    / "modern"
    / "ingestion"
    / "src"
    / "northwind_pay"
    / "types"
    / "06-merchant-chargeback"
    / "handler.py"
)
SAMPLES = REPO_ROOT / "spec" / "type-06-merchant-chargeback" / "samples"

sys.path.insert(0, str(REPO_ROOT / "modern" / "ingestion" / "src"))


def _load_handler():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("nwp_t06_handler_test", HANDLER)
    if spec is None or spec.loader is None:
        raise ImportError("handler.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nwp_t06_handler_test"] = module
    spec.loader.exec_module(module)
    return module


class Type06EmitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.handler = _load_handler()

    def test_valid_minimal_publishes_half_up_1_01(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            landing = Path(directory)
            outcome = self.handler.process(
                SAMPLES / "valid-minimal.csv", landing_root=landing
            )
            parquet = list(landing.rglob("*.parquet"))
        self.assertEqual(outcome.status, "succeeded")
        self.assertIsNotNone(outcome.parquet_sha256)
        self.assertEqual(outcome.record_count, 1)
        self.assertEqual(outcome.controls["computed_chargeback_amount"], "1.01")
        self.assertEqual(outcome.batch_id, "B202607230000501")
        self.assertEqual(parquet[0].name, "NW_MERCHANT_CHARGEBACK_20260723_B202607230000501.parquet")

    def test_half_even_is_not_used(self) -> None:
        # 67.00 * 1.500% = 1.005. HALF_EVEN would be 1.00. Contract is 1.01.
        parser_path = HANDLER.parent / "parser.py"
        spec = importlib.util.spec_from_file_location("nwp_t06_parser_test", parser_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules["nwp_t06_parser_test"] = module
        spec.loader.exec_module(module)
        calculated = module.calculate_chargeback(Decimal("67.00"), Decimal("1.500"))
        self.assertEqual(calculated, Decimal("1.01"))
        self.assertNotEqual(calculated, Decimal("1.00"))

    def test_malformed_is_quarantined_without_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            landing = Path(directory)
            outcome = self.handler.process(
                SAMPLES / "malformed.csv", landing_root=landing
            )
            parquet = list(landing.rglob("*.parquet"))
        self.assertEqual(outcome.status, "quarantined")
        self.assertEqual(outcome.code, "INVALID_CSV_QUOTING")
        self.assertEqual(outcome.batch_id, "B202607230000503")
        self.assertIsNone(outcome.parquet_sha256)
        self.assertEqual(parquet, [])

    def test_leap_day_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outcome = self.handler.process(
                SAMPLES / "valid-boundary.csv", landing_root=Path(directory)
            )
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.controls["computed_chargeback_amount"], "0.02")
        self.assertEqual(outcome.batch_id, "B200002290000502")


if __name__ == "__main__":
    unittest.main()
