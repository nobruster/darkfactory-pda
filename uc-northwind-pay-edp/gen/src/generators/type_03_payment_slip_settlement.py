"""Deterministic Type 03 payment-slip source-system simulator.

The renderer creates every fixed-width byte from frozen typed data. Restricted
payment references, beneficiaries, tax IDs, and accounts are redacted from
representations and never included in validation failures or metadata.
"""

from __future__ import annotations

import re
from datetime import datetime

from models import (
    PaymentSlipBatch,
    PaymentSlipLot,
    PaymentSlipSettlement,
    Type03Contract,
    Type03GeneratedBatch,
    ValidationError,
)


VALID_MINIMAL = "valid-minimal"
VALID_BOUNDARY = "valid-boundary"
MALFORMED = "malformed"
MULTI_LOT = "multi-lot"
DF_SOURCE_003 = "DF-SOURCE-003"
SUPPORTED_SCENARIOS = (
    VALID_MINIMAL,
    VALID_BOUNDARY,
    MALFORMED,
    MULTI_LOT,
    DF_SOURCE_003,
)

_BATCH_ID = re.compile(r"B[0-9]{15}")
_SIX_DIGITS = re.compile(r"(?!000000)[0-9]{6}")
_SETTLEMENT_ID = re.compile(r"[A-Z][A-Z0-9]{15}")
_REFERENCE = re.compile(r"[A-Z][A-Z0-9]{19}")
_ORIGINATOR = re.compile(r"[A-Z][A-Z0-9]{15}")
_PAYMENT_REFERENCE = re.compile(r"[0-9]{48}")
_BENEFICIARY_NAME = re.compile(r"[A-Z][A-Z0-9 .&/-]{0,39}")
_BANK_CODE = re.compile(r"(?!000)[0-9]{3}")
_BRANCH = re.compile(r"[0-9]{5}")
_ACCOUNT = re.compile(r"[0-9]{12}")
_CHECK_DIGIT = re.compile(r"[A-Z0-9]")


def _settlement(
    *,
    sequence: str,
    settlement_id: str,
    payment_reference: str,
    face_amount_minor: int,
    due_date: str,
    payment_date: str,
    discount_minor: int,
    fee_minor: int,
    bank_reference: str,
    tax_id_type: str,
    beneficiary_tax_id: str,
    beneficiary_name: str,
    bank_code: str,
    branch_number: str,
    account_number: str,
    account_check_digit: str,
    client_reference: str,
) -> PaymentSlipSettlement:
    return PaymentSlipSettlement(
        sequence=sequence,
        settlement_id=settlement_id,
        payment_reference=payment_reference,
        face_amount_minor=face_amount_minor,
        due_date=due_date,
        payment_date=payment_date,
        discount_minor=discount_minor,
        fee_minor=fee_minor,
        bank_reference=bank_reference,
        tax_id_type=tax_id_type,
        beneficiary_tax_id=beneficiary_tax_id,
        beneficiary_name=beneficiary_name,
        bank_code=bank_code,
        branch_number=branch_number,
        account_number=account_number,
        account_check_digit=account_check_digit,
        client_reference=client_reference,
    )


def valid_minimal_batch() -> PaymentSlipBatch:
    """Return the canonical two-settlement Type 03 batch."""

    return PaymentSlipBatch(
        file_date="20260723",
        batch_id="B202607230000201",
        lots=(
            PaymentSlipLot(
                lot_number="000001",
                settlement_date="20260723",
                originator_id="NWPORIGIN0000001",
                settlements=(
                    _settlement(
                        sequence="000001",
                        settlement_id="PSL0000000000001",
                        payment_reference="1" * 48,
                        face_amount_minor=15_000,
                        due_date="20260730",
                        payment_date="20260723",
                        discount_minor=500,
                        fee_minor=250,
                        bank_reference="BANKREF0000000000001",
                        tax_id_type="1",
                        beneficiary_tax_id="00012345678909",
                        beneficiary_name="ALPHA COMERCIO E SERVICOS LTDA",
                        bank_code="341",
                        branch_number="01234",
                        account_number="000123456789",
                        account_check_digit="5",
                        client_reference="CLIENT00000000000001",
                    ),
                    _settlement(
                        sequence="000002",
                        settlement_id="PSL0000000000002",
                        payment_reference="2" * 48,
                        face_amount_minor=5_000,
                        due_date="20260801",
                        payment_date="20260723",
                        discount_minor=0,
                        fee_minor=100,
                        bank_reference="BANKREF0000000000002",
                        tax_id_type="2",
                        beneficiary_tax_id="11222333000181",
                        beneficiary_name="BETA INDUSTRIA E COMERCIO S A",
                        bank_code="237",
                        branch_number="05678",
                        account_number="000987654321",
                        account_check_digit="0",
                        client_reference="CLIENT00000000000002",
                    ),
                ),
            ),
        ),
    )


def valid_boundary_batch() -> PaymentSlipBatch:
    """Return leap-day and maximum-width monetary boundary values."""

    return PaymentSlipBatch(
        file_date="20240229",
        batch_id="B202402290000202",
        lots=(
            PaymentSlipLot(
                lot_number="000001",
                settlement_date="20240229",
                originator_id="NWPORIGIN0000001",
                settlements=(
                    _settlement(
                        sequence="999999",
                        settlement_id="PSL9999999999999",
                        payment_reference="9" * 48,
                        face_amount_minor=999_999_999_999_999,
                        due_date="20991231",
                        payment_date="20240229",
                        discount_minor=999_999_999_999,
                        fee_minor=999_999_999_999,
                        bank_reference="Z" * 20,
                        tax_id_type="2",
                        beneficiary_tax_id="99999999999962",
                        beneficiary_name="Z" * 40,
                        bank_code="999",
                        branch_number="99999",
                        account_number="999999999998",
                        account_check_digit="Z",
                        client_reference="Z" * 20,
                    ),
                ),
            ),
        ),
    )


def malformed_batch() -> PaymentSlipBatch:
    """Return the valid model whose B sequence is changed during rendering."""

    return PaymentSlipBatch(
        file_date="20260723",
        batch_id="B202607230000203",
        lots=(
            PaymentSlipLot(
                lot_number="000001",
                settlement_date="20260723",
                originator_id="NWPORIGIN0000001",
                settlements=(
                    _settlement(
                        sequence="000001",
                        settlement_id="PSL0000000000003",
                        payment_reference="3" * 48,
                        face_amount_minor=1_000,
                        due_date="20260730",
                        payment_date="20260723",
                        discount_minor=0,
                        fee_minor=0,
                        bank_reference="BANKREF0000000000003",
                        tax_id_type="1",
                        beneficiary_tax_id="00012345678909",
                        beneficiary_name="MISMATCH PARTY",
                        bank_code="104",
                        branch_number="00001",
                        account_number="000000000123",
                        account_check_digit="9",
                        client_reference="CLIENT00000000000003",
                    ),
                ),
            ),
        ),
    )


def multi_lot_batch() -> PaymentSlipBatch:
    """Return two lots with one completed pair in each lot."""

    return PaymentSlipBatch(
        file_date="20260723",
        batch_id="B202607230000204",
        lots=(
            PaymentSlipLot(
                lot_number="000001",
                settlement_date="20260723",
                originator_id="NWPORIGIN0000001",
                settlements=(
                    _settlement(
                        sequence="000001",
                        settlement_id="PSL0000000000204",
                        payment_reference="3" * 48,
                        face_amount_minor=15_000,
                        due_date="20260730",
                        payment_date="20260723",
                        discount_minor=500,
                        fee_minor=250,
                        bank_reference="BANKREF0000000000204",
                        tax_id_type="1",
                        beneficiary_tax_id="00012345678909",
                        beneficiary_name="GAMMA COMERCIO LTDA",
                        bank_code="341",
                        branch_number="11111",
                        account_number="000000002204",
                        account_check_digit="1",
                        client_reference="CLIENT00000000000204",
                    ),
                ),
            ),
            PaymentSlipLot(
                lot_number="000002",
                settlement_date="20260723",
                originator_id="NWPORIGIN0000001",
                settlements=(
                    _settlement(
                        sequence="000001",
                        settlement_id="PSL0000000001204",
                        payment_reference="4" * 48,
                        face_amount_minor=5_000,
                        due_date="20260801",
                        payment_date="20260723",
                        discount_minor=0,
                        fee_minor=100,
                        bank_reference="BANKREF0000000001204",
                        tax_id_type="2",
                        beneficiary_tax_id="11222333000181",
                        beneficiary_name="DELTA INDUSTRIA S A",
                        bank_code="237",
                        branch_number="22222",
                        account_number="000000003204",
                        account_check_digit="2",
                        client_reference="CLIENT00000000001204",
                    ),
                ),
            ),
        ),
    )


def df_source_003_batch() -> PaymentSlipBatch:
    """Return the source-defect batch before its file trailer is changed."""

    return PaymentSlipBatch(
        file_date="20260723",
        batch_id="B202607230000205",
        lots=(
            PaymentSlipLot(
                lot_number="000001",
                settlement_date="20260723",
                originator_id="NWPORIGIN0000001",
                settlements=(
                    _settlement(
                        sequence="000001",
                        settlement_id="PSL0000000000205",
                        payment_reference="5" * 48,
                        face_amount_minor=15_000,
                        due_date="20260730",
                        payment_date="20260723",
                        discount_minor=500,
                        fee_minor=250,
                        bank_reference="BANKREF0000000000205",
                        tax_id_type="1",
                        beneficiary_tax_id="00012345678909",
                        beneficiary_name="EPSILON COMERCIO LTDA",
                        bank_code="341",
                        branch_number="33333",
                        account_number="000000002205",
                        account_check_digit="3",
                        client_reference="CLIENT00000000000205",
                    ),
                    _settlement(
                        sequence="000002",
                        settlement_id="PSL0000000001205",
                        payment_reference="6" * 48,
                        face_amount_minor=5_000,
                        due_date="20260801",
                        payment_date="20260723",
                        discount_minor=0,
                        fee_minor=100,
                        bank_reference="BANKREF0000000001205",
                        tax_id_type="2",
                        beneficiary_tax_id="11222333000181",
                        beneficiary_name="THETA INDUSTRIA S A",
                        bank_code="237",
                        branch_number="44444",
                        account_number="000000003205",
                        account_check_digit="4",
                        client_reference="CLIENT00000000001205",
                    ),
                ),
            ),
        ),
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


def _valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError:
        return False
    return True


def _validate_settlement(
    settlement: PaymentSlipSettlement,
    *,
    settlement_date: str,
) -> None:
    try:
        beneficiary_name = settlement.beneficiary_name.encode(
            "ascii",
            errors="strict",
        ).decode("ascii")
    except UnicodeError as exc:
        raise ValidationError(
            "Beneficiary name violates the Type 03 ASCII contract"
        ) from exc
    if (
        _SIX_DIGITS.fullmatch(settlement.sequence) is None
        or _SETTLEMENT_ID.fullmatch(settlement.settlement_id) is None
        or _PAYMENT_REFERENCE.fullmatch(settlement.payment_reference) is None
        or _REFERENCE.fullmatch(settlement.bank_reference) is None
        or _REFERENCE.fullmatch(settlement.client_reference) is None
        or _BENEFICIARY_NAME.fullmatch(beneficiary_name) is None
        or _BANK_CODE.fullmatch(settlement.bank_code) is None
        or _BRANCH.fullmatch(settlement.branch_number) is None
        or _ACCOUNT.fullmatch(settlement.account_number) is None
        or _CHECK_DIGIT.fullmatch(settlement.account_check_digit) is None
    ):
        raise ValidationError(
            "Type 03 settlement violates a lexical field contract"
        )
    if (
        not _valid_date(settlement.due_date)
        or not _valid_date(settlement.payment_date)
        or settlement.payment_date != settlement_date
        or settlement.payment_date > settlement.due_date
    ):
        raise ValidationError(
            "Type 03 settlement violates its business dates"
        )
    if (
        type(settlement.face_amount_minor) is not int
        or type(settlement.discount_minor) is not int
        or type(settlement.fee_minor) is not int
        or not 1 <= settlement.face_amount_minor <= 999_999_999_999_999
        or not 0 <= settlement.discount_minor <= 999_999_999_999
        or not 0 <= settlement.fee_minor <= 999_999_999_999
        or settlement.discount_minor > settlement.face_amount_minor
        or not 0 <= settlement.net_amount_minor <= 999_999_999_999_999
    ):
        raise ValidationError(
            "Type 03 settlement violates exact monetary bounds"
        )
    document = settlement.beneficiary_tax_id
    document_valid = (
        settlement.tax_id_type == "1"
        and document.startswith("000")
        and _valid_cpf(document[3:])
    ) or (
        settlement.tax_id_type == "2"
        and _valid_cnpj(document)
    )
    if not document_valid:
        raise ValidationError(
            "Beneficiary document violates the Type 03 contract"
        )
    restricted = (
        settlement.payment_reference,
        document,
        document[3:] if settlement.tax_id_type == "1" else document,
        settlement.account_number,
    )
    for safe_value in (
        settlement.settlement_id,
        settlement.bank_reference,
        settlement.client_reference,
    ):
        if any(value in safe_value for value in restricted):
            raise ValidationError(
                "A Type 03 safe identifier contains restricted source data"
            )


def _validate_batch(
    batch: PaymentSlipBatch,
    *,
    contract: Type03Contract,
) -> None:
    if (
        contract.type_number != "03"
        or contract.code != "PAYSLIPSET03"
        or contract.layout_version != "001"
        or contract.encoding != "US-ASCII"
        or contract.line_ending != "CRLF"
        or contract.final_newline != "required"
        or contract.record_length_bytes != 240
        or contract.transport_record_length_bytes != 242
        or contract.reserved_character != "~"
    ):
        raise ValidationError(
            "Type 03 generator received an unsupported contract"
        )
    if (
        not _valid_date(batch.file_date)
        or _BATCH_ID.fullmatch(batch.batch_id) is None
        or batch.batch_id[1:9] != batch.file_date
        or re.fullmatch(contract.filename_pattern, batch.filename) is None
    ):
        raise ValidationError("Type 03 batch identity is invalid")
    if (
        not 1 <= len(batch.lots) <= contract.max_lots
        or not 1 <= batch.logical_count <= contract.max_logical_rows
        or not 6 <= batch.physical_record_count
        <= contract.max_physical_records
    ):
        raise ValidationError("Type 03 batch size is outside its limits")

    lot_numbers: set[str] = set()
    settlement_ids: set[str] = set()
    for lot in batch.lots:
        if (
            _SIX_DIGITS.fullmatch(lot.lot_number) is None
            or lot.lot_number in lot_numbers
            or lot.settlement_date != batch.file_date
            or _ORIGINATOR.fullmatch(lot.originator_id) is None
            or not lot.settlements
        ):
            raise ValidationError("Type 03 lot violates its contract")
        lot_numbers.add(lot.lot_number)
        sequences: set[str] = set()
        for settlement in lot.settlements:
            _validate_settlement(
                settlement,
                settlement_date=lot.settlement_date,
            )
            if (
                settlement.sequence in sequences
                or settlement.settlement_id in settlement_ids
            ):
                raise ValidationError(
                    "Type 03 settlement identifiers are not unique"
                )
            sequences.add(settlement.sequence)
            settlement_ids.add(settlement.settlement_id)


def _implied_money(value_minor: int, *, width: int) -> str:
    rendered = str(value_minor)
    if value_minor < 0 or len(rendered) > width:
        raise ValidationError("Type 03 money does not fit its source field")
    return rendered.zfill(width)


def _fixed_record(value: str, *, contract: Type03Contract) -> bytes:
    try:
        prefix = value.encode("ascii", errors="strict")
        filler = contract.reserved_character.encode("ascii")
    except UnicodeError as exc:
        raise ValidationError(
            "Type 03 record contains non-ASCII data"
        ) from exc
    if len(prefix) > contract.record_length_bytes:
        raise ValidationError("Type 03 record exceeds 240 bytes")
    return prefix + filler * (contract.record_length_bytes - len(prefix))


def encode_file_header(
    batch: PaymentSlipBatch,
    *,
    contract: Type03Contract,
) -> bytes:
    return _fixed_record(
        (
            f"H{batch.file_date}{batch.batch_id}{contract.code}"
            f"{contract.layout_version}NWP00001{batch.batch_id[-6:]}"
        ),
        contract=contract,
    )


def encode_lot_header(
    batch: PaymentSlipBatch,
    lot: PaymentSlipLot,
    *,
    contract: Type03Contract,
) -> bytes:
    return _fixed_record(
        (
            f"L{lot.lot_number}SLIPSETTLE01BRL"
            f"{lot.settlement_date}{batch.batch_id}{lot.originator_id}"
        ),
        contract=contract,
    )


def encode_financial_segment(
    lot: PaymentSlipLot,
    settlement: PaymentSlipSettlement,
    *,
    contract: Type03Contract,
) -> bytes:
    return _fixed_record(
        (
            f"A{lot.lot_number}{settlement.sequence}"
            f"{settlement.settlement_id}{settlement.payment_reference}"
            f"{_implied_money(settlement.face_amount_minor, width=15)}"
            f"{settlement.due_date}{settlement.payment_date}"
            f"{_implied_money(settlement.discount_minor, width=12)}"
            f"{_implied_money(settlement.fee_minor, width=12)}"
            f"00{settlement.bank_reference}"
        ),
        contract=contract,
    )


def encode_beneficiary_segment(
    lot: PaymentSlipLot,
    settlement: PaymentSlipSettlement,
    *,
    contract: Type03Contract,
    sequence_override: str | None = None,
) -> bytes:
    sequence = sequence_override or settlement.sequence
    return _fixed_record(
        (
            f"B{lot.lot_number}{sequence}{settlement.settlement_id}"
            f"{settlement.tax_id_type}{settlement.beneficiary_tax_id}"
            f"{settlement.beneficiary_name.ljust(40)}"
            f"{settlement.bank_code}{settlement.branch_number}"
            f"{settlement.account_number}{settlement.account_check_digit}"
            f"{settlement.client_reference}"
        ),
        contract=contract,
    )


def encode_lot_trailer(
    batch: PaymentSlipBatch,
    lot: PaymentSlipLot,
    *,
    contract: Type03Contract,
) -> bytes:
    return _fixed_record(
        (
            f"T{lot.lot_number}{len(lot.settlements):06d}"
            f"{_implied_money(lot.face_amount_minor, width=15)}"
            f"{_implied_money(lot.discount_amount_minor, width=15)}"
            f"{_implied_money(lot.fee_amount_minor, width=15)}"
            f"{_implied_money(lot.net_amount_minor, width=15)}"
            f"{batch.batch_id}"
        ),
        contract=contract,
    )


def encode_file_trailer(
    batch: PaymentSlipBatch,
    *,
    contract: Type03Contract,
    declared_net_amount_minor: int,
) -> bytes:
    return _fixed_record(
        (
            f"Z{len(batch.lots):06d}"
            f"{batch.physical_record_count:06d}"
            f"{batch.logical_count:06d}"
            f"{_implied_money(declared_net_amount_minor, width=15)}"
            f"{batch.batch_id}"
        ),
        contract=contract,
    )


def _render_batch(
    *,
    scenario: str,
    batch: PaymentSlipBatch,
    contract: Type03Contract,
    declared_net_amount_minor: int,
    expected_contract_status: str,
    expected_violation: str | None,
    inject_pair_mismatch: bool = False,
) -> Type03GeneratedBatch:
    _validate_batch(batch, contract=contract)
    records = [encode_file_header(batch, contract=contract)]
    for lot_index, lot in enumerate(batch.lots):
        records.append(
            encode_lot_header(batch, lot, contract=contract)
        )
        for settlement_index, settlement in enumerate(lot.settlements):
            records.append(
                encode_financial_segment(
                    lot,
                    settlement,
                    contract=contract,
                )
            )
            records.append(
                encode_beneficiary_segment(
                    lot,
                    settlement,
                    contract=contract,
                    sequence_override=(
                        "000002"
                        if inject_pair_mismatch
                        and lot_index == 0
                        and settlement_index == 0
                        else None
                    ),
                )
            )
        records.append(
            encode_lot_trailer(batch, lot, contract=contract)
        )
    records.append(
        encode_file_trailer(
            batch,
            contract=contract,
            declared_net_amount_minor=declared_net_amount_minor,
        )
    )
    if (
        len(records) != batch.physical_record_count
        or any(len(record) != contract.record_length_bytes for record in records)
    ):
        raise ValidationError("Type 03 physical record controls drifted")
    raw_bytes = b"\r\n".join(records) + b"\r\n"
    if (
        len(raw_bytes)
        != len(records) * contract.transport_record_length_bytes
        or len(raw_bytes) > contract.max_source_file_bytes
    ):
        raise ValidationError("Type 03 source transport size is invalid")

    return Type03GeneratedBatch(
        scenario=scenario,
        contract=contract,
        batch=batch,
        raw_bytes=raw_bytes,
        computed_lot_count=len(batch.lots),
        computed_physical_record_count=batch.physical_record_count,
        computed_logical_count=batch.logical_count,
        computed_face_amount_minor=batch.face_amount_minor,
        computed_discount_amount_minor=batch.discount_amount_minor,
        computed_fee_amount_minor=batch.fee_amount_minor,
        computed_net_amount_minor=batch.net_amount_minor,
        computed_orphan_segment_count=0,
        declared_lot_count=len(batch.lots),
        declared_physical_record_count=batch.physical_record_count,
        declared_logical_count=batch.logical_count,
        declared_face_amount_minor=batch.face_amount_minor,
        declared_discount_amount_minor=batch.discount_amount_minor,
        declared_fee_amount_minor=batch.fee_amount_minor,
        declared_net_amount_minor=declared_net_amount_minor,
        expected_contract_status=expected_contract_status,
        expected_violation=expected_violation,
    )


def render_valid_minimal(contract: Type03Contract) -> Type03GeneratedBatch:
    batch = valid_minimal_batch()
    return _render_batch(
        scenario=VALID_MINIMAL,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_valid_boundary(contract: Type03Contract) -> Type03GeneratedBatch:
    batch = valid_boundary_batch()
    return _render_batch(
        scenario=VALID_BOUNDARY,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_malformed(contract: Type03Contract) -> Type03GeneratedBatch:
    batch = malformed_batch()
    return _render_batch(
        scenario=MALFORMED,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="REJECTED",
        expected_violation="SEGMENT_PAIR_MISMATCH",
        inject_pair_mismatch=True,
    )


def render_multi_lot(contract: Type03Contract) -> Type03GeneratedBatch:
    batch = multi_lot_batch()
    return _render_batch(
        scenario=MULTI_LOT,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=batch.net_amount_minor,
        expected_contract_status="ACCEPTED",
        expected_violation=None,
    )


def render_df_source_003(contract: Type03Contract) -> Type03GeneratedBatch:
    batch = df_source_003_batch()
    return _render_batch(
        scenario=DF_SOURCE_003,
        batch=batch,
        contract=contract,
        declared_net_amount_minor=19_849,
        expected_contract_status="REJECTED",
        expected_violation="SOURCE_CONTROL_NET_MISMATCH",
    )


def render_scenario(
    scenario: str,
    *,
    contract: Type03Contract,
) -> Type03GeneratedBatch:
    """Dispatch one approved Type 03 scenario without fixture copying."""

    renderers = {
        VALID_MINIMAL: render_valid_minimal,
        VALID_BOUNDARY: render_valid_boundary,
        MALFORMED: render_malformed,
        MULTI_LOT: render_multi_lot,
        DF_SOURCE_003: render_df_source_003,
    }
    renderer = renderers.get(scenario)
    if renderer is None:
        raise ValidationError(f"Unsupported Type 03 scenario: {scenario}")
    return renderer(contract)
