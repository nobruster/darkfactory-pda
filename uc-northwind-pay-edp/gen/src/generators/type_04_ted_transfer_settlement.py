"""Deterministic Type 04 TED transfer source-system simulator.

The renderer owns every heterogeneous fixed-width record. Restricted account,
document, beneficiary-name, and return-reason values stay redacted from model
representations and never enter generated metadata.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from models import (
    TedReturn,
    TedTransfer,
    TedTransferBatch,
    Type04Contract,
    Type04GeneratedBatch,
    ValidationError,
)


VALID_MINIMAL = "valid-minimal"
VALID_BOUNDARY = "valid-boundary"
MALFORMED = "malformed"
ALL_RETURNED_ZERO_NET = "all-returned-zero-net"
DF_SOURCE_004 = "DF-SOURCE-004"
SUPPORTED_SCENARIOS = (
    VALID_MINIMAL,
    VALID_BOUNDARY,
    MALFORMED,
    ALL_RETURNED_ZERO_NET,
    DF_SOURCE_004,
)

_BATCH_ID = re.compile(r"B[0-9]{15}")
_MOVEMENT_ID = re.compile(r"[A-Z][A-Z0-9]{15}")
_ISPB = re.compile(r"[0-9]{8}")
_BRANCH = re.compile(r"[0-9]{4}")
_ACCOUNT = re.compile(r"[0-9]{12}")
_PURPOSE = re.compile(r"[A-Z][A-Z0-9_]{1,9}")
_BENEFICIARY_NAME = re.compile(r"[A-Z][A-Z0-9 .&/-]{0,22}")
_REASON_CODE = re.compile(r"[A-Z][A-Z0-9]{4}")
_REASON_TEXT = re.compile(r"[A-Z][A-Z0-9 .&/-]{0,23}")


def _return(
    *,
    return_id: str,
    return_date: str,
    return_time: str,
    reason_code: str,
    reason_text: str,
) -> TedReturn:
    return TedReturn(
        return_id=return_id,
        return_date=return_date,
        return_time=return_time,
        reason_code=reason_code,
        reason_text=reason_text,
    )


def _transfer(
    *,
    transfer_id: str,
    amount_minor: int,
    transfer_date: str,
    transfer_time: str,
    payer_ispb: str,
    payer_branch: str,
    payer_account: str,
    payer_tax_id: str,
    payer_party_type: str,
    beneficiary_ispb: str,
    beneficiary_branch: str,
    beneficiary_account: str,
    beneficiary_tax_id: str,
    beneficiary_party_type: str,
    purpose_code: str,
    status_code: str,
    beneficiary_name: str,
    return_record: TedReturn | None = None,
) -> TedTransfer:
    return TedTransfer(
        transfer_id=transfer_id,
        amount_minor=amount_minor,
        transfer_date=transfer_date,
        transfer_time=transfer_time,
        payer_ispb=payer_ispb,
        payer_branch=payer_branch,
        payer_account=payer_account,
        payer_tax_id=payer_tax_id,
        payer_party_type=payer_party_type,
        beneficiary_ispb=beneficiary_ispb,
        beneficiary_branch=beneficiary_branch,
        beneficiary_account=beneficiary_account,
        beneficiary_tax_id=beneficiary_tax_id,
        beneficiary_party_type=beneficiary_party_type,
        purpose_code=purpose_code,
        status_code=status_code,
        beneficiary_name=beneficiary_name,
        return_record=return_record,
    )


def _standard_batch(
    *,
    batch_id: str,
    first_returned: bool,
) -> TedTransferBatch:
    suffix = batch_id[-3:]
    first_id = f"TED2026072300{suffix}"
    second_id = f"TED2026072301{suffix}"
    first_return = (
        _return(
            return_id=f"RET2026072300{suffix}",
            return_date="20260724",
            return_time="101500",
            reason_code="ACERR",
            reason_text="CONTA ENCERRADA",
        )
        if first_returned
        else None
    )
    return TedTransferBatch(
        file_date="20260723",
        batch_id=batch_id,
        origin_ispb="12345678",
        transfers=(
            _transfer(
                transfer_id=first_id,
                amount_minor=100_000,
                transfer_date="20260723",
                transfer_time="091500",
                payer_ispb="12345678",
                payer_branch="0001",
                payer_account="000123456789",
                payer_tax_id="00012345678909",
                payer_party_type="F",
                beneficiary_ispb="60701190",
                beneficiary_branch="3412",
                beneficiary_account="000987654321",
                beneficiary_tax_id="12345678000195",
                beneficiary_party_type="J",
                purpose_code="FORNECEDOR",
                status_code="RT" if first_returned else "OK",
                beneficiary_name="LOJA AZUL LTDA",
                return_record=first_return,
            ),
            _transfer(
                transfer_id=second_id,
                amount_minor=25_000,
                transfer_date="20260723",
                transfer_time="094500",
                payer_ispb="12345678",
                payer_branch="0001",
                payer_account="000123456789",
                payer_tax_id="00012345678909",
                payer_party_type="F",
                beneficiary_ispb="87654321",
                beneficiary_branch="0002",
                beneficiary_account="000111222333",
                beneficiary_tax_id="00098765432100",
                beneficiary_party_type="F",
                purpose_code="SERVICOS",
                status_code="RT",
                beneficiary_name="JOAO SOUZA",
                return_record=_return(
                    return_id=(
                        f"RET2026072301{suffix}"
                        if first_returned
                        else f"RET2026072300{suffix}"
                    ),
                    return_date="20260724",
                    return_time="101600" if first_returned else "101500",
                    reason_code="DEVOL" if first_returned else "ACERR",
                    reason_text=(
                        "DEVOLUCAO TOTAL"
                        if first_returned
                        else "CONTA ENCERRADA"
                    ),
                ),
            ),
        ),
    )


def valid_minimal_batch() -> TedTransferBatch:
    """Return the canonical mixed successful/full-return batch."""

    return _standard_batch(
        batch_id="B202607230000301",
        first_returned=False,
    )


def valid_boundary_batch() -> TedTransferBatch:
    """Return leap-day and maximum-width monetary boundary values."""

    return TedTransferBatch(
        file_date="20000229",
        batch_id="B200002290000302",
        origin_ispb="99999999",
        transfers=(
            _transfer(
                transfer_id="TED2000022900302",
                amount_minor=99_999_999_999_999,
                transfer_date="20000229",
                transfer_time="235959",
                payer_ispb="99999999",
                payer_branch="9999",
                payer_account="999999999998",
                payer_tax_id="99999999999962",
                payer_party_type="J",
                beneficiary_ispb="00000001",
                beneficiary_branch="0001",
                beneficiary_account="000000000001",
                beneficiary_tax_id="00012345678909",
                beneficiary_party_type="F",
                purpose_code="SALARIO",
                status_code="OK",
                beneficiary_name="BENEFICIARIO LIMITE",
            ),
        ),
    )


def malformed_batch() -> TedTransferBatch:
    """Return the valid model whose first CRLF is changed during rendering."""

    return _standard_batch(
        batch_id="B202607230000303",
        first_returned=False,
    )


def all_returned_zero_net_batch() -> TedTransferBatch:
    """Return two transfers that are both fully returned."""

    return _standard_batch(
        batch_id="B202607230000304",
        first_returned=True,
    )


def df_source_004_batch() -> TedTransferBatch:
    """Return the source-defect batch before its trailer net is changed."""

    return _standard_batch(
        batch_id="B202607230000305",
        first_returned=False,
    )


def _valid_cpf(value: str) -> bool:
    if re.fullmatch(r"[0-9]{11}", value) is None or len(set(value)) == 1:
        return False
    numbers = [int(character) for character in value]
    first_sum = sum(
        digit * weight
        for digit, weight in zip(numbers[:9], range(10, 1, -1))
    )
    first_remainder = first_sum % 11
    first = 0 if first_remainder < 2 else 11 - first_remainder
    second_sum = sum(
        digit * weight
        for digit, weight in zip(
            numbers[:9] + [first],
            range(11, 1, -1),
        )
    )
    second_remainder = second_sum % 11
    second = 0 if second_remainder < 2 else 11 - second_remainder
    return numbers[-2:] == [first, second]


def _valid_cnpj(value: str) -> bool:
    if re.fullmatch(r"[0-9]{14}", value) is None or len(set(value)) == 1:
        return False
    numbers = [int(character) for character in value]
    first_weights = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    first_remainder = sum(
        digit * weight
        for digit, weight in zip(numbers[:12], first_weights)
    ) % 11
    first = 0 if first_remainder < 2 else 11 - first_remainder
    second_weights = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    second_remainder = sum(
        digit * weight
        for digit, weight in zip(
            numbers[:12] + [first],
            second_weights,
        )
    ) % 11
    second = 0 if second_remainder < 2 else 11 - second_remainder
    return numbers[-2:] == [first, second]


def _valid_document(value: str, party_type: str) -> bool:
    return (
        party_type == "F"
        and value.startswith("000")
        and _valid_cpf(value[3:])
    ) or (
        party_type == "J"
        and _valid_cnpj(value)
    )


def _local_timestamp(
    date_value: str,
    time_value: str,
    *,
    source_zone: str,
) -> datetime:
    try:
        naive = datetime.strptime(
            date_value + time_value,
            "%Y%m%d%H%M%S",
        )
        zone = ZoneInfo(source_zone)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValidationError(
            "Type 04 timestamp violates its local-time contract"
        ) from exc
    candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold)
        if (
            candidate.astimezone(UTC)
            .astimezone(zone)
            .replace(tzinfo=None)
            == naive
        ):
            candidates.append(candidate)
    if not candidates:
        raise ValidationError(
            "Type 04 timestamp violates its local-time contract"
        )
    return candidates[0]


def _validate_transfer(
    transfer: TedTransfer,
    *,
    file_date: str,
    source_zone: str,
) -> None:
    try:
        transfer.beneficiary_name.encode("ascii", errors="strict")
        if transfer.return_record is not None:
            transfer.return_record.reason_text.encode(
                "ascii",
                errors="strict",
            )
    except UnicodeError as exc:
        raise ValidationError(
            "Type 04 restricted text violates US-ASCII"
        ) from exc
    transfer_timestamp = _local_timestamp(
        transfer.transfer_date,
        transfer.transfer_time,
        source_zone=source_zone,
    )
    if (
        _MOVEMENT_ID.fullmatch(transfer.transfer_id) is None
        or type(transfer.amount_minor) is not int
        or not 1 <= transfer.amount_minor <= 99_999_999_999_999
        or transfer.transfer_date != file_date
        or _ISPB.fullmatch(transfer.payer_ispb) is None
        or _BRANCH.fullmatch(transfer.payer_branch) is None
        or _ACCOUNT.fullmatch(transfer.payer_account) is None
        or not _valid_document(
            transfer.payer_tax_id,
            transfer.payer_party_type,
        )
        or _ISPB.fullmatch(transfer.beneficiary_ispb) is None
        or _BRANCH.fullmatch(transfer.beneficiary_branch) is None
        or _ACCOUNT.fullmatch(transfer.beneficiary_account) is None
        or not _valid_document(
            transfer.beneficiary_tax_id,
            transfer.beneficiary_party_type,
        )
        or _PURPOSE.fullmatch(transfer.purpose_code) is None
        or _BENEFICIARY_NAME.fullmatch(transfer.beneficiary_name) is None
        or "~" in transfer.purpose_code
        or "~" in transfer.beneficiary_name
        or transfer.status_code not in {"OK", "RT"}
        or (
            transfer.status_code == "OK"
            and transfer.return_record is not None
        )
        or (
            transfer.status_code == "RT"
            and transfer.return_record is None
        )
    ):
        raise ValidationError(
            "Type 04 transfer violates its field contract"
        )
    restricted = (
        transfer.payer_account,
        transfer.payer_tax_id,
        transfer.payer_tax_id[3:]
        if transfer.payer_party_type == "F"
        else transfer.payer_tax_id,
        transfer.beneficiary_account,
        transfer.beneficiary_tax_id,
        transfer.beneficiary_tax_id[3:]
        if transfer.beneficiary_party_type == "F"
        else transfer.beneficiary_tax_id,
        transfer.beneficiary_name,
    )
    for safe_value in (transfer.transfer_id, transfer.purpose_code):
        if any(value in safe_value for value in restricted):
            raise ValidationError(
                "A Type 04 safe identifier contains restricted source data"
            )

    returned = transfer.return_record
    if returned is None:
        return
    returned_timestamp = _local_timestamp(
        returned.return_date,
        returned.return_time,
        source_zone=source_zone,
    )
    if (
        _MOVEMENT_ID.fullmatch(returned.return_id) is None
        or returned.return_id == transfer.transfer_id
        or _REASON_CODE.fullmatch(returned.reason_code) is None
        or _REASON_TEXT.fullmatch(returned.reason_text) is None
        or "~" in returned.reason_text
        or returned_timestamp <= transfer_timestamp
        or any(
            value in safe_value
            for safe_value in (returned.return_id, returned.reason_code)
            for value in (*restricted, returned.reason_text)
        )
    ):
        raise ValidationError(
            "Type 04 return violates its linked-record contract"
        )


def _validate_batch(
    batch: TedTransferBatch,
    *,
    contract: Type04Contract,
) -> None:
    if (
        contract.type_number != "04"
        or contract.code != "TED_SETTLE04"
        or contract.layout_version != "001"
        or contract.encoding != "US-ASCII"
        or contract.line_ending != "CRLF"
        or contract.final_newline != "required"
        or (
            contract.header_length,
            contract.transfer_length,
            contract.return_length,
            contract.trailer_length,
        )
        != (56, 162, 91, 82)
        or contract.visible_padding_character != "~"
        or contract.source_zone != "America/Sao_Paulo"
    ):
        raise ValidationError(
            "Type 04 generator received an unsupported contract"
        )
    _local_timestamp(
        batch.file_date,
        "120000",
        source_zone=contract.source_zone,
    )
    if (
        _BATCH_ID.fullmatch(batch.batch_id) is None
        or batch.batch_id[1:9] != batch.file_date
        or re.fullmatch(contract.filename_pattern, batch.filename) is None
        or _ISPB.fullmatch(batch.origin_ispb) is None
        or not 1 <= batch.transfer_count <= contract.max_transfers
        or not 0 <= batch.return_count <= contract.max_returns
        or not 1 <= batch.movement_count <= contract.max_movements
        or not 3 <= batch.physical_record_count
        <= contract.max_physical_records
        or batch.net_amount_minor < 0
    ):
        raise ValidationError("Type 04 batch identity or size is invalid")
    movement_ids: set[str] = set()
    for transfer in batch.transfers:
        _validate_transfer(
            transfer,
            file_date=batch.file_date,
            source_zone=contract.source_zone,
        )
        identifiers = {transfer.transfer_id}
        if transfer.return_record is not None:
            identifiers.add(transfer.return_record.return_id)
        if (
            len(identifiers) != 1
            + int(transfer.return_record is not None)
            or not movement_ids.isdisjoint(identifiers)
        ):
            raise ValidationError(
                "Type 04 movement identifiers are not unique"
            )
        movement_ids.update(identifiers)


def _money_magnitude(value_minor: int) -> str:
    rendered = str(value_minor)
    if value_minor < 0 or len(rendered) > 14:
        raise ValidationError("Type 04 money does not fit its source field")
    return rendered.zfill(14)


def _right_tilde_pad(
    value: str,
    *,
    width: int,
    contract: Type04Contract,
) -> str:
    if "~" in value or len(value.encode("ascii")) > width:
        raise ValidationError("Type 04 visible padding field is invalid")
    return value + contract.visible_padding_character * (width - len(value))


def encode_header(
    batch: TedTransferBatch,
    *,
    contract: Type04Contract,
) -> bytes:
    value = (
        f"H{batch.file_date}{batch.batch_id}{contract.code}"
        f"{contract.layout_version}{batch.file_date}{batch.origin_ispb}"
    ).encode("ascii")
    if len(value) != contract.header_length:
        raise ValidationError("Type 04 header length drifted")
    return value


def encode_transfer(
    transfer: TedTransfer,
    *,
    contract: Type04Contract,
) -> bytes:
    value = (
        f"D{transfer.transfer_id}+"
        f"{_money_magnitude(transfer.amount_minor)}BRL"
        f"{transfer.transfer_date}{transfer.transfer_time}"
        f"{transfer.payer_ispb}{transfer.payer_branch}"
        f"{transfer.payer_account}{transfer.payer_tax_id}"
        f"{transfer.payer_party_type}{transfer.beneficiary_ispb}"
        f"{transfer.beneficiary_branch}{transfer.beneficiary_account}"
        f"{transfer.beneficiary_tax_id}"
        f"{transfer.beneficiary_party_type}"
        f"{_right_tilde_pad(transfer.purpose_code, width=10, contract=contract)}"
        f"{transfer.status_code}"
        f"{_right_tilde_pad(transfer.beneficiary_name, width=23, contract=contract)}"
    ).encode("ascii")
    if len(value) != contract.transfer_length:
        raise ValidationError("Type 04 transfer length drifted")
    return value


def encode_return(
    transfer: TedTransfer,
    *,
    contract: Type04Contract,
) -> bytes:
    returned = transfer.return_record
    if returned is None:
        raise ValidationError("Type 04 return record is unavailable")
    value = (
        f"R{returned.return_id}{transfer.transfer_id}-"
        f"{_money_magnitude(transfer.amount_minor)}"
        f"{returned.return_date}{returned.return_time}"
        f"{returned.reason_code}"
        f"{_right_tilde_pad(returned.reason_text, width=24, contract=contract)}"
    ).encode("ascii")
    if len(value) != contract.return_length:
        raise ValidationError("Type 04 return length drifted")
    return value


def encode_trailer(
    batch: TedTransferBatch,
    *,
    contract: Type04Contract,
    declared_net_amount_minor: int,
) -> bytes:
    returned_sign = "-" if batch.return_count else "+"
    returned_magnitude = abs(batch.return_amount_minor)
    value = (
        f"T{batch.file_date}{batch.transfer_count:06d}"
        f"{batch.return_count:06d}+"
        f"{_money_magnitude(batch.gross_amount_minor)}"
        f"{returned_sign}{_money_magnitude(returned_magnitude)}+"
        f"{_money_magnitude(declared_net_amount_minor)}{batch.batch_id}"
    ).encode("ascii")
    if len(value) != contract.trailer_length:
        raise ValidationError("Type 04 trailer length drifted")
    return value


def _render_batch(
    *,
    scenario: str,
    batch: TedTransferBatch,
    contract: Type04Contract,
    declared_net_amount_minor: int,
    expected_contract_status: str,
    expected_violation: str | None,
    inject_bare_lf: bool = False,
) -> Type04GeneratedBatch:
    _validate_batch(batch, contract=contract)
    records = [encode_header(batch, contract=contract)]
    for transfer in batch.transfers:
        records.append(encode_transfer(transfer, contract=contract))
        if transfer.return_record is not None:
            records.append(encode_return(transfer, contract=contract))
    records.append(
        encode_trailer(
            batch,
            contract=contract,
            declared_net_amount_minor=declared_net_amount_minor,
        )
    )
    if len(records) != batch.physical_record_count:
        raise ValidationError("Type 04 physical record controls drifted")
    if inject_bare_lf:
        raw_bytes = (
            records[0]
            + b"\n"
            + b"\r\n".join(records[1:])
            + b"\r\n"
        )
    else:
        raw_bytes = b"\r\n".join(records) + b"\r\n"
    if len(raw_bytes) > contract.max_source_file_bytes:
        raise ValidationError("Type 04 source transport size is invalid")
    return Type04GeneratedBatch(
        scenario=scenario,
        contract=contract,
        batch=batch,
        raw_bytes=raw_bytes,
        computed_transfer_count=batch.transfer_count,
        computed_return_count=batch.return_count,
        computed_gross_amount_minor=batch.gross_amount_minor,
        computed_return_amount_minor=batch.return_amount_minor,
        computed_net_amount_minor=batch.net_amount_minor,
        declared_transfer_count=batch.transfer_count,
        declared_return_count=batch.return_count,
        declared_gross_amount_minor=batch.gross_amount_minor,
        declared_return_amount_minor=batch.return_amount_minor,
        declared_net_amount_minor=declared_net_amount_minor,
        expected_contract_status=expected_contract_status,
        expected_violation=expected_violation,
    )


def render_valid_minimal(contract: Type04Contract) -> Type04GeneratedBatch:
    batch = valid_minimal_batch()
    return _render_batch(
        scenario=VALID_MINIMAL,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_valid_boundary(contract: Type04Contract) -> Type04GeneratedBatch:
    batch = valid_boundary_batch()
    return _render_batch(
        scenario=VALID_BOUNDARY,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_malformed(contract: Type04Contract) -> Type04GeneratedBatch:
    batch = malformed_batch()
    return _render_batch(
        scenario=MALFORMED,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="REJECTED",
        expected_violation="INVALID_TRANSPORT",
        inject_bare_lf=True,
    )


def render_all_returned_zero_net(
    contract: Type04Contract,
) -> Type04GeneratedBatch:
    batch = all_returned_zero_net_batch()
    return _render_batch(
        scenario=ALL_RETURNED_ZERO_NET,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_df_source_004(contract: Type04Contract) -> Type04GeneratedBatch:
    batch = df_source_004_batch()
    return _render_batch(
        scenario=DF_SOURCE_004,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=99_999,
        expected_contract_status="REJECTED",
        expected_violation="SOURCE_CONTROL_NET_MISMATCH",
    )


def render_scenario(
    scenario: str,
    *,
    contract: Type04Contract,
) -> Type04GeneratedBatch:
    """Dispatch one approved Type 04 scenario without fixture copying."""

    renderers = {
        VALID_MINIMAL: render_valid_minimal,
        VALID_BOUNDARY: render_valid_boundary,
        MALFORMED: render_malformed,
        ALL_RETURNED_ZERO_NET: render_all_returned_zero_net,
        DF_SOURCE_004: render_df_source_004,
    }
    renderer = renderers.get(scenario)
    if renderer is None:
        raise ValidationError(f"Unsupported Type 04 scenario: {scenario}")
    return renderer(contract)
