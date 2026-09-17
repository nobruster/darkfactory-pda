"""Compose parse → schema → writer for one Type 02 batch. First write is landing Parquet."""

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
from schema import SchemaError, controls_of, money_text, sanitize
import writer

TYPE_NUMBER = "02"


def _load_parser():  # type: ignore[no-untyped-def]
    path = _HERE / "parser.py"
    spec = importlib.util.spec_from_file_location("nwp_t02_parser", path)
    if spec is None or spec.loader is None:
        raise ImportError("parser.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nwp_t02_parser"] = module
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


def _header_identity(payload: bytes) -> tuple[str | None, str | None]:
    try:
        header = payload.decode("utf-8").split("\n", 1)[0]
    except UnicodeDecodeError:
        return None, None
    fields = header.split("|")
    if len(fields) != 5 or fields[0] != "H":
        return None, None
    file_date, batch_id = fields[3], fields[4]
    if file_date.isdigit() and batch_id.startswith("B"):
        return file_date, batch_id
    return None, None


def _source_filename(payload: bytes, fallback: str) -> str:
    file_date, batch_id = _header_identity(payload)
    if file_date and batch_id:
        return f"NW_INSTANT_PAYMENT_{file_date}_{batch_id}.txt"
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
    source_filename = _source_filename(payload, raw_path.name)
    parsed = parser.parse_instant_payment_events(payload, filename=source_filename)
    _, header_batch = _header_identity(payload)
    batch_id = parsed.batch_id or header_batch or raw_path.stem
    controls = {
        key: value for key, value in controls_of(parsed).items() if value is not None
    }
    if not parsed.accepted:
        return _quarantined(
            batch_id=batch_id,
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
    parquet_name = source_filename.replace(".txt", ".parquet")
    arrow = writer.table(records, batch_id=batch_id, raw_sha256=raw_sha256)
    published = publish(
        arrow,
        directory=landing_root,
        filename=parquet_name,
        manifest={
            "batch_id": batch_id,
            "computed_credit_amount": controls["computed_credit_amount"],
            "computed_debit_amount": controls["computed_debit_amount"],
            "computed_event_count": len(records),
            "computed_net_amount": controls["computed_net_amount"],
            "contract_code": "PIX_EVENTS01",
            "currency": "BRL",
            "declared_credit_amount": controls["declared_credit_amount"],
            "declared_debit_amount": controls["declared_debit_amount"],
            "declared_event_count": len(records),
            "declared_net_amount": controls["declared_net_amount"],
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
