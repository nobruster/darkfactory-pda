"""Stable catalog IDs. Same shape as OntoLayer's warehouse document ids."""

from __future__ import annotations


def _sanitize(part: str) -> str:
    return part.replace(" ", "_").replace(".", "_")


def entity_id(kind: str, *parts: str) -> str:
    sanitized = [_sanitize(p) for p in parts if p]
    return f"warehouse_{kind}_{'_'.join(sanitized)}"
