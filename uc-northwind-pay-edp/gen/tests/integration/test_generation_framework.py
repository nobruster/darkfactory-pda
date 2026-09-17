"""Shared DataGen integration tests independent of one business file type.

Type 01 is used only as a deterministic representative seed. The behaviors
proved here belong to the shared artifact writer, generator registry, and CLI.
Type 01 business assertions live in ``test_type_01_generation.py``.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import artifacts as artifacts_module
from checksum import sha256_hex
from cli import main
from generation import generate
from models import (
    ArtifactConflictError,
    ArtifactWriteError,
    GenerationError,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts" / "types"
REPRESENTATIVE_TYPE = "01"
REPRESENTATIVE_SCENARIO = "valid-minimal"
REPRESENTATIVE_BATCH_ID = "B202607230000001"


def _artifact_contents(directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


class GenerationFrameworkIntegrationTest(unittest.TestCase):
    """Prove failure safety and determinism at shared DataGen boundaries."""

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

    def test_existing_immutable_batch_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            output_root = Path(output)
            bundle = generate(
                type_number=REPRESENTATIVE_TYPE,
                scenario=REPRESENTATIVE_SCENARIO,
                output_root=output_root,
                contracts_root=CONTRACTS_ROOT,
            )
            before = _artifact_contents(bundle.directory)

            with self.assertRaises(ArtifactConflictError):
                generate(
                    type_number=REPRESENTATIVE_TYPE,
                    scenario=REPRESENTATIVE_SCENARIO,
                    output_root=output_root,
                    contracts_root=CONTRACTS_ROOT,
                )

            self.assert_artifacts_equal(
                _artifact_contents(bundle.directory),
                before,
            )
            self.assertFalse(
                any(
                    path.name.startswith(f".{REPRESENTATIVE_BATCH_ID}.")
                    for path in output_root.iterdir()
                )
            )

    def test_unsupported_type_creates_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            output_root = Path(output) / "not-created"
            with self.assertRaisesRegex(GenerationError, "Unsupported type"):
                generate(
                    type_number="99",
                    scenario=REPRESENTATIVE_SCENARIO,
                    output_root=output_root,
                    contracts_root=CONTRACTS_ROOT,
                )
            self.assertFalse(output_root.exists())

    def test_mid_write_failure_leaves_no_final_or_temporary_batch(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            output_root = Path(output)
            real_write = artifacts_module._write_private_file
            call_count = 0

            def fail_on_third_write(path: Path, content: bytes) -> None:
                nonlocal call_count
                call_count += 1
                if call_count == 3:
                    raise OSError("injected safe write failure")
                real_write(path, content)

            with patch(
                "artifacts._write_private_file",
                side_effect=fail_on_third_write,
            ):
                with self.assertRaises(ArtifactWriteError):
                    generate(
                        type_number=REPRESENTATIVE_TYPE,
                        scenario=REPRESENTATIVE_SCENARIO,
                        output_root=output_root,
                        contracts_root=CONTRACTS_ROOT,
                    )

            self.assertFalse(
                (output_root / REPRESENTATIVE_BATCH_ID).exists()
            )
            self.assertFalse(
                any(
                    path.name.startswith(f".{REPRESENTATIVE_BATCH_ID}.")
                    for path in output_root.iterdir()
                )
            )

    def test_cli_reports_filesystem_failure_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            blocked_output = Path(temporary) / "output-is-a-file"
            blocked_output.write_text("occupied", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--type",
                        REPRESENTATIVE_TYPE,
                        "--scenario",
                        REPRESENTATIVE_SCENARIO,
                        "--output",
                        str(blocked_output),
                        "--contracts-root",
                        str(CONTRACTS_ROOT),
                    ]
                )

            self.assertEqual(exit_code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("generation failed:", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_is_deterministic_across_cwd_timezone_and_locale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            first_output = temporary_root / "first"
            second_output = temporary_root / "second"
            cli_path = REPOSITORY_ROOT / "gen" / "src" / "cli.py"
            base_command = [
                sys.executable,
                str(cli_path),
                "--type",
                REPRESENTATIVE_TYPE,
                "--scenario",
                REPRESENTATIVE_SCENARIO,
                "--contracts-root",
                str(CONTRACTS_ROOT),
            ]
            first_environment = os.environ | {
                "LC_ALL": "C",
                "PYTHONHASHSEED": "1",
                "TZ": "UTC",
            }
            second_environment = os.environ | {
                "LC_ALL": "C",
                "PYTHONHASHSEED": "777",
                "TZ": "America/Sao_Paulo",
            }

            first = subprocess.run(
                [*base_command, "--output", str(first_output)],
                cwd=REPOSITORY_ROOT,
                env=first_environment,
                capture_output=True,
                check=False,
                text=True,
            )
            second = subprocess.run(
                [*base_command, "--output", str(second_output)],
                cwd=REPOSITORY_ROOT / "gen",
                env=second_environment,
                capture_output=True,
                check=False,
                text=True,
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            first_bundle = first_output / REPRESENTATIVE_BATCH_ID
            second_bundle = second_output / REPRESENTATIVE_BATCH_ID
            self.assert_artifacts_equal(
                _artifact_contents(first_bundle),
                _artifact_contents(second_bundle),
            )


if __name__ == "__main__":
    unittest.main()
