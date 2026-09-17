"""Bundle-level schema and control tests for Type 04 generation."""

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
        "B202607230000301",
        2,
        1,
        "1250.00",
        "-250.00",
        "1000.00",
        "1000.00",
        "ACCEPTED",
        None,
    ),
    "valid-boundary": (
        "B200002290000302",
        1,
        0,
        "999999999999.99",
        "0.00",
        "999999999999.99",
        "999999999999.99",
        "ACCEPTED",
        None,
    ),
    "malformed": (
        "B202607230000303",
        2,
        1,
        "1250.00",
        "-250.00",
        "1000.00",
        "1000.00",
        "REJECTED",
        "INVALID_TRANSPORT",
    ),
    "all-returned-zero-net": (
        "B202607230000304",
        2,
        2,
        "1250.00",
        "-1250.00",
        "0.00",
        "0.00",
        "ACCEPTED",
        None,
    ),
    "DF-SOURCE-004": (
        "B202607230000305",
        2,
        1,
        "1250.00",
        "-250.00",
        "999.99",
        "1000.00",
        "REJECTED",
        "SOURCE_CONTROL_NET_MISMATCH",
    ),
}


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON / filename).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


class Type04GenerationIntegrationTest(unittest.TestCase):
    """Verify immutable bundle linkage and complete Type 04 controls."""

    def test_all_five_bundles_are_schema_valid(self) -> None:
        source_validator = _validator("source-manifest.schema.json")
        receipt_validator = _validator("generation-receipt.schema.json")
        with tempfile.TemporaryDirectory() as output:
            for scenario, expected in EXPECTED.items():
                with self.subTest(scenario=scenario):
                    (
                        batch_id,
                        transfer_count,
                        return_count,
                        gross,
                        returned,
                        declared_net,
                        computed_net,
                        status,
                        violation,
                    ) = expected
                    bundle = generate(
                        type_number="04",
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
                            "gross_amount": gross,
                            "net_amount": declared_net,
                            "return_amount": returned,
                            "return_count": return_count,
                            "transfer_count": transfer_count,
                        },
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
                "Unsupported Type 04 scenario",
            ):
                generate(
                    type_number="04",
                    scenario="not-a-scenario",
                    output_root=target,
                    contracts_root=CONTRACTS,
                )
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
