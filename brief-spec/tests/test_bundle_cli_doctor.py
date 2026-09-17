from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from briefspec.bundle import build_zipapp
from briefspec.capabilities import runtime_capabilities
from briefspec.cli import main
from briefspec.diagnostics import doctor_runtime
from briefspec.hooks import read_hook_payload
from briefspec.installers import install_runtime
from briefspec.models import Runtime

ROOT = Path(__file__).resolve().parents[1]


def _module_env(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["BRIEFSPEC_HOME"] = str(home)
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT / "src") + (os.pathsep + current if current else "")
    return env


def test_zipapp_build_is_byte_for_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.pyz"
    second = tmp_path / "second.pyz"
    first_hash = build_zipapp(first)
    second_hash = build_zipapp(second)
    assert first_hash == second_hash
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert "__main__.py" in archive.namelist()
        assert "briefspec/cli.py" in archive.namelist()
        assert all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in archive.infolist())


def test_zipapp_executes_without_source_tree_on_pythonpath(tmp_path: Path) -> None:
    bundle = tmp_path / "briefspec.pyz"
    build_zipapp(bundle)
    result = subprocess.run(
        [sys.executable, str(bundle), "--version"],
        cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", "")},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("brief-spec ")


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param("not-json", id="malformed-json"),
        pytest.param("x" * (1024 * 1024 + 1), id="oversized"),
    ],
)
def test_cli_hook_malformed_or_oversized_input_fails_open(tmp_path: Path, payload: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "briefspec",
            "hook",
            "--provider",
            "codex",
            "--event",
            "SessionStart",
        ],
        input=payload,
        text=True,
        capture_output=True,
        env=_module_env(tmp_path / "state"),
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout) == {}
    assert "fail-open" in result.stderr


def test_read_hook_payload_rejects_non_object() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        read_hook_payload(io.StringIO("[]"))


def test_cli_session_start_returns_provider_specific_context(tmp_path: Path) -> None:
    payload = {
        "session_id": "cli-session",
        "timestamp": "2026-07-31T12:00:00Z",
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "briefspec",
            "hook",
            "--provider",
            "copilot",
            "--event",
            "sessionStart",
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=_module_env(tmp_path / "state"),
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Brief-Spec is active" in json.loads(result.stdout)["additionalContext"]


def test_cli_validate_auto_reports_machine_readable_result(
    outcome_text: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(outcome_text()))  # type: ignore[operator]
    assert main(["validate", "auto", "-", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is True
    assert output["kind"] == "outcome-brief"


def test_doctor_reports_missing_installation_as_fail(
    isolated_homes: dict[str, Path],
) -> None:
    result = doctor_runtime(Runtime.COPILOT)
    assert result["status"] == "FAIL"
    statuses = {check["name"]: check["status"] for check in result["checks"]}
    assert statuses["receipt"] == "FAIL"
    assert statuses["skills"] == "FAIL"
    assert statuses["runtime bundle"] == "FAIL"
    assert statuses["hook configuration"] == "FAIL"


def test_doctor_all_can_treat_an_unavailable_host_as_optional(
    isolated_homes: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("briefspec.harnesses.shutil.which", lambda _candidate: None)
    result = doctor_runtime(Runtime.COPILOT, optional_when_absent=True)
    assert result["status"] == "WARN"
    statuses = {check["name"]: check["status"] for check in result["checks"]}
    assert statuses["receipt"] == "WARN"
    assert statuses["host executable"] == "WARN"


def test_doctor_auto_scope_prefers_project_install_for_cwd(
    isolated_homes: dict[str, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    install_runtime(Runtime.CLAUDE, scope="project", project=project)
    monkeypatch.chdir(project)
    result = doctor_runtime(Runtime.CLAUDE)
    assert result["scope"] == "project"
    statuses = {check["name"]: check["status"] for check in result["checks"]}
    assert statuses["receipt"] == "PASS"
    assert statuses["skills"] == "PASS"


def test_doctor_auto_scope_falls_back_to_user_when_no_project_receipt(
    isolated_homes: dict[str, Path],
) -> None:
    install_runtime(Runtime.CLAUDE)
    result = doctor_runtime(Runtime.CLAUDE)
    assert result["scope"] == "user"
    statuses = {check["name"]: check["status"] for check in result["checks"]}
    assert statuses["receipt"] == "PASS"


def test_doctor_probe_executes_installed_bundle(
    isolated_homes: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_runtime(Runtime.COPILOT)
    monkeypatch.setattr(
        "briefspec.diagnostics.host_executable",
        lambda runtime: "/usr/local/bin/copilot",
    )
    result = doctor_runtime(Runtime.COPILOT, probe=True)
    checks = {check["name"]: check for check in result["checks"]}
    assert result["status"] == "PASS", checks
    assert checks["synthetic hook"]["status"] == "PASS"
    assert "additionalContext" in checks["synthetic hook"]["detail"]


def test_capabilities_are_explicit_and_fail_open() -> None:
    result = runtime_capabilities(Runtime.CODEX)
    assert result["final_output"] is True
    assert result["pre_compact"] is True
    assert result["compatibility"] == "best-effort-fail-open"
