from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_make(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run Make without allowing a test command to wait indefinitely."""

    return subprocess.run(
        ["make", "--no-print-directory", *arguments],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )


class MakeFacadeTest(unittest.TestCase):
    """Protect the documented Make interface without invoking live services."""

    def test_help_lists_five_type_worker_test_and_compatibility_surface(
        self,
    ) -> None:
        result = run_make("help")

        self.assertEqual(result.returncode, 0, result.stderr)
        for target in (
            "init",
            "deploy",
            "gen",
            "migrate",
            "publish",
            "publish-raw",
            "run",
            "run-type",
            "run-file",
            "worker",
            "worker-once",
            "ontology",
            "ontology-ask",
            "ontology-ask-sql",
            "ontology-mcp",
            "test-contracts",
            "test-gen",
            "test-python",
            "test-postgres",
            "test-java",
            "test-type01",
            "test-e2e",
            "test-worker-e2e",
            "check",
            "test",
            "clean",
            "clean-runtime",
        ):
            self.assertRegex(result.stdout, rf"(?m)^  {target}\s")
        self.assertIn("TYPE=01|02|03|04|05|06|all", result.stdout)
        self.assertIn("POLL_INTERVAL=secs", result.stdout)
        self.assertIn("MAX_BATCHES=count", result.stdout)
        self.assertIn("BATCH and BUNDLE are mutually exclusive.", result.stdout)
        self.assertIn("ontology-ask-sql (without), then ontology-ask (with).", result.stdout)
        self.assertIn("There is no dlt, dbt, or modern target.", result.stdout)
        self.assertNotRegex(result.stdout, r"(?m)^  dlt\s")
        self.assertNotRegex(result.stdout, r"(?m)^  dbt\s")

    def test_deploy_applies_migrations_before_runtime_status(self) -> None:
        result = run_make("-n", "deploy")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "docker compose up -d --build --force-recreate --wait sftp postgres",
            result.stdout,
        )
        migration_position = result.stdout.index("legacy/postgres/migrate.py")
        status_position = result.stdout.index("legacy/runner/runtime_status.py")
        self.assertLess(migration_position, status_position)

    def test_migrate_target_uses_the_versioned_runner(self) -> None:
        result = run_make("-n", "migrate")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PYTHONPATH=legacy/runner", result.stdout)
        self.assertIn("legacy/postgres/migrate.py", result.stdout)

    def test_compatibility_aliases_preserve_existing_recipes(self) -> None:
        cases = (
            (
                ("-n", "publish", "BATCH=B202402290000001"),
                ("-n", "publish-raw", "BATCH=B202402290000001"),
            ),
            (
                ("-n", "run", "TYPE=01", "SCENARIO=valid-minimal"),
                ("-n", "run-type", "TYPE=01", "SCENARIO=valid-minimal"),
            ),
            (
                ("-n", "clean", "CONFIRM=clean-runtime"),
                ("-n", "clean-runtime", "CONFIRM=clean-runtime"),
            ),
        )

        for canonical, compatibility in cases:
            with self.subTest(target=canonical[1]):
                canonical_result = run_make(*canonical)
                compatibility_result = run_make(*compatibility)
                self.assertEqual(canonical_result.returncode, 0)
                self.assertEqual(compatibility_result.returncode, 0)
                self.assertEqual(
                    compatibility_result.stdout,
                    canonical_result.stdout,
                )

    def test_all_five_types_use_generic_generation_and_runner_entrypoints(
        self,
    ) -> None:
        for type_number in ("01", "02", "03", "04", "05", "06"):
            with self.subTest(type_number=type_number):
                generation = run_make(
                    "-n",
                    "gen",
                    f"TYPE={type_number}",
                    "SCENARIO=valid-minimal",
                )
                scenario = run_make(
                    "-n",
                    "run",
                    f"TYPE={type_number}",
                    "SCENARIO=valid-minimal",
                )
                explicit_file = run_make(
                    "-n",
                    "run-file",
                    f"TYPE={type_number}",
                    f"FILE=/tmp/type{type_number}.raw",
                )

                self.assertEqual(generation.returncode, 0)
                self.assertIn("gen/src/cli.py", generation.stdout)
                self.assertIn(
                    f'--type "{type_number}"',
                    generation.stdout,
                )
                self.assertEqual(scenario.returncode, 0)
                self.assertIn(
                    "legacy/runner/run_type.py",
                    scenario.stdout,
                )
                self.assertIn(
                    f'--type "{type_number}"',
                    scenario.stdout,
                )
                self.assertNotIn("run_type01.py", scenario.stdout)
                self.assertEqual(explicit_file.returncode, 0)
                self.assertIn(
                    "legacy/runner/run_type.py",
                    explicit_file.stdout,
                )
                self.assertIn(
                    f'--file "/tmp/type{type_number}.raw"',
                    explicit_file.stdout,
                )

    def test_all_selector_is_bounded_to_generation_run_and_e2e(self) -> None:
        generation = run_make(
            "-n",
            "gen",
            "TYPE=all",
            "SCENARIO=valid-minimal",
        )
        scenario = run_make(
            "-n",
            "run",
            "TYPE=all",
            "SCENARIO=valid-minimal",
        )
        acceptance = run_make("-n", "test-e2e", "TYPE=all")
        explicit_file = run_make(
            "run-file",
            "TYPE=all",
            "FILE=/tmp/source.raw",
        )

        self.assertEqual(generation.returncode, 0)
        self.assertIn("for type_number in 01 02 03 04 05 06", generation.stdout)
        self.assertEqual(scenario.returncode, 0)
        self.assertIn("for type_number in 01 02 03 04 05 06", scenario.stdout)
        self.assertEqual(acceptance.returncode, 0)
        self.assertIn(
            "run_type${type_number}_suite.py",
            acceptance.stdout,
        )
        self.assertNotEqual(explicit_file.returncode, 0)
        self.assertIn(
            "TYPE for run-file must be one of",
            explicit_file.stderr,
        )

    def test_worker_targets_are_foreground_and_single_cycle_facades(
        self,
    ) -> None:
        foreground = run_make(
            "-n",
            "worker",
            "POLL_INTERVAL=2.5",
            "MAX_BATCHES=7",
            "EVIDENCE=/tmp/evidence",
        )
        once = run_make(
            "-n",
            "worker-once",
            "POLL_INTERVAL=2.5",
            "MAX_BATCHES=7",
            "EVIDENCE=/tmp/evidence",
        )

        self.assertEqual(foreground.returncode, 0)
        self.assertIn("legacy/runner/worker.py", foreground.stdout)
        self.assertNotIn("--once", foreground.stdout)
        self.assertIn('--poll-interval "2.5"', foreground.stdout)
        self.assertIn('--max-batches "7"', foreground.stdout)
        self.assertIn('--evidence-root "/tmp/evidence"', foreground.stdout)
        self.assertEqual(once.returncode, 0)
        self.assertIn("--once", once.stdout)

    def test_layered_targets_keep_typed_and_worker_live_suites_separate(
        self,
    ) -> None:
        python_tests = run_make("-n", "test-python")
        typed = run_make("-n", "test-e2e", "TYPE=all")
        full = run_make("-n", "test")

        self.assertEqual(python_tests.returncode, 0)
        self.assertIn("--start-directory tests/unit", python_tests.stdout)
        self.assertIn(
            "--start-directory tests/security",
            python_tests.stdout,
        )
        self.assertIn(
            "--start-directory validation/oracle/tests",
            python_tests.stdout,
        )
        self.assertIn("--strict", python_tests.stdout)
        self.assertIn("--no-incremental", python_tests.stdout)
        self.assertNotIn("--ignore-missing-imports", python_tests.stdout)
        for worker_boundary in (
            "legacy/runner/worker.py",
            "legacy/intake/raw_intake.py",
            "legacy/publisher/raw_publisher.py",
        ):
            self.assertIn(worker_boundary, python_tests.stdout)
        self.assertEqual(typed.returncode, 0)
        self.assertIn(
            "for type_number in 01 02 03 04 05",
            typed.stdout,
        )
        self.assertEqual(full.returncode, 0)
        self.assertIn(
            "--start-directory tests/postgres",
            full.stdout,
        )
        self.assertIn(
            'legacy/runner/.venv/bin/python '
            '"tests/end-to-end/run_worker_suite.py"',
            full.stdout,
        )
        self.assertNotIn("run_type${type_number}_suite.py", full.stdout)

    def test_type01_gate_names_every_layer_without_cleaning_state(
        self,
    ) -> None:
        result = run_make("-n", "test-type01")

        self.assertEqual(result.returncode, 0, result.stderr)
        for proof in (
            "--start-directory gen/tests",
            "--pattern 'test_type_01_*.py'",
            "--start-directory tests/contracts",
            "--start-directory tests/unit",
            "--start-directory validation/oracle/tests",
            "--start-directory tests/security",
            "--pattern 'test_worker_security.py'",
            "docker compose build processor",
            "docker compose config --quiet",
            "--start-directory tests/postgres",
            "tests/end-to-end/run_type01_suite.py",
        ):
            self.assertIn(proof, result.stdout)
        self.assertNotIn("clean_runtime.py", result.stdout)
        self.assertNotIn("docker compose down", result.stdout)

    def test_worker_live_gate_uses_the_implemented_suite_without_indirection(
        self,
    ) -> None:
        result = run_make("-n", "test-worker-e2e")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            'legacy/runner/.venv/bin/python '
            '"tests/end-to-end/run_worker_suite.py"',
            result.stdout,
        )

    def test_publish_requires_exactly_one_bundle_selector(self) -> None:
        missing = run_make("publish")
        conflicting = run_make(
            "publish",
            "BATCH=B202402290000001",
            "BUNDLE=/tmp/bundle",
        )

        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("set exactly one of BATCH", missing.stderr)
        self.assertNotEqual(conflicting.returncode, 0)
        self.assertIn("mutually exclusive", conflicting.stderr)

    def test_publish_resolves_batch_below_configured_output(self) -> None:
        result = run_make(
            "-n",
            "publish",
            "BATCH=B202402290000001",
            "OUTPUT=/tmp/generated",
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn(
            'publish_raw_cli.py \\\n\t\t"/tmp/generated/B202402290000001"',
            result.stdout,
        )

    def test_clean_refuses_to_touch_state_without_exact_confirmation(
        self,
    ) -> None:
        result = run_make("clean")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "rerun with CONFIRM=clean-runtime",
            result.stderr,
        )


class DocumentationLinksTest(unittest.TestCase):
    """Keep the operator-facing local Markdown navigation intact."""

    def test_local_markdown_links_resolve(self) -> None:
        documents = (
            ROOT / "README.md",
            *(ROOT / "plans").glob("*.md"),
            *(ROOT / "docs").glob("*.md"),
            ROOT / "tests" / "README.md",
        )
        missing: list[str] = []

        for document in documents:
            content = document.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
                path_text = target.split("#", 1)[0]
                if not path_text or "://" in path_text or path_text.startswith(
                    "mailto:"
                ):
                    continue
                linked_path = (document.parent / path_text).resolve()
                if not linked_path.exists():
                    missing.append(f"{document.relative_to(ROOT)} -> {target}")

        self.assertEqual(missing, [])

    def test_documented_make_commands_name_real_targets(self) -> None:
        documents = (
            ROOT / "README.md",
            *(ROOT / "plans").glob("*.md"),
            ROOT / "legacy" / "processor" / "README.md",
            *(ROOT / "docs").glob("*.md"),
            ROOT / "tests" / "README.md",
        )
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        available = set(
            re.findall(
                r"(?m)^([a-zA-Z0-9_-]+):",
                makefile,
            )
        )
        missing: list[str] = []

        for document in documents:
            content = document.read_text(encoding="utf-8")
            for block in re.findall(
                r"```(?:bash|sh)?\n(.*?)```",
                content,
                flags=re.DOTALL,
            ):
                for target in re.findall(
                    r"(?m)^\s*make\s+([a-zA-Z0-9_-]+)",
                    block,
                ):
                    if target not in available:
                        missing.append(
                            f"{document.relative_to(ROOT)} -> make {target}"
                        )

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
