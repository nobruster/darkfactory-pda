#!/usr/bin/env python3
"""Build and validate the Converge complete system travel reference.

The prose and layout are hand-authored in ``brief-converge-trv.src.html``;
content is distilled from ``brf-converge.md`` in this directory. Unlike the
kurv pipeline there are no git-derived volatile inventories — truth
boundaries (release anchor, audited HEAD, working-tree delta) are fixed
constants of the brief and appear verbatim in the source.

Intermediates (rendered HTML, font CSS) land in ``ebooks/build/``.

Usage:
    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:/usr/local/lib:/usr/lib \
      /Users/luanmorenomaciel/Pythian/kurv-edp/.venv/bin/python \
      ebooks/build-brief-converge-trv.py
    ... same ... --check
"""
from __future__ import annotations

import argparse
import base64
from datetime import date
import hashlib
from pathlib import Path
import re
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
SRC = HERE / "brief-converge-trv.src.html"
OUT = HERE / "brief-converge-trv.pdf"
BUILD = HERE / "build"
FONTS_CSS = BUILD / "fonts_b64.css"
RENDERED_HTML = BUILD / "brief-converge-trv.rendered.html"

BRAND_KIT = Path(
    "/Users/luanmorenomaciel/Downloads/brand-kit/converge-brand-kit-v1/01-primary/color"
)
LOGO_LOCKUP_LIGHT = BRAND_KIT / "converge-lockup-color-light.svg"  # dark surfaces
LOGO_ICON_LIGHT = BRAND_KIT / "converge-icon-color-light.svg"  # dark surfaces

MIN_PAGES = 40
MAX_PAGES = 110

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150 Safari/537.36"
)
KEEP_SUBSETS = {"latin", "latin-ext"}
# Per converge brand-tokens.json typography: Inter (display/UI) + IBM Plex
# Mono (technical/data). Avenir Next / Menlo are system fallbacks in the CSS.
FAMILIES = {
    "Inter": "family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400",
    "IBM Plex Mono": "family=IBM+Plex+Mono:wght@400;500;600",
}

RELEASE_ANCHOR = "3de9f0b5f83f1bb62475308317c58e53f851b0db"
AUDITED_HEAD = "58b1ddb73e31a2b03426ab9ad25f02b9a166f559"
PDF_TITLE = "Converge — Complete System Travel Reference"
PDF_AUTHOR = "Converge · Settlement Fold"
PDF_KEYWORDS = (
    "Converge, Seamwise, Task-Spec, TaskPlan, settlement receipts, "
    "evidence ladder, factory coordinator, Settlement Fold, travel reference"
)
PDF_SUBJECT = (
    "Source-backed travel reference for Converge 0.2.0: authority separation, "
    "the nine-pass descent, the human barrier, bounded execution, settlement, "
    "and the exact release/main/working-tree truth boundaries."
)


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def fetch_fonts() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    faces: list[str] = []
    for family, query in FAMILIES.items():
        css = _fetch(
            f"https://fonts.googleapis.com/css2?{query}&display=swap"
        ).decode("utf-8")
        for block in re.split(r"(?=/\*\s*[a-z0-9-]+\s*\*/)", css):
            match = re.match(r"/\*\s*([a-z0-9-]+)\s*\*/", block.strip())
            if not match or match.group(1) not in KEEP_SUBSETS or "@font-face" not in block:
                continue
            face = block[block.index("@font-face") :]
            url_match = re.search(r"url\((https://[^)]+\.woff2)\)", face)
            if not url_match:
                continue
            payload = base64.b64encode(_fetch(url_match.group(1))).decode("ascii")
            faces.append(
                face.replace(url_match.group(1), f"data:font/woff2;base64,{payload}").strip()
            )
            print(f"embedded {family} {match.group(1)}", file=sys.stderr)
    if not faces:
        raise RuntimeError("font download produced no embeddable faces")
    FONTS_CSS.write_text("\n".join(faces) + "\n", encoding="utf-8")


def _svg_data_uri(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"brand asset missing: {path}")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{payload}"


def render_html() -> str:
    source = SRC.read_text(encoding="utf-8")
    replacements = {
        "<!-- GENERATED:FONT_LINK -->": '<link rel="stylesheet" href="build/fonts_b64.css">',
        "{{ICON_LOCKUP_LIGHT}}": _svg_data_uri(LOGO_LOCKUP_LIGHT),
        "{{ICON_MARK_LIGHT}}": _svg_data_uri(LOGO_ICON_LIGHT),
    }
    for token, value in replacements.items():
        if token not in source:
            raise ValueError(f"source token missing: {token}")
        source = source.replace(token, value)
    unresolved = re.findall(r"\{\{[A-Z0-9_]+\}\}|<!-- GENERATED:[A-Z_]+ -->", source)
    if unresolved:
        raise ValueError(f"unresolved source tokens: {unresolved}")
    return source


def _semantic_digest(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    normalized = "\n".join(
        " ".join((page.extract_text() or "").split()) for page in reader.pages
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def validate_pdf(path: Path) -> None:
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = len(reader.pages)
    if not MIN_PAGES <= pages <= MAX_PAGES:
        raise ValueError(f"page count {pages} outside target {MIN_PAGES}-{MAX_PAGES}")
    for page_no, page in enumerate(reader.pages, start=1):
        box = page.mediabox
        width = float(box.width)
        height = float(box.height)
        if abs(width - 595.276) > 1.0 or abs(height - 841.89) > 1.0:
            raise ValueError(f"page {page_no} is not A4: {width} x {height}")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    required = [
        "Converge",
        "Travel Reference",
        "Nine Passes",
        "Hashed Consent",
        "Bounded Motion",
        "Settlement",
        "Three Corridors",
        "Traveler's Field Guide",
        "Source Index and Claim Map",
        "dispatch_authorized",
        "LOCAL_SETTLED",
        "CHECK_RUNTIME_CONTRACT=PASS",
        RELEASE_ANCHOR,
        AUDITED_HEAD,
        "16 modified files",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise ValueError(f"PDF semantic QA missing: {missing}")
    metadata = reader.metadata or {}
    if metadata.get("/Title") != PDF_TITLE:
        raise ValueError("PDF title metadata is incorrect")
    if metadata.get("/Author") != PDF_AUTHOR:
        raise ValueError("PDF author metadata is incorrect")
    if not reader.outline:
        raise ValueError("PDF contains no bookmarks")


def render_pdf(rendered: str, destination: Path) -> None:
    from pypdf import PdfReader, PdfWriter
    from weasyprint import HTML

    BUILD.mkdir(parents=True, exist_ok=True)
    RENDERED_HTML.write_text(rendered, encoding="utf-8")
    raw_pdf = BUILD / "brief-converge-trv.weasyprint.pdf"
    HTML(string=rendered, base_url=str(HERE)).write_pdf(raw_pdf)

    reader = PdfReader(raw_pdf)
    writer = PdfWriter()
    writer.append(reader, import_outline=True)
    writer.add_metadata(
        {
            "/Title": PDF_TITLE,
            "/Author": PDF_AUTHOR,
            "/Subject": PDF_SUBJECT,
            "/Keywords": PDF_KEYWORDS,
            "/Creator": "Converge travel-reference builder (WeasyPrint)",
        }
    )
    with destination.open("wb") as stream:
        writer.write(stream)
    validate_pdf(destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh-fonts", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.refresh_fonts or not FONTS_CSS.exists():
        fetch_fonts()
    rendered = render_html()
    destination = BUILD / "brief-converge-trv.check.pdf" if args.check else OUT
    render_pdf(rendered, destination)
    if args.check:
        if not OUT.exists():
            raise FileNotFoundError(f"published PDF is missing: {OUT}")
        validate_pdf(OUT)
        if _semantic_digest(OUT) != _semantic_digest(destination):
            raise ValueError(
                "published PDF is stale: semantic digest differs from a fresh source build"
            )
    from pypdf import PdfReader

    print(
        " ".join(
            (
                "brief_converge_trv=PASS",
                f"date={date.today().isoformat()}",
                f"pages={len(PdfReader(destination).pages)}",
                f"pdf={destination}",
            )
        )
    )


if __name__ == "__main__":
    main()
