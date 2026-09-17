#!/usr/bin/env python3
"""Hermetic unit and Git-integration tests for the repository gate."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _gate_policy import GatePolicyError, parse_gate  # noqa: E402

CHECK_GATE = SCRIPTS / "check-gate.py"
CHECK_PATH = SCRIPTS / "check-path-policy.py"

POLICY_V2 = """\
version: 2
protected_paths:
  - "**/auth/**"
  - ".cvg/gate.yaml"
max_changed_files: 3
"""


class GateParserTests(unittest.TestCase):
    def test_v2_segment_globs_are_portable_and_case_sensitive(self) -> None:
        gate = parse_gate(POLICY_V2)
        self.assertEqual(gate.schema_version, 2)
        self.assertTrue(gate.forbids("auth/login.py"))
        self.assertTrue(gate.forbids("project/auth/login.py"))
        self.assertFalse(gate.forbids("project/Auth/login.py"))

        one_segment = parse_gate(
            'version: 2\nprotected_paths:\n  - "auth/*"\n'
        )
        self.assertTrue(one_segment.forbids("auth/login.py"))
        self.assertFalse(one_segment.forbids("auth/nested/login.py"))

    def test_v1_is_read_compatible_but_cannot_mix_v2_keys(self) -> None:
        legacy = parse_gate(
            'version: 1\ndenylist:\n  - "auth/**"\nmax_files: 2\n'
        )
        self.assertEqual(legacy.schema_version, 1)
        self.assertEqual(legacy.max_changed_files, 2)
        self.assertTrue(legacy.forbids("auth/login.py"))
        with self.assertRaises(GatePolicyError):
            parse_gate(
                'version: 1\ndenylist:\n  - "auth/**"\nmax_changed_files: 2\n'
            )

    def test_invalid_yaml_subset_fails_closed(self) -> None:
        invalid = (
            "",
            'protected_paths:\n  - "auth/**"\n',
            "version: 2\nprotected_paths:\n",
            'version: 2\nprotected_paths:\n  - ""\n',
            'version: 2\nversion: 2\nprotected_paths:\n  - "auth/**"\n',
            'version: 2\nprotected_paths:\n  - "auth/**"\nmax_changed_files: -1\n',
            'version: 2\nprotected_paths:\n  - "auth/**"\nauto_merge_allowlist:\n  - "docs/**"\n',
            'version: 2\nprotected_paths:\n  - "a/../auth/**"\n',
            'version: 2\nprotected_paths:\n  - "auth\\**"\n',
            'version: 2\nprotected_paths:\n  - "auth/**\n',
            'version:\t2\nprotected_paths:\n  - "auth/**"\n',
        )
        for text in invalid:
            with self.subTest(text=text):
                with self.assertRaises(GatePolicyError):
                    parse_gate(text)

    def test_policy_self_protection_is_not_optional(self) -> None:
        gate = parse_gate(
            'version: 2\nprotected_paths:\n  - "docs/private/**"\n'
        )
        self.assertEqual(gate.forbids(".cvg/gate.yaml"), "<policy-self>")

    def test_glob_work_is_bounded_for_adversarial_paths(self) -> None:
        too_deep = "/".join(["a"] * 257)
        with self.assertRaises(GatePolicyError):
            parse_gate(
                f'version: 2\nprotected_paths:\n  - "{too_deep}"\n'
            )
        recursive = parse_gate(
            'version: 2\nprotected_paths:\n  - "**/**/**/target"\n'
        )
        self.assertTrue(recursive.forbids("/".join(["a"] * 200 + ["target"])))


class GateGitIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="cvg-gate-test-")
        self.repo = Path(self.temp.name)
        self._git("init", "--quiet")
        self._git("config", "user.email", "gate@test.invalid")
        self._git("config", "user.name", "Gate Test")
        (self.repo / ".cvg").mkdir()
        (self.repo / ".cvg/gate.yaml").write_text(POLICY_V2, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            text=True,
            capture_output=True,
            check=True,
        )
        return proc.stdout.strip()

    def _commit_all(self) -> str:
        self._git("add", "-A")
        self._git("commit", "--quiet", "-m", "fixture")
        return self._git("rev-parse", "HEAD")

    def _run(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_nested_project_inherits_the_git_root_policy(self) -> None:
        project = self.repo / "project"
        (project / "cvg/tasks").mkdir(parents=True)
        self._commit_all()
        result = self._run(
            CHECK_GATE,
            "--repo",
            str(project),
            "--path",
            "auth/login.py",
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("inherited by: project", result.stdout)
        self.assertIn("CHECK_GATE=FORBIDDEN", result.stdout)

    def test_worktree_policy_deletion_cannot_disable_trusted_base(self) -> None:
        base = self._commit_all()
        (self.repo / ".cvg/gate.yaml").unlink()
        result = self._run(
            CHECK_PATH,
            "--repo",
            str(self.repo),
            "--gate-only",
            "--base",
            base,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(".cvg/gate.yaml", result.stdout)
        self.assertIn("<policy-self>", result.stdout)

    def test_task_cannot_introduce_policy_when_base_has_no_gate(self) -> None:
        (self.repo / ".cvg/gate.yaml").unlink()
        (self.repo / "README.md").write_text("base\n", encoding="utf-8")
        base = self._commit_all()
        (self.repo / ".cvg/gate.yaml").write_text(POLICY_V2, encoding="utf-8")
        result = self._run(
            CHECK_PATH,
            "--repo",
            str(self.repo),
            "--gate-only",
            "--base",
            base,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(".cvg/gate.yaml", result.stdout)
        self.assertIn("<policy-self>", result.stdout)

        (self.repo / ".cvg/gate.yaml").unlink()
        candidate = self._run(
            CHECK_GATE,
            "--repo",
            str(self.repo),
            "--path",
            ".cvg/gate.yaml",
        )
        self.assertEqual(candidate.returncode, 1, candidate.stdout + candidate.stderr)
        self.assertIn("CHECK_GATE=FORBIDDEN", candidate.stdout)

    def test_rename_reports_the_protected_source_endpoint(self) -> None:
        (self.repo / "auth").mkdir()
        (self.repo / "auth/secret.txt").write_text("secret\n", encoding="utf-8")
        base = self._commit_all()
        self._git("mv", "auth/secret.txt", "safe.txt")
        result = self._run(
            CHECK_PATH,
            "--repo",
            str(self.repo),
            "--gate-only",
            "--base",
            base,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("auth/secret.txt", result.stdout)

    def test_whole_repo_diff_rejects_changes_outside_nested_project(self) -> None:
        project = self.repo / "project"
        project.mkdir()
        (project / "inside.txt").write_text("inside\n", encoding="utf-8")
        (self.repo / "outside.txt").write_text("base\n", encoding="utf-8")
        base = self._commit_all()
        (self.repo / "outside.txt").write_text("changed\n", encoding="utf-8")
        result = self._run(
            CHECK_PATH,
            "--repo",
            str(project),
            "--gate-only",
            "--base",
            base,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Changes outside the consuming project", result.stdout)
        self.assertIn("outside.txt", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
