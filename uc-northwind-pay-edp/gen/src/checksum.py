from __future__ import annotations

import hashlib


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def checksum_sidecar(*, digest: str, filename: str) -> bytes:
    return f"{digest}  {filename}\n".encode("ascii")
