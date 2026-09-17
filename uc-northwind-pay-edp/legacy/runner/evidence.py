from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path


class EvidenceError(Exception):
    """Batch evidence cannot be written immutably."""


class EvidenceWriter:
    def __init__(self, root: Path, batch_id: str) -> None:
        root = root.resolve()
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._final = root / batch_id
        if self._final.exists():
            raise EvidenceError(
                f"Immutable evidence already exists: {batch_id}"
            )
        self._temporary = Path(
            tempfile.mkdtemp(prefix=f".{batch_id}.", dir=root)
        )
        os.chmod(self._temporary, 0o700)
        self._closed = False

    @property
    def final_directory(self) -> Path:
        return self._final

    def write_json(self, name: str, value: object) -> None:
        self.write_bytes(
            name,
            (
                json.dumps(
                    value,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=True,
                )
                + "\n"
            ).encode("utf-8"),
        )

    def write_bytes(self, name: str, content: bytes) -> None:
        if "/" in name or name in {"", ".", ".."}:
            raise EvidenceError("Evidence filename is unsafe")
        path = self._temporary / name
        try:
            with path.open("xb") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise EvidenceError(
                f"Cannot write immutable evidence artifact: {name}"
            ) from exc

    def commit(self) -> Path:
        try:
            self._temporary.rename(self._final)
        except OSError as exc:
            raise EvidenceError("Cannot publish immutable batch evidence") from exc
        self._closed = True
        return self._final

    def abort(self) -> None:
        if not self._closed and self._temporary.exists():
            shutil.rmtree(self._temporary, ignore_errors=True)
        self._closed = True

    def __enter__(self) -> EvidenceWriter:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if not self._closed:
            self.abort()

