"""Privacy, determinism, permission, and immutability tests for Type 04."""

from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path

from checksum import sha256_hex
from generation import generate
from generators.type_04_ted_transfer_settlement import (
    all_returned_zero_net_batch,
    df_source_004_batch,
    malformed_batch,
    valid_boundary_batch,
    valid_minimal_batch,
)
from models import ArtifactConflictError, TedTransferBatch


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts" / "types"
BATCHES = {
    "valid-minimal": valid_minimal_batch,
    "valid-boundary": valid_boundary_batch,
    "malformed": malformed_batch,
    "all-returned-zero-net": all_returned_zero_net_batch,
    "DF-SOURCE-004": df_source_004_batch,
}


def _artifacts(directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def _restricted(batch: TedTransferBatch) -> tuple[bytes, ...]:
    values: list[bytes] = []
    for transfer in batch.transfers:
        for value in (
            transfer.payer_account,
            transfer.payer_tax_id,
            (
                transfer.payer_tax_id[3:]
                if transfer.payer_party_type == "F"
                else transfer.payer_tax_id
            ),
            transfer.beneficiary_account,
            transfer.beneficiary_tax_id,
            (
                transfer.beneficiary_tax_id[3:]
                if transfer.beneficiary_party_type == "F"
                else transfer.beneficiary_tax_id
            ),
            transfer.beneficiary_name,
        ):
            values.append(value.encode("ascii"))
        if transfer.return_record is not None:
            values.append(
                transfer.return_record.reason_text.encode("ascii")
            )
    return tuple(values)


class Type04SecurityAcceptanceTest(unittest.TestCase):
    """Prove restricted Type 04 values remain in the raw file only."""

    def test_restricted_values_never_enter_metadata(self) -> None:
        for scenario, factory in BATCHES.items():
            with self.subTest(scenario=scenario):
                batch = factory()
                restricted = _restricted(batch)
                with tempfile.TemporaryDirectory() as output:
                    bundle = generate(
                        type_number="04",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS,
                    )
                    artifacts = _artifacts(bundle.directory)
                    for secret in restricted:
                        self.assertIn(secret, artifacts[bundle.raw_file.name])
                    for name, content in artifacts.items():
                        if name == bundle.raw_file.name:
                            continue
                        if any(secret in content for secret in restricted):
                            self.fail(
                                "Type 04 restricted value escaped raw input: "
                                f"scenario={scenario}, artifact={name}"
                            )

    def test_outputs_are_private_deterministic_and_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as first_root:
            first_path = Path(first_root)
            for scenario in BATCHES:
                with self.subTest(scenario=scenario):
                    with tempfile.TemporaryDirectory() as second_root:
                        first = generate(
                            type_number="04",
                            scenario=scenario,
                            output_root=first_path,
                            contracts_root=CONTRACTS,
                        )
                        second = generate(
                            type_number="04",
                            scenario=scenario,
                            output_root=Path(second_root),
                            contracts_root=CONTRACTS,
                        )
                        first_artifacts = _artifacts(first.directory)
                        second_artifacts = _artifacts(second.directory)
                        if first_artifacts != second_artifacts:
                            self.fail(
                                "Type 04 deterministic artifacts differ: "
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
                                type_number="04",
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
