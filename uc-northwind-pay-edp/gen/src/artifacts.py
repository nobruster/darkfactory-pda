from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from checksum import checksum_sidecar, sha256_hex
from manifest import build_generation_receipt, build_source_manifest
from models import (
    ArtifactConflictError,
    ArtifactWriteError,
    GeneratedArtifact,
    WrittenBundle,
)


def _write_private_file(path: Path, content: bytes) -> None:
    """Create, flush, and fsync one owner-readable immutable artifact."""

    with path.open("xb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def write_bundle(
    generated: GeneratedArtifact,
    *,
    output_root: Path,
) -> WrittenBundle:
    """Atomically publish one private bundle without overwriting prior output."""

    temporary_directory: Path | None = None
    final_directory: Path | None = None
    try:
        output_root = output_root.resolve()
        raw_sha256 = sha256_hex(generated.raw_bytes)
        raw_filename = generated.batch.filename
        checksum_filename = f"{raw_filename}.sha256"
        manifest_bytes = build_source_manifest(
            generated,
            raw_sha256=raw_sha256,
        )
        receipt_bytes = build_generation_receipt(
            generated,
            raw_sha256=raw_sha256,
            manifest_bytes=manifest_bytes,
            checksum_filename=checksum_filename,
        )

        output_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        final_directory = output_root / generated.batch.batch_id
        if final_directory.exists():
            raise ArtifactConflictError(
                f"Immutable batch output already exists: {generated.batch.batch_id}"
            )

        temporary_directory = Path(
            tempfile.mkdtemp(
                prefix=f".{generated.batch.batch_id}.",
                dir=output_root,
            )
        )
        os.chmod(temporary_directory, 0o700)
        _write_private_file(
            temporary_directory / raw_filename,
            generated.raw_bytes,
        )
        _write_private_file(
            temporary_directory / checksum_filename,
            checksum_sidecar(digest=raw_sha256, filename=raw_filename),
        )
        _write_private_file(
            temporary_directory / "source-manifest.json",
            manifest_bytes,
        )
        _write_private_file(
            temporary_directory / "generation-receipt.json",
            receipt_bytes,
        )
        temporary_directory.rename(final_directory)
    except BaseException as exc:
        if temporary_directory is not None and temporary_directory.exists():
            shutil.rmtree(temporary_directory, ignore_errors=True)
        if isinstance(exc, ArtifactConflictError):
            raise
        if isinstance(exc, OSError):
            if final_directory is not None and final_directory.exists():
                raise ArtifactConflictError(
                    "Immutable batch output became occupied during publication"
                ) from exc
            raise ArtifactWriteError(
                f"Cannot safely write batch artifacts: {generated.batch.batch_id}"
            ) from exc
        raise

    return WrittenBundle(
        batch_id=generated.batch.batch_id,
        directory=final_directory,
        raw_file=final_directory / raw_filename,
        checksum_file=final_directory / checksum_filename,
        manifest_file=final_directory / "source-manifest.json",
        receipt_file=final_directory / "generation-receipt.json",
        raw_sha256=raw_sha256,
    )
