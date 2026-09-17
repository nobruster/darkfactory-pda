"""Bundle-level integration tests for Type 02 generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from checksum import sha256_hex
from generation import generate
from models import GenerationError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts" / "types"
COMMON_ROOT = REPOSITORY_ROOT / "contracts" / "common"

EXPECTED = {
    "valid-minimal": {
        "batch_id": "B202607230000101",
        "source": {
            "credit_amount": "200.00",
            "currency": "BRL",
            "debit_amount": "26.55",
            "event_count": 2,
            "net_amount": "173.45",
        },
        "computed_net": "173.45",
        "status": "ACCEPTED",
        "violation": None,
    },
    "valid-boundary": {
        "batch_id": "B202402290000102",
        "source": {
            "credit_amount": "0.01",
            "currency": "BRL",
            "debit_amount": "0.00",
            "event_count": 1,
            "net_amount": "0.01",
        },
        "computed_net": "0.01",
        "status": "ACCEPTED",
        "violation": None,
    },
    "escaped-content": {
        "batch_id": "B202607230000104",
        "source": {
            "credit_amount": "1.23",
            "currency": "BRL",
            "debit_amount": "0.00",
            "event_count": 1,
            "net_amount": "1.23",
        },
        "computed_net": "1.23",
        "status": "ACCEPTED",
        "violation": None,
    },
    "malformed": {
        "batch_id": "B202607230000103",
        "source": {
            "credit_amount": "0.00",
            "currency": "BRL",
            "debit_amount": "10.00",
            "event_count": 1,
            "net_amount": "-10.00",
        },
        "computed_net": "-10.00",
        "status": "REJECTED",
        "violation": "INVALID_FIELD_COUNT",
    },
    "DF-SOURCE-002": {
        "batch_id": "B202607230000105",
        "source": {
            "credit_amount": "200.00",
            "currency": "BRL",
            "debit_amount": "26.55",
            "event_count": 2,
            "net_amount": "173.44",
        },
        "computed_net": "173.45",
        "status": "REJECTED",
        "violation": "SOURCE_CONTROL_NET_MISMATCH",
    },
}


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON_ROOT / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


class Type02GenerationIntegrationTest(unittest.TestCase):
    """Verify metadata, schemas, controls, and immutable bundle linking."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source_validator = _validator("source-manifest.schema.json")
        cls.receipt_validator = _validator(
            "generation-receipt.schema.json"
        )

    def test_all_five_bundles_are_schema_valid_and_self_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            output_root = Path(output)
            for scenario, expected in EXPECTED.items():
                with self.subTest(scenario=scenario):
                    bundle = generate(
                        type_number="02",
                        scenario=scenario,
                        output_root=output_root,
                        contracts_root=CONTRACTS_ROOT,
                    )
                    manifest_bytes = bundle.manifest_file.read_bytes()
                    receipt_bytes = bundle.receipt_file.read_bytes()
                    manifest = json.loads(manifest_bytes)
                    receipt = json.loads(receipt_bytes)

                    self.source_validator.validate(manifest)
                    self.receipt_validator.validate(receipt)
                    self.assertEqual(bundle.batch_id, expected["batch_id"])
                    self.assertEqual(
                        manifest["source_controls"],
                        expected["source"],
                    )
                    self.assertEqual(
                        manifest["source_file"]["sha256"],
                        sha256_hex(bundle.raw_file.read_bytes()),
                    )
                    self.assertEqual(
                        manifest["source_file"]["size_bytes"],
                        bundle.raw_file.stat().st_size,
                    )
                    self.assertEqual(
                        bundle.checksum_file.read_bytes(),
                        (
                            f"{bundle.raw_sha256}  {bundle.raw_file.name}\n"
                        ).encode("ascii"),
                    )
                    self.assertEqual(
                        receipt["artifacts"]["source_manifest_sha256"],
                        sha256_hex(manifest_bytes),
                    )
                    self.assertEqual(
                        receipt["controls"]["computed_net_amount"],
                        expected["computed_net"],
                    )
                    self.assertEqual(
                        receipt["controls"]["declared_net_amount"],
                        expected["source"]["net_amount"],
                    )
                    self.assertEqual(
                        receipt["expected_contract_result"],
                        {
                            "status": expected["status"],
                            "violation": expected["violation"],
                        },
                    )

    def test_type02_unsupported_scenario_creates_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            output_root = Path(output) / "not-created"
            with self.assertRaisesRegex(
                GenerationError,
                "Unsupported Type 02 scenario",
            ):
                generate(
                    type_number="02",
                    scenario="not-a-scenario",
                    output_root=output_root,
                    contracts_root=CONTRACTS_ROOT,
                )
            self.assertFalse(output_root.exists())


if __name__ == "__main__":
    unittest.main()
