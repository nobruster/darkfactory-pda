from __future__ import annotations

import importlib.util
from pathlib import Path

from briefspec.work_types import classify_task


def _module():
    path = Path(__file__).parents[1] / "scripts" / "run-live-e2e.py"
    spec = importlib.util.spec_from_file_location("brief_spec_live_e2e", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_authorized_implementation_accepts_one_semantic_line_with_or_without_final_newline(
    tmp_path: Path,
) -> None:
    authorized = _module()._authorized_workspace_changes
    feature = tmp_path / "feature.txt"
    for content in ("feature flag: enabled", "feature flag: enabled\n"):
        feature.write_text(content, encoding="utf-8")
        assert authorized(tmp_path, "implementation", " M feature.txt\n")


def test_authorized_implementation_rejects_wrong_path_or_value(tmp_path: Path) -> None:
    authorized = _module()._authorized_workspace_changes
    (tmp_path / "feature.txt").write_text("feature flag: disabled\n", encoding="utf-8")
    assert not authorized(tmp_path, "implementation", " M feature.txt\n")
    (tmp_path / "feature.txt").write_text("feature flag: enabled\n", encoding="utf-8")
    assert not authorized(tmp_path, "implementation", " M feature.txt\n M evidence.txt\n")


def test_authorized_read_only_scenario_requires_clean_worktree(tmp_path: Path) -> None:
    authorized = _module()._authorized_workspace_changes
    assert authorized(tmp_path, "review", "")
    assert not authorized(tmp_path, "review", " M evidence.txt\n")


def test_grok_live_prompt_uses_native_stop_metadata_without_shell_classification() -> None:
    module = _module()
    prompt = module._prompt("grok", "review", "teach")
    assert prompt.startswith("GROK NATIVE HOOK HANDSHAKE:")
    assert "Before any tool call or task answer" in prompt
    assert "sole permitted pre-boundary response" in prompt
    assert "native Brief-Spec hook owns classification" in prompt
    assert "Do not run the classifier" in prompt
    assert "Run the installed Brief-Spec skill's deterministic local classifier" not in prompt

    command = module._host_command("grok", "review", prompt, Path("unused.md"))
    system = command[command.index("--system-prompt-override") + 1]
    assert "native hook owns classification" in system
    assert "load at most the one matching profile" in system
    assert "do not search directories" in system
    assert "first text completion MUST be exactly BRIEF_SPEC_METADATA_PENDING" in system
    assert "After that correction, copy its marker exactly" in system
    assert "do not modify files" in system
    assert command[command.index("--tools") + 1] == "read_file"


def test_grok_implementation_system_policy_allows_only_fixture_change() -> None:
    module = _module()
    prompt = module._prompt("grok", "implementation", "spoken")
    command = module._host_command("grok", "implementation", prompt, Path("unused.md"))
    system = command[command.index("--system-prompt-override") + 1]
    assert "change only feature.txt" in system
    assert "Do not touch any other file" in system
    assert "use search_replace once" in system
    assert command[command.index("--tools") + 1] == "read_file,search_replace"
    assert command[command.index("--permission-mode") + 1] == "bypassPermissions"
    assert command[command.index("--max-turns") + 1] == "16"

    classification = classify_task(prompt, now=None)
    assert (classification.work_type, classification.subject) == ("implementation", "feature")


def test_live_fixture_contains_bounded_scenario_evidence(tmp_path: Path) -> None:
    module = _module()
    module._prepare_repository(tmp_path, "review")
    evidence = (tmp_path / "evidence.txt").read_text(encoding="utf-8")
    assert "Pull request #42 scope" in evidence
    assert "downstream integration behavior" in evidence
    assert (tmp_path / "feature.txt").read_text(encoding="utf-8") == ("feature flag: disabled\n")
