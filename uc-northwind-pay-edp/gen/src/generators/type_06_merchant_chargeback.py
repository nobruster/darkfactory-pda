"""Deterministic Type 06 merchant-chargeback source-system simulator.

Contract calculation is exact HALF_UP. The live Java plant may MATCHED a
different cent; that is a legacy defect, not a DataGen concern.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from models import (
    MerchantChargeback,
    MerchantChargebackBatch,
    Type06Contract,
    Type06GeneratedBatch,
    ValidationError,
    minor_units_to_string,
)

VALID_MINIMAL = "valid-minimal"
VALID_BOUNDARY = "valid-boundary"
MALFORMED = "malformed"
LEGACY_MISS = "legacy-miss"
SUPPORTED_SCENARIOS = (
    VALID_MINIMAL,
    VALID_BOUNDARY,
    MALFORMED,
    LEGACY_MISS,
)

_BATCH_ID = re.compile(r"B[0-9]{15}")
_CHARGEBACK_ID = re.compile(r"CBK[0-9]{13}")
_MERCHANT_ID = re.compile(r"MER[0-9]{13}")
_REASON_CODE = re.compile(r"[A-Z][A-Z0-9_]{1,9}")
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


def _row(
    *,
    chargeback_id: str,
    merchant_id: str,
    merchant_tax_id: str,
    reason_code: str,
    description: str,
    original_amount_minor: int,
    rate_milli_percent: int,
    chargeback_amount_minor: int,
    business_date: str,
) -> MerchantChargeback:
    return MerchantChargeback(
        chargeback_id=chargeback_id,
        merchant_id=merchant_id,
        merchant_tax_id=merchant_tax_id,
        reason_code=reason_code,
        description=description,
        original_amount_minor=original_amount_minor,
        rate_milli_percent=rate_milli_percent,
        chargeback_amount_minor=chargeback_amount_minor,
        business_date=business_date,
    )


def valid_minimal_batch() -> MerchantChargebackBatch:
    """67.00 at 1.500% = 1.005 → HALF_UP 1.01."""

    return MerchantChargebackBatch(
        file_date="20260723",
        batch_id="B202607230000501",
        rows=(
            _row(
                chargeback_id="CBK2026072305001",
                merchant_id="MER0000000000001",
                merchant_tax_id="12345678000195",
                reason_code="FRAUD",
                description="Ajuste de chargeback",
                original_amount_minor=6700,
                rate_milli_percent=1500,
                chargeback_amount_minor=101,
                business_date="20260723",
            ),
        ),
    )


def valid_boundary_batch() -> MerchantChargebackBatch:
    """Leap day, exact 2.00 * 1.000% = 0.02."""

    return MerchantChargebackBatch(
        file_date="20000229",
        batch_id="B200002290000502",
        rows=(
            _row(
                chargeback_id="CBK2000022905002",
                merchant_id="MER0000000000002",
                merchant_tax_id="98765432000198",
                reason_code="MIN",
                description="Limite inferior",
                original_amount_minor=200,
                rate_milli_percent=1000,
                chargeback_amount_minor=2,
                business_date="20000229",
            ),
        ),
    )


def malformed_batch() -> MerchantChargebackBatch:
    return MerchantChargebackBatch(
        file_date="20260723",
        batch_id="B202607230000503",
        rows=(
            _row(
                chargeback_id="CBK2026072305003",
                merchant_id="MER0000000000003",
                merchant_tax_id="11222333000181",
                reason_code="FRAUD",
                description="bad;unquoted",
                original_amount_minor=1000,
                rate_milli_percent=1000,
                chargeback_amount_minor=10,
                business_date="20260723",
            ),
        ),
    )


def legacy_miss_batch() -> MerchantChargebackBatch:
    """Same HALF_UP steel thread, separate batch id."""

    return MerchantChargebackBatch(
        file_date="20260723",
        batch_id="B202607230000504",
        rows=(
            _row(
                chargeback_id="CBK2026072305004",
                merchant_id="MER0000000000004",
                merchant_tax_id="12345678000195",
                reason_code="FRAUD",
                description="Mesmo arredondamento HALF_UP",
                original_amount_minor=6700,
                rate_milli_percent=1500,
                chargeback_amount_minor=101,
                business_date="20260723",
            ),
        ),
    )


def _valid_cnpj(value: str) -> bool:
    if re.fullmatch(r"[0-9]{14}", value) is None or len(set(value)) == 1:
        return False
    numbers = [int(character) for character in value]
    first_weights = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    first_remainder = sum(
        digit * weight for digit, weight in zip(numbers[:12], first_weights)
    ) % 11
    first = 0 if first_remainder < 2 else 11 - first_remainder
    second_weights = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    second_remainder = sum(
        digit * weight
        for digit, weight in zip(numbers[:12] + [first], second_weights)
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


def _validate_contract(contract: Type06Contract) -> None:
    expected_header = (
        "chargeback_id;batch_id;merchant_id;merchant_tax_id;reason_code;"
        "description;original_amount_brl;rate_percent;chargeback_amount_brl;"
        "business_date"
    )
    if (
        contract.contract_version != 1
        or contract.type_number != "06"
        or contract.code != "MER_CHGBK06"
        or contract.layout_version != "001"
        or contract.encoding != "UTF-8"
        or contract.delimiter != ";"
        or contract.field_count != 10
        or contract.exact_header != expected_header
    ):
        raise ValidationError("Type 06 generator received an unsupported contract")


def encode_row(
    row: MerchantChargeback,
    *,
    batch_id: str,
    contract: Type06Contract,
    quote_description: bool = True,
) -> bytes:
    escaped = row.description.replace('"', '""')
    description = (
        f"{contract.quote_character}{escaped}{contract.quote_character}"
        if quote_description
        else escaped
    )
    money = lambda minor: minor_units_to_string(minor).replace(".", ",")
    rate = f"{row.rate_milli_percent // 1000},{row.rate_milli_percent % 1000:03d}"
    date = datetime.strptime(row.business_date, "%Y%m%d").strftime("%d/%m/%Y")
    fields = (
        row.chargeback_id,
        batch_id,
        row.merchant_id,
        row.merchant_tax_id,
        row.reason_code,
        description,
        money(row.original_amount_minor),
        rate,
        money(row.chargeback_amount_minor),
        date,
    )
    return contract.delimiter.join(fields).encode("utf-8")


def _render_batch(
    *,
    scenario: str,
    batch: MerchantChargebackBatch,
    contract: Type06Contract,
    quote_description: bool = True,
    expected_violation: str | None = None,
) -> Type06GeneratedBatch:
    _validate_contract(contract)
    records = [contract.exact_header.encode("utf-8")]
    records.extend(
        encode_row(
            row,
            batch_id=batch.batch_id,
            contract=contract,
            quote_description=quote_description,
        )
        for row in batch.rows
    )
    raw_bytes = b"\n".join(records) + b"\n"
    return Type06GeneratedBatch(
        scenario=scenario,
        contract=contract,
        batch=batch,
        raw_bytes=raw_bytes,
        computed_row_count=batch.row_count,
        computed_original_amount_minor=batch.original_amount_minor,
        computed_chargeback_amount_minor=batch.chargeback_amount_minor,
        computed_calculated_amount_minor=batch.calculated_amount_minor,
        declared_row_count=batch.row_count,
        declared_original_amount_minor=batch.original_amount_minor,
        declared_chargeback_amount_minor=batch.chargeback_amount_minor,
        declared_calculated_amount_minor=batch.calculated_amount_minor,
        expected_contract_status=(
            "REJECTED" if expected_violation else "ACCEPTED"
        ),
        expected_violation=expected_violation,
    )


def render_scenario(
    scenario: str,
    *,
    contract: Type06Contract,
) -> Type06GeneratedBatch:
    if scenario == VALID_MINIMAL:
        return _render_batch(
            scenario=scenario, batch=valid_minimal_batch(), contract=contract
        )
    if scenario == VALID_BOUNDARY:
        return _render_batch(
            scenario=scenario, batch=valid_boundary_batch(), contract=contract
        )
    if scenario == MALFORMED:
        return _render_batch(
            scenario=scenario,
            batch=malformed_batch(),
            contract=contract,
            quote_description=False,
            expected_violation="INVALID_CSV_QUOTING",
        )
    if scenario == LEGACY_MISS:
        return _render_batch(
            scenario=scenario, batch=legacy_miss_batch(), contract=contract
        )
    raise ValidationError(f"Unsupported Type 06 scenario: {scenario}")
