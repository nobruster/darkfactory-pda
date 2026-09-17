"""Privacy, determinism, permission, and immutability acceptance for Type 02."""

from __future__ import annotations

import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from checksum import sha256_hex
from cli import main
from generation import generate
from generators.type_02_instant_payment_events import (
    df_source_002_batch,
    escaped_content_batch,
    malformed_batch,
    valid_boundary_batch,
    valid_minimal_batch,
)
from models import ArtifactConflictError, InstantPaymentBatch


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts" / "types"
SCENARIO_BATCHES = {
    "valid-minimal": valid_minimal_batch,
    "valid-boundary": valid_boundary_batch,
    "escaped-content": escaped_content_batch,
    "malformed": malformed_batch,
    "DF-SOURCE-002": df_source_002_batch,
}


def _artifact_contents(directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def _restricted_values(batch: InstantPaymentBatch) -> tuple[bytes, ...]:
    return tuple(
        value
        for event in batch.events
        for value in (
            event.end_to_end_id.encode("ascii"),
            event.transaction_id.encode("ascii"),
            event.payer_document.encode("ascii"),
            event.payee_document.encode("ascii"),
            event.description.encode("utf-8"),
            event.description.replace("\\", "\\\\")
            .replace("|", "\\|")
            .encode("utf-8"),
        )
    )


class Type02SecurityAcceptanceTest(unittest.TestCase):
    """Prove restricted Type 02 source values remain raw-only."""

    def assert_artifacts_equal(
        self,
        first: dict[str, bytes],
        second: dict[str, bytes],
        *,
        scenario: str,
    ) -> None:
        self.assertEqual(set(first), set(second))
        for filename in sorted(first):
            if first[filename] != second[filename]:
                self.fail(
                    "Deterministic artifacts differ without exposing content: "
                    f"scenario={scenario}, filename={filename}, "
                    f"first_sha256={sha256_hex(first[filename])}, "
                    f"second_sha256={sha256_hex(second[filename])}"
                )

    def test_every_scenario_keeps_restricted_values_raw_only(self) -> None:
        for scenario, batch_factory in SCENARIO_BATCHES.items():
            with self.subTest(scenario=scenario):
                batch = batch_factory()
                restricted = _restricted_values(batch)
                expected_raw_values = tuple(
                    value
                    for event in batch.events
                    for value in (
                        event.end_to_end_id.encode("ascii"),
                        event.transaction_id.encode("ascii"),
                        event.payer_document.encode("ascii"),
                        event.payee_document.encode("ascii"),
                        (
                            event.description
                            if scenario == "malformed"
                            else event.description.replace("\\", "\\\\").replace(
                                "|",
                                "\\|",
                            )
                        ).encode("utf-8"),
                    )
                )
                with tempfile.TemporaryDirectory() as output:
                    bundle = generate(
                        type_number="02",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS_ROOT,
                    )
                    artifacts = _artifact_contents(bundle.directory)
                    self.assertEqual(
                        set(artifacts),
                        {
                            bundle.raw_file.name,
                            bundle.checksum_file.name,
                            "source-manifest.json",
                            "generation-receipt.json",
                        },
                    )
                    for value in expected_raw_values:
                        self.assertIn(value, artifacts[bundle.raw_file.name])
                    for filename, content in artifacts.items():
                        if filename == bundle.raw_file.name:
                            continue
                        if any(value in content for value in restricted):
                            self.fail(
                                "A restricted document or description appeared "
                                f"outside raw input: scenario={scenario}, "
                                f"artifact={filename}"
                            )

                    manifest = artifacts["source-manifest.json"]
                    self.assertNotIn(scenario.encode("ascii"), manifest)
                    self.assertNotIn(b'"scenario"', manifest)
                    self.assertNotIn(b'"fault"', manifest)

    def test_bundles_are_private_deterministic_and_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as shared:
            shared_root = Path(shared)
            for scenario in SCENARIO_BATCHES:
                with self.subTest(scenario=scenario):
                    with tempfile.TemporaryDirectory() as second:
                        first_bundle = generate(
                            type_number="02",
                            scenario=scenario,
                            output_root=shared_root,
                            contracts_root=CONTRACTS_ROOT,
                        )
                        second_bundle = generate(
                            type_number="02",
                            scenario=scenario,
                            output_root=Path(second),
                            contracts_root=CONTRACTS_ROOT,
                        )
                        self.assert_artifacts_equal(
                            _artifact_contents(first_bundle.directory),
                            _artifact_contents(second_bundle.directory),
                            scenario=scenario,
                        )
                        self.assertEqual(
                            stat.S_IMODE(first_bundle.directory.stat().st_mode),
                            0o700,
                        )
                        for artifact in first_bundle.directory.iterdir():
                            self.assertEqual(
                                stat.S_IMODE(artifact.stat().st_mode),
                                0o600,
                            )
                        before = _artifact_contents(first_bundle.directory)
                        with self.assertRaises(ArtifactConflictError):
                            generate(
                                type_number="02",
                                scenario=scenario,
                                output_root=shared_root,
                                contracts_root=CONTRACTS_ROOT,
                            )
                        self.assert_artifacts_equal(
                            _artifact_contents(first_bundle.directory),
                            before,
                            scenario=scenario,
                        )
            self.assertFalse(
                any(path.name.startswith(".B") for path in shared_root.iterdir())
            )

    def test_cli_output_and_errors_do_not_disclose_restricted_values(self) -> None:
        batch = escaped_content_batch()
        restricted = _restricted_values(batch)
        with tempfile.TemporaryDirectory() as output:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--type",
                        "02",
                        "--scenario",
                        "escaped-content",
                        "--output",
                        output,
                        "--contracts-root",
                        str(CONTRACTS_ROOT),
                    ]
                )
            self.assertEqual(exit_code, 0)
            captured = (stdout.getvalue() + stderr.getvalue()).encode("utf-8")
            if any(value in captured for value in restricted):
                self.fail("Type 02 CLI output disclosed a restricted source value")

    def test_cli_is_deterministic_across_process_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first_output = root / "first"
            second_output = root / "second"
            cli_path = REPOSITORY_ROOT / "gen" / "src" / "cli.py"
            command = [
                sys.executable,
                str(cli_path),
                "--type",
                "02",
                "--scenario",
                "escaped-content",
                "--contracts-root",
                str(CONTRACTS_ROOT),
            ]
            first = subprocess.run(
                [*command, "--output", str(first_output)],
                cwd=REPOSITORY_ROOT,
                env=os.environ
                | {"LC_ALL": "C", "PYTHONHASHSEED": "1", "TZ": "UTC"},
                capture_output=True,
                check=False,
                text=True,
            )
            second = subprocess.run(
                [*command, "--output", str(second_output)],
                cwd=REPOSITORY_ROOT / "gen",
                env=os.environ
                | {
                    "LC_ALL": "C",
                    "PYTHONHASHSEED": "999",
                    "TZ": "America/Sao_Paulo",
                },
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assert_artifacts_equal(
                _artifact_contents(first_output / "B202607230000104"),
                _artifact_contents(second_output / "B202607230000104"),
                scenario="escaped-content",
            )


if __name__ == "__main__":
    unittest.main()
