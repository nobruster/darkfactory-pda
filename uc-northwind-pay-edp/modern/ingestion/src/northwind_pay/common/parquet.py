"""Deterministic atomic Parquet publication for modern/landing/."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

import pyarrow as pa
import pyarrow.parquet as pq

COMPRESSION = "zstd"
COMPRESSION_LEVEL = 3
FORMAT_VERSION = "2.6"
MANIFEST_NAME = "parquet-manifest.json"


class PublicationError(RuntimeError):
    """A deterministic Parquet publication could not complete atomically."""


def write_table(table: pa.Table, destination: Path) -> None:
    pq.write_table(
        table,
        destination,
        compression=COMPRESSION,
        compression_level=COMPRESSION_LEVEL,
        use_dictionary=False,
        write_statistics=False,
        store_schema=True,
        version=FORMAT_VERSION,
        row_group_size=max(table.num_rows, 1),
        write_page_index=False,
    )


def canonical_metadata(
    *,
    batch_id: str,
    type_number: str,
    contract_code: str,
    contract_version: int,
    layout_version: str,
    raw_sha256: str,
    writer_version: str,
) -> dict[bytes, bytes]:
    return {
        key.encode("utf-8"): value.encode("utf-8")
        for key, value in {
            "northwind.batch_id": batch_id,
            "northwind.contract_code": contract_code,
            "northwind.contract_version": str(contract_version),
            "northwind.layout_version": layout_version,
            "northwind.raw_sha256": raw_sha256,
            "northwind.type_number": type_number,
            "northwind.writer_version": writer_version,
        }.items()
    }


def publish(
    table: pa.Table,
    *,
    directory: Path,
    filename: str,
    manifest: Mapping[str, Any],
) -> dict[str, str]:
    """Publish Parquet, checksum, and manifest all-or-nothing, manifest last."""

    directory = directory.resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{filename}.", dir=directory))
    try:
        data_path = staging / filename
        write_table(table, data_path)
        payload = data_path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        (staging / f"{filename}.sha256").write_text(
            f"{digest}  {filename}\n", encoding="ascii"
        )
        (staging / MANIFEST_NAME).write_text(
            json.dumps({**dict(manifest), "parquet_sha256": digest}, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        final = directory / str(manifest["batch_id"])
        if final.exists():
            existing = final / f"{filename}.sha256"
            if existing.is_file() and existing.read_text(encoding="ascii").split()[0] == digest:
                shutil.rmtree(staging, ignore_errors=True)
                return {"parquet_sha256": digest, "status": "already_published"}
            shutil.rmtree(staging, ignore_errors=True)
            raise PublicationError(
                "a different Parquet publication already exists for this batch"
            )
        os.chmod(staging, 0o700)
        staging.rename(final)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise PublicationError("Parquet publication could not complete") from exc
    return {"parquet_sha256": digest, "status": "published"}
