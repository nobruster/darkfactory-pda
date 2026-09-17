"""Deterministic Type 02 instant-payment source-system simulator.

The renderer builds every canonical byte from frozen typed scenario data. It
does not read or copy canonical fixtures. Monetary controls use integer BRL
minor units, and restricted source documents and descriptions never appear in
validation messages or dataclass representations.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from zoneinfo import ZoneInfo

from models import (
    InstantPaymentBatch,
    InstantPaymentEvent,
    Type02Contract,
    Type02GeneratedBatch,
    ValidationError,
    minor_units_to_string,
)


VALID_MINIMAL = "valid-minimal"
VALID_BOUNDARY = "valid-boundary"
ESCAPED_CONTENT = "escaped-content"
MALFORMED = "malformed"
DF_SOURCE_002 = "DF-SOURCE-002"

SUPPORTED_SCENARIOS = (
    VALID_MINIMAL,
    VALID_BOUNDARY,
    ESCAPED_CONTENT,
    MALFORMED,
    DF_SOURCE_002,
)

_BATCH_ID_PATTERN = re.compile(r"B[0-9]{15}")
_END_TO_END_ID_PATTERN = re.compile(r"E[0-9]{31}")
_TRANSACTION_ID_PATTERN = re.compile(r"(?=.*[A-Z])[A-Z0-9]{16}")
_RETURN_CODE_PATTERN = re.compile(r"[A-Z0-9]{0,4}")
_TIMESTAMP_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:Z|[+-][0-9]{2}:[0-9]{2})"
)
_SENSITIVE_DIGIT_RUN = re.compile(r"[0-9]{11,19}")
_SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def valid_minimal_batch() -> InstantPaymentBatch:
    """Return the canonical two-event Type 02 happy-path batch."""

    return InstantPaymentBatch(
        file_date="20260723",
        batch_id="B202607230000101",
        events=(
            InstantPaymentEvent(
                end_to_end_id="E2026072300000000000000000000001",
                transaction_id="PIXTXN0000000001",
                payer_document_type="CPF",
                payer_document="12345678909",
                payee_document_type="CNPJ",
                payee_document="12345678000195",
                event_timestamp="2026-07-23T09:00:00-03:00",
                amount_minor=20_000,
                direction="C",
                status="SETTLED",
                return_code="",
                description="Invoice 1001",
            ),
            InstantPaymentEvent(
                end_to_end_id="E2026072300000000000000000000002",
                transaction_id="PIXTXN0000000002",
                payer_document_type="CNPJ",
                payer_document="98765432000198",
                payee_document_type="CPF",
                payee_document="11144477735",
                event_timestamp="2026-07-23T10:00:00-03:00",
                amount_minor=2_655,
                direction="D",
                status="RETURNED",
                return_code="AC03",
                description="Return|beneficiary",
            ),
        ),
    )


def valid_boundary_batch() -> InstantPaymentBatch:
    """Return the canonical leap-day, UTC, one-cent boundary batch."""

    return InstantPaymentBatch(
        file_date="20240229",
        batch_id="B202402290000102",
        events=(
            InstantPaymentEvent(
                end_to_end_id="E2024022900000000000000000000001",
                transaction_id="PIXTXN9999999999",
                payer_document_type="CNPJ",
                payer_document="12345678000195",
                payee_document_type="CPF",
                payee_document="11144477735",
                event_timestamp="2024-02-29T23:59:59Z",
                amount_minor=1,
                direction="C",
                status="SETTLED",
                return_code="",
                description="Cafe",
            ),
        ),
    )


def escaped_content_batch() -> InstantPaymentBatch:
    """Return the UTF-8 scenario containing escaped delimiter and backslash."""

    return InstantPaymentBatch(
        file_date="20260723",
        batch_id="B202607230000104",
        events=(
            InstantPaymentEvent(
                end_to_end_id="E2026072300000000000000000000004",
                transaction_id="PIXTXN0000000004",
                payer_document_type="CPF",
                payer_document="12345678909",
                payee_document_type="CNPJ",
                payee_document="12345678000195",
                event_timestamp="2026-07-23T12:00:00-03:00",
                amount_minor=123,
                direction="C",
                status="SETTLED",
                return_code="",
                description="Café, invoice | folder \\2026",
            ),
        ),
    )


def malformed_batch() -> InstantPaymentBatch:
    """Return valid typed data whose renderer injects one unescaped delimiter."""

    return InstantPaymentBatch(
        file_date="20260723",
        batch_id="B202607230000103",
        events=(
            InstantPaymentEvent(
                end_to_end_id="E2026072300000000000000000000003",
                transaction_id="PIXTXN0000000003",
                payer_document_type="CPF",
                payer_document="12345678909",
                payee_document_type="CNPJ",
                payee_document="12345678000195",
                event_timestamp="2026-07-23T11:00:00-03:00",
                amount_minor=1_000,
                direction="D",
                status="RETURNED",
                return_code="AC03",
                description="Unescaped|delimiter",
            ),
        ),
    )


def df_source_002_batch() -> InstantPaymentBatch:
    """Return the Dark Factory batch before its trailer defect is injected."""

    canonical = valid_minimal_batch()
    events = (
        InstantPaymentEvent(
            end_to_end_id="E2026072300000000000000000000005",
            transaction_id="PIXTXN0000000005",
            payer_document_type=canonical.events[0].payer_document_type,
            payer_document=canonical.events[0].payer_document,
            payee_document_type=canonical.events[0].payee_document_type,
            payee_document=canonical.events[0].payee_document,
            event_timestamp=canonical.events[0].event_timestamp,
            amount_minor=canonical.events[0].amount_minor,
            direction=canonical.events[0].direction,
            status=canonical.events[0].status,
            return_code=canonical.events[0].return_code,
            description="Invoice 1005",
        ),
        InstantPaymentEvent(
            end_to_end_id="E2026072300000000000000000000006",
            transaction_id="PIXTXN0000000006",
            payer_document_type=canonical.events[1].payer_document_type,
            payer_document=canonical.events[1].payer_document,
            payee_document_type=canonical.events[1].payee_document_type,
            payee_document=canonical.events[1].payee_document,
            event_timestamp=canonical.events[1].event_timestamp,
            amount_minor=canonical.events[1].amount_minor,
            direction=canonical.events[1].direction,
            status=canonical.events[1].status,
            return_code=canonical.events[1].return_code,
            description=canonical.events[1].description,
        ),
    )
    return InstantPaymentBatch(
        file_date=canonical.file_date,
        batch_id="B202607230000105",
        events=events,
    )


def _mod11_digit(digits: str, weights: tuple[int, ...]) -> str:
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights))
    remainder = total % 11
    result = 0 if remainder < 2 else 11 - remainder
    return str(result)


def _valid_cpf(value: str) -> bool:
    if re.fullmatch(r"[0-9]{11}", value) is None or len(set(value)) == 1:
        return False
    first = _mod11_digit(value[:9], tuple(range(10, 1, -1)))
    second = _mod11_digit(value[:9] + first, tuple(range(11, 1, -1)))
    return value[-2:] == first + second


def _valid_cnpj(value: str) -> bool:
    if re.fullmatch(r"[0-9]{14}", value) is None or len(set(value)) == 1:
        return False
    first_weights = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    second_weights = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    first = _mod11_digit(value[:12], first_weights)
    second = _mod11_digit(value[:12] + first, second_weights)
    return value[-2:] == first + second


def _validate_document(document_type: str, value: str, *, field_name: str) -> None:
    valid = (
        _valid_cpf(value)
        if document_type == "CPF"
        else _valid_cnpj(value)
        if document_type == "CNPJ"
        else False
    )
    if not valid:
        raise ValidationError(
            f"Document does not satisfy its declared type: {field_name}"
        )


def _validate_description(event: InstantPaymentEvent) -> None:
    value = event.description
    if not 1 <= len(value) <= 80:
        raise ValidationError("Description length violates the Type 02 contract")
    if unicodedata.normalize("NFC", value) != value:
        raise ValidationError("Description is not NFC-normalized")
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise ValidationError("Description contains a forbidden control character")
    if value[0] in "=+-@":
        raise ValidationError("Description has a forbidden formula prefix")
    if _SENSITIVE_DIGIT_RUN.search(value) is not None:
        raise ValidationError("Description contains a forbidden digit run")
    if event.payer_document in value or event.payee_document in value:
        raise ValidationError("Description contains a restricted document")


def _validate_event(event: InstantPaymentEvent, *, file_date: str) -> None:
    if _END_TO_END_ID_PATTERN.fullmatch(event.end_to_end_id) is None:
        raise ValidationError("End-to-end ID violates the Type 02 contract")
    if _TRANSACTION_ID_PATTERN.fullmatch(event.transaction_id) is None:
        raise ValidationError("Transaction ID violates the Type 02 contract")
    _validate_document(
        event.payer_document_type,
        event.payer_document,
        field_name="payer_document",
    )
    _validate_document(
        event.payee_document_type,
        event.payee_document,
        field_name="payee_document",
    )
    if _TIMESTAMP_PATTERN.fullmatch(event.event_timestamp) is None:
        raise ValidationError("Timestamp violates the Type 02 lexical contract")
    if event.event_timestamp.endswith(("+00:00", "-00:00")):
        raise ValidationError("Zero-offset timestamp must use Z")
    try:
        parsed_timestamp = datetime.fromisoformat(
            event.event_timestamp.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValidationError("Timestamp is not a valid offset datetime") from exc
    if parsed_timestamp.astimezone(_SAO_PAULO).strftime("%Y%m%d") != file_date:
        raise ValidationError("Timestamp does not map to the Type 02 file date")
    if not 1 <= event.amount_minor <= 999_999_999_999_999_999:
        raise ValidationError("Amount violates the Type 02 precision contract")
    if event.direction not in {"C", "D"}:
        raise ValidationError("Direction violates the Type 02 contract")
    if event.status == "SETTLED" and event.return_code:
        raise ValidationError("Settled event cannot have a return code")
    if event.status == "RETURNED" and not event.return_code:
        raise ValidationError("Returned event requires a return code")
    if event.status not in {"SETTLED", "RETURNED"}:
        raise ValidationError("Status violates the Type 02 contract")
    if _RETURN_CODE_PATTERN.fullmatch(event.return_code) is None:
        raise ValidationError("Return code violates the Type 02 contract")
    _validate_description(event)


def _validate_batch(
    batch: InstantPaymentBatch,
    *,
    contract: Type02Contract,
) -> None:
    if (
        contract.type_number != "02"
        or contract.code != "PIX_EVENTS01"
        or contract.layout_version != "001"
    ):
        raise ValidationError("Type 02 generator received another contract")
    if (
        contract.encoding != "UTF-8"
        or contract.line_ending != "LF"
        or contract.final_newline != "required"
        or contract.delimiter != "|"
        or contract.escape_character != "\\"
        or (
            contract.header_field_count,
            contract.event_field_count,
            contract.trailer_field_count,
        )
        != (5, 13, 5)
    ):
        raise ValidationError(
            "Type 02 generator supports only its approved transport and grammar"
        )
    try:
        date.fromisoformat(
            f"{batch.file_date[:4]}-"
            f"{batch.file_date[4:6]}-"
            f"{batch.file_date[6:]}"
        )
    except ValueError as exc:
        raise ValidationError("Type 02 file date is invalid") from exc
    if _BATCH_ID_PATTERN.fullmatch(batch.batch_id) is None:
        raise ValidationError("Type 02 batch ID is invalid")
    if batch.batch_id[1:9] != batch.file_date:
        raise ValidationError("Type 02 batch ID date does not match the file date")
    if re.fullmatch(contract.filename_pattern, batch.filename) is None:
        raise ValidationError("Generated filename violates the Type 02 contract")
    if not 1 <= batch.event_count <= 10_000:
        raise ValidationError("Type 02 batch event count is outside its limits")

    for event in batch.events:
        _validate_event(event, file_date=batch.file_date)
    end_to_end_ids = [event.end_to_end_id for event in batch.events]
    transaction_ids = [event.transaction_id for event in batch.events]
    if len(set(end_to_end_ids)) != len(end_to_end_ids):
        raise ValidationError("Duplicate end-to-end ID in Type 02 batch")
    if len(set(transaction_ids)) != len(transaction_ids):
        raise ValidationError("Duplicate transaction ID in Type 02 batch")


def escape_field(value: str, *, contract: Type02Contract) -> str:
    """Escape a Type 02 field exactly once for the approved lexer."""

    return value.replace(
        contract.escape_character,
        contract.escape_character * 2,
    ).replace(
        contract.delimiter,
        contract.escape_character + contract.delimiter,
    )


def encode_header(
    batch: InstantPaymentBatch,
    *,
    contract: Type02Contract,
) -> bytes:
    """Encode one canonical Type 02 header record."""

    fields = (
        "H",
        contract.code,
        contract.layout_version,
        batch.file_date,
        batch.batch_id,
    )
    return contract.delimiter.join(fields).encode(contract.encoding)


def encode_event(
    event: InstantPaymentEvent,
    *,
    contract: Type02Contract,
    escape_description: bool = True,
) -> bytes:
    """Encode one Type 02 event, optionally injecting the named field defect."""

    description = (
        escape_field(event.description, contract=contract)
        if escape_description
        else event.description
    )
    fields = (
        "D",
        event.end_to_end_id,
        event.transaction_id,
        event.payer_document_type,
        event.payer_document,
        event.payee_document_type,
        event.payee_document,
        event.event_timestamp,
        minor_units_to_string(event.amount_minor),
        event.direction,
        event.status,
        event.return_code,
        description,
    )
    return contract.delimiter.join(fields).encode(contract.encoding)


def encode_trailer(
    batch: InstantPaymentBatch,
    *,
    contract: Type02Contract,
    declared_event_count: int,
    declared_credit_amount_minor: int,
    declared_debit_amount_minor: int,
    declared_net_amount_minor: int,
) -> bytes:
    """Encode one Type 02 trailer from explicit source-declared controls."""

    fields = (
        "T",
        str(declared_event_count),
        minor_units_to_string(declared_credit_amount_minor),
        minor_units_to_string(declared_debit_amount_minor),
        minor_units_to_string(declared_net_amount_minor),
    )
    return contract.delimiter.join(fields).encode(contract.encoding)


def _render_batch(
    *,
    scenario: str,
    batch: InstantPaymentBatch,
    contract: Type02Contract,
    declared_net_amount_minor: int,
    expected_contract_status: str,
    expected_violation: str | None,
    inject_unescaped_description: bool = False,
) -> Type02GeneratedBatch:
    _validate_batch(batch, contract=contract)
    records = [
        encode_header(batch, contract=contract),
        *(
            encode_event(
                event,
                contract=contract,
                escape_description=not (
                    inject_unescaped_description and index == 0
                ),
            )
            for index, event in enumerate(batch.events)
        ),
        encode_trailer(
            batch,
            contract=contract,
            declared_event_count=batch.event_count,
            declared_credit_amount_minor=batch.credit_amount_minor,
            declared_debit_amount_minor=batch.debit_amount_minor,
            declared_net_amount_minor=declared_net_amount_minor,
        ),
    ]
    if any(len(record) > contract.max_record_bytes for record in records):
        raise ValidationError("Generated Type 02 record exceeds its byte limit")
    raw_bytes = b"\n".join(records) + b"\n"
    if len(raw_bytes) > contract.max_source_file_bytes:
        raise ValidationError("Generated Type 02 file exceeds its byte limit")

    return Type02GeneratedBatch(
        scenario=scenario,
        contract=contract,
        batch=batch,
        raw_bytes=raw_bytes,
        computed_event_count=batch.event_count,
        computed_credit_amount_minor=batch.credit_amount_minor,
        computed_debit_amount_minor=batch.debit_amount_minor,
        computed_net_amount_minor=batch.net_amount_minor,
        declared_event_count=batch.event_count,
        declared_credit_amount_minor=batch.credit_amount_minor,
        declared_debit_amount_minor=batch.debit_amount_minor,
        declared_net_amount_minor=declared_net_amount_minor,
        expected_contract_status=expected_contract_status,
        expected_violation=expected_violation,
    )


def render_valid_minimal(contract: Type02Contract) -> Type02GeneratedBatch:
    """Render the canonical Type 02 minimal accepted scenario."""

    batch = valid_minimal_batch()
    return _render_batch(
        scenario=VALID_MINIMAL,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_valid_boundary(contract: Type02Contract) -> Type02GeneratedBatch:
    """Render the canonical Type 02 boundary accepted scenario."""

    batch = valid_boundary_batch()
    return _render_batch(
        scenario=VALID_BOUNDARY,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_escaped_content(contract: Type02Contract) -> Type02GeneratedBatch:
    """Render the canonical Type 02 UTF-8 and escaping scenario."""

    batch = escaped_content_batch()
    return _render_batch(
        scenario=ESCAPED_CONTENT,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_malformed(contract: Type02Contract) -> Type02GeneratedBatch:
    """Render the one-defect invalid-field-count Type 02 scenario."""

    batch = malformed_batch()
    return _render_batch(
        scenario=MALFORMED,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="REJECTED",
        expected_violation="INVALID_FIELD_COUNT",
        inject_unescaped_description=True,
    )


def render_df_source_002(contract: Type02Contract) -> Type02GeneratedBatch:
    """Render the Type 02 source-system net-control Dark Factory defect."""

    batch = df_source_002_batch()
    return _render_batch(
        scenario=DF_SOURCE_002,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=17_344,
        expected_contract_status="REJECTED",
        expected_violation="SOURCE_CONTROL_NET_MISMATCH",
    )


def render_scenario(
    scenario: str,
    *,
    contract: Type02Contract,
) -> Type02GeneratedBatch:
    """Dispatch one approved Type 02 scenario without fixture copying."""

    renderers = {
        VALID_MINIMAL: render_valid_minimal,
        VALID_BOUNDARY: render_valid_boundary,
        ESCAPED_CONTENT: render_escaped_content,
        MALFORMED: render_malformed,
        DF_SOURCE_002: render_df_source_002,
    }
    renderer = renderers.get(scenario)
    if renderer is None:
        raise ValidationError(f"Unsupported Type 02 scenario: {scenario}")
    return renderer(contract)
