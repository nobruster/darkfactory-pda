from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

from briefspec import __version__
from briefspec.models import CheckpointMode, OutcomeStatus

ROOT = Path(__file__).resolve().parents[1]


JSON_FILES = (
    ROOT / "plugin.json",
    ROOT / ".codex-plugin" / "plugin.json",
    ROOT / ".claude-plugin" / "plugin.json",
    ROOT / ".agents" / "plugins" / "marketplace.json",
    ROOT / ".claude-plugin" / "marketplace.json",
    ROOT / ".github" / "plugin" / "marketplace.json",
    ROOT / "hooks" / "hooks.json",
    ROOT / "hooks" / "copilot.json",
    *sorted((ROOT / "schemas").glob("*.json")),
)


@pytest.mark.parametrize("path", JSON_FILES, ids=lambda path: str(path.relative_to(ROOT)))
def test_manifest_and_schema_json_is_valid(path: Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)


def test_plugin_manifests_share_identity_and_version() -> None:
    manifests = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (
            ROOT / "plugin.json",
            ROOT / ".codex-plugin" / "plugin.json",
            ROOT / ".claude-plugin" / "plugin.json",
        )
    ]
    assert {item["name"] for item in manifests} == {"brief-spec"}
    assert {item["version"] for item in manifests} == {__version__}
    assert {item["license"] for item in manifests} == {"MIT"}
    assert all(item["skills"].rstrip("/").endswith("skills") for item in manifests[1:])


def test_root_plugin_component_paths_exist() -> None:
    manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert "skills" not in manifest and "hooks" not in manifest
    assert (ROOT / "skills").is_dir()
    assert (ROOT / "hooks" / "copilot.json").is_file()


def test_hook_manifests_cover_the_complete_lifecycle() -> None:
    nested = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    copilot = json.loads((ROOT / "hooks" / "copilot.json").read_text(encoding="utf-8"))
    assert set(nested["hooks"]) == {
        "SessionStart",
        "UserPromptSubmit",
        "PostToolUse",
        "PreCompact",
        "Stop",
    }
    assert copilot["version"] == 1
    assert set(copilot["hooks"]) == {
        "sessionStart",
        "userPromptSubmitted",
        "postToolUse",
        "preCompact",
        "agentStop",
    }
    assert "briefspec-hook" in json.dumps(nested)
    assert "briefspec-hook" in json.dumps(copilot)


def test_schema_enums_match_python_contract() -> None:
    outcome = json.loads(
        (ROOT / "schemas" / "outcome-brief.schema.json").read_text(encoding="utf-8")
    )
    checkpoint = json.loads(
        (ROOT / "schemas" / "session-checkpoint.schema.json").read_text(encoding="utf-8")
    )
    assert set(outcome["properties"]["status"]["enum"]) == {item.value for item in OutcomeStatus}
    assert set(checkpoint["properties"]["mode"]["enum"]) == {item.value for item in CheckpointMode}


def test_all_local_schema_references_resolve() -> None:
    for path in sorted((ROOT / "schemas").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        for reference in re.findall(r'"\\$ref"\\s*:\\s*"([^"]+)"', json.dumps(value)):
            if "://" not in reference and not reference.startswith("#"):
                assert (path.parent / reference).is_file(), f"{path}: {reference}"


def test_project_metadata_is_dependency_free_and_python_311_plus() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["requires-python"] == ">=3.11"
    assert metadata["project"]["dependencies"] == []
    assert metadata["project"]["scripts"]["brief-spec"] == "brief_spec.cli:main"
    assert metadata["project"]["scripts"]["briefspec"] == "briefspec.cli:main"


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, raw, _ = text.split("---", 2)
    result: dict[str, str] = {}
    for line in raw.strip().splitlines():
        key, separator, value = line.partition(":")
        if separator:
            result[key.strip()] = value.strip()
    return result


@pytest.mark.parametrize("name", ["brief-spec", "outcome-brief", "session-checkpoint"])
def test_skill_metadata_is_complete_and_installable(name: str) -> None:
    skill_dir = ROOT / "skills" / name
    skill = skill_dir / "SKILL.md"
    metadata = _frontmatter(skill)
    text = skill.read_text(encoding="utf-8")
    agent = (skill_dir / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert metadata["name"] == name
    assert len(metadata["description"]) >= 80
    assert "TODO" not in text
    assert "<!-- brief-spec:skill:v1 -->" in text or "<!-- briefspec:skill:v1 -->" in text
    assert agent.startswith(("# Managed by Brief-Spec.", "# Managed by BriefSpec."))
    assert "display_name:" in agent
    assert "short_description:" in agent
    assert "default_prompt:" in agent


@pytest.mark.parametrize("name", ["brief-spec", "outcome-brief", "session-checkpoint"])
def test_skill_relative_markdown_links_resolve(name: str) -> None:
    skill = ROOT / "skills" / name / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    references = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    assert references
    for reference in references:
        if "://" not in reference and not reference.startswith("#"):
            assert (skill.parent / reference).is_file(), reference


def test_skill_contracts_name_every_required_output_mode() -> None:
    outcome = (ROOT / "skills" / "outcome-brief" / "SKILL.md").read_text(encoding="utf-8")
    checkpoint = (ROOT / "skills" / "session-checkpoint" / "SKILL.md").read_text(encoding="utf-8")
    for status in OutcomeStatus:
        assert f"`{status.value}`" in outcome
    for mode in CheckpointMode:
        assert f"`{mode.value}`" in checkpoint
