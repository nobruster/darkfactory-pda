"""Pure tests for the shared Type 03-05 end-to-end harness."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
HARNESS_DIRECTORY = ROOT / "tests" / "end-to-end"
sys.path.insert(0, str(HARNESS_DIRECTORY))

from typed_acceptance import (  # noqa: E402
    AcceptanceConfigurationError,
    ScenarioExpectation,
    _directory_snapshot,
    interrupt_scenario,
    load_expectations,
    runner_command,
    suite_for_type,
)


class TypedAcceptanceHarnessTest(unittest.TestCase):
    """Verify fail-closed configuration without contacting live services."""

    def test_only_types_03_through_05_are_supported(self) -> None:
        for type_number in ("03", "04", "05"):
            self.assertEqual(
                suite_for_type(type_number).type_number,
                type_number,
            )
        for type_number in ("01", "02", "06", "3", ""):
            with self.subTest(type_number=type_number):
                with self.assertRaises(AcceptanceConfigurationError):
                    suite_for_type(type_number)

    def test_each_suite_maps_exactly_five_canonical_yaml_outcomes(
        self,
    ) -> None:
        for type_number in ("03", "04", "05"):
            with self.subTest(type_number=type_number):
                spec = suite_for_type(type_number)
                expectations = load_expectations(spec)
                statuses = [
                    expectation.status
                    for expectation in expectations.values()
                ]
                self.assertEqual(len(expectations), 5)
                self.assertEqual(statuses.count("succeeded"), 3)
                self.assertEqual(statuses.count("quarantined"), 2)
                self.assertEqual(
                    {
                        expectation.scenario
                        for expectation in expectations.values()
                    },
                    {scenario.name for scenario in spec.scenarios},
                )
                self.assertTrue(
                    all(
                        expectation.batch_id.startswith("B")
                        for expectation in expectations.values()
                    )
                )

    def test_dark_factory_precedes_both_continuation_peers(self) -> None:
        for type_number in ("03", "04", "05"):
            with self.subTest(type_number=type_number):
                names = [
                    scenario.name
                    for scenario in suite_for_type(type_number).scenarios
                ]
                dark_factory_index = next(
                    index
                    for index, name in enumerate(names)
                    if name.startswith("DF-SOURCE-")
                )
                self.assertLess(
                    dark_factory_index,
                    names.index("valid-boundary"),
                )
                self.assertEqual(len(names[dark_factory_index + 1 :]), 2)

    def test_runner_command_uses_only_the_public_typed_cli(self) -> None:
        spec = suite_for_type("04")
        command = runner_command(
            spec,
            "valid-minimal",
            output_root=Path("/tmp/generated"),
            evidence_root=Path("/tmp/evidence"),
        )
        self.assertEqual(
            Path(command[1]),
            ROOT / "legacy" / "runner" / "run_type.py",
        )
        self.assertEqual(command[2:4], ["--type", "04"])
        self.assertNotIn("run_type04.py", " ".join(command))
        with self.assertRaises(AcceptanceConfigurationError):
            runner_command(
                spec,
                "not-canonical",
                output_root=Path("/tmp/generated"),
                evidence_root=Path("/tmp/evidence"),
            )

    def test_interrupt_hook_is_bound_to_the_expected_batch(self) -> None:
        spec = suite_for_type("03")
        expectation = ScenarioExpectation(
            scenario="valid-minimal",
            batch_id="B202607230000201",
            status="succeeded",
            code=None,
            oracle={},
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch(
                "typed_acceptance.subprocess.run",
                return_value=SimpleNamespace(returncode=2),
            ) as run:
                interrupt_scenario(
                    spec,
                    expectation,
                    boundary="database_commit",
                    output_root=root / "generated",
                    evidence_root=root / "evidence",
                )

        environment = run.call_args.kwargs["env"]
        self.assertEqual(
            environment["NWP_TEST_INTERRUPT_AFTER"],
            "database_commit",
        )
        self.assertEqual(
            environment["NWP_TEST_INTERRUPT_BATCH_ID"],
            expectation.batch_id,
        )

    def test_contract_offset_extractors_find_values_to_guard(self) -> None:
        fixtures = {
            "03": "valid-minimal.rem",
            "04": "valid-minimal.dat",
            "05": "valid-minimal.csv",
        }
        for type_number, filename in fixtures.items():
            with self.subTest(type_number=type_number):
                spec = suite_for_type(type_number)
                values = spec.extract_evidence_values(
                    (spec.contract_main / filename).read_bytes()
                )
                self.assertTrue(values.restricted)
                self.assertTrue(values.row_scoped)
                self.assertTrue(
                    all(len(value) >= 8 for value in values.restricted)
                )
                self.assertTrue(
                    all(len(value) >= 16 for value in values.row_scoped)
                )

    def test_replay_snapshot_is_content_addressed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.json"
            nested = root / "nested"
            nested.mkdir()
            second = nested / "second.txt"
            first.write_text('{"status":"succeeded"}\n', encoding="utf-8")
            second.write_text("immutable\n", encoding="utf-8")
            before = dict(_directory_snapshot(root))
            second.write_text("changed\n", encoding="utf-8")
            after = dict(_directory_snapshot(root))
            self.assertEqual(before["first.json"], after["first.json"])
            self.assertNotEqual(
                before["nested/second.txt"],
                after["nested/second.txt"],
            )


if __name__ == "__main__":
    unittest.main()
