from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

import briefspec.config as config
import briefspec.resources as resources


def test_state_home_resolution_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BRIEFSPEC_HOME", str(tmp_path / "explicit"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg"))
    assert config.briefspec_home() == tmp_path / "explicit"

    monkeypatch.delenv("BRIEFSPEC_HOME")
    assert config.briefspec_home() == tmp_path / "xdg" / "brief-spec"

    monkeypatch.delenv("XDG_STATE_HOME")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    assert config.briefspec_home() == tmp_path / "home" / ".local" / "state" / "brief-spec"


def test_config_precedence_and_unknown_keys_are_ignored(
    isolated_homes: dict[str, Path], tmp_path: Path
) -> None:
    isolated_homes["state"].mkdir(parents=True)
    (isolated_homes["state"] / "config.toml").write_text(
        """\
[checkpoint]
turns = 5
unknown = "ignored"
[unknown]
command = "must never execute"
""",
        encoding="utf-8",
    )
    project = tmp_path / "project"
    project.mkdir()
    (project / ".briefspec.toml").write_text(
        """\
[checkpoint]
turns = 2
policy = "auto"
[outcome]
one_repair = false
""",
        encoding="utf-8",
    )
    effective = config.load_config(project)
    assert effective["checkpoint"]["turns"] == 2
    assert effective["checkpoint"]["policy"] == "auto"
    assert effective["outcome"]["one_repair"] is False
    assert "unknown" not in effective
    assert "unknown" not in effective["checkpoint"]


@pytest.mark.parametrize(
    "content",
    [
        "not valid = [",
        'checkpoint = "not-a-table"',
    ],
)
def test_malformed_or_wrong_shape_config_falls_back_safely(
    content: str,
    isolated_homes: dict[str, Path],
) -> None:
    isolated_homes["state"].mkdir(parents=True)
    (isolated_homes["state"] / "config.toml").write_text(content, encoding="utf-8")
    effective = config.load_config()
    assert effective["checkpoint"]["turns"] == config.DEFAULT_CONFIG["checkpoint"]["turns"]


def test_config_template_is_valid_and_complete_toml() -> None:
    value = tomllib.loads(config.config_template())
    assert set(value) == {"checkpoint", "outcome", "state", "typing"}
    assert value["typing"] == {
        "enabled": True,
        "activation": "substantive",
        "default_type": "general",
        "sticky": True,
    }
    assert value["checkpoint"]["default_mode"] == "orient"
    assert value["outcome"]["one_repair"] is True


def _fake_module_file(root: Path) -> Path:
    module = root / "src" / "briefspec" / "resources.py"
    module.parent.mkdir(parents=True)
    module.touch()
    return module


def test_resource_root_prefers_packaged_assets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _fake_module_file(tmp_path)
    packaged = module.parent / "resources"
    packaged.mkdir()
    monkeypatch.setattr(resources, "__file__", str(module))
    assert resources.resource_root() == packaged


def test_resource_root_falls_back_to_source_repository(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _fake_module_file(tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "pyproject.toml").touch()
    monkeypatch.setattr(resources, "__file__", str(module))
    assert resources.resource_root() == tmp_path
    assert resources.repository_root() == tmp_path


def test_resource_root_reports_missing_installable_assets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _fake_module_file(tmp_path)
    monkeypatch.setattr(resources, "__file__", str(module))
    with pytest.raises(FileNotFoundError, match="installable resources"):
        resources.resource_root()
    assert resources.repository_root() is None
