from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from briefspec import bundle as bundle_module
from briefspec import renderers, state
from briefspec import verification as verification_module
from briefspec.bundle import build_delivery_bundle, deliver_bundle, export_delivery_formats
from briefspec.delivery import (
    canonical_json_bytes,
    export_core,
    load_delivery,
    parse_evidence,
    render_markdown,
    render_ssml,
    sha256_bytes,
    validate_delivery,
)
from briefspec.models import VerificationLevel
from briefspec.verification import verify_target

OUTCOME = """<!-- briefspec:outcome:v1 -->
Status: DONE
Outcome: Edge behavior is covered.
Human action: None
Proof:
- [direct/pass kind=file] Fixture at `evidence.txt`
Gaps: None
Next: None
Open: None
<!-- /briefspec -->
"""

SPOKEN = """<!-- briefspec:checkpoint:v1 mode=spoken -->
Headline: Edge recap
Script:
The canonical delivery object is rendered into every format, with stable metadata and integrity
hashes that make later verification possible. The spoken form contains only the script and keeps
screen evidence separate. This fixture includes enough words to satisfy strict quality checks while
remaining concise. It explains the completed work, the evidence boundary, the safe local provider,
and the next verification action. It never exposes authentication data or executes evidence. The
recipient can compare the bundle manifest, inspect the adjacent receipt, and confirm that every
download communicates the same bounded result.
Screen-only proof:
- [direct/pass kind=file] Fixture at `evidence.txt`
Next:
- Verify the result.
<!-- /briefspec -->
"""


def _delivery(text: str = OUTCOME) -> dict[str, object]:
    value, warnings = load_delivery(
        text,
        runtime="test",
        created_at="2026-08-11T12:00:00Z",
    )
    assert warnings == ["Legacy untyped brief loaded as general + general"]
    return value


@pytest.mark.parametrize(
    ("text", "kind", "locator"),
    [
        ("[direct/pass] [source](https://example.test/a)", "url", "https://example.test/a"),
        ("[derived/info] see https://example.test/b.", "url", "https://example.test/b"),
        ("[reported/info] PR #42", "pr", "PR #42"),
        ("[direct/pass] commit deadbeef", "commit", "deadbeef"),
        ("[reported/info] observation `ready`", "observation", "ready"),
        ("[direct/pass] `wc -l evidence.txt`", "observation", "wc -l evidence.txt"),
        ("legacy evidence", "observation", "legacy evidence"),
    ],
)
def test_evidence_inference(text: str, kind: str, locator: str) -> None:
    parsed = parse_evidence(text)
    assert parsed["kind"] == kind
    assert parsed["locator"] == locator


def test_legacy_command_like_backticks_are_warned_and_never_promoted_to_files(
    outcome_text: Any,
) -> None:
    delivery, warnings = load_delivery(
        outcome_text(
            proof=(
                "[direct/pass] `tests/test_delivery_edge_cases.py`",
                "[reported/info] `wc -l tests/test_delivery_edge_cases.py`",
            )
        ),
        created_at="2026-08-13T12:00:00Z",
    )
    assert delivery["brief"]["proof"][1]["kind"] == "observation"
    assert any("no command was executed" in warning for warning in warnings)


def test_loads_bare_brief_json_and_rejects_unrelated_json() -> None:
    delivery = _delivery()
    bare = json.dumps(delivery["brief"])
    rebuilt, _ = load_delivery(bare, runtime="test", created_at="2026-08-11T12:00:00Z")
    assert rebuilt["brief"] == delivery["brief"]
    with pytest.raises(ValueError, match="not a Brief-Spec"):
        load_delivery('{"kind":"other"}')


def test_validation_reports_malformed_envelope() -> None:
    delivery = _delivery()
    delivery["schema_version"] = "9"
    delivery["source"] = {"runtime": "", "briefspec_version": "", "created_at": "bad"}
    delivery["brief"]["proof"] = [
        {"kind": "shell", "basis": "guess", "result": "maybe", "label": "", "locator": ""}
    ]
    delivery["provenance"] = [
        {"provider": "", "locator": "", "access": "secret", "content_sha256": "short"}
    ]
    delivery["artifacts"] = [
        {
            "artifact_id": "",
            "role": "",
            "locator": "",
            "media_type": "",
            "access": "x",
            "size_bytes": -1,
            "expires_at": "bad",
        }
    ]
    delivery["work_items"] = [{"work_id": "", "activity": "UNKNOWN"}]
    result = validate_delivery(delivery)
    assert not result.valid
    assert len(result.errors) >= 15


def test_render_and_export_fail_closed(tmp_path: Path) -> None:
    delivery = _delivery(SPOKEN)
    assert render_ssml(delivery).startswith("<speak><p>")
    assert "Screen-only proof" in render_markdown(delivery)
    export_core(delivery, ["json"], tmp_path)
    with pytest.raises(FileExistsError, match="Refusing"):
        export_core(delivery, ["json"], tmp_path)
    with pytest.raises(ValueError, match="Unsupported"):
        export_core(delivery, ["pdf"], tmp_path)
    with pytest.raises(ValueError, match="Duplicate"):
        export_core(delivery, ["html", "html"], tmp_path, force=True)


def test_public_export_preserves_directory_permissions(tmp_path: Path) -> None:
    tmp_path.chmod(0o755)
    export_core(_delivery(), ["json"], tmp_path)
    if os.name != "nt":
        assert tmp_path.stat().st_mode & 0o777 == 0o755
    assert (tmp_path / "brief.json").is_file()


def test_atomic_output_transaction_rolls_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("original", encoding="utf-8")
    original = state.atomic_write_public
    calls = 0

    def fail_second(path: Path, content: bytes, mode: int = 0o644) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated partial write")
        original(path, content, mode)

    monkeypatch.setattr(state, "atomic_write_public", fail_second)
    with pytest.raises(OSError, match="simulated"):
        state.atomic_write_many([(first, b"changed", 0o644), (second, b"new", 0o644)])
    assert first.read_text(encoding="utf-8") == "original"
    assert not second.exists()


def test_plugin_failure_leaves_no_partial_core_exports(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        bundle_module,
        "render_with_plugin",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("renderer failed")),
    )
    with pytest.raises(RuntimeError, match="renderer failed"):
        export_delivery_formats(_delivery(), ["json", "fake"], tmp_path)
    assert not list(tmp_path.iterdir())


def test_resolvers_cover_files_hashes_expiry_and_offline_urls(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("proof\n", encoding="utf-8")
    delivery = _delivery()
    delivery["brief"]["proof"] = [
        {
            "kind": "file",
            "label": "fixture at `evidence.txt`",
            "locator": "evidence.txt:1",
            "basis": "direct",
            "result": "pass",
        },
        {
            "kind": "url",
            "label": "private URL https://example.invalid/private",
            "locator": "https://example.invalid/private",
            "basis": "reported",
            "result": "info",
        },
        {
            "kind": "command",
            "label": "must not execute `echo unsafe`",
            "locator": "echo unsafe",
            "basis": "reported",
            "result": "info",
        },
        {
            "kind": "observation",
            "label": "unresolved `reported.txt`",
            "locator": "reported only",
            "basis": "reported",
            "result": "info",
        },
    ]
    delivery["artifacts"] = [
        {
            "artifact_id": "expired",
            "role": "proof",
            "locator": "evidence.txt",
            "media_type": "text/plain",
            "access": "local",
            "expires_at": "2000-01-01T00:00:00Z",
        },
    ]
    source = tmp_path / "brief.json"
    source.write_bytes(canonical_json_bytes(delivery))
    result = verify_target(
        source,
        level=VerificationLevel.RESOLVED,
        workspace=tmp_path,
        offline=True,
    )
    details = "\n".join(check["detail"] for check in result["checks"])
    assert "file resolved" in details
    assert "network consent not granted; URL declared but unresolved" in details
    assert "never executed" in details
    assert "unresolved observation" in details
    assert "expired artifact" in details
    assert result["status"] == "FAIL"


def test_resolver_rejects_symlink_escape(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (workspace / "escape.txt").symlink_to(outside)
    delivery = _delivery()
    delivery["brief"]["proof"] = [
        {
            "kind": "file",
            "label": "symlink at `escape.txt`",
            "locator": "escape.txt",
            "basis": "direct",
            "result": "pass",
        }
    ]
    source = workspace / "brief.json"
    source.write_bytes(canonical_json_bytes(delivery))

    result = verify_target(source, level=VerificationLevel.RESOLVED, workspace=workspace)

    assert result["status"] == "FAIL"
    assert "path escapes workspace" in result["checks"][-1]["detail"]


def test_resolver_handles_private_and_timed_out_provenance_urls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("proof\n", encoding="utf-8")
    delivery = _delivery()
    delivery["provenance"] = [
        {
            "provider": "exa",
            "locator": "https://private.example.test/result",
            "retrieved_at": "2026-08-11T12:00:00Z",
            "access": "private",
            "basis": "direct",
        },
        {
            "provider": "tavily",
            "locator": "https://public.example.test/result",
            "retrieved_at": "2026-08-11T12:00:00Z",
            "access": "public",
            "basis": "direct",
        },
    ]

    def time_out(*_args: object, **_kwargs: object) -> object:
        raise TimeoutError("bounded timeout")

    monkeypatch.setattr(verification_module, "_network_request", time_out)
    source = tmp_path / "brief.json"
    source.write_bytes(canonical_json_bytes(delivery))

    result = verify_target(
        source,
        level=VerificationLevel.RESOLVED,
        workspace=tmp_path,
        consent_network=True,
    )
    details = "\n".join(check["detail"] for check in result["checks"])

    assert "private URL requires authorized access" in details
    assert "URL unresolved: bounded timeout" in details
    assert result["status"] == "FAIL"


def test_commit_and_hash_resolvers(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("proof\n", encoding="utf-8")
    subprocess.run(["git", "add", "evidence.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True, capture_output=True, check=True
    ).stdout.strip()
    delivery = _delivery()
    delivery["brief"]["proof"] = [
        {
            "kind": "commit",
            "label": revision,
            "locator": revision,
            "basis": "direct",
            "result": "pass",
        }
    ]
    delivery["artifacts"] = [
        {
            "artifact_id": "file",
            "role": "proof",
            "locator": "evidence.txt",
            "media_type": "text/plain",
            "access": "local",
            "sha256": "0" * 64,
        }
    ]
    source = tmp_path / "brief.json"
    source.write_bytes(canonical_json_bytes(delivery))
    result = verify_target(source, level=VerificationLevel.RESOLVED, workspace=tmp_path)
    details = "\n".join(check["detail"] for check in result["checks"])
    assert "commit resolved" in details
    assert "hash mismatch" in details


def test_html_bundle_and_receipt_tampering_is_detected(tmp_path: Path) -> None:
    delivery = _delivery()
    export_core(delivery, ["html"], tmp_path)
    html_path = tmp_path / "brief.html"
    html_path.write_text(
        html_path.read_text(encoding="utf-8").replace("default-src 'none'", "default-src https:"),
        encoding="utf-8",
    )
    assert verify_target(html_path, level=VerificationLevel.RENDERED)["status"] == "FAIL"
    html_path.write_text("<html><main><h1>missing integrity</h1></main></html>", encoding="utf-8")
    assert verify_target(html_path, level=VerificationLevel.RENDERED)["status"] == "FAIL"

    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as archive:
        archive.writestr("brief.json", "{}")
    assert verify_target(bad_zip, level=VerificationLevel.RENDERED)["status"] == "FAIL"
    with pytest.raises(ValueError, match="Refusing to deliver an invalid bundle"):
        deliver_bundle(bad_zip, tmp_path / "bad-destination")

    bundle = tmp_path / "delivery.zip"
    build_delivery_bundle(delivery, bundle)
    delivered = deliver_bundle(bundle, tmp_path / "destination")
    Path(delivered["bundle"]).write_bytes(b"tampered")
    assert (
        verify_target(Path(delivered["receipt"]), level=VerificationLevel.DELIVERED)["status"]
        == "FAIL"
    )


def test_bundle_rejects_hash_consistent_noncanonical_rendering(tmp_path: Path) -> None:
    bundle = tmp_path / "delivery.zip"
    build_delivery_bundle(_delivery(), bundle)
    with zipfile.ZipFile(bundle) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    contents["brief.md"] = contents["brief.md"].replace(b"Edge behavior", b"Altered output")
    manifest = json.loads(contents["manifest.json"])
    markdown = next(item for item in manifest["files"] if item["path"] == "brief.md")
    markdown["size_bytes"] = len(contents["brief.md"])
    markdown["sha256"] = sha256_bytes(contents["brief.md"])
    contents["manifest.json"] = json.dumps(manifest).encode("utf-8") + b"\n"
    with zipfile.ZipFile(bundle, "w") as archive:
        for name, content in contents.items():
            archive.writestr(name, content)
    result = verify_target(bundle, level=VerificationLevel.RENDERED)
    assert result["status"] == "FAIL"
    assert "not the deterministic rendering" in result["checks"][0]["detail"]


def test_missing_target_and_missing_delivery_receipt_fail(tmp_path: Path) -> None:
    missing = verify_target(tmp_path / "missing.json")
    assert missing["status"] == "FAIL"
    source = tmp_path / "brief.json"
    source.write_bytes(canonical_json_bytes(_delivery()))
    result = verify_target(source, level=VerificationLevel.DELIVERED, workspace=tmp_path)
    assert result["status"] == "FAIL"
    assert "receipt not found" in result["checks"][-1]["detail"]


class _FakeRenderer:
    name = "fake"
    filename = "brief.fake"
    media_type = "application/x-fake"

    def capabilities(self) -> dict[str, object]:
        return {"ready": True}

    def render(
        self, delivery: dict[str, object], output: Path, options: dict[str, object]
    ) -> dict[str, object]:
        output.write_text(str(options.get("text", "fake")), encoding="utf-8")
        return {
            "format": "fake",
            "path": str(output),
            "media_type": self.media_type,
            "renderer_version": "1",
        }

    def verify(self, artifact: Path) -> dict[str, str]:
        return {"status": "PASS", "detail": artifact.name}

    def setup(self, *, dry_run: bool) -> dict[str, object]:
        return {"status": "PASS", "dry_run": dry_run}


def test_renderer_discovery_render_and_setup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    entry_point = SimpleNamespace(load=lambda: _FakeRenderer)
    entry_points = SimpleNamespace(select=lambda **_kwargs: [entry_point])
    monkeypatch.setattr(renderers.metadata, "entry_points", lambda: entry_points)
    assert renderers.renderer_capabilities() == [{"name": "fake", "ready": True}]
    record = renderers.render_with_plugin(
        "fake", _delivery(), tmp_path, options={"text": "rendered"}
    )
    assert Path(record["path"]).read_text(encoding="utf-8") == "rendered"
    assert renderers.setup_renderers(dry_run=True)[0]["dry_run"] is True
    with pytest.raises(FileExistsError):
        renderers.render_with_plugin("fake", _delivery(), tmp_path)


def test_missing_renderer_is_actionable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(renderers, "available_renderers", lambda: {})
    with pytest.raises(ValueError, match="not installed"):
        renderers.render_with_plugin("missing", _delivery(), tmp_path)
