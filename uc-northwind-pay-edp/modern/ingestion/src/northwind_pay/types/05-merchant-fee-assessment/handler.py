"""Compose parse -> schema -> writer for one Type 05 batch. First write is landing Parquet."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from northwind_pay.common.parquet import publish
from schema import SchemaError, sanitize
import writer

TYPE_NUMBER = "05"


def _load_parser():  # type: ignore[no-untyped-def]
    path = _HERE / "parser.py"
    spec = importlib.util.spec_from_file_location("nwp_t05_parser", path)
    if spec is None or spec.loader is None:
        raise ImportError("parser.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nwp_t05_parser"] = module
    spec.loader.exec_module(module)
    return module


parser = _load_parser()


@dataclass(frozen=True)
class BatchOutcome:
    batch_id: str
    type_number: str
    status: str
    code: str | None
    stage: str
    raw_sha256: str
    parquet_sha256: str | None
    record_count: int
    controls: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "code": self.code,
            "controls": self.controls,
            "parquet_sha256": self.parquet_sha256,
            "raw_sha256": self.raw_sha256,
            "record_count": self.record_count,
            "stage": self.stage,
            "status": self.status,
            "type_number": self.type_number,
        }


def _source_filename(batch_id: str | None, business_date: str | None, fallback: str) -> str:
    if batch_id and business_date:
        return f"NW_MERCHANT_FEES_{business_date.replace('-', '')}_{batch_id}.csv"
    return fallback


def _quarantined(
    *,
    batch_id: str,
    code: str,
    stage: str,
    raw_sha256: str,
    controls: dict[str, Any],
) -> BatchOutcome:
    return BatchOutcome(
        batch_id=batch_id,
        type_number=TYPE_NUMBER,
        status="quarantined",
        code=code,
        stage=stage,
        raw_sha256=raw_sha256,
        parquet_sha256=None,
        record_count=0,
        controls=controls,
    )


def process(raw_path: Path, *, landing_root: Path) -> BatchOutcome:
    payload = raw_path.read_bytes()
    raw_sha256 = hashlib.sha256(payload).hexdigest()
    parsed = parser.parse_merchant_fee_assessment(payload, filename=raw_path.name)
    batch_id = parsed.batch_id or raw_path.stem
    controls = dict(parsed.controls)
    if not parsed.accepted:
        return _quarantined(
            batch_id=batch_id,
            code=parsed.rejection_code or "REJECTED",
            stage="parse",
            raw_sha256=raw_sha256,
            controls=controls,
        )
    business_date = parsed.assessments[0].assessment_date if parsed.assessments else None
    source_filename = _source_filename(batch_id, business_date, raw_path.name)
    try:
        records = sanitize(parsed, source_filename=source_filename)
    except SchemaError as error:
        return _quarantined(
            batch_id=batch_id,
            code=error.code,
            stage="validate",
            raw_sha256=raw_sha256,
            controls=controls,
        )
    parquet_name = source_filename.replace(".csv", ".parquet")
    arrow = writer.table(records, batch_id=batch_id, raw_sha256=raw_sha256)
    published = publish(
        arrow,
        directory=landing_root,
        filename=parquet_name,
        manifest={
            "batch_id": batch_id,
            "computed_assessed_fee": controls["computed_assessed_fee"],
            "computed_row_count": controls["computed_row_count"],
            "contract_code": "MER_FEESET05",
            "currency": "BRL",
            "declared_assessed_fee": controls["declared_assessed_fee"],
            "declared_row_count": controls["declared_row_count"],
            "layout_version": "001",
            "parquet_file": parquet_name,
            "raw_sha256": raw_sha256,
            "record_count": len(records),
            "source_file": source_filename,
            "type_number": TYPE_NUMBER,
            "writer_version": writer.WRITER_VERSION,
        },
    )
    return BatchOutcome(
        batch_id=batch_id,
        type_number=TYPE_NUMBER,
        status="succeeded",
        code=None,
        stage="published",
        raw_sha256=raw_sha256,
        parquet_sha256=published["parquet_sha256"],
        record_count=len(records),
        controls=controls,
    )
