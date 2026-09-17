from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from briefspec import __version__
from briefspec.state import atomic_write_many, atomic_write_public


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize one canonical JSON representation for hashing and delivery."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def artifact_record(
    *,
    format_name: str,
    filename: str,
    media_type: str,
    content: bytes,
    renderer_version: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "format": format_name,
        "path": filename,
        "media_type": media_type,
        "size_bytes": len(content),
        "sha256": sha256_bytes(content),
        "renderer_version": renderer_version,
        "metadata": metadata or {},
    }


def build_manifest(
    *,
    kind: str,
    schema_version: str,
    canonical_sha256: str,
    created_at: str,
    files: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "kind": kind,
        "brief_spec_version": __version__,
        "canonical_sha256": canonical_sha256,
        "created_at": created_at,
        "files": sorted(files, key=lambda item: str(item["path"])),
        "metadata": metadata or {},
    }


def verify_manifest(manifest: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return ["Manifest files must be a non-empty array"]
    seen: set[str] = set()
    for index, record in enumerate(files):
        if not isinstance(record, dict):
            errors.append(f"files[{index}] must be an object")
            continue
        name = str(record.get("path", ""))
        if not name or Path(name).name != name:
            errors.append(f"files[{index}].path must be one filename")
            continue
        if name in seen:
            errors.append(f"Duplicate manifest path: {name}")
            continue
        seen.add(name)
        path = root / name
        if not path.is_file():
            errors.append(f"Manifest file is missing: {name}")
            continue
        content = path.read_bytes()
        if record.get("size_bytes") != len(content):
            errors.append(f"Manifest size mismatch: {name}")
        if record.get("sha256") != sha256_bytes(content):
            errors.append(f"Manifest hash mismatch: {name}")
    return errors


def build_receipt(
    *,
    kind: str,
    schema_version: str,
    receipt_id: str,
    content_sha256: str,
    created_at: str,
    destination: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "kind": kind,
        "receipt_id": receipt_id,
        "brief_spec_version": __version__,
        "content_sha256": content_sha256,
        "created_at": created_at,
        "destination": destination,
        "metadata": metadata or {},
    }


def verify_receipt(receipt: dict[str, Any], content: bytes) -> list[str]:
    expected = receipt.get("content_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        return ["Receipt content_sha256 is invalid"]
    actual = sha256_bytes(content)
    return [] if actual == expected else ["Receipt content hash mismatch"]


def atomic_write_set(files: list[tuple[Path, bytes, int]]) -> None:
    atomic_write_many(files)


def write_json(path: Path, value: Any, *, force: bool = False, mode: int = 0o644) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing output: {path}")
    content = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    atomic_write_public(path, content, mode=mode)
