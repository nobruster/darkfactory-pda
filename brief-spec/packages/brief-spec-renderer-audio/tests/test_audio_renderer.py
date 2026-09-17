from __future__ import annotations

import json
from pathlib import Path

import briefspec_renderer_audio as audio
import pytest


class _Response:
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return b"mock-mp3"


def test_openai_requires_explicit_consent_and_environment_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    renderer = audio.AudioRenderer()
    target = tmp_path / "speech.mp3"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="consent"):
        renderer._openai("bounded script", target, "marin", {})
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        renderer._openai("bounded script", target, "marin", {"consent_network": True})


def test_openai_request_uses_documented_defaults_without_persisting_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def urlopen(request: object, timeout: int) -> _Response:
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-never-persist")
    monkeypatch.setattr(audio.urllib.request, "urlopen", urlopen)
    target = tmp_path / "speech.mp3"
    model = audio.AudioRenderer()._openai(
        "bounded script",
        target,
        "marin",
        {"consent_network": True},
    )
    request = captured["request"]
    payload = json.loads(request.data)
    assert model == "gpt-4o-mini-tts"
    assert payload == {
        "model": "gpt-4o-mini-tts",
        "voice": "marin",
        "input": "bounded script",
        "response_format": "mp3",
    }
    assert request.get_header("Authorization") == "Bearer test-secret-never-persist"
    assert target.read_bytes() == b"mock-mp3"
    assert b"test-secret-never-persist" not in target.read_bytes()


def test_local_provider_never_falls_back_to_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(audio.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        audio.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network attempted")),
    )
    with pytest.raises(RuntimeError, match="no cloud fallback"):
        audio.AudioRenderer()._macos("script", tmp_path / "speech.aiff", "Samantha", 190)


def test_generic_script_helper_fails_closed_before_tool_use(tmp_path: Path) -> None:
    target = tmp_path / "chronicle.mp3"
    target.write_bytes(b"existing")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        audio.render_script_document(
            "Bounded script",
            target,
            created_at="2026-08-14T12:00:00+00:00",
        )
    with pytest.raises(ValueError, match="canonical created_at"):
        audio.render_script_document("Bounded script", tmp_path / "new.mp3", created_at="")
