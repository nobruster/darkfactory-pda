"""Type 01 golden-match: call shipped emit/Gold/attach, assert three fixtures."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1")


def _load(name: str, relative: str):
    path = REPO_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Type01GoldenMatchTest(unittest.TestCase):
    gold = None
    attach = None

    @classmethod
    def setUpClass(cls) -> None:
        landing = REPO_ROOT / "modern" / "landing"
        cls.gold = _load("run_type01_gold", "modern/scripts/run_type01_gold.py")
        try:
            cls.gold.main()
        except Exception:
            if landing.exists():
                shutil.rmtree(landing)
            cls.gold.main()
        cls.attach = _load("attach_type01", "modern/validation/attach_type01.py")

    def test_happy_resolved_both_questions_unexplained_zero(self) -> None:
        comparison = self.attach.attach_happy()
        payload = comparison.as_dict()
        self.assertTrue(payload["resolved"])
        self.assertEqual(payload["unexplained_count"], 0)
        self.assertTrue(comparison.checks["contract_reconciliation"])
        self.assertTrue(comparison.checks["records_match_contract"])
        self.assertTrue(comparison.checks["gold_present"])

    def test_source_lie_confirmed_source_defect_keeps_173_44(self) -> None:
        lie = self.attach.attach_rejection(
            self.attach.LIE_BATCH,
            "expected-df-source-001-finding.yaml",
            "source-defect",
        )
        payload = lie.as_dict()
        classes = {item["classification"] for item in payload["differences"]}
        self.assertIn("CONFIRMED_SOURCE_DEFECT", classes)
        nets = {
            (item["reference"], item["modern"])
            for item in payload["differences"]
            if item["classification"] == "CONFIRMED_SOURCE_DEFECT"
        }
        self.assertIn(("173.44", "173.45"), nets)
        self.assertTrue(lie.checks["gold_absent"])
        self.assertTrue(lie.checks["modern_produced_no_parquet"])
        self.assertEqual(payload["unexplained_count"], 0)

    def test_malformed_classified_unexplained_zero_no_gold(self) -> None:
        malformed = self.attach.attach_rejection(
            self.attach.MALFORMED_BATCH,
            "expected-malformed-rejection.yaml",
            "rejected",
        )
        payload = malformed.as_dict()
        self.assertEqual(payload["unexplained_count"], 0)
        self.assertTrue(malformed.checks["gold_absent"])
        self.assertTrue(malformed.checks["modern_produced_no_parquet"])
        self.assertEqual(payload["outcome_class"], "rejected")


if __name__ == "__main__":
    unittest.main()
