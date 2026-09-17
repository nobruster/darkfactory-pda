"""Bundle-level schema and control tests for Type 03 generation."""

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
        "B202607230000201",
        1,
        8,
        2,
        "200.00",
        "5.00",
        "3.50",
        "198.50",
        "198.50",
        "ACCEPTED",
        None,
    ),
    "valid-boundary": (
        "B202402290000202",
        1,
        6,
        1,
        "9999999999999.99",
        "9999999999.99",
        "9999999999.99",
        "9999999999999.99",
        "9999999999999.99",
        "ACCEPTED",
        None,
    ),
    "malformed": (
        "B202607230000203",
        1,
        6,
        1,
        "10.00",
        "0.00",
        "0.00",
        "10.00",
        "10.00",
        "REJECTED",
        "SEGMENT_PAIR_MISMATCH",
    ),
    "multi-lot": (
        "B202607230000204",
        2,
        10,
        2,
        "200.00",
        "5.00",
        "3.50",
        "198.50",
        "198.50",
        "ACCEPTED",
        None,
    ),
    "DF-SOURCE-003": (
        "B202607230000205",
        1,
        8,
        2,
        "200.00",
        "5.00",
        "3.50",
        "198.49",
        "198.50",
        "REJECTED",
        "SOURCE_CONTROL_NET_MISMATCH",
    ),
}


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON / filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


class Type03GenerationIntegrationTest(unittest.TestCase):
    """Verify immutable bundle linkage and complete source controls."""

    def test_all_five_bundles_are_schema_valid(self) -> None:
        source_validator = _validator("source-manifest.schema.json")
        receipt_validator = _validator("generation-receipt.schema.json")
        with tempfile.TemporaryDirectory() as output:
            for scenario, expected in EXPECTED.items():
                with self.subTest(scenario=scenario):
                    (
                        batch_id,
                        lot_count,
                        physical_count,
                        logical_count,
                        face,
                        discount,
                        fee,
                        declared_net,
                        computed_net,
                        status,
                        violation,
                    ) = expected
                    bundle = generate(
                        type_number="03",
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
                            "currency": "BRL",
                            "discount_amount": discount,
                            "face_amount": face,
                            "fee_amount": fee,
                            "logical_count": logical_count,
                            "lot_count": lot_count,
                            "net_amount": declared_net,
                            "orphan_segment_count": 0,
                            "physical_record_count": physical_count,
                        },
                    )
                    self.assertEqual(
                        manifest["source_file"]["record_length_bytes"],
                        240,
                    )
                    self.assertEqual(
                        manifest["source_file"]["sha256"],
                        sha256_hex(bundle.raw_file.read_bytes()),
                    )
                    self.assertEqual(
                        receipt["controls"]["computed_net_amount"],
                        computed_net,
                    )
                    self.assertEqual(
                        receipt["controls"]["declared_net_amount"],
                        declared_net,
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
                "Unsupported Type 03 scenario",
            ):
                generate(
                    type_number="03",
                    scenario="not-a-scenario",
                    output_root=target,
                    contracts_root=CONTRACTS,
                )
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
