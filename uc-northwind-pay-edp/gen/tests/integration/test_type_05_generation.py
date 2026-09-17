"""Bundle-level schema and control tests for Type 05 generation."""

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
        "B202607230000401",
        2,
        "1001.00",
        "12.36",
        "12.36",
        "12.36",
        "ACCEPTED",
        None,
    ),
    "valid-boundary": (
        "B200002290000402",
        1,
        "999999999999.99",
        "999999999999.99",
        "999999999999.99",
        "999999999999.99",
        "ACCEPTED",
        None,
    ),
    "malformed": (
        "B202607230000403",
        1,
        "10.00",
        "0.10",
        "0.10",
        "0.10",
        "REJECTED",
        "INVALID_CSV_QUOTING",
    ),
    "rounding-half-up": (
        "B202607230000404",
        2,
        "3.50",
        "0.04",
        "0.04",
        "0.04",
        "ACCEPTED",
        None,
    ),
    "DF-SOURCE-005": (
        "B202607230000405",
        1,
        "100.00",
        "0.99",
        "1.00",
        "1.00",
        "REJECTED",
        "SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
    ),
}


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON / filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


class Type05GenerationIntegrationTest(unittest.TestCase):
    """Verify immutable bundle linkage and complete Type 05 controls."""

    def test_all_five_bundles_are_schema_valid(self) -> None:
        source_validator = _validator("source-manifest.schema.json")
        receipt_validator = _validator("generation-receipt.schema.json")
        with tempfile.TemporaryDirectory() as output:
            for scenario, expected in EXPECTED.items():
                with self.subTest(scenario=scenario):
                    (
                        batch_id,
                        row_count,
                        gross,
                        declared_assessed,
                        computed_assessed,
                        calculated,
                        status,
                        violation,
                    ) = expected
                    bundle = generate(
                        type_number="05",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS,
                    )
                    manifest_bytes = bundle.manifest_file.read_bytes()
                    manifest = json.loads(manifest_bytes)
                    receipt = json.loads(
                        bundle.receipt_file.read_bytes()
                    )
                    source_validator.validate(manifest)
                    receipt_validator.validate(receipt)
                    self.assertEqual(bundle.batch_id, batch_id)
                    self.assertEqual(
                        manifest["source_controls"],
                        {
                            "assessed_fee": declared_assessed,
                            "calculated_fee": calculated,
                            "currency": "BRL",
                            "gross_amount": gross,
                            "row_count": row_count,
                        },
                    )
                    self.assertEqual(
                        manifest["source_file"]["unicode_normalization"],
                        "NFC",
                    )
                    self.assertEqual(
                        manifest["source_file"]["sha256"],
                        sha256_hex(bundle.raw_file.read_bytes()),
                    )
                    self.assertEqual(
                        receipt["controls"]["computed_assessed_fee"],
                        computed_assessed,
                    )
                    self.assertEqual(
                        receipt["controls"]["declared_assessed_fee"],
                        declared_assessed,
                    )
                    self.assertEqual(
                        receipt["expected_contract_result"],
                        {"status": status, "violation": violation},
                    )
                    self.assertEqual(
                        receipt["artifacts"][
                            "source_manifest_sha256"
                        ],
                        sha256_hex(manifest_bytes),
                    )

    def test_unsupported_scenario_creates_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            target = Path(output) / "not-created"
            with self.assertRaisesRegex(
                GenerationError,
                "Unsupported Type 05 scenario",
            ):
                generate(
                    type_number="05",
                    scenario="not-a-scenario",
                    output_root=target,
                    contracts_root=CONTRACTS,
                )
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
