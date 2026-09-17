"""dlt boundary: register published landing Parquet. Never parse raw. Never own money."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pyarrow.parquet as pq

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LANDING = REPOSITORY_ROOT / "modern" / "landing"
DEFAULT_DATABASE = (
    REPOSITORY_ROOT / "modern" / "lakehouse" / "ducklake" / "northwind_modern.duckdb"
)

TABLE_BY_TYPE = {
    "01": "card_settlement",
    "06": "merchant_chargeback",
}


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    dataset: str
    table: str
    load_id: str
    row_count: int
    parquet_files: tuple[str, ...]


def landing_files(landing_root: Path, type_number: str) -> list[Path]:
    suffix = {"01": "NW_CARD_SETTLEMENT", "06": "NW_MERCHANT_CHARGEBACK"}[type_number]
    return sorted(
        path
        for path in landing_root.rglob("*.parquet")
        if path.name.startswith(suffix)
        and not any(part.startswith(".") for part in path.relative_to(landing_root).parts)
    )


def _arrow_batches(files: list[Path]) -> Iterator[object]:
    for path in files:
        yield pq.read_table(path)


def _batch_controls(files: list[Path], type_number: str) -> Iterator[dict[str, object]]:
    for path in files:
        manifest_path = path.parent / "parquet-manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        row: dict[str, object] = {
            "batch_id": str(manifest["batch_id"]),
            "computed_detail_count": int(manifest["computed_detail_count"]),
            "contract_code": str(manifest["contract_code"]),
            "currency": str(manifest.get("currency", "BRL")),
            "declared_detail_count": int(manifest["declared_detail_count"]),
            "parquet_sha256": str(manifest["parquet_sha256"]),
            "raw_sha256": str(manifest["raw_sha256"]),
            "record_count": int(manifest["record_count"]),
            "source_file": str(manifest["source_file"]),
            "type_number": type_number,
        }
        if type_number == "01":
            row["computed_net_amount"] = str(manifest["computed_net_amount"])
            row["declared_net_amount"] = str(manifest["declared_net_amount"])
        elif type_number == "06":
            row["computed_original_amount"] = str(manifest["computed_original_amount"])
            row["declared_original_amount"] = str(manifest["declared_original_amount"])
            row["computed_chargeback_amount"] = str(manifest["computed_chargeback_amount"])
            row["declared_chargeback_amount"] = str(manifest["declared_chargeback_amount"])
            row["computed_calculated_amount"] = str(manifest["computed_calculated_amount"])
            row["declared_calculated_amount"] = str(manifest["declared_calculated_amount"])
            row["rounding_mode"] = str(manifest.get("rounding_mode", "HALF_UP"))
        yield row


def register(
    type_number: str,
    *,
    landing_root: Path = DEFAULT_LANDING,
    database: Path = DEFAULT_DATABASE,
    dataset: str = "landing",
) -> RegistrationResult:
    """Load every landing Parquet file for one type into DuckDB through dlt."""

    import dlt

    files = landing_files(landing_root, type_number)
    table = TABLE_BY_TYPE[type_number]
    if not files:
        return RegistrationResult(
            dataset=dataset, table=table, load_id="", row_count=0, parquet_files=()
        )

    database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.environ.setdefault("DLT_DATA_DIR", str(REPOSITORY_ROOT / ".runtime" / "dlt"))
    pipeline = dlt.pipeline(
        pipeline_name=f"northwind_modern_type{type_number}",
        destination=dlt.destinations.duckdb(str(database)),
        dataset_name=dataset,
        progress=None,
    )
    info = pipeline.run(
        _arrow_batches(files),
        table_name=table,
        write_disposition="replace",
    )
    pipeline.run(
        _batch_controls(files, type_number),
        table_name=f"{table}_control",
        write_disposition="replace",
    )
    load_ids = getattr(info, "loads_ids", None) or [""]
    row_count = sum(pq.read_metadata(path).num_rows for path in files)
    return RegistrationResult(
        dataset=dataset,
        table=table,
        load_id=str(load_ids[-1]),
        row_count=row_count,
        parquet_files=tuple(str(path.name) for path in files),
    )
