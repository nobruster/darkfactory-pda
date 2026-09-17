from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import briefspec.installers as installers
from briefspec.diagnostics import doctor_runtime
from briefspec.errors import InstallConflict
from briefspec.models import Runtime


def test_invalid_install_scope_is_rejected_before_writes(
    isolated_homes: dict[str, Path],
) -> None:
    with pytest.raises(ValueError, match="scope must be user or project"):
        installers.install_runtime(Runtime.CODEX, scope="system")
    assert not isolated_homes["codex"].exists()


def test_non_object_hook_configuration_is_a_conflict(
    isolated_homes: dict[str, Path],
) -> None:
    _, _, hook = installers._user_targets(Runtime.CODEX)
    hook.parent.mkdir(parents=True)
    hook.write_text("[]", encoding="utf-8")
    with pytest.raises(InstallConflict, match="non-object JSON"):
        installers.install_runtime(Runtime.CODEX)
    assert hook.read_text(encoding="utf-8") == "[]"


def test_foreign_copilot_instruction_aborts_before_any_project_mutation(
    isolated_homes: dict[str, Path],
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    instruction = project / ".github" / "instructions" / "brief-spec.instructions.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("Repository-owned instructions.", encoding="utf-8")
    skills, pyz, hook = installers._project_targets(Runtime.COPILOT, project)

    with pytest.raises(InstallConflict, match="foreign file"):
        installers.install_runtime(Runtime.COPILOT, scope="project", project=project)

    assert instruction.read_text(encoding="utf-8") == "Repository-owned instructions."
    assert not skills.exists()
    assert not pyz.exists()
    assert not hook.exists()


def test_install_transaction_rolls_back_all_partial_writes(
    isolated_homes: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skills, pyz, hook = installers._user_targets(Runtime.CLAUDE)
    receipt = installers.receipt_path(Runtime.CLAUDE, "user")
    original_atomic_write = installers.atomic_write
    failed = False

    def fail_once_at_receipt(path: Path, content: bytes, mode: int = 0o600) -> None:
        nonlocal failed
        if path == receipt and not failed:
            failed = True
            raise OSError("simulated receipt failure")
        original_atomic_write(path, content, mode)

    monkeypatch.setattr(installers, "atomic_write", fail_once_at_receipt)
    with pytest.raises(OSError, match="simulated receipt failure"):
        installers.install_runtime(Runtime.CLAUDE)

    assert not receipt.exists()
    assert not pyz.exists()
    assert not hook.exists()
    assert not any(path.is_file() for path in skills.rglob("*"))


def test_install_rollback_restores_preexisting_hook_bytes(
    isolated_homes: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, hook = installers._user_targets(Runtime.CODEX)
    hook.parent.mkdir(parents=True)
    original_hook = b'{"hooks":{"Stop":[]},"owner":"repository"}\n'
    hook.write_bytes(original_hook)
    receipt = installers.receipt_path(Runtime.CODEX, "user")
    original_atomic_write = installers.atomic_write
    failed = False

    def fail_once_at_receipt(path: Path, content: bytes, mode: int = 0o600) -> None:
        nonlocal failed
        if path == receipt and not failed:
            failed = True
            raise OSError("simulated receipt failure")
        original_atomic_write(path, content, mode)

    monkeypatch.setattr(installers, "atomic_write", fail_once_at_receipt)
    with pytest.raises(OSError, match="simulated receipt failure"):
        installers.install_runtime(Runtime.CODEX)
    assert hook.read_bytes() == original_hook


def test_rollback_failure_is_attached_to_original_error(
    isolated_homes: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        installers,
        "build_zipapp",
        lambda destination: (_ for _ in ()).throw(OSError("build failed")),
    )
    monkeypatch.setattr(
        installers,
        "_restore_files",
        lambda snapshots: (_ for _ in ()).throw(OSError("rollback failed")),
    )
    with pytest.raises(OSError, match="build failed") as raised:
        installers.install_runtime(Runtime.COPILOT)
    assert raised.value.__notes__ == ["Brief-Spec rollback also failed: rollback failed"]


def test_second_project_install_recognizes_unchanged_managed_instruction(
    isolated_homes: dict[str, Path],
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    installers.install_runtime(Runtime.COPILOT, scope="project", project=project)
    result = installers.install_runtime(Runtime.COPILOT, scope="project", project=project)
    instruction = project / ".github" / "instructions" / "brief-spec.instructions.md"
    operations = [
        operation for operation in result["operations"] if operation["path"] == str(instruction)
    ]
    assert operations == [
        {
            "action": "unchanged",
            "path": str(instruction),
            "detail": "already current",
        }
    ]


def test_repeat_install_upgrades_unchanged_receipt_owned_skill_references(
    isolated_homes: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    installers.install_runtime(Runtime.CODEX, scope="project", project=project)
    target = project / ".agents" / "skills" / "outcome-brief" / "references" / "contract.md"

    staged_resources = tmp_path / "staged-resources"
    shutil.copytree(installers.resource_root() / "skills", staged_resources / "skills")
    staged_contract = staged_resources / "skills" / "outcome-brief" / "references" / "contract.md"
    updated = staged_contract.read_text(encoding="utf-8") + "\nManaged upgrade.\n"
    staged_contract.write_text(updated, encoding="utf-8")
    monkeypatch.setattr(installers, "resource_root", lambda: staged_resources)

    installers.install_runtime(Runtime.CODEX, scope="project", project=project)

    assert target.read_text(encoding="utf-8") == updated


def test_repeat_install_preserves_modified_receipt_owned_skill_references(
    isolated_homes: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    installers.install_runtime(Runtime.CODEX, scope="project", project=project)
    target = project / ".agents" / "skills" / "outcome-brief" / "references" / "contract.md"
    target.write_text("Repository-specific contract.\n", encoding="utf-8")

    staged_resources = tmp_path / "staged-resources"
    shutil.copytree(installers.resource_root() / "skills", staged_resources / "skills")
    staged_contract = staged_resources / "skills" / "outcome-brief" / "references" / "contract.md"
    staged_contract.write_text("Managed upgrade.\n", encoding="utf-8")
    monkeypatch.setattr(installers, "resource_root", lambda: staged_resources)

    result = installers.install_runtime(Runtime.CODEX, scope="project", project=project)

    assert target.read_text(encoding="utf-8") == "Repository-specific contract.\n"
    candidate = target.with_name("contract.md.brief-spec-new")
    assert candidate.read_text(encoding="utf-8") == "Managed upgrade.\n"
    assert any(operation["action"] == "conflict" for operation in result["operations"])
    report = doctor_runtime(Runtime.CODEX, scope="project", project=project)
    assert report["status"] == "WARN"
    assert any(check["name"] == "managed file drift" for check in report["checks"])

    installers.install_runtime(
        Runtime.CODEX,
        scope="project",
        project=project,
        replace_modified=True,
    )
    assert target.read_text(encoding="utf-8") == "Managed upgrade.\n"
    assert not candidate.exists()


def test_codex_project_hook_executes_from_nested_directory(
    isolated_homes: dict[str, Path],
    tmp_path: Path,
) -> None:
    project = tmp_path / "project with spaces"
    project.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
    installers.install_runtime(Runtime.CODEX, scope="project", project=project)
    _, _, hook = installers._project_targets(Runtime.CODEX, project.resolve())
    hook_text = hook.read_text(encoding="utf-8")
    value = json.loads(hook_text)
    handler = value["hooks"]["SessionStart"][0]["hooks"][0]
    command = handler["commandWindows"] if os.name == "nt" else handler["command"]
    nested = project / "docs" / "architecture"
    nested.mkdir(parents=True)
    payload = {
        "session_id": "nested-project-hook",
        "cwd": str(nested),
        "hook_event_name": "SessionStart",
    }

    completed = subprocess.run(
        command,
        cwd=nested,
        check=False,
        capture_output=True,
        input=json.dumps(payload),
        shell=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert isinstance(json.loads(completed.stdout), dict)
    assert "git rev-parse --show-toplevel" in handler["command"]
    assert "commandWindows" in handler
    assert ".codex/brief-spec/brief-spec.pyz" in handler["commandWindows"]
    assert str(project.resolve()) not in hook_text


def test_claude_project_hook_uses_project_dir_anchor(
    isolated_homes: dict[str, Path],
    tmp_path: Path,
) -> None:
    project = tmp_path / "claude"
    project.mkdir()
    installers.install_runtime(Runtime.CLAUDE, scope="project", project=project)
    _, _, hook = installers._project_targets(Runtime.CLAUDE, project.resolve())
    text = hook.read_text(encoding="utf-8")
    value = json.loads(text)
    commands = [
        handler["command"]
        for entries in value["hooks"].values()
        for entry in entries
        for handler in entry["hooks"]
    ]
    assert all(
        '"$CLAUDE_PROJECT_DIR/.claude/brief-spec/brief-spec.pyz"' in command for command in commands
    )
    assert str(project.resolve()) not in text


def test_copilot_project_hook_is_vscode_compatible_while_user_hook_stays_native(
    isolated_homes: dict[str, Path],
    tmp_path: Path,
) -> None:
    project = tmp_path / "copilot-project"
    project.mkdir()
    installers.install_runtime(Runtime.COPILOT, scope="project", project=project)
    _, _, project_hook = installers._project_targets(Runtime.COPILOT, project.resolve())
    project_value = json.loads(project_hook.read_text(encoding="utf-8"))
    assert set(project_value["hooks"]) == {
        "SessionStart",
        "UserPromptSubmit",
        "PostToolUse",
        "PreCompact",
        "Stop",
    }
    for entries in project_value["hooks"].values():
        command_text = json.dumps(entries)
        assert "--output-profile vscode" in command_text

    installers.install_runtime(Runtime.COPILOT)
    _, _, user_hook = installers._user_targets(Runtime.COPILOT)
    user_value = json.loads(user_hook.read_text(encoding="utf-8"))
    assert set(user_value["hooks"]) == {
        "sessionStart",
        "userPromptSubmitted",
        "postToolUse",
        "preCompact",
        "agentStop",
    }
    assert "--output-profile vscode" not in json.dumps(user_value)


def test_uninstall_without_receipt_is_an_explainable_noop(
    isolated_homes: dict[str, Path],
) -> None:
    result = installers.uninstall_runtime(Runtime.COPILOT)
    assert result["operations"] == []
    assert result["warnings"] == ["No installation receipt found"]


def test_uninstall_dry_run_keeps_every_installed_file(
    isolated_homes: dict[str, Path],
) -> None:
    installers.install_runtime(Runtime.CODEX)
    skills, pyz, hook = installers._user_targets(Runtime.CODEX)
    receipt = installers.receipt_path(Runtime.CODEX, "user")
    result = installers.uninstall_runtime(Runtime.CODEX, dry_run=True)
    assert result["operations"]
    assert (skills / "outcome-brief" / "SKILL.md").exists()
    assert pyz.exists()
    assert hook.exists()
    assert receipt.exists()


def test_uninstall_tolerates_already_missing_receipt_owned_files(
    isolated_homes: dict[str, Path],
) -> None:
    installers.install_runtime(Runtime.COPILOT)
    _, pyz, hook = installers._user_targets(Runtime.COPILOT)
    pyz.unlink()
    hook.unlink()
    result = installers.uninstall_runtime(Runtime.COPILOT)
    assert not result["warnings"]
    assert not installers.receipt_path(Runtime.COPILOT, "user").exists()


def test_uninstall_preserves_malformed_merged_hook_with_warning(
    isolated_homes: dict[str, Path],
) -> None:
    installers.install_runtime(Runtime.CLAUDE)
    _, _, hook = installers._user_targets(Runtime.CLAUDE)
    hook.write_text("{broken", encoding="utf-8")
    result = installers.uninstall_runtime(Runtime.CLAUDE)
    assert hook.exists()
    assert any("Preserved unreadable merged file" in item for item in result["warnings"])


def test_uninstall_preserves_skills_shared_by_another_runtime_receipt(
    isolated_homes: dict[str, Path],
) -> None:
    installers.install_runtime(Runtime.CODEX)
    installers.install_runtime(Runtime.CLAUDE)
    shared_skill = (
        isolated_homes["codex"].parent / "codex" / "skills" / "outcome-brief" / "SKILL.md"
    )
    # User runtime homes differ in the test fixture, so model a second receipt
    # referencing the Codex-owned skill exactly as a real shared installation would.
    claude_receipt = installers.receipt_path(Runtime.CLAUDE, "user")
    receipt_value = json.loads(claude_receipt.read_text(encoding="utf-8"))
    receipt_value["files"].append(
        {
            "path": str(shared_skill),
            "sha256": installers._hash_file(shared_skill),
            "kind": "owned",
        }
    )
    claude_receipt.write_text(json.dumps(receipt_value), encoding="utf-8")

    result = installers.uninstall_runtime(Runtime.CODEX)
    assert shared_skill.exists()
    assert any("Preserved shared file" in item for item in result["warnings"])


def test_corrupt_unrelated_receipt_does_not_break_uninstall(
    isolated_homes: dict[str, Path],
) -> None:
    installers.install_runtime(Runtime.CODEX)
    receipts = isolated_homes["state"] / "receipts"
    (receipts / "unrelated.json").write_text("{bad", encoding="utf-8")
    result = installers.uninstall_runtime(Runtime.CODEX)
    assert not any("unrelated" in item for item in result["warnings"])
