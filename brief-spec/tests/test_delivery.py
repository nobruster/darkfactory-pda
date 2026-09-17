from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from briefspec.bundle import build_delivery_bundle, deliver_bundle
from briefspec.cli import main
from briefspec.delivery import (
    canonical_json_bytes,
    export_core,
    load_delivery,
    render_html,
    render_markdown,
    render_spoken_text,
    validate_delivery,
)
from briefspec.models import VerificationLevel
from briefspec.verification import verify_target

ROOT = Path(__file__).resolve().parents[1]

OUTCOME = """Prelude that must not be exported.
<!-- briefspec:outcome:v1 -->
Status: DONE
Outcome: Canonical delivery is implemented.
Human action: None
Proof:
- [direct/pass kind=file] Contract test at `tests/test_delivery.py`
Gaps: None
Next: None
Open: None
<!-- /briefspec -->
Trailing host transcript that must not be exported.
"""

SPOKEN = """<!-- briefspec:checkpoint:v1 mode=spoken -->
Headline: Delivery recap
Script:
This is a sufficiently useful spoken delivery script. It explains that every Brief-Spec download
comes from one canonical object, that each artifact has an integrity hash, and that the reader can
independently verify the result. It also says that local audio stays offline unless the user
explicitly selects the OpenAI provider and consents to a network request. The next step is to
inspect the generated delivery bundle and compare its manifest against the files it contains.
Screen-only proof:
- [direct/pass kind=file] Contract test at `tests/test_delivery.py`
Next:
- Verify the generated MP3.
<!-- /briefspec -->
"""


def _delivery(text: str = OUTCOME) -> dict[str, object]:
    value, _ = load_delivery(
        text,
        source_path=ROOT / "tests" / "test_delivery.py",
        runtime="codex",
        session_ref="test-session",
        host_version="test-host",
        source_revision="deadbeef",
        created_at="2026-08-11T12:00:00Z",
    )
    return value


def test_markdown_json_and_html_share_one_canonical_delivery(tmp_path: Path) -> None:
    delivery = _delivery()
    validation = validate_delivery(delivery)
    assert validation.valid, validation.errors
    markdown = render_markdown(delivery)
    assert "Prelude" not in markdown and "Trailing" not in markdown
    assert "[direct/pass kind=file]" in markdown
    assert (
        markdown.index("Status: DONE")
        < markdown.index("Outcome: Canonical delivery is implemented.")
        < markdown.index("Human action: None")
        < markdown.index("Type: general + general")
        < markdown.index("### Answer")
        < markdown.index("Proof:")
    )

    records = export_core(delivery, ["markdown", "json", "html"], tmp_path)
    assert {record["format"] for record in records} == {"markdown", "json", "html"}
    assert (tmp_path / "brief.json").read_bytes() == canonical_json_bytes(delivery)
    rendered_html = render_html(delivery)
    assert "Content-Security-Policy" in rendered_html
    assert "data-briefspec-sha256" in rendered_html
    assert "<script" not in rendered_html
    assert "<title>Canonical delivery is implemented.</title>" in rendered_html
    assert (
        rendered_html.index('id="field-status"')
        < rendered_html.index('id="field-outcome"')
        < rendered_html.index('id="field-human_action"')
        < rendered_html.index('id="classification"')
        < rendered_html.index('class="typed"')
        < rendered_html.index('id="field-proof"')
    )

    result = verify_target(
        tmp_path / "brief.html",
        level=VerificationLevel.RENDERED,
        workspace=ROOT,
    )
    assert result["status"] == "PASS", result


def test_bundle_is_deterministic_and_manifest_is_verified(tmp_path: Path) -> None:
    delivery = _delivery()
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    first_result = build_delivery_bundle(delivery, first)
    second_result = build_delivery_bundle(delivery, second)
    assert first.read_bytes() == second.read_bytes()
    assert first_result["sha256"] == second_result["sha256"]
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == ["brief.html", "brief.json", "brief.md", "manifest.json"]
        assert all(item.date_time == (2026, 8, 11, 12, 0, 0) for item in archive.infolist())
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["canonical_sha256"]
    verified = verify_target(first, level=VerificationLevel.RENDERED)
    assert verified["status"] == "PASS", verified


def test_delivery_receipt_attests_to_copied_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "brief.zip"
    build_delivery_bundle(_delivery(), bundle)
    destination = tmp_path / "delivered"
    result = deliver_bundle(bundle, destination)
    receipt = Path(result["receipt"])
    assert receipt.is_file()
    verified = verify_target(receipt, level=VerificationLevel.DELIVERED)
    assert verified["status"] == "PASS", verified


def test_resolved_verification_rejects_workspace_escape(tmp_path: Path) -> None:
    delivery = _delivery()
    delivery["brief"]["proof"][0]["locator"] = str(ROOT / "tests" / "test_delivery.py")
    delivery_path = tmp_path / "brief.json"
    delivery_path.write_bytes(canonical_json_bytes(delivery))
    result = verify_target(
        delivery_path,
        level=VerificationLevel.RESOLVED,
        workspace=tmp_path,
    )
    assert result["status"] == "FAIL"
    assert any("escapes workspace" in check["detail"] for check in result["checks"])


def test_spoken_outputs_are_mode_bounded() -> None:
    spoken = _delivery(SPOKEN)
    assert "canonical object" in render_spoken_text(spoken)
    with pytest.raises(ValueError, match="Spoken Checkpoint"):
        render_spoken_text(_delivery())


def test_cli_export_bundle_verify_and_deliver(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "outcome.md"
    source.write_text(OUTCOME, encoding="utf-8")
    output_dir = tmp_path / "exports"
    assert (
        main(
            [
                "export",
                str(source),
                "--formats",
                "markdown,json,html",
                "--output-dir",
                str(output_dir),
                "--created-at",
                "2026-08-11T12:00:00Z",
                "--json",
            ]
        )
        == 0
    )
    assert len(json.loads(capsys.readouterr().out)["outputs"]) == 3
    bundle = tmp_path / "delivery.zip"
    assert main(["bundle", str(source), "--output", str(bundle), "--json"]) == 0
    capsys.readouterr()
    assert main(["verify", str(bundle), "--level", "rendered", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"
    delivered = tmp_path / "destination"
    assert main(["deliver", str(bundle), "--to", str(delivered), "--json"]) == 0
    receipt = Path(json.loads(capsys.readouterr().out)["receipt"])
    assert main(["verify", str(receipt), "--level", "delivered"]) == 0


def test_validate_accepts_new_path_first_form(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "outcome.md"
    source.write_text(OUTCOME, encoding="utf-8")
    assert main(["validate", str(source), "--strict"]) == 0
    assert "VALID" in capsys.readouterr().out
