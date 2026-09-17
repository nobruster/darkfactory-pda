from __future__ import annotations

import json
import runpy
import tomllib
from pathlib import Path

import brief_spec_renderer_video as video
import pytest
from brief_spec_chronicle.cli import main
from brief_spec_chronicle.sources import normalize_source_event
from jsonschema.validators import validator_for

ROOT = Path(__file__).resolve().parents[1]


def test_chronicle_cli_end_to_end(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("BRIEF_SPEC_HOME", str(tmp_path / "state"))
    project = tmp_path / "project"
    project.mkdir()
    assert main(["init", "--project", str(project), "--name", "CLI Pilot", "--json"]) == 0
    registration = json.loads(capsys.readouterr().out)
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "kind": "INTENT_DECLARED",
                "headline": "Prove the Chronicle CLI",
                "occurred_at": "2026-08-14T12:00:00+00:00",
                "method_context": {
                    "method": "task-spec",
                    "phase": "declared",
                    "intent_ref": "intent-cli",
                },
                "entity_refs": ["intent-cli"],
                "evidence_ids": ["evidence:cli-test"],
                "details": {"next": ["Generate the review pack"]},
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "ingest",
                str(event),
                "--project",
                str(project),
                "--source",
                "test",
                "--observed-at",
                "2026-08-14T12:00:00+00:00",
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "INGESTED"
    snapshot = tmp_path / "chronicle.json"
    assert (
        main(
            [
                "snapshot",
                "--project",
                str(project),
                "--created-at",
                "2026-08-14T12:01:00+00:00",
                "--output",
                str(snapshot),
                "--json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    output = tmp_path / "output"
    assert (
        main(
            [
                "export",
                str(snapshot),
                "--formats",
                "markdown,json,html,zip",
                "--output-dir",
                str(output),
                "--json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["verify", str(output), "--level", "rendered", "--json"]) == 0
    verification = json.loads(capsys.readouterr().out)
    assert verification["status"] == "WARN"
    assert verification["warnings"]
    assert (
        main(
            [
                "delete",
                "--project-id",
                registration["project_id"],
                "--confirm",
                registration["project_id"],
                "--json",
            ]
        )
        == 0
    )


def test_chronicle_package_metadata_and_schemas_are_valid() -> None:
    projects = {
        "packages/brief-spec-chronicle/pyproject.toml": "brief-spec-chronicle",
        "packages/brief-spec-renderer-video/pyproject.toml": "brief-spec-renderer-video",
    }
    for relative, expected in projects.items():
        value = tomllib.loads((ROOT / relative).read_text(encoding="utf-8"))
        assert value["project"]["name"] == expected
        assert value["project"]["requires-python"] == ">=3.11"
    schema_dir = ROOT / "packages" / "brief-spec-chronicle" / "schemas"
    for path in schema_dir.glob("*.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        validator_for(schema).check_schema(schema)


@pytest.mark.parametrize(
    ("source", "value", "expected_kind", "expected_method"),
    [
        (
            "seamwise",
            {"schema": "seamwise/1.0", "intent_id": "intent-1", "intent": "Ship safely"},
            "INTENT_DECLARED",
            "seamwise",
        ),
        (
            "task-spec",
            {"kind": "task-handoff", "task_id": "task-1", "goal": "Implement safely"},
            "TASK_CREATED",
            "task-spec",
        ),
        (
            "converge",
            {
                "event_kind": "TASK_STARTED",
                "task_ref": "task-1",
                "headline": "Authorized execution began",
                "authorization_ref": "auth-1",
            },
            "TASK_STARTED",
            "converge",
        ),
        (
            "firecrawl",
            {"url": "https://example.com/evidence", "title": "Provider evidence"},
            "EVIDENCE_ADDED",
            "general",
        ),
    ],
)
def test_source_normalization_is_bounded_and_provider_neutral(
    source: str,
    value: dict[str, object],
    expected_kind: str,
    expected_method: str,
) -> None:
    event = normalize_source_event(value, source_system=source)
    assert event["kind"] == expected_kind
    assert event["method_context"]["method"] == expected_method
    assert "transcript" not in json.dumps(event).lower()


def test_delivery_source_normalization_retains_only_bounded_references() -> None:
    value = {
        "schema_version": "2.0",
        "kind": "brief-spec-delivery",
        "source": {
            "harness": "codex",
            "session_ref": "opaque-session",
            "created_at": "2026-08-14T12:00:00+00:00",
        },
        "classification": {
            "work_type": "implementation",
            "subject": "feature",
            "confidence": "high",
            "origin": "inferred",
        },
        "brief": {
            "status": "DONE",
            "outcome": "Chronicle source normalization shipped",
            "proof": [
                {
                    "kind": "file",
                    "locator": "tests/test_chronicle_cli_and_video.py",
                    "sha256": "a" * 64,
                }
            ],
            "next": [],
            "gaps": [],
        },
        "provenance": [],
        "artifacts": [],
        "work_items": [{"work_id": "task-normalizer"}],
        "raw_transcript": "must not be retained",
    }
    event = normalize_source_event(value, source_system="brief-spec")
    assert event["kind"] == "TASK_COMPLETED"
    assert event["evidence_ids"] == [
        "file:tests/test_chronicle_cli_and_video.py#sha256=" + "a" * 64
    ]
    assert "raw_transcript" not in json.dumps(event)


def test_disposable_seamwise_task_spec_converge_journey() -> None:
    module = runpy.run_path(str(ROOT / "scripts" / "run-chronicle-e2e.py"))
    result = module["run"]()
    assert result["status"] == "PASS"
    assert result["events"] == 6
    assert result["restored"] == "RESTORED"


def test_video_storyboard_escapes_content_and_verifies_sidecars(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    snapshot = {
        "project": {"name": "Unsafe <project>"},
        "current_state": {"method": "general", "phase": None, "headline": "Current & safe"},
        "intent_anchors": [{"headline": "Render <script> safely"}],
        "milestones": [],
        "drift": [],
        "decisions": [],
        "next_actions": ["Inspect the output"],
    }
    scenes = video._scenes(snapshot)
    rendered = video._scene_html(scenes[0], snapshot["project"]["name"], 0, len(scenes))
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "Unsafe &lt;project&gt;" in rendered
    assert video._vtt(scenes, 12).startswith("WEBVTT\n")

    target = tmp_path / "chronicle.mp4"
    target.write_bytes(b"video")
    target.with_suffix(".storyboard.json").write_text("{}", encoding="utf-8")
    target.with_suffix(".vtt").write_text("WEBVTT", encoding="utf-8")
    target.with_suffix(".txt").write_text("Transcript", encoding="utf-8")
    monkeypatch.setattr(
        video,
        "_probe",
        lambda _path: {
            "format": {"duration": "12.0"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1600,
                    "height": 900,
                },
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        },
    )
    assert video.verify_video(target)["status"] == "PASS"
