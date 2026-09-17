from __future__ import annotations

import re
from datetime import datetime

from models import (
    CardSettlementBatch,
    CardSettlementDetail,
    Type01Contract,
    Type01GeneratedBatch,
    ValidationError,
)


VALID_MINIMAL = "valid-minimal"
VALID_BOUNDARY = "valid-boundary"
NEGATIVE_OVERPUNCH = "negative-overpunch"
MALFORMED = "malformed"
DF_SOURCE_001 = "DF-SOURCE-001"

SUPPORTED_SCENARIOS = (
    VALID_MINIMAL,
    VALID_BOUNDARY,
    NEGATIVE_OVERPUNCH,
    MALFORMED,
    DF_SOURCE_001,
)


def valid_minimal_batch() -> CardSettlementBatch:
    return CardSettlementBatch(
        file_date="20260723",
        batch_id="B202607230000001",
        details=(
            CardSettlementDetail(
                transaction_id="TXN0000000000001",
                merchant_id="MERCHANT00000001",
                pan="4111111111111111",
                cpf="12345678909",
                transaction_date="20260723",
                transaction_time="091530",
                amount_minor=12_345,
                currency="BRL",
                movement_code="P",
                authorization_code="A1B2C3",
                nsu="000000000001",
                terminal_id="TERMINAL00000001",
            ),
            CardSettlementDetail(
                transaction_id="TXN0000000000002",
                merchant_id="MERCHANT00000002",
                pan="5555555555554444",
                cpf="98765432100",
                transaction_date="20260723",
                transaction_time="101500",
                amount_minor=5_000,
                currency="BRL",
                movement_code="P",
                authorization_code="D4E5F6",
                nsu="000000000002",
                terminal_id="TERMINAL00000002",
            ),
        ),
    )


def valid_boundary_batch() -> CardSettlementBatch:
    return CardSettlementBatch(
        file_date="20240229",
        batch_id="B202402290000001",
        details=(
            CardSettlementDetail(
                transaction_id="TXN9999999999999",
                merchant_id="MERCHANT99999999",
                pan="4000000000000002",
                cpf="11144477735",
                transaction_date="20240229",
                transaction_time="235959",
                amount_minor=999_999_999_999,
                currency="BRL",
                movement_code="P",
                authorization_code="ZZ9999",
                nsu="999999999999",
                terminal_id="TERMINAL99999999",
            ),
        ),
    )


def negative_overpunch_batch() -> CardSettlementBatch:
    return CardSettlementBatch(
        file_date="20260723",
        batch_id="B202607230000002",
        details=(
            CardSettlementDetail(
                transaction_id="TXN0000000000003",
                merchant_id="MERCHANT00000003",
                pan="4000000000000002",
                cpf="11144477735",
                transaction_date="20260723",
                transaction_time="113000",
                amount_minor=-1_234,
                currency="BRL",
                movement_code="R",
                authorization_code="R1R2R3",
                nsu="000000000003",
                terminal_id="TERMINAL00000003",
            ),
        ),
    )


def malformed_batch() -> CardSettlementBatch:
    return CardSettlementBatch(
        file_date="20260723",
        batch_id="B202607230000003",
        details=(
            CardSettlementDetail(
                transaction_id="TXN0000000000004",
                merchant_id="MERCHANT00000004",
                pan="4000000000000002",
                cpf="11144477735",
                transaction_date="20260723",
                transaction_time="120000",
                amount_minor=1_234,
                currency="BRL",
                movement_code="P",
                authorization_code="R4R5R6",
                nsu="000000000004",
                terminal_id="TERMINAL00000004",
            ),
        ),
    )


def df_source_001_batch() -> CardSettlementBatch:
    canonical = valid_minimal_batch()
    return CardSettlementBatch(
        file_date=canonical.file_date,
        batch_id="B202607230000004",
        details=canonical.details,
    )


def _require_pattern(*, name: str, value: str, pattern: str) -> None:
    if re.fullmatch(pattern, value) is None:
        raise ValidationError(f"Field does not match its contract: {name}")


def _require_date(value: str, *, name: str) -> None:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValidationError(f"Field is not a valid yyyyMMdd date: {name}") from exc


def _require_time(value: str, *, name: str) -> None:
    try:
        datetime.strptime(value, "%H%M%S")
    except ValueError as exc:
        raise ValidationError(f"Field is not a valid HHmmss time: {name}") from exc


def _encode_exact(
    *,
    name: str,
    value: str,
    length: int,
    encoding: str,
) -> bytes:
    try:
        encoded = value.encode(encoding)
    except UnicodeEncodeError as exc:
        raise ValidationError(f"Field cannot be encoded under the contract: {name}") from exc
    if len(encoded) != length:
        raise ValidationError(f"Field has the wrong encoded byte length: {name}")
    return encoded


def encode_overpunch(
    amount_minor: int,
    *,
    width: int,
    contract: Type01Contract,
) -> str:
    digits = str(abs(amount_minor))
    if len(digits) > width:
        raise ValidationError("Amount does not fit its overpunch field")
    padded = digits.zfill(width)
    mapping = (
        contract.negative_overpunch
        if amount_minor < 0
        else contract.positive_overpunch
    )
    return padded[:-1] + mapping[int(padded[-1])]


def encode_header(
    batch: CardSettlementBatch,
    *,
    contract: Type01Contract,
) -> bytes:
    _require_date(batch.file_date, name="header.file_date")
    _require_pattern(
        name="header.batch_id",
        value=batch.batch_id,
        pattern=r"B[0-9]{15}",
    )
    record = b"".join(
        (
            b"H",
            _encode_exact(
                name="header.file_date",
                value=batch.file_date,
                length=8,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="header.batch_id",
                value=batch.batch_id,
                length=16,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="header.file_type_code",
                value=contract.code,
                length=12,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="header.layout_version",
                value=contract.layout_version,
                length=3,
                encoding=contract.encoding,
            ),
        )
    )
    if len(record) != contract.header_length:
        raise ValidationError("Header has the wrong encoded byte length")
    return record


def encode_detail(
    detail: CardSettlementDetail,
    *,
    contract: Type01Contract,
) -> bytes:
    _require_pattern(
        name="detail.transaction_id",
        value=detail.transaction_id,
        pattern=r"[A-Z0-9]{16}",
    )
    _require_pattern(
        name="detail.merchant_id",
        value=detail.merchant_id,
        pattern=r"[A-Z0-9]{16}",
    )
    _require_pattern(name="detail.pan", value=detail.pan, pattern=r"[0-9]{16}")
    _require_pattern(name="detail.cpf", value=detail.cpf, pattern=r"[0-9]{11}")
    _require_date(detail.transaction_date, name="detail.transaction_date")
    _require_time(detail.transaction_time, name="detail.transaction_time")
    _require_pattern(
        name="detail.authorization_code",
        value=detail.authorization_code,
        pattern=r"[A-Z0-9]{6}",
    )
    _require_pattern(name="detail.nsu", value=detail.nsu, pattern=r"[0-9]{12}")
    _require_pattern(
        name="detail.terminal_id",
        value=detail.terminal_id,
        pattern=r"[A-Z0-9]{16}",
    )
    if detail.currency != "BRL":
        raise ValidationError("Type 01 currency must be BRL")
    if detail.movement_code == "P" and detail.amount_minor <= 0:
        raise ValidationError("Purchase movement requires a positive amount")
    if detail.movement_code == "R" and detail.amount_minor >= 0:
        raise ValidationError("Refund movement requires a negative amount")
    if detail.movement_code not in {"P", "R"}:
        raise ValidationError("Movement code is not supported")

    record = b"".join(
        (
            b"D",
            _encode_exact(
                name="detail.transaction_id",
                value=detail.transaction_id,
                length=16,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="detail.merchant_id",
                value=detail.merchant_id,
                length=16,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="detail.pan",
                value=detail.pan,
                length=16,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="detail.cpf",
                value=detail.cpf,
                length=11,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="detail.transaction_date",
                value=detail.transaction_date,
                length=8,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="detail.transaction_time",
                value=detail.transaction_time,
                length=6,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="detail.amount_brl",
                value=encode_overpunch(
                    detail.amount_minor,
                    width=12,
                    contract=contract,
                ),
                length=12,
                encoding=contract.encoding,
            ),
            b"BRL",
            _encode_exact(
                name="detail.movement_code",
                value=detail.movement_code,
                length=1,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="detail.authorization_code",
                value=detail.authorization_code,
                length=6,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="detail.nsu",
                value=detail.nsu,
                length=12,
                encoding=contract.encoding,
            ),
            _encode_exact(
                name="detail.terminal_id",
                value=detail.terminal_id,
                length=16,
                encoding=contract.encoding,
            ),
        )
    )
    if len(record) != contract.detail_length:
        raise ValidationError("Detail has the wrong encoded byte length")
    return record


def encode_trailer(
    batch: CardSettlementBatch,
    *,
    contract: Type01Contract,
    declared_detail_count: int | None = None,
    declared_net_amount_minor: int | None = None,
) -> bytes:
    detail_count = (
        batch.detail_count
        if declared_detail_count is None
        else declared_detail_count
    )
    net_amount_minor = (
        batch.net_amount_minor
        if declared_net_amount_minor is None
        else declared_net_amount_minor
    )
    if detail_count < 0 or detail_count > 999_999:
        raise ValidationError("Detail count does not fit the trailer")
    record = b"".join(
        (
            b"T",
            _encode_exact(
                name="trailer.file_date",
                value=batch.file_date,
                length=8,
                encoding=contract.encoding,
            ),
            f"{detail_count:06d}".encode("ascii"),
            encode_overpunch(
                net_amount_minor,
                width=15,
                contract=contract,
            ).encode(contract.encoding),
            _encode_exact(
                name="trailer.batch_id",
                value=batch.batch_id,
                length=16,
                encoding=contract.encoding,
            ),
        )
    )
    if len(record) != contract.trailer_length:
        raise ValidationError("Trailer has the wrong encoded byte length")
    return record


def _validate_batch(
    batch: CardSettlementBatch,
    *,
    contract: Type01Contract,
) -> None:
    if contract.type_number != "01":
        raise ValidationError("Type 01 generator received another contract")
    if (
        contract.encoding != "ISO-8859-1"
        or contract.line_ending != "LF"
        or contract.final_newline != "required"
    ):
        raise ValidationError("Type 01 generator supports only its approved transport")

    if re.fullmatch(contract.filename_pattern, batch.filename) is None:
        raise ValidationError("Generated filename violates the contract")
    if batch.batch_id[1:9] != batch.file_date:
        raise ValidationError("Batch ID date does not match the file date")
    transaction_ids = [detail.transaction_id for detail in batch.details]
    if len(set(transaction_ids)) != len(transaction_ids):
        raise ValidationError("Duplicate transaction ID in batch")


def _render_batch(
    *,
    scenario: str,
    batch: CardSettlementBatch,
    contract: Type01Contract,
    computed_net_amount_minor: int | None,
    declared_net_amount_minor: int,
    expected_contract_status: str,
    expected_violation: str | None,
    corrupt_first_detail_overpunch: bool = False,
) -> Type01GeneratedBatch:
    _validate_batch(batch, contract=contract)
    detail_records = [
        encode_detail(detail, contract=contract)
        for detail in batch.details
    ]
    if corrupt_first_detail_overpunch:
        if not detail_records:
            raise ValidationError("Malformed scenario requires a detail record")
        amount_final_byte = 85
        first_detail = detail_records[0]
        detail_records[0] = (
            first_detail[:amount_final_byte]
            + b"Z"
            + first_detail[amount_final_byte + 1 :]
        )

    records = [
        encode_header(batch, contract=contract),
        *detail_records,
        encode_trailer(
            batch,
            contract=contract,
            declared_detail_count=batch.detail_count,
            declared_net_amount_minor=declared_net_amount_minor,
        ),
    ]
    return Type01GeneratedBatch(
        scenario=scenario,
        contract=contract,
        batch=batch,
        raw_bytes=b"\n".join(records) + b"\n",
        computed_detail_count=batch.detail_count,
        computed_net_amount_minor=computed_net_amount_minor,
        declared_detail_count=batch.detail_count,
        declared_net_amount_minor=declared_net_amount_minor,
        expected_contract_status=expected_contract_status,
        expected_violation=expected_violation,
    )


def render_valid_minimal(
    contract: Type01Contract,
) -> Type01GeneratedBatch:
    batch = valid_minimal_batch()
    return _render_batch(
        scenario=VALID_MINIMAL,
        batch=batch,
        contract=contract,
        computed_net_amount_minor=batch.net_amount_minor,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_valid_boundary(
    contract: Type01Contract,
) -> Type01GeneratedBatch:
    batch = valid_boundary_batch()
    return _render_batch(
        scenario=VALID_BOUNDARY,
        batch=batch,
        contract=contract,
        computed_net_amount_minor=batch.net_amount_minor,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_negative_overpunch(
    contract: Type01Contract,
) -> Type01GeneratedBatch:
    batch = negative_overpunch_batch()
    return _render_batch(
        scenario=NEGATIVE_OVERPUNCH,
        batch=batch,
        contract=contract,
        computed_net_amount_minor=batch.net_amount_minor,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_malformed(contract: Type01Contract) -> Type01GeneratedBatch:
    batch = malformed_batch()
    return _render_batch(
        scenario=MALFORMED,
        batch=batch,
        contract=contract,
        computed_net_amount_minor=None,
        declared_net_amount_minor=-1_234,
        expected_contract_status="REJECTED",
        expected_violation="INVALID_OVERPUNCH",
        corrupt_first_detail_overpunch=True,
    )


def render_df_source_001(
    contract: Type01Contract,
) -> Type01GeneratedBatch:
    batch = df_source_001_batch()
    return _render_batch(
        scenario=DF_SOURCE_001,
        batch=batch,
        contract=contract,
        computed_net_amount_minor=batch.net_amount_minor,
        declared_net_amount_minor=17_344,
        expected_contract_status="REJECTED",
        expected_violation="SOURCE_CONTROL_TOTAL_MISMATCH",
    )


def render_scenario(
    scenario: str,
    *,
    contract: Type01Contract,
) -> Type01GeneratedBatch:
    renderers = {
        VALID_MINIMAL: render_valid_minimal,
        VALID_BOUNDARY: render_valid_boundary,
        NEGATIVE_OVERPUNCH: render_negative_overpunch,
        MALFORMED: render_malformed,
        DF_SOURCE_001: render_df_source_001,
    }
    renderer = renderers.get(scenario)
    if renderer is None:
        raise ValidationError(f"Unsupported Type 01 scenario: {scenario}")
    return renderer(contract)
