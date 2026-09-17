"""Deterministic Type 05 merchant-fee source-system simulator.

The renderer owns the strict semicolon grammar and exact positive ``HALF_UP``
calculation. Clear merchant CNPJs and descriptions stay out of representations
and metadata; generated raw bytes are the only artifact that contains them.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from models import (
    MerchantFeeAssessment,
    MerchantFeeBatch,
    Type05Contract,
    Type05GeneratedBatch,
    ValidationError,
    minor_units_to_string,
)


VALID_MINIMAL = "valid-minimal"
VALID_BOUNDARY = "valid-boundary"
MALFORMED = "malformed"
ROUNDING_HALF_UP = "rounding-half-up"
DF_SOURCE_005 = "DF-SOURCE-005"
SUPPORTED_SCENARIOS = (
    VALID_MINIMAL,
    VALID_BOUNDARY,
    MALFORMED,
    ROUNDING_HALF_UP,
    DF_SOURCE_005,
)

_BATCH_ID = re.compile(r"B[0-9]{15}")
_ASSESSMENT_ID = re.compile(r"FEE[0-9]{13}")
_MERCHANT_ID = re.compile(r"MER[0-9]{13}")
_FEE_CODE = re.compile(r"[A-Z][A-Z0-9_]{1,9}")
_DIGIT_RUN = re.compile(r"[0-9]{11}")
_BIDI_CONTROLS = frozenset(
    {
        "\u061c",
        "\u200e",
        "\u200f",
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",
        "\u2066",
        "\u2067",
        "\u2068",
        "\u2069",
    }
)


def _assessment(
    *,
    assessment_id: str,
    merchant_id: str,
    merchant_tax_id: str,
    fee_code: str,
    description: str,
    gross_amount_minor: int,
    rate_milli_percent: int,
    assessed_fee_minor: int,
    assessment_date: str,
) -> MerchantFeeAssessment:
    return MerchantFeeAssessment(
        assessment_id=assessment_id,
        merchant_id=merchant_id,
        merchant_tax_id=merchant_tax_id,
        fee_code=fee_code,
        description=description,
        gross_amount_minor=gross_amount_minor,
        rate_milli_percent=rate_milli_percent,
        assessed_fee_minor=assessed_fee_minor,
        assessment_date=assessment_date,
    )


def valid_minimal_batch() -> MerchantFeeBatch:
    """Return embedded delimiters, quotes, and accented NFC text."""

    return MerchantFeeBatch(
        file_date="20260723",
        batch_id="B202607230000401",
        assessments=(
            _assessment(
                assessment_id="FEE2026072304001",
                merchant_id="MER0000000000001",
                merchant_tax_id="12345678000195",
                fee_code="MDR",
                description='Tarifa "VIP"; julho, lote A',
                gross_amount_minor=100_000,
                rate_milli_percent=1_235,
                assessed_fee_minor=1_235,
                assessment_date="20260723",
            ),
            _assessment(
                assessment_id="FEE2026072304002",
                merchant_id="MER0000000000002",
                merchant_tax_id="98765432000198",
                fee_code="MIN",
                description="Arredondamento mínimo",
                gross_amount_minor=100,
                rate_milli_percent=500,
                assessed_fee_minor=1,
                assessment_date="20260723",
            ),
        ),
    )


def valid_boundary_batch() -> MerchantFeeBatch:
    """Return maximum money/rate/text widths on a leap-day boundary."""

    return MerchantFeeBatch(
        file_date="20000229",
        batch_id="B200002290000402",
        assessments=(
            _assessment(
                assessment_id="FEE2000022904003",
                merchant_id="MER9999999999999",
                merchant_tax_id="99999999999962",
                fee_code="MAX_BOUND",
                description="Á" * 80,
                gross_amount_minor=99_999_999_999_999,
                rate_milli_percent=100_000,
                assessed_fee_minor=99_999_999_999_999,
                assessment_date="20000229",
            ),
        ),
    )


def malformed_batch() -> MerchantFeeBatch:
    """Return a valid model whose mandatory description quotes are omitted."""

    return MerchantFeeBatch(
        file_date="20260723",
        batch_id="B202607230000403",
        assessments=(
            _assessment(
                assessment_id="FEE2026072304004",
                merchant_id="MER0000000000003",
                merchant_tax_id="11222333000181",
                fee_code="MDR",
                description="Tarifa sem aspas",
                gross_amount_minor=1_000,
                rate_milli_percent=1_000,
                assessed_fee_minor=10,
                assessment_date="20260723",
            ),
        ),
    )


def rounding_half_up_batch() -> MerchantFeeBatch:
    """Return two positive ties that must round away from zero."""

    return MerchantFeeBatch(
        file_date="20260723",
        batch_id="B202607230000404",
        assessments=(
            _assessment(
                assessment_id="FEE2026072304005",
                merchant_id="MER0000000000004",
                merchant_tax_id="12345678000195",
                fee_code="TIE_ONE",
                description="Empate positivo",
                gross_amount_minor=100,
                rate_milli_percent=500,
                assessed_fee_minor=1,
                assessment_date="20260723",
            ),
            _assessment(
                assessment_id="FEE2026072304006",
                merchant_id="MER0000000000005",
                merchant_tax_id="98765432000198",
                fee_code="TIE_TWO",
                description="Segundo empate",
                gross_amount_minor=250,
                rate_milli_percent=1_000,
                assessed_fee_minor=3,
                assessment_date="20260723",
            ),
        ),
    )


def df_source_005_batch() -> MerchantFeeBatch:
    """Return the valid row used for the source-manifest control defect."""

    return MerchantFeeBatch(
        file_date="20260723",
        batch_id="B202607230000405",
        assessments=(
            _assessment(
                assessment_id="FEE2026072304007",
                merchant_id="MER0000000000006",
                merchant_tax_id="11222333000181",
                fee_code="MDR",
                description="Controle da origem",
                gross_amount_minor=10_000,
                rate_milli_percent=1_000,
                assessed_fee_minor=100,
                assessment_date="20260723",
            ),
        ),
    )


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


def _valid_description(value: str) -> bool:
    return (
        unicodedata.normalize("NFC", value) == value
        and 1 <= len(value) <= 80
        and value[0] not in "=+-@"
        and _DIGIT_RUN.search(value) is None
        and all(
            not (
                ord(character) <= 0x1F
                or 0x7F <= ord(character) <= 0x9F
                or character in _BIDI_CONTROLS
            )
            for character in value
        )
    )


def _validate_contract(contract: Type05Contract) -> None:
    expected_header = (
        "assessment_id;batch_id;merchant_id;merchant_tax_id;fee_code;"
        "description;gross_amount_brl;rate_percent;assessed_fee_brl;"
        "assessment_date"
    )
    if (
        contract.contract_version != 1
        or contract.type_number != "05"
        or contract.code != "MER_FEESET05"
        or contract.layout_version != "001"
        or contract.encoding != "UTF-8"
        or contract.unicode_normalization != "NFC"
        or contract.line_ending != "LF"
        or contract.final_newline != "required"
        or contract.delimiter != ";"
        or contract.quote_character != '"'
        or contract.field_count != 10
        or contract.exact_header != expected_header
    ):
        raise ValidationError(
            "Type 05 generator received an unsupported contract"
        )


def _validate_batch(
    batch: MerchantFeeBatch,
    *,
    contract: Type05Contract,
) -> None:
    _validate_contract(contract)
    try:
        file_date = datetime.strptime(batch.file_date, "%Y%m%d").date()
    except ValueError as exc:
        raise ValidationError(
            "Type 05 batch date violates its contract"
        ) from exc
    if (
        _BATCH_ID.fullmatch(batch.batch_id) is None
        or batch.batch_id[1:9] != batch.file_date
        or re.fullmatch(contract.filename_pattern, batch.filename) is None
        or not 1 <= batch.row_count <= contract.max_detail_rows
    ):
        raise ValidationError("Type 05 batch identity or size is invalid")

    assessment_ids: set[str] = set()
    raw_cnpjs = tuple(row.merchant_tax_id for row in batch.assessments)
    for row in batch.assessments:
        try:
            assessment_date = datetime.strptime(
                row.assessment_date,
                "%Y%m%d",
            ).date()
        except ValueError as exc:
            raise ValidationError(
                "Type 05 assessment date violates its contract"
            ) from exc
        safe_values = (
            row.assessment_id,
            row.merchant_id,
            row.fee_code,
            row.description,
        )
        if (
            _ASSESSMENT_ID.fullmatch(row.assessment_id) is None
            or row.assessment_id in assessment_ids
            or _MERCHANT_ID.fullmatch(row.merchant_id) is None
            or not _valid_cnpj(row.merchant_tax_id)
            or _FEE_CODE.fullmatch(row.fee_code) is None
            or not _valid_description(row.description)
            or any(
                cnpj in safe_value
                for safe_value in safe_values
                for cnpj in raw_cnpjs
            )
            or type(row.gross_amount_minor) is not int
            or not 1 <= row.gross_amount_minor <= 99_999_999_999_999
            or type(row.rate_milli_percent) is not int
            or not 1 <= row.rate_milli_percent <= 100_000
            or type(row.assessed_fee_minor) is not int
            or not 0 <= row.assessed_fee_minor <= 99_999_999_999_999
            or row.assessed_fee_minor != row.calculated_fee_minor
            or assessment_date != file_date
        ):
            raise ValidationError(
                "Type 05 assessment violates its field contract"
            )
        assessment_ids.add(row.assessment_id)


def _locale_money(amount_minor: int) -> str:
    return minor_units_to_string(amount_minor).replace(".", ",")


def _locale_rate(rate_milli_percent: int) -> str:
    return f"{rate_milli_percent // 1000},{rate_milli_percent % 1000:03d}"


def _localized_date(date_value: str) -> str:
    parsed = datetime.strptime(date_value, "%Y%m%d")
    return parsed.strftime("%d/%m/%Y")


def encode_assessment(
    row: MerchantFeeAssessment,
    *,
    batch_id: str,
    contract: Type05Contract,
    quote_description: bool = True,
) -> bytes:
    """Encode one validated Type 05 detail under the strict source grammar."""

    escaped = row.description.replace('"', '""')
    description = (
        f'{contract.quote_character}{escaped}{contract.quote_character}'
        if quote_description
        else escaped
    )
    fields = (
        row.assessment_id,
        batch_id,
        row.merchant_id,
        row.merchant_tax_id,
        row.fee_code,
        description,
        _locale_money(row.gross_amount_minor),
        _locale_rate(row.rate_milli_percent),
        _locale_money(row.assessed_fee_minor),
        _localized_date(row.assessment_date),
    )
    value = contract.delimiter.join(fields).encode("utf-8")
    if len(value) > contract.max_physical_record_bytes:
        raise ValidationError("Type 05 physical record exceeds its byte bound")
    return value


def _render_batch(
    *,
    scenario: str,
    batch: MerchantFeeBatch,
    contract: Type05Contract,
    declared_assessed_fee_minor: int,
    expected_contract_status: str,
    expected_violation: str | None,
    quote_description: bool = True,
) -> Type05GeneratedBatch:
    _validate_batch(batch, contract=contract)
    records = [contract.exact_header.encode("utf-8")]
    records.extend(
        encode_assessment(
            row,
            batch_id=batch.batch_id,
            contract=contract,
            quote_description=quote_description,
        )
        for row in batch.assessments
    )
    if any(
        len(record) > contract.max_physical_record_bytes
        for record in records
    ):
        raise ValidationError("Type 05 physical record exceeds its byte bound")
    raw_bytes = b"\n".join(records) + b"\n"
    if len(raw_bytes) > contract.max_source_file_bytes:
        raise ValidationError("Type 05 source transport size is invalid")
    return Type05GeneratedBatch(
        scenario=scenario,
        contract=contract,
        batch=batch,
        raw_bytes=raw_bytes,
        computed_row_count=batch.row_count,
        computed_gross_amount_minor=batch.gross_amount_minor,
        computed_assessed_fee_minor=batch.assessed_fee_minor,
        computed_calculated_fee_minor=batch.calculated_fee_minor,
        declared_row_count=batch.row_count,
        declared_gross_amount_minor=batch.gross_amount_minor,
        declared_assessed_fee_minor=declared_assessed_fee_minor,
        declared_calculated_fee_minor=batch.calculated_fee_minor,
        expected_contract_status=expected_contract_status,
        expected_violation=expected_violation,
    )


def render_valid_minimal(contract: Type05Contract) -> Type05GeneratedBatch:
    batch = valid_minimal_batch()
    return _render_batch(
        scenario=VALID_MINIMAL,
        batch=batch,
        contract=contract,
        declared_assessed_fee_minor=batch.assessed_fee_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_valid_boundary(contract: Type05Contract) -> Type05GeneratedBatch:
    batch = valid_boundary_batch()
    return _render_batch(
        scenario=VALID_BOUNDARY,
        batch=batch,
        contract=contract,
        declared_assessed_fee_minor=batch.assessed_fee_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_malformed(contract: Type05Contract) -> Type05GeneratedBatch:
    batch = malformed_batch()
    return _render_batch(
        scenario=MALFORMED,
        batch=batch,
        contract=contract,
        declared_assessed_fee_minor=batch.assessed_fee_minor,
        expected_contract_status="REJECTED",
        expected_violation="INVALID_CSV_QUOTING",
        quote_description=False,
    )


def render_rounding_half_up(contract: Type05Contract) -> Type05GeneratedBatch:
    batch = rounding_half_up_batch()
    return _render_batch(
        scenario=ROUNDING_HALF_UP,
        batch=batch,
        contract=contract,
        declared_assessed_fee_minor=batch.assessed_fee_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_df_source_005(contract: Type05Contract) -> Type05GeneratedBatch:
    batch = df_source_005_batch()
    return _render_batch(
        scenario=DF_SOURCE_005,
        batch=batch,
        contract=contract,
        declared_assessed_fee_minor=99,
        expected_contract_status="REJECTED",
        expected_violation="SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
    )


def render_scenario(
    scenario: str,
    *,
    contract: Type05Contract,
) -> Type05GeneratedBatch:
    """Dispatch one approved Type 05 scenario without fixture copying."""

    renderers = {
        VALID_MINIMAL: render_valid_minimal,
        VALID_BOUNDARY: render_valid_boundary,
        MALFORMED: render_malformed,
        ROUNDING_HALF_UP: render_rounding_half_up,
        DF_SOURCE_005: render_df_source_005,
    }
    renderer = renderers.get(scenario)
    if renderer is None:
        raise ValidationError(f"Unsupported Type 05 scenario: {scenario}")
    return renderer(contract)
