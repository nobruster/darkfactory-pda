"""Compose parse → schema → writer for one Type 06 batch. First write is landing Parquet."""

from __future__ import annotations

import hashlib
import importlib.util
import re
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
from schema import SchemaError, controls_of, money_text, sanitize
import writer

TYPE_NUMBER = "06"
BATCH_IN_NAME = re.compile(r"(B[0-9]{15})")


def _load_parser():  # type: ignore[no-untyped-def]
    path = _HERE / "parser.py"
    spec = importlib.util.spec_from_file_location("nwp_t06_parser", path)
    if spec is None or spec.loader is None:
        raise ImportError("parser.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nwp_t06_parser"] = module
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


def _source_filename(payload: bytes, fallback: str, parsed_name: str) -> str:
    if parsed_name and parsed_name.startswith("NW_MERCHANT_CHARGEBACK_"):
        return parsed_name
    match = BATCH_IN_NAME.search(fallback)
    if match:
        return fallback
    return parsed_name or fallback


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
    parsed = parser.parse_merchant_chargeback(
        payload, filename=raw_path.name, raw_path=raw_path
    )
    source_filename = parsed.source_filename or raw_path.name
    if not source_filename.startswith("NW_MERCHANT_CHARGEBACK_"):
        source_filename = parsed.source_filename or raw_path.name
    batch_id = parsed.batch_id
    if not batch_id:
        found = re.search(rb"B[0-9]{15}", payload)
        batch_id = found.group(0).decode("ascii") if found else raw_path.stem
    controls = {
        key: value
        for key, value in controls_of(parsed).items()
        if value is not None
    }
    if parsed.declared_chargeback_amount is not None:
        controls["declared_chargeback_amount"] = money_text(
            parsed.declared_chargeback_amount
        )
    if parsed.computed_chargeback_amount is not None:
        controls["computed_chargeback_amount"] = money_text(
            parsed.computed_chargeback_amount
        )
    if not parsed.accepted:
        return _quarantined(
            batch_id=batch_id or "UNKNOWN",
            code=parsed.rejection_code or "REJECTED",
            stage="parse",
            raw_sha256=raw_sha256,
            controls=controls,
        )
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
            "computed_calculated_amount": controls["computed_calculated_amount"],
            "computed_chargeback_amount": controls["computed_chargeback_amount"],
            "computed_detail_count": len(records),
            "computed_original_amount": controls["computed_original_amount"],
            "contract_code": "MER_CHGBK06",
            "currency": "BRL",
            "declared_calculated_amount": controls["declared_calculated_amount"],
            "declared_chargeback_amount": controls["declared_chargeback_amount"],
            "declared_detail_count": len(records),
            "declared_original_amount": controls["declared_original_amount"],
            "layout_version": "001",
            "parquet_file": parquet_name,
            "raw_sha256": raw_sha256,
            "record_count": len(records),
            "rounding_mode": "HALF_UP",
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
