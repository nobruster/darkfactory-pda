from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from checksum import sha256_hex
from generation import generate
from models import ArtifactConflictError, WrittenBundle


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts" / "types"
CANONICAL_ROOT = CONTRACTS_ROOT / "01-card-settlement" / "main"

SCENARIOS = (
    "valid-minimal",
    "valid-boundary",
    "negative-overpunch",
    "malformed",
    "DF-SOURCE-001",
)

CANONICAL_FIXTURES = {
    "valid-minimal": (
        "valid-minimal.dat",
        "66c2d02217d133e88ec28486f170a90fc"
        "134ff7a70e63e8096b8be37dacbd82f",
    ),
    "valid-boundary": (
        "valid-boundary.dat",
        "b1bcb59bcc8e0163c1cdc853f8354c88"
        "1630ffbd1091385a2a368eea09b4f23d",
    ),
    "negative-overpunch": (
        "negative-overpunch.dat",
        "0c773790558e429aeaaf9beeb9e8ed8d"
        "ef45061b0804c9a4cb3e84825cac1de2",
    ),
    "malformed": (
        "malformed.dat",
        "c4b7815f3ae95d3259064a7a9afe52d"
        "0f30b6a289d456e09b896351294308934",
    ),
    "DF-SOURCE-001": (
        "df-source-001.dat",
        "4b72707c859c755fe9aeba6ec67996fb7"
        "b084ab0992231c8d60358bdfdd13980",
    ),
}

EXPECTED_CONTRACT_RESULTS = {
    "valid-minimal": {
        "status": "ACCEPTED",
        "violation": None,
    },
    "valid-boundary": {
        "status": "ACCEPTED",
        "violation": None,
    },
    "negative-overpunch": {
        "status": "ACCEPTED",
        "violation": None,
    },
    "malformed": {
        "status": "REJECTED",
        "violation": "INVALID_OVERPUNCH",
    },
    "DF-SOURCE-001": {
        "status": "REJECTED",
        "violation": "SOURCE_CONTROL_TOTAL_MISMATCH",
    },
}

EXPECTED_SOURCE_MANIFEST_SHA256 = {
    "valid-minimal": (
        "641b5841c62a3836cd8bafbf859d8cd17"
        "49748d34f804265ca9f29454a84ca63"
    ),
    "valid-boundary": (
        "c7069a1b19c2cdbee5911921b6f502e7"
        "b972441d5c07b0f960127c4d518e1754"
    ),
    "negative-overpunch": (
        "6e1ad151851ae818688ce64870b24a8f0"
        "9cb77d522fe541a249a535dac7e84e3"
    ),
    "malformed": (
        "ab63644b6c064e25b1fe727d9d34d368"
        "195850eb1c0ed9accd3951b4a9c5968f"
    ),
    "DF-SOURCE-001": (
        "0e730ad7c51eef1a429870b4ae08a7d6d"
        "bb9794e69798f69307a4b3d732ef0cc"
    ),
}

POSITIVE_OVERPUNCH = "{ABCDEFGHI"
NEGATIVE_OVERPUNCH = "}JKLMNOPQR"


def _artifact_contents(bundle: WrittenBundle) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(bundle.directory.iterdir())
        if path.is_file()
    }


def _artifact_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256_hex(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _raw_artifact(artifacts: dict[str, bytes]) -> tuple[str, bytes]:
    raw_names = [name for name in artifacts if name.endswith(".dat")]
    if len(raw_names) != 1:
        raise AssertionError(
            f"Expected one raw data artifact, found {len(raw_names)}"
        )
    raw_name = raw_names[0]
    return raw_name, artifacts[raw_name]


def _decode_overpunch_minor_units(encoded: bytes) -> int:
    try:
        text = encoded.decode("ascii")
    except UnicodeDecodeError as exc:
        raise AssertionError("Overpunch field is not ASCII") from exc
    if not text or not text[:-1].isdigit():
        raise AssertionError("Overpunch field has invalid magnitude digits")

    final = text[-1]
    if final in POSITIVE_OVERPUNCH:
        sign = 1
        final_digit = POSITIVE_OVERPUNCH.index(final)
    elif final in NEGATIVE_OVERPUNCH:
        sign = -1
        final_digit = NEGATIVE_OVERPUNCH.index(final)
    else:
        raise AssertionError("Overpunch field has an invalid sign character")

    return sign * int(f"{text[:-1]}{final_digit}")


class Type01SecurityAcceptanceTest(unittest.TestCase):
    maxDiff = None

    def assert_sensitive_bytes_equal(
        self,
        *,
        actual: bytes,
        expected: bytes,
        label: str,
    ) -> None:
        if actual == expected:
            return
        mismatch = next(
            (
                offset
                for offset, pair in enumerate(
                    zip(actual, expected, strict=False)
                )
                if pair[0] != pair[1]
            ),
            min(len(actual), len(expected)),
        )
        self.fail(
            "Sensitive artifacts differ without exposing their contents: "
            f"label={label}, "
            f"actual_length={len(actual)}, "
            f"expected_length={len(expected)}, "
            f"actual_sha256={sha256_hex(actual)}, "
            f"expected_sha256={sha256_hex(expected)}, "
            f"first_mismatch_offset={mismatch}"
        )

    def assert_no_identifiers(
        self,
        *,
        content: bytes,
        identifiers: tuple[bytes, ...],
        location: str,
    ) -> None:
        if any(identifier in content for identifier in identifiers):
            self.fail(f"A raw PAN or CPF appeared in {location}")

    def generate_scenario(
        self,
        *,
        scenario: str,
        output_root: Path,
    ) -> WrittenBundle:
        return generate(
            type_number="01",
            scenario=scenario,
            output_root=output_root,
            contracts_root=CONTRACTS_ROOT,
        )

    def assert_bundle_integrity_and_privacy(
        self,
        *,
        bundle: WrittenBundle,
        expected_scenario: str,
    ) -> tuple[bytes, dict[str, object], dict[str, object]]:
        artifacts = _artifact_contents(bundle)
        raw_name, raw_bytes = _raw_artifact(artifacts)
        expected_names = {
            raw_name,
            f"{raw_name}.sha256",
            "source-manifest.json",
            "generation-receipt.json",
        }
        self.assertEqual(set(artifacts), expected_names)

        records = raw_bytes.splitlines()
        details = [record for record in records if record[:1] == b"D"]
        self.assertGreaterEqual(len(details), 1)
        identifiers = tuple(
            value
            for detail in details
            for value in (detail[33:49], detail[49:60])
        )
        self.assertTrue(all(identifier in raw_bytes for identifier in identifiers))

        for name, content in artifacts.items():
            if name == raw_name:
                continue
            self.assert_no_identifiers(
                content=content,
                identifiers=identifiers,
                location=f"{expected_scenario}:{name}",
            )

        manifest_bytes = artifacts["source-manifest.json"]
        receipt_bytes = artifacts["generation-receipt.json"]
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        receipt = json.loads(receipt_bytes.decode("utf-8"))

        prohibited_manifest_disclosures = (
            expected_scenario.encode("ascii"),
            b'"scenario"',
            b'"fault"',
            b"SOURCE_CONTROL_TOTAL_MISMATCH",
            b"INVALID_OVERPUNCH",
        )
        if any(
            disclosure in manifest_bytes
            for disclosure in prohibited_manifest_disclosures
        ):
            self.fail(
                "The transport source manifest disclosed local scenario "
                "or fault metadata"
            )
        self.assertEqual(manifest["batch_id"], bundle.batch_id)
        self.assertEqual(manifest["source_file"]["name"], raw_name)
        self.assertEqual(
            manifest["source_file"]["size_bytes"],
            len(raw_bytes),
        )
        self.assertEqual(
            manifest["source_file"]["sha256"],
            sha256_hex(raw_bytes),
        )
        self.assertEqual(
            artifacts[f"{raw_name}.sha256"],
            f"{sha256_hex(raw_bytes)}  {raw_name}\n".encode("ascii"),
        )

        self.assertEqual(receipt["scenario"], expected_scenario)
        self.assertEqual(
            receipt["expected_contract_result"],
            EXPECTED_CONTRACT_RESULTS[expected_scenario],
        )
        self.assertEqual(receipt["artifacts"]["data_file"], raw_name)
        self.assertEqual(
            receipt["artifacts"]["data_sha256"],
            sha256_hex(raw_bytes),
        )
        self.assertEqual(
            receipt["artifacts"]["source_manifest"],
            "source-manifest.json",
        )
        self.assertEqual(
            receipt["artifacts"]["source_manifest_sha256"],
            sha256_hex(manifest_bytes),
        )
        return raw_bytes, manifest, receipt

    def test_every_scenario_keeps_raw_identifiers_out_of_metadata(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                with tempfile.TemporaryDirectory() as output:
                    bundle = self.generate_scenario(
                        scenario=scenario,
                        output_root=Path(output),
                    )
                    self.assert_bundle_integrity_and_privacy(
                        bundle=bundle,
                        expected_scenario=scenario,
                    )

    def test_canonical_scenarios_match_independent_contract_fixtures(
        self,
    ) -> None:
        for scenario, (fixture_name, expected_sha256) in CANONICAL_FIXTURES.items():
            with self.subTest(scenario=scenario):
                with tempfile.TemporaryDirectory() as output:
                    bundle = self.generate_scenario(
                        scenario=scenario,
                        output_root=Path(output),
                    )
                    artifacts = _artifact_contents(bundle)
                    _, raw_bytes = _raw_artifact(artifacts)
                    expected = (CANONICAL_ROOT / fixture_name).read_bytes()

                    self.assert_sensitive_bytes_equal(
                        actual=raw_bytes,
                        expected=expected,
                        label=scenario,
                    )
                    self.assertEqual(sha256_hex(raw_bytes), expected_sha256)

    def test_source_manifest_bytes_remain_frozen_for_every_scenario(
        self,
    ) -> None:
        for scenario, expected_sha256 in (
            EXPECTED_SOURCE_MANIFEST_SHA256.items()
        ):
            with self.subTest(scenario=scenario):
                with tempfile.TemporaryDirectory() as output:
                    bundle = self.generate_scenario(
                        scenario=scenario,
                        output_root=Path(output),
                    )
                    self.assertEqual(
                        sha256_hex(bundle.manifest_file.read_bytes()),
                        expected_sha256,
                    )

    def test_negative_scenario_is_a_valid_refund_with_negative_controls(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as output:
            bundle = self.generate_scenario(
                scenario="negative-overpunch",
                output_root=Path(output),
            )
            raw_bytes, manifest, receipt = (
                self.assert_bundle_integrity_and_privacy(
                    bundle=bundle,
                    expected_scenario="negative-overpunch",
                )
            )

            records = raw_bytes.splitlines()
            detail = next(record for record in records if record[:1] == b"D")
            trailer = next(record for record in records if record[:1] == b"T")
            self.assertEqual(detail[89:90], b"R")
            self.assertEqual(_decode_overpunch_minor_units(detail[74:86]), -1_234)
            self.assertEqual(
                _decode_overpunch_minor_units(trailer[15:30]),
                -1_234,
            )
            self.assertEqual(
                manifest["source_controls"],
                {
                    "currency": "BRL",
                    "detail_count": 1,
                    "net_amount": "-12.34",
                },
            )
            self.assertEqual(
                receipt["controls"],
                {
                    "computed_detail_count": 1,
                    "computed_net_amount": "-12.34",
                    "declared_detail_count": 1,
                    "declared_net_amount": "-12.34",
                },
            )
            self.assertEqual(
                receipt["expected_contract_result"],
                {
                    "status": "ACCEPTED",
                    "violation": None,
                },
            )

    def test_malformed_scenario_has_only_the_named_overpunch_violation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as output:
            bundle = self.generate_scenario(
                scenario="malformed",
                output_root=Path(output),
            )
            raw_bytes, manifest, receipt = (
                self.assert_bundle_integrity_and_privacy(
                    bundle=bundle,
                    expected_scenario="malformed",
                )
            )

            records = raw_bytes.splitlines()
            self.assertEqual([len(record) for record in records], [40, 124, 46])
            detail = next(record for record in records if record[:1] == b"D")
            trailer = next(record for record in records if record[:1] == b"T")
            self.assertEqual(detail[85:86], b"Z")
            with self.assertRaisesRegex(
                AssertionError,
                "invalid sign character",
            ):
                _decode_overpunch_minor_units(detail[74:86])
            self.assertEqual(
                _decode_overpunch_minor_units(trailer[15:30]),
                -1_234,
            )
            self.assertEqual(manifest["source_controls"]["net_amount"], "-12.34")
            self.assertEqual(
                receipt["controls"]["declared_net_amount"],
                "-12.34",
            )
            self.assertIsNone(receipt["controls"]["computed_net_amount"])
            self.assertEqual(
                receipt["expected_contract_result"],
                {
                    "status": "REJECTED",
                    "violation": "INVALID_OVERPUNCH",
                },
            )

    def test_source_defect_is_hidden_from_transport_and_self_contradictory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as output:
            bundle = self.generate_scenario(
                scenario="DF-SOURCE-001",
                output_root=Path(output),
            )
            raw_bytes, manifest, receipt = (
                self.assert_bundle_integrity_and_privacy(
                    bundle=bundle,
                    expected_scenario="DF-SOURCE-001",
                )
            )
            self.assertEqual(bundle.batch_id, "B202607230000004")

            records = raw_bytes.splitlines()
            self.assertEqual(
                [len(record) for record in records],
                [40, 124, 124, 46],
            )
            details = [record for record in records if record[:1] == b"D"]
            trailer = next(record for record in records if record[:1] == b"T")
            independently_computed = sum(
                _decode_overpunch_minor_units(detail[74:86])
                for detail in details
            )
            source_declared = _decode_overpunch_minor_units(trailer[15:30])

            self.assertEqual(independently_computed, 17_345)
            self.assertEqual(source_declared, 17_344)
            self.assertEqual(int(trailer[9:15]), 2)
            self.assertEqual(
                manifest["source_controls"],
                {
                    "currency": "BRL",
                    "detail_count": 2,
                    "net_amount": "173.44",
                },
            )
            self.assertEqual(
                receipt["controls"],
                {
                    "computed_detail_count": 2,
                    "computed_net_amount": "173.45",
                    "declared_detail_count": 2,
                    "declared_net_amount": "173.44",
                },
            )
            self.assertEqual(
                receipt["expected_contract_result"],
                {
                    "status": "REJECTED",
                    "violation": "SOURCE_CONTROL_TOTAL_MISMATCH",
                },
            )

    def test_every_scenario_is_deterministic_and_immutable(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                with (
                    tempfile.TemporaryDirectory() as first,
                    tempfile.TemporaryDirectory() as second,
                ):
                    first_bundle = self.generate_scenario(
                        scenario=scenario,
                        output_root=Path(first),
                    )
                    second_bundle = self.generate_scenario(
                        scenario=scenario,
                        output_root=Path(second),
                    )
                    first_artifacts = _artifact_contents(first_bundle)
                    second_artifacts = _artifact_contents(second_bundle)
                    self.assertEqual(
                        set(first_artifacts),
                        set(second_artifacts),
                    )
                    for name in sorted(first_artifacts):
                        self.assert_sensitive_bytes_equal(
                            actual=first_artifacts[name],
                            expected=second_artifacts[name],
                            label=f"{scenario}:{name}",
                        )

        with tempfile.TemporaryDirectory() as shared:
            shared_root = Path(shared)
            batch_ids: set[str] = set()
            for scenario in SCENARIOS:
                bundle = self.generate_scenario(
                    scenario=scenario,
                    output_root=shared_root,
                )
                self.assertNotIn(bundle.batch_id, batch_ids)
                batch_ids.add(bundle.batch_id)

            before = _artifact_hashes(shared_root)
            for scenario in SCENARIOS:
                with self.assertRaises(ArtifactConflictError):
                    self.generate_scenario(
                        scenario=scenario,
                        output_root=shared_root,
                    )
            self.assertEqual(_artifact_hashes(shared_root), before)
            self.assertFalse(
                any(path.name.startswith(".B") for path in shared_root.iterdir())
            )


if __name__ == "__main__":
    unittest.main()
