#!/usr/bin/env python3
"""Verify the self-contained HTML delivery in a real Chromium browser."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from briefspec.delivery import export_core, load_delivery

OUTCOME = (
    "<!-- brief-spec:typed:v1 type=general subject=general confidence=high "
    "origin=explicit classified_at=2026-08-11T12:00:00Z profile=1.0 -->\n"
    """
### Answer

The offline browser delivery is independently readable and verifiable.

### Rationale

Its canonical hash, evidence classifications, and browser structure remain visible.

### Next action

Retain this result with the release evidence.

<!-- briefspec:outcome:v1 -->
Status: DONE
Outcome: Browser delivery is independently readable and verifiable.
Human action: None
Proof:
- [direct/pass kind=url] Official source at https://example.test/evidence
Gaps: None
Next: None
Open: None
<!-- /briefspec -->
<!-- /brief-spec -->
"""
)


def _delivery() -> dict[str, Any]:
    delivery, warnings = load_delivery(
        OUTCOME,
        runtime="browser-e2e",
        host_version="Playwright Chromium",
        source_revision="browser-fixture",
        created_at="2026-08-11T12:00:00Z",
    )
    if warnings:
        raise RuntimeError("strict browser fixture is invalid: " + "; ".join(warnings))
    delivery["provenance"] = [
        {
            "provider": "tavily",
            "locator": "https://example.test/evidence",
            "retrieved_at": "2026-08-11T11:59:00Z",
            "basis": "direct",
            "access": "public",
        }
    ]
    delivery["artifacts"] = [
        {
            "artifact_id": "private-proof",
            "role": "supporting evidence",
            "locator": "private/evidence.txt",
            "media_type": "text/plain",
            "access": "private",
            "observed_at": "2026-08-11T11:59:00Z",
            "expires_at": "2030-08-11T11:59:00Z",
        }
    ]
    delivery["work_items"] = [
        {
            "work_id": "browser-check",
            "activity": "COMPLETED",
            "headline": "Verify browser delivery",
            "last_updated": "2026-08-11T12:00:00Z",
            "result_ref": "brief.html",
        }
    ]
    return delivery


def main() -> int:
    from playwright.sync_api import sync_playwright

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="briefspec-browser-") as temporary:
        root = Path(temporary)
        export_core(_delivery(), ["html"], root)
        html_path = root / "brief.html"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for name, width, height in (
                ("desktop", 1440, 1000),
                ("mobile", 390, 844),
            ):
                page = browser.new_page(viewport={"width": width, "height": height})
                external_requests: list[str] = []
                page.on(
                    "request",
                    lambda request, requests=external_requests: (
                        requests.append(request.url)
                        if request.url.startswith(("http://", "https://"))
                        else None
                    ),
                )
                page.goto(html_path.as_uri(), wait_until="load")
                checks = page.evaluate(
                    """() => ({
                      title: document.title,
                      main: document.querySelectorAll('main').length,
                      h1: document.querySelectorAll('h1').length,
                      regions: document.querySelectorAll('section[aria-labelledby]').length,
                      expandable: document.querySelectorAll('details > summary').length,
                      privateVisible: document.body.innerText.includes('private'),
                      expiryVisible: document.body.innerText.includes('2030-08-11T11:59:00Z'),
                      links: document.querySelectorAll('a[href^="https://"]').length,
                      horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth,
                      decisionSignalsInViewport: [...document.querySelectorAll('.decision-signal')]
                        .every((node) => node.getBoundingClientRect().bottom <= window.innerHeight),
                    })"""
                )
                if checks != {
                    "title": "Browser delivery is independently readable and verifiable.",
                    "main": 1,
                    "h1": 1,
                    "regions": 14,
                    "expandable": 3,
                    "privateVisible": True,
                    "expiryVisible": True,
                    "links": 2,
                    "horizontalOverflow": False,
                    "decisionSignalsInViewport": True,
                }:
                    raise RuntimeError(f"{name} semantic/layout regression: {checks}")
                page.keyboard.press("Tab")
                focused = page.evaluate("document.activeElement?.tagName")
                if focused not in {"SUMMARY", "A"}:
                    raise RuntimeError(f"{name} keyboard focus did not reach an interactive item")
                first = page.screenshot(full_page=True)
                second = page.screenshot(full_page=True)
                if first != second:
                    raise RuntimeError(f"{name} screenshot changed without a DOM change")
                page.emulate_media(media="print")
                pdf = page.pdf(format="A4", print_background=True)
                if not pdf.startswith(b"%PDF"):
                    raise RuntimeError(f"{name} print rendering did not produce a PDF")
                if external_requests:
                    raise RuntimeError(f"{name} made external requests: {external_requests}")
                results.append(
                    {
                        "viewport": name,
                        "screenshot_sha256": hashlib.sha256(first).hexdigest(),
                        "print_pdf_size": len(pdf),
                        "keyboard_focus": focused,
                        "external_requests": external_requests,
                    }
                )
                page.close()
            browser.close()
    print(json.dumps({"status": "PASS", "results": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
