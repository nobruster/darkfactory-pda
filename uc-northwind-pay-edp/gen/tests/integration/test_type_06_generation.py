"""Bundle-level schema and control tests for Type 06 generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from checksum import sha256_hex
from generation import generate
from models import GenerationError


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts" / "types"
COMMON = ROOT / "contracts" / "common"
EXPECTED = {
    "valid-minimal": (
        "B202607230000501",
        1,
        "67.00",
        "1.01",
        "1.01",
        "ACCEPTED",
        None,
    ),
    "valid-boundary": (
        "B200002290000502",
        1,
        "2.00",
        "0.02",
        "0.02",
        "ACCEPTED",
        None,
    ),
    "malformed": (
        "B202607230000503",
        1,
        "10.00",
        "0.10",
        "0.10",
        "REJECTED",
        "INVALID_CSV_QUOTING",
    ),
    "legacy-miss": (
        "B202607230000504",
        1,
        "67.00",
        "1.01",
        "1.01",
        "ACCEPTED",
        None,
    ),
}


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON / filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


class Type06GenerationIntegrationTest(unittest.TestCase):
    """Verify immutable bundle linkage and Type 06 HALF_UP source controls."""

    def test_canonical_bundles_are_schema_valid_and_half_up(self) -> None:
        source_validator = _validator("source-manifest.schema.json")
        receipt_validator = _validator("generation-receipt.schema.json")
        with tempfile.TemporaryDirectory() as output:
            for scenario, expected in EXPECTED.items():
                with self.subTest(scenario=scenario):
                    (
                        batch_id,
                        row_count,
                        original,
                        chargeback,
                        calculated,
                        status,
                        violation,
                    ) = expected
                    bundle = generate(
                        type_number="06",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS,
                    )
                    manifest_bytes = bundle.manifest_file.read_bytes()
                    manifest = json.loads(manifest_bytes)
                    receipt = json.loads(bundle.receipt_file.read_bytes())
                    source_validator.validate(manifest)
                    receipt_validator.validate(receipt)
                    self.assertEqual(bundle.batch_id, batch_id)
                    self.assertEqual(
                        manifest["source_controls"],
                        {
                            "calculated_amount": calculated,
                            "chargeback_amount": chargeback,
                            "currency": "BRL",
                            "original_amount": original,
                            "row_count": row_count,
                        },
                    )
                    self.assertEqual(
                        receipt["controls"]["computed_chargeback_amount"],
                        chargeback,
                    )
                    self.assertEqual(
                        receipt["expected_contract_result"],
                        {"status": status, "violation": violation},
                    )
                    self.assertEqual(
                        receipt["artifacts"]["source_manifest_sha256"],
                        sha256_hex(manifest_bytes),
                    )

    def test_unsupported_scenario_creates_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            target = Path(output) / "not-created"
            with self.assertRaisesRegex(
                GenerationError,
                "Unsupported Type 06 scenario",
            ):
                generate(
                    type_number="06",
                    scenario="not-a-scenario",
                    output_root=target,
                    contracts_root=CONTRACTS,
                )
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
