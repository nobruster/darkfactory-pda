"""Privacy, determinism, permission, and immutability tests for Type 05."""

from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path

from checksum import sha256_hex
from generation import generate
from generators.type_05_merchant_fee_assessment import (
    df_source_005_batch,
    malformed_batch,
    rounding_half_up_batch,
    valid_boundary_batch,
    valid_minimal_batch,
)
from models import ArtifactConflictError, MerchantFeeBatch


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts" / "types"
BATCHES = {
    "valid-minimal": valid_minimal_batch,
    "valid-boundary": valid_boundary_batch,
    "malformed": malformed_batch,
    "rounding-half-up": rounding_half_up_batch,
    "DF-SOURCE-005": df_source_005_batch,
}


def _artifacts(directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def _raw_cnpjs(batch: MerchantFeeBatch) -> tuple[bytes, ...]:
    return tuple(
        row.merchant_tax_id.encode("utf-8")
        for row in batch.assessments
    )


def _metadata_prohibited(batch: MerchantFeeBatch) -> tuple[bytes, ...]:
    return tuple(
        value.encode("utf-8")
        for row in batch.assessments
        for value in (row.merchant_tax_id, row.description)
    )


class Type05SecurityAcceptanceTest(unittest.TestCase):
    """Prove Type 05 raw values never enter aggregate metadata."""

    def test_restricted_values_never_enter_metadata(self) -> None:
        for scenario, factory in BATCHES.items():
            with self.subTest(scenario=scenario):
                batch = factory()
                raw_cnpjs = _raw_cnpjs(batch)
                metadata_prohibited = _metadata_prohibited(batch)
                with tempfile.TemporaryDirectory() as output:
                    bundle = generate(
                        type_number="05",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS,
                    )
                    artifacts = _artifacts(bundle.directory)
                    for secret in raw_cnpjs:
                        self.assertIn(secret, artifacts[bundle.raw_file.name])
                    for name, content in artifacts.items():
                        if name == bundle.raw_file.name:
                            continue
                        if any(
                            secret in content
                            for secret in metadata_prohibited
                        ):
                            self.fail(
                                "Type 05 raw value escaped into metadata: "
                                f"scenario={scenario}, artifact={name}"
                            )

    def test_outputs_are_private_deterministic_and_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as first_root:
            first_path = Path(first_root)
            for scenario in BATCHES:
                with self.subTest(scenario=scenario):
                    with tempfile.TemporaryDirectory() as second_root:
                        first = generate(
                            type_number="05",
                            scenario=scenario,
                            output_root=first_path,
                            contracts_root=CONTRACTS,
                        )
                        second = generate(
                            type_number="05",
                            scenario=scenario,
                            output_root=Path(second_root),
                            contracts_root=CONTRACTS,
                        )
                        first_artifacts = _artifacts(first.directory)
                        second_artifacts = _artifacts(second.directory)
                        if first_artifacts != second_artifacts:
                            self.fail(
                                "Type 05 deterministic artifacts differ: "
                                f"scenario={scenario}, "
                                f"first_raw_sha256="
                                f"{sha256_hex(first.raw_file.read_bytes())}, "
                                f"second_raw_sha256="
                                f"{sha256_hex(second.raw_file.read_bytes())}"
                            )
                        self.assertEqual(
                            stat.S_IMODE(first.directory.stat().st_mode),
                            0o700,
                        )
                        self.assertTrue(
                            all(
                                stat.S_IMODE(path.stat().st_mode) == 0o600
                                for path in first.directory.iterdir()
                            )
                        )
                        with self.assertRaises(ArtifactConflictError):
                            generate(
                                type_number="05",
                                scenario=scenario,
                                output_root=first_path,
                                contracts_root=CONTRACTS,
                            )
                        self.assertEqual(
                            _artifacts(first.directory),
                            first_artifacts,
                        )


if __name__ == "__main__":
    unittest.main()
