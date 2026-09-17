"""Bundle-level integration tests for Type 01 generation."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from jsonschema import Draft202012Validator

from checksum import sha256_hex
from cli import main
from generation import generate
from models import GenerationError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts" / "types"
COMMON_ROOT = REPOSITORY_ROOT / "contracts" / "common"
RAW_FILENAME = "NW_CARD_SETTLEMENT_20260723_B202607230000001.dat"
CANONICAL_SHA256 = (
    "66c2d02217d133e88ec28486f170a90fc"
    "134ff7a70e63e8096b8be37dacbd82f"
)
SENSITIVE_VALUES = (
    b"4111111111111111",
    b"12345678909",
    b"5555555555554444",
    b"98765432100",
)
EXPECTED = {
    "valid-minimal": {
        "batch_id": "B202607230000001",
        "raw_name": RAW_FILENAME,
        "size_bytes": 338,
        "source_controls": {
            "currency": "BRL",
            "detail_count": 2,
            "net_amount": "173.45",
        },
        "receipt_controls": {
            "computed_detail_count": 2,
            "computed_net_amount": "173.45",
            "declared_detail_count": 2,
            "declared_net_amount": "173.45",
        },
        "status": "ACCEPTED",
        "violation": None,
    },
    "valid-boundary": {
        "batch_id": "B202402290000001",
        "raw_name": (
            "NW_CARD_SETTLEMENT_20240229_B202402290000001.dat"
        ),
        "size_bytes": 213,
        "source_controls": {
            "currency": "BRL",
            "detail_count": 1,
            "net_amount": "9999999999.99",
        },
        "receipt_controls": {
            "computed_detail_count": 1,
            "computed_net_amount": "9999999999.99",
            "declared_detail_count": 1,
            "declared_net_amount": "9999999999.99",
        },
        "status": "ACCEPTED",
        "violation": None,
    },
    "negative-overpunch": {
        "batch_id": "B202607230000002",
        "raw_name": (
            "NW_CARD_SETTLEMENT_20260723_B202607230000002.dat"
        ),
        "size_bytes": 213,
        "source_controls": {
            "currency": "BRL",
            "detail_count": 1,
            "net_amount": "-12.34",
        },
        "receipt_controls": {
            "computed_detail_count": 1,
            "computed_net_amount": "-12.34",
            "declared_detail_count": 1,
            "declared_net_amount": "-12.34",
        },
        "status": "ACCEPTED",
        "violation": None,
    },
    "malformed": {
        "batch_id": "B202607230000003",
        "raw_name": (
            "NW_CARD_SETTLEMENT_20260723_B202607230000003.dat"
        ),
        "size_bytes": 213,
        "source_controls": {
            "currency": "BRL",
            "detail_count": 1,
            "net_amount": "-12.34",
        },
        "receipt_controls": {
            "computed_detail_count": 1,
            "computed_net_amount": None,
            "declared_detail_count": 1,
            "declared_net_amount": "-12.34",
        },
        "status": "REJECTED",
        "violation": "INVALID_OVERPUNCH",
    },
    "DF-SOURCE-001": {
        "batch_id": "B202607230000004",
        "raw_name": (
            "NW_CARD_SETTLEMENT_20260723_B202607230000004.dat"
        ),
        "size_bytes": 338,
        "source_controls": {
            "currency": "BRL",
            "detail_count": 2,
            "net_amount": "173.44",
        },
        "receipt_controls": {
            "computed_detail_count": 2,
            "computed_net_amount": "173.45",
            "declared_detail_count": 2,
            "declared_net_amount": "173.44",
        },
        "status": "REJECTED",
        "violation": "SOURCE_CONTROL_TOTAL_MISMATCH",
    },
}


def _artifact_contents(directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def _validator(filename: str) -> Draft202012Validator:
    schema = json.loads((COMMON_ROOT / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


class Type01GenerationIntegrationTest(unittest.TestCase):
    """Verify every Type 01 bundle and its privacy-safe metadata links."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source_validator = _validator("source-manifest.schema.json")
        cls.receipt_validator = _validator(
            "generation-receipt.schema.json"
        )

    def assert_artifacts_equal(
        self,
        first: dict[str, bytes],
        second: dict[str, bytes],
    ) -> None:
        """Compare artifacts without disclosing restricted raw contents."""

        self.assertEqual(set(first), set(second))
        for filename in sorted(first):
            first_content = first[filename]
            second_content = second[filename]
            if first_content == second_content:
                continue
            mismatch = next(
                (
                    offset
                    for offset, pair in enumerate(
                        zip(first_content, second_content, strict=False)
                    )
                    if pair[0] != pair[1]
                ),
                min(len(first_content), len(second_content)),
            )
            self.fail(
                "Artifacts differ without exposing their contents: "
                f"filename={filename}, "
                f"first_length={len(first_content)}, "
                f"second_length={len(second_content)}, "
                f"first_sha256={sha256_hex(first_content)}, "
                f"second_sha256={sha256_hex(second_content)}, "
                f"first_mismatch_offset={mismatch}"
            )

    def assert_no_restricted_identifiers(
        self,
        content: bytes,
        *,
        location: str,
    ) -> None:
        """Fail safely when Type 01 PAN or CPF values escape raw data."""

        if any(value in content for value in SENSITIVE_VALUES):
            self.fail(f"A restricted identifier appeared in {location}")

    def test_all_five_bundles_are_schema_valid_and_self_consistent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as output:
            output_root = Path(output)
            for scenario, expected in EXPECTED.items():
                with self.subTest(scenario=scenario):
                    bundle = generate(
                        type_number="01",
                        scenario=scenario,
                        output_root=output_root,
                        contracts_root=CONTRACTS_ROOT,
                    )
                    raw_bytes = bundle.raw_file.read_bytes()
                    manifest_bytes = bundle.manifest_file.read_bytes()
                    receipt_bytes = bundle.receipt_file.read_bytes()
                    manifest = json.loads(manifest_bytes)
                    receipt = json.loads(receipt_bytes)

                    self.source_validator.validate(manifest)
                    self.receipt_validator.validate(receipt)
                    self.assertEqual(bundle.batch_id, expected["batch_id"])
                    self.assertEqual(
                        manifest["batch_id"],
                        expected["batch_id"],
                    )
                    self.assertEqual(
                        receipt["batch_id"],
                        expected["batch_id"],
                    )
                    self.assertEqual(
                        manifest["file_type"]["number"],
                        "01",
                    )
                    self.assertEqual(
                        receipt["contract"]["type_number"],
                        "01",
                    )
                    self.assertEqual(
                        bundle.raw_file.name,
                        expected["raw_name"],
                    )
                    self.assertEqual(
                        len(raw_bytes),
                        expected["size_bytes"],
                    )
                    self.assertEqual(
                        manifest["source_controls"],
                        expected["source_controls"],
                    )
                    self.assertEqual(
                        manifest["source_file"]["name"],
                        expected["raw_name"],
                    )
                    self.assertEqual(
                        manifest["source_file"]["size_bytes"],
                        expected["size_bytes"],
                    )
                    self.assertEqual(
                        manifest["source_file"]["sha256"],
                        sha256_hex(raw_bytes),
                    )
                    self.assertNotIn("scenario", manifest)
                    self.assertNotIn("fault", manifest)
                    self.assertEqual(
                        bundle.checksum_file.read_bytes(),
                        (
                            f"{bundle.raw_sha256}  "
                            f"{bundle.raw_file.name}\n"
                        ).encode("ascii"),
                    )
                    self.assertEqual(
                        receipt["controls"],
                        expected["receipt_controls"],
                    )
                    self.assertEqual(receipt["scenario"], scenario)
                    self.assertEqual(
                        receipt["expected_contract_result"],
                        {
                            "status": expected["status"],
                            "violation": expected["violation"],
                        },
                    )
                    self.assertEqual(
                        receipt["artifacts"]["data_file"],
                        expected["raw_name"],
                    )
                    self.assertEqual(
                        receipt["artifacts"]["data_sha256"],
                        sha256_hex(raw_bytes),
                    )
                    self.assertEqual(
                        receipt["artifacts"]["source_manifest"],
                        "source-manifest.json",
                    )
                    self.assertEqual(
                        receipt["artifacts"][
                            "source_manifest_sha256"
                        ],
                        sha256_hex(manifest_bytes),
                    )

    def test_valid_minimal_bundle_is_deterministic_and_privacy_scoped(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            first_bundle = generate(
                type_number="01",
                scenario="valid-minimal",
                output_root=Path(first),
                contracts_root=CONTRACTS_ROOT,
            )
            second_bundle = generate(
                type_number="01",
                scenario="valid-minimal",
                output_root=Path(second),
                contracts_root=CONTRACTS_ROOT,
            )

            first_artifacts = _artifact_contents(first_bundle.directory)
            second_artifacts = _artifact_contents(second_bundle.directory)
            self.assert_artifacts_equal(first_artifacts, second_artifacts)
            self.assertEqual(
                set(first_artifacts),
                {
                    RAW_FILENAME,
                    f"{RAW_FILENAME}.sha256",
                    "source-manifest.json",
                    "generation-receipt.json",
                },
            )

            raw_bytes = first_artifacts[RAW_FILENAME]
            self.assertEqual(sha256_hex(raw_bytes), CANONICAL_SHA256)
            self.assertEqual(
                first_artifacts[f"{RAW_FILENAME}.sha256"],
                f"{CANONICAL_SHA256}  {RAW_FILENAME}\n".encode("ascii"),
            )

            for filename, content in first_artifacts.items():
                if filename == RAW_FILENAME:
                    continue
                self.assert_no_restricted_identifiers(
                    content,
                    location=filename,
                )

    def test_unsupported_type01_scenario_creates_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            output_root = Path(output) / "not-created"
            with self.assertRaisesRegex(
                GenerationError,
                "Unsupported Type 01 scenario",
            ):
                generate(
                    type_number="01",
                    scenario="not-a-scenario",
                    output_root=output_root,
                    contracts_root=CONTRACTS_ROOT,
                )
            self.assertFalse(output_root.exists())

    def test_cli_output_contains_no_type01_raw_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--type",
                        "01",
                        "--scenario",
                        "valid-minimal",
                        "--output",
                        output,
                        "--contracts-root",
                        str(CONTRACTS_ROOT),
                    ]
                )
            self.assertEqual(exit_code, 0)
            captured = (stdout.getvalue() + stderr.getvalue()).encode("utf-8")
            self.assert_no_restricted_identifiers(
                captured,
                location="CLI output",
            )


if __name__ == "__main__":
    unittest.main()
