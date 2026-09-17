from __future__ import annotations

from pathlib import Path

import briefspec_renderer_pdf as pdf
import pytest


def test_pdf_timestamp_normalization_is_deterministic() -> None:
    first = b"/CreationDate (D:20260812192135+00'00') /ModDate (D:20260812192135+00'00')"
    second = b"/CreationDate (D:20260812192137+00'00') /ModDate (D:20260812192137+00'00')"
    expected = b"/CreationDate (D:20260811120000+00'00') /ModDate (D:20260811120000+00'00')"
    assert pdf._canonicalize_pdf_timestamps(first, "2026-08-11T12:00:00Z") == expected
    assert pdf._canonicalize_pdf_timestamps(second, "2026-08-11T12:00:00Z") == expected


def test_setup_dry_run_uses_current_python() -> None:
    result = pdf.PDFRenderer().setup(dry_run=True)
    assert result["status"] == "DRY-RUN"
    assert result["command"][1:] == ["-m", "playwright", "install", "chromium"]


def test_verify_reports_missing_tools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pdf.shutil, "which", lambda _name: None)
    result = pdf.PDFRenderer().verify(tmp_path / "missing.pdf")
    assert result["status"] == "FAIL"
    assert "missing PDF verifier" in result["detail"]


def test_invalid_page_format_fails_before_browser_launch(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="A4 or Letter"):
        pdf.PDFRenderer().render({}, tmp_path / "brief.pdf", {"page_format": "Legal"})


def test_missing_canonical_timestamp_fails_before_browser_launch(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source.created_at"):
        pdf.PDFRenderer().render({}, tmp_path / "brief.pdf", {})


def test_generic_html_helper_fails_closed_before_browser_launch(tmp_path: Path) -> None:
    target = tmp_path / "chronicle.pdf"
    target.write_bytes(b"existing")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        pdf.render_html_document(
            b"<!doctype html><title>Chronicle</title>",
            target,
            created_at="2026-08-14T12:00:00+00:00",
            title="Chronicle",
        )
    with pytest.raises(ValueError, match="canonical created_at"):
        pdf.render_html_document(
            b"<!doctype html><title>Chronicle</title>",
            tmp_path / "new.pdf",
            created_at="",
            title="Chronicle",
        )
