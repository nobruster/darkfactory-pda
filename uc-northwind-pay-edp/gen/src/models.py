from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class GenerationError(Exception):
    """Base error for a safe, user-facing generation failure."""


class ContractError(GenerationError):
    """The requested contract is missing, unapproved, or unsupported."""


class ValidationError(GenerationError):
    """Scenario data cannot be encoded under the approved contract."""


class ArtifactConflictError(GenerationError):
    """An immutable output batch already exists."""


class ArtifactWriteError(GenerationError):
    """The immutable output bundle could not be safely written."""


class ContractIdentity(Protocol):
    """Contract identity and transport fields required by artifact metadata."""

    @property
    def contract_version(self) -> int: ...

    @property
    def type_number(self) -> str: ...

    @property
    def code(self) -> str: ...

    @property
    def layout_version(self) -> str: ...

    @property
    def filename_pattern(self) -> str: ...

    @property
    def encoding(self) -> str: ...

    @property
    def line_ending(self) -> str: ...

    @property
    def final_newline(self) -> str: ...

    @property
    def registry_path(self) -> Path: ...

    @property
    def layout_path(self) -> Path: ...


class BatchIdentity(Protocol):
    """Stable batch identity required by the common artifact writer."""

    @property
    def batch_id(self) -> str: ...

    @property
    def filename(self) -> str: ...


class GeneratedArtifact(Protocol):
    """Structural boundary shared by independently implemented file types."""

    @property
    def scenario(self) -> str: ...

    @property
    def contract(self) -> ContractIdentity: ...

    @property
    def batch(self) -> BatchIdentity: ...

    @property
    def raw_bytes(self) -> bytes: ...

    @property
    def expected_contract_status(self) -> str: ...

    @property
    def expected_violation(self) -> str | None: ...

    def source_control_values(self) -> Mapping[str, object]:
        """Return exact type-specific controls for the source manifest."""

    def receipt_control_values(self) -> Mapping[str, object]:
        """Return computed and declared controls for generator evidence."""


@dataclass(frozen=True, slots=True)
class Type01Contract:
    contract_version: int
    type_number: str
    code: str
    layout_version: str
    filename_pattern: str
    encoding: str
    line_ending: str
    final_newline: str
    header_length: int
    detail_length: int
    trailer_length: int
    positive_overpunch: str
    negative_overpunch: str
    registry_path: Path
    layout_path: Path


@dataclass(frozen=True, slots=True)
class CardSettlementDetail:
    transaction_id: str
    merchant_id: str
    pan: str = field(repr=False)
    cpf: str = field(repr=False)
    transaction_date: str
    transaction_time: str
    amount_minor: int
    currency: str
    movement_code: str
    authorization_code: str
    nsu: str
    terminal_id: str


@dataclass(frozen=True, slots=True)
class CardSettlementBatch:
    file_date: str
    batch_id: str
    details: tuple[CardSettlementDetail, ...]

    @property
    def filename(self) -> str:
        return f"NW_CARD_SETTLEMENT_{self.file_date}_{self.batch_id}.dat"

    @property
    def detail_count(self) -> int:
        return len(self.details)

    @property
    def net_amount_minor(self) -> int:
        return sum(detail.amount_minor for detail in self.details)


@dataclass(frozen=True, slots=True)
class Type01GeneratedBatch:
    """Rendered Type 01 source batch and its declared control evidence."""

    scenario: str
    contract: Type01Contract
    batch: CardSettlementBatch
    raw_bytes: bytes = field(repr=False)
    computed_detail_count: int
    computed_net_amount_minor: int | None
    declared_detail_count: int
    declared_net_amount_minor: int
    expected_contract_status: str
    expected_violation: str | None

    def source_control_values(self) -> Mapping[str, object]:
        """Return Type 01 controls without exposing raw identifiers."""

        return {
            "currency": "BRL",
            "detail_count": self.declared_detail_count,
            "net_amount": minor_units_to_string(
                self.declared_net_amount_minor
            ),
        }

    def receipt_control_values(self) -> Mapping[str, object]:
        """Return the Type 01 computed-versus-declared control evidence."""

        return {
            "computed_detail_count": self.computed_detail_count,
            "computed_net_amount": optional_minor_units_to_string(
                self.computed_net_amount_minor
            ),
            "declared_detail_count": self.declared_detail_count,
            "declared_net_amount": minor_units_to_string(
                self.declared_net_amount_minor
            ),
        }


@dataclass(frozen=True, slots=True)
class Type02Contract:
    """Approved Type 02 identity, transport, and grammar constraints."""

    contract_version: int
    type_number: str
    code: str
    layout_version: str
    filename_pattern: str
    encoding: str
    line_ending: str
    final_newline: str
    delimiter: str
    escape_character: str
    header_field_count: int
    event_field_count: int
    trailer_field_count: int
    max_record_bytes: int
    max_source_file_bytes: int
    registry_path: Path
    layout_path: Path


@dataclass(frozen=True, slots=True)
class InstantPaymentEvent:
    """One typed Type 02 source event.

    Clear documents and untrusted descriptions are intentionally excluded from
    the dataclass representation so validation failures cannot disclose them.
    """

    end_to_end_id: str = field(repr=False)
    transaction_id: str = field(repr=False)
    payer_document_type: str
    payer_document: str = field(repr=False)
    payee_document_type: str
    payee_document: str = field(repr=False)
    event_timestamp: str
    amount_minor: int
    direction: str
    status: str
    return_code: str
    description: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class InstantPaymentBatch:
    """A deterministic Type 02 batch before transport encoding."""

    file_date: str
    batch_id: str
    events: tuple[InstantPaymentEvent, ...]

    @property
    def filename(self) -> str:
        """Return the contract-defined Type 02 source filename."""

        return f"NW_INSTANT_PAYMENT_{self.file_date}_{self.batch_id}.txt"

    @property
    def event_count(self) -> int:
        """Return the logical source event count."""

        return len(self.events)

    @property
    def credit_amount_minor(self) -> int:
        """Return the exact sum of credit magnitudes in integer minor units."""

        return sum(
            event.amount_minor
            for event in self.events
            if event.direction == "C"
        )

    @property
    def debit_amount_minor(self) -> int:
        """Return the exact sum of debit magnitudes in integer minor units."""

        return sum(
            event.amount_minor
            for event in self.events
            if event.direction == "D"
        )

    @property
    def net_amount_minor(self) -> int:
        """Return credits minus debits in exact integer minor units."""

        return self.credit_amount_minor - self.debit_amount_minor


@dataclass(frozen=True, slots=True)
class Type02GeneratedBatch:
    """Generated Type 02 bytes plus independently visible source controls."""

    scenario: str
    contract: Type02Contract
    batch: InstantPaymentBatch
    raw_bytes: bytes = field(repr=False)
    computed_event_count: int
    computed_credit_amount_minor: int
    computed_debit_amount_minor: int
    computed_net_amount_minor: int
    declared_event_count: int
    declared_credit_amount_minor: int
    declared_debit_amount_minor: int
    declared_net_amount_minor: int
    expected_contract_status: str
    expected_violation: str | None

    def source_control_values(self) -> Mapping[str, object]:
        """Return the exact Type 02 controls declared by the source trailer."""

        return {
            "credit_amount": minor_units_to_string(
                self.declared_credit_amount_minor
            ),
            "currency": "BRL",
            "debit_amount": minor_units_to_string(
                self.declared_debit_amount_minor
            ),
            "event_count": self.declared_event_count,
            "net_amount": minor_units_to_string(
                self.declared_net_amount_minor
            ),
        }

    def receipt_control_values(self) -> Mapping[str, object]:
        """Return Type 02 computed-versus-declared control evidence."""

        return {
            "computed_credit_amount": minor_units_to_string(
                self.computed_credit_amount_minor
            ),
            "computed_debit_amount": minor_units_to_string(
                self.computed_debit_amount_minor
            ),
            "computed_event_count": self.computed_event_count,
            "computed_net_amount": minor_units_to_string(
                self.computed_net_amount_minor
            ),
            "declared_credit_amount": minor_units_to_string(
                self.declared_credit_amount_minor
            ),
            "declared_debit_amount": minor_units_to_string(
                self.declared_debit_amount_minor
            ),
            "declared_event_count": self.declared_event_count,
            "declared_net_amount": minor_units_to_string(
                self.declared_net_amount_minor
            ),
        }


@dataclass(frozen=True, slots=True)
class Type03Contract:
    """Approved Type 03 identity and fixed-record transport constraints."""

    contract_version: int
    type_number: str
    code: str
    layout_version: str
    filename_pattern: str
    encoding: str
    line_ending: str
    final_newline: str
    record_length_bytes: int
    transport_record_length_bytes: int
    max_lots: int
    max_logical_rows: int
    max_physical_records: int
    max_source_file_bytes: int
    reserved_character: str
    registry_path: Path
    layout_path: Path


@dataclass(frozen=True, slots=True)
class PaymentSlipSettlement:
    """One Type 03 logical settlement before paired-segment encoding."""

    sequence: str
    settlement_id: str
    payment_reference: str = field(repr=False)
    face_amount_minor: int
    due_date: str
    payment_date: str
    discount_minor: int
    fee_minor: int
    bank_reference: str
    tax_id_type: str
    beneficiary_tax_id: str = field(repr=False)
    beneficiary_name: str = field(repr=False)
    bank_code: str
    branch_number: str = field(repr=False)
    account_number: str = field(repr=False)
    account_check_digit: str = field(repr=False)
    client_reference: str

    @property
    def net_amount_minor(self) -> int:
        """Return face minus discount plus fee using integer minor units."""

        return (
            self.face_amount_minor
            - self.discount_minor
            + self.fee_minor
        )


@dataclass(frozen=True, slots=True)
class PaymentSlipLot:
    """One Type 03 lot and its ordered logical settlements."""

    lot_number: str
    settlement_date: str
    originator_id: str
    settlements: tuple[PaymentSlipSettlement, ...]

    @property
    def face_amount_minor(self) -> int:
        return sum(row.face_amount_minor for row in self.settlements)

    @property
    def discount_amount_minor(self) -> int:
        return sum(row.discount_minor for row in self.settlements)

    @property
    def fee_amount_minor(self) -> int:
        return sum(row.fee_minor for row in self.settlements)

    @property
    def net_amount_minor(self) -> int:
        return sum(row.net_amount_minor for row in self.settlements)


@dataclass(frozen=True, slots=True)
class PaymentSlipBatch:
    """A deterministic Type 03 source batch before transport rendering."""

    file_date: str
    batch_id: str
    lots: tuple[PaymentSlipLot, ...]

    @property
    def filename(self) -> str:
        return f"NW_PAYMENT_SLIP_{self.file_date}_{self.batch_id}.rem"

    @property
    def logical_count(self) -> int:
        return sum(len(lot.settlements) for lot in self.lots)

    @property
    def physical_record_count(self) -> int:
        return 2 + sum(2 + 2 * len(lot.settlements) for lot in self.lots)

    @property
    def face_amount_minor(self) -> int:
        return sum(lot.face_amount_minor for lot in self.lots)

    @property
    def discount_amount_minor(self) -> int:
        return sum(lot.discount_amount_minor for lot in self.lots)

    @property
    def fee_amount_minor(self) -> int:
        return sum(lot.fee_amount_minor for lot in self.lots)

    @property
    def net_amount_minor(self) -> int:
        return sum(lot.net_amount_minor for lot in self.lots)


@dataclass(frozen=True, slots=True)
class Type03GeneratedBatch:
    """Generated Type 03 bytes and declared-versus-computed controls."""

    scenario: str
    contract: Type03Contract
    batch: PaymentSlipBatch
    raw_bytes: bytes = field(repr=False)
    computed_lot_count: int
    computed_physical_record_count: int
    computed_logical_count: int
    computed_face_amount_minor: int
    computed_discount_amount_minor: int
    computed_fee_amount_minor: int
    computed_net_amount_minor: int
    computed_orphan_segment_count: int
    declared_lot_count: int
    declared_physical_record_count: int
    declared_logical_count: int
    declared_face_amount_minor: int
    declared_discount_amount_minor: int
    declared_fee_amount_minor: int
    declared_net_amount_minor: int
    expected_contract_status: str
    expected_violation: str | None

    def source_control_values(self) -> Mapping[str, object]:
        """Return privacy-safe Type 03 controls from source trailers."""

        return {
            "currency": "BRL",
            "discount_amount": minor_units_to_string(
                self.declared_discount_amount_minor
            ),
            "face_amount": minor_units_to_string(
                self.declared_face_amount_minor
            ),
            "fee_amount": minor_units_to_string(
                self.declared_fee_amount_minor
            ),
            "logical_count": self.declared_logical_count,
            "lot_count": self.declared_lot_count,
            "net_amount": minor_units_to_string(
                self.declared_net_amount_minor
            ),
            "orphan_segment_count": self.computed_orphan_segment_count,
            "physical_record_count": self.declared_physical_record_count,
        }

    def receipt_control_values(self) -> Mapping[str, object]:
        """Return complete Type 03 declared-versus-computed evidence."""

        return {
            "computed_discount_amount": minor_units_to_string(
                self.computed_discount_amount_minor
            ),
            "computed_face_amount": minor_units_to_string(
                self.computed_face_amount_minor
            ),
            "computed_fee_amount": minor_units_to_string(
                self.computed_fee_amount_minor
            ),
            "computed_logical_count": self.computed_logical_count,
            "computed_lot_count": self.computed_lot_count,
            "computed_net_amount": minor_units_to_string(
                self.computed_net_amount_minor
            ),
            "computed_orphan_segment_count": (
                self.computed_orphan_segment_count
            ),
            "computed_physical_record_count": (
                self.computed_physical_record_count
            ),
            "declared_discount_amount": minor_units_to_string(
                self.declared_discount_amount_minor
            ),
            "declared_face_amount": minor_units_to_string(
                self.declared_face_amount_minor
            ),
            "declared_fee_amount": minor_units_to_string(
                self.declared_fee_amount_minor
            ),
            "declared_logical_count": self.declared_logical_count,
            "declared_lot_count": self.declared_lot_count,
            "declared_net_amount": minor_units_to_string(
                self.declared_net_amount_minor
            ),
            "declared_physical_record_count": (
                self.declared_physical_record_count
            ),
        }


@dataclass(frozen=True, slots=True)
class Type04Contract:
    """Approved Type 04 identity and heterogeneous-record constraints."""

    contract_version: int
    type_number: str
    code: str
    layout_version: str
    filename_pattern: str
    encoding: str
    line_ending: str
    final_newline: str
    header_length: int
    transfer_length: int
    return_length: int
    trailer_length: int
    max_transfers: int
    max_returns: int
    max_movements: int
    max_physical_records: int
    max_source_file_bytes: int
    visible_padding_character: str
    source_zone: str
    registry_path: Path
    layout_path: Path


@dataclass(frozen=True, slots=True)
class TedReturn:
    """One full-return record attached to its preceding Type 04 transfer."""

    return_id: str
    return_date: str
    return_time: str
    reason_code: str
    reason_text: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class TedTransfer:
    """One Type 04 transfer and its optional status-selected return."""

    transfer_id: str
    amount_minor: int
    transfer_date: str
    transfer_time: str
    payer_ispb: str
    payer_branch: str = field(repr=False)
    payer_account: str = field(repr=False)
    payer_tax_id: str = field(repr=False)
    payer_party_type: str
    beneficiary_ispb: str
    beneficiary_branch: str = field(repr=False)
    beneficiary_account: str = field(repr=False)
    beneficiary_tax_id: str = field(repr=False)
    beneficiary_party_type: str
    purpose_code: str
    status_code: str
    beneficiary_name: str = field(repr=False)
    return_record: TedReturn | None = field(default=None, repr=False)

    @property
    def return_amount_minor(self) -> int:
        """Return the signed full-return amount, or zero for status OK."""

        return -self.amount_minor if self.return_record is not None else 0


@dataclass(frozen=True, slots=True)
class TedTransferBatch:
    """A deterministic Type 04 source batch before byte rendering."""

    file_date: str
    batch_id: str
    origin_ispb: str
    transfers: tuple[TedTransfer, ...]

    @property
    def filename(self) -> str:
        return f"NW_TED_SETTLEMENT_{self.file_date}_{self.batch_id}.dat"

    @property
    def transfer_count(self) -> int:
        return len(self.transfers)

    @property
    def return_count(self) -> int:
        return sum(row.return_record is not None for row in self.transfers)

    @property
    def movement_count(self) -> int:
        return self.transfer_count + self.return_count

    @property
    def physical_record_count(self) -> int:
        return self.movement_count + 2

    @property
    def gross_amount_minor(self) -> int:
        return sum(row.amount_minor for row in self.transfers)

    @property
    def return_amount_minor(self) -> int:
        return sum(row.return_amount_minor for row in self.transfers)

    @property
    def net_amount_minor(self) -> int:
        return self.gross_amount_minor + self.return_amount_minor


@dataclass(frozen=True, slots=True)
class Type04GeneratedBatch:
    """Generated Type 04 bytes and declared-versus-computed controls."""

    scenario: str
    contract: Type04Contract
    batch: TedTransferBatch
    raw_bytes: bytes = field(repr=False)
    computed_transfer_count: int
    computed_return_count: int
    computed_gross_amount_minor: int
    computed_return_amount_minor: int
    computed_net_amount_minor: int
    declared_transfer_count: int
    declared_return_count: int
    declared_gross_amount_minor: int
    declared_return_amount_minor: int
    declared_net_amount_minor: int
    expected_contract_status: str
    expected_violation: str | None

    def source_control_values(self) -> Mapping[str, object]:
        """Return privacy-safe Type 04 controls from the source trailer."""

        return {
            "currency": "BRL",
            "gross_amount": minor_units_to_string(
                self.declared_gross_amount_minor
            ),
            "net_amount": minor_units_to_string(
                self.declared_net_amount_minor
            ),
            "return_amount": minor_units_to_string(
                self.declared_return_amount_minor
            ),
            "return_count": self.declared_return_count,
            "transfer_count": self.declared_transfer_count,
        }

    def receipt_control_values(self) -> Mapping[str, object]:
        """Return complete Type 04 declared-versus-computed evidence."""

        return {
            "computed_gross_amount": minor_units_to_string(
                self.computed_gross_amount_minor
            ),
            "computed_net_amount": minor_units_to_string(
                self.computed_net_amount_minor
            ),
            "computed_return_amount": minor_units_to_string(
                self.computed_return_amount_minor
            ),
            "computed_return_count": self.computed_return_count,
            "computed_transfer_count": self.computed_transfer_count,
            "declared_gross_amount": minor_units_to_string(
                self.declared_gross_amount_minor
            ),
            "declared_net_amount": minor_units_to_string(
                self.declared_net_amount_minor
            ),
            "declared_return_amount": minor_units_to_string(
                self.declared_return_amount_minor
            ),
            "declared_return_count": self.declared_return_count,
            "declared_transfer_count": self.declared_transfer_count,
        }


@dataclass(frozen=True, slots=True)
class Type05Contract:
    """Approved Type 05 identity, transport, grammar, and size constraints."""

    contract_version: int
    type_number: str
    code: str
    layout_version: str
    filename_pattern: str
    encoding: str
    unicode_normalization: str
    line_ending: str
    final_newline: str
    delimiter: str
    quote_character: str
    field_count: int
    exact_header: str
    max_detail_rows: int
    max_physical_record_bytes: int
    max_source_file_bytes: int
    registry_path: Path
    layout_path: Path


@dataclass(frozen=True, slots=True)
class MerchantFeeAssessment:
    """One Type 05 assessment represented without binary floating point."""

    assessment_id: str
    merchant_id: str
    merchant_tax_id: str = field(repr=False)
    fee_code: str
    description: str = field(repr=False)
    gross_amount_minor: int
    rate_milli_percent: int
    assessed_fee_minor: int
    assessment_date: str

    @property
    def calculated_fee_minor(self) -> int:
        """Calculate the row fee in minor units with exact positive HALF_UP."""

        numerator = self.gross_amount_minor * self.rate_milli_percent
        whole, remainder = divmod(numerator, 100_000)
        return whole + int(remainder * 2 >= 100_000)


@dataclass(frozen=True, slots=True)
class MerchantFeeBatch:
    """A deterministic Type 05 merchant-fee batch before byte rendering."""

    file_date: str
    batch_id: str
    assessments: tuple[MerchantFeeAssessment, ...]

    @property
    def filename(self) -> str:
        return f"NW_MERCHANT_FEES_{self.file_date}_{self.batch_id}.csv"

    @property
    def row_count(self) -> int:
        return len(self.assessments)

    @property
    def gross_amount_minor(self) -> int:
        return sum(row.gross_amount_minor for row in self.assessments)

    @property
    def assessed_fee_minor(self) -> int:
        return sum(row.assessed_fee_minor for row in self.assessments)

    @property
    def calculated_fee_minor(self) -> int:
        return sum(row.calculated_fee_minor for row in self.assessments)


@dataclass(frozen=True, slots=True)
class Type06Contract:
    """Approved Type 06 identity, transport, grammar, and size constraints."""

    contract_version: int
    type_number: str
    code: str
    layout_version: str
    filename_pattern: str
    encoding: str
    unicode_normalization: str
    line_ending: str
    final_newline: str
    delimiter: str
    quote_character: str
    field_count: int
    exact_header: str
    max_detail_rows: int
    max_physical_record_bytes: int
    max_source_file_bytes: int
    registry_path: Path
    layout_path: Path


@dataclass(frozen=True, slots=True)
class MerchantChargeback:
    """One Type 06 chargeback without binary floating point."""

    chargeback_id: str
    merchant_id: str
    merchant_tax_id: str = field(repr=False)
    reason_code: str
    description: str = field(repr=False)
    original_amount_minor: int
    rate_milli_percent: int
    chargeback_amount_minor: int
    business_date: str

    @property
    def calculated_amount_minor(self) -> int:
        numerator = self.original_amount_minor * self.rate_milli_percent
        whole, remainder = divmod(numerator, 100_000)
        return whole + int(remainder * 2 >= 100_000)


@dataclass(frozen=True, slots=True)
class MerchantChargebackBatch:
    """A deterministic Type 06 batch before byte rendering."""

    file_date: str
    batch_id: str
    rows: tuple[MerchantChargeback, ...]

    @property
    def filename(self) -> str:
        return f"NW_MERCHANT_CHARGEBACK_{self.file_date}_{self.batch_id}.csv"

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def original_amount_minor(self) -> int:
        return sum(row.original_amount_minor for row in self.rows)

    @property
    def chargeback_amount_minor(self) -> int:
        return sum(row.chargeback_amount_minor for row in self.rows)

    @property
    def calculated_amount_minor(self) -> int:
        return sum(row.calculated_amount_minor for row in self.rows)


@dataclass(frozen=True, slots=True)
class Type06GeneratedBatch:
    """Generated Type 06 bytes and declared-versus-computed controls."""

    scenario: str
    contract: Type06Contract
    batch: MerchantChargebackBatch
    raw_bytes: bytes = field(repr=False)
    computed_row_count: int
    computed_original_amount_minor: int
    computed_chargeback_amount_minor: int
    computed_calculated_amount_minor: int
    declared_row_count: int
    declared_original_amount_minor: int
    declared_chargeback_amount_minor: int
    declared_calculated_amount_minor: int
    expected_contract_status: str
    expected_violation: str | None

    def source_control_values(self) -> Mapping[str, object]:
        return {
            "calculated_amount": minor_units_to_string(
                self.declared_calculated_amount_minor
            ),
            "chargeback_amount": minor_units_to_string(
                self.declared_chargeback_amount_minor
            ),
            "currency": "BRL",
            "original_amount": minor_units_to_string(
                self.declared_original_amount_minor
            ),
            "row_count": self.declared_row_count,
        }

    def receipt_control_values(self) -> Mapping[str, object]:
        return {
            "computed_calculated_amount": minor_units_to_string(
                self.computed_calculated_amount_minor
            ),
            "computed_chargeback_amount": minor_units_to_string(
                self.computed_chargeback_amount_minor
            ),
            "computed_original_amount": minor_units_to_string(
                self.computed_original_amount_minor
            ),
            "computed_row_count": self.computed_row_count,
            "currency": "BRL",
            "declared_calculated_amount": minor_units_to_string(
                self.declared_calculated_amount_minor
            ),
            "declared_chargeback_amount": minor_units_to_string(
                self.declared_chargeback_amount_minor
            ),
            "declared_original_amount": minor_units_to_string(
                self.declared_original_amount_minor
            ),
            "declared_row_count": self.declared_row_count,
        }


@dataclass(frozen=True, slots=True)
class Type05GeneratedBatch:
    """Generated Type 05 bytes and declared-versus-computed controls."""

    scenario: str
    contract: Type05Contract
    batch: MerchantFeeBatch
    raw_bytes: bytes = field(repr=False)
    computed_row_count: int
    computed_gross_amount_minor: int
    computed_assessed_fee_minor: int
    computed_calculated_fee_minor: int
    declared_row_count: int
    declared_gross_amount_minor: int
    declared_assessed_fee_minor: int
    declared_calculated_fee_minor: int
    expected_contract_status: str
    expected_violation: str | None

    def source_control_values(self) -> Mapping[str, object]:
        """Return privacy-safe source-owned Type 05 aggregate controls."""

        return {
            "assessed_fee": minor_units_to_string(
                self.declared_assessed_fee_minor
            ),
            "calculated_fee": minor_units_to_string(
                self.declared_calculated_fee_minor
            ),
            "currency": "BRL",
            "gross_amount": minor_units_to_string(
                self.declared_gross_amount_minor
            ),
            "row_count": self.declared_row_count,
        }

    def receipt_control_values(self) -> Mapping[str, object]:
        """Return complete Type 05 computed-versus-declared evidence."""

        return {
            "computed_assessed_fee": minor_units_to_string(
                self.computed_assessed_fee_minor
            ),
            "computed_calculated_fee": minor_units_to_string(
                self.computed_calculated_fee_minor
            ),
            "computed_gross_amount": minor_units_to_string(
                self.computed_gross_amount_minor
            ),
            "computed_row_count": self.computed_row_count,
            "declared_assessed_fee": minor_units_to_string(
                self.declared_assessed_fee_minor
            ),
            "declared_calculated_fee": minor_units_to_string(
                self.declared_calculated_fee_minor
            ),
            "declared_gross_amount": minor_units_to_string(
                self.declared_gross_amount_minor
            ),
            "declared_row_count": self.declared_row_count,
        }


@dataclass(frozen=True, slots=True)
class WrittenBundle:
    batch_id: str
    directory: Path
    raw_file: Path
    checksum_file: Path
    manifest_file: Path
    receipt_file: Path
    raw_sha256: str


def minor_units_to_string(amount_minor: int) -> str:
    """Render integer BRL minor units as a canonical two-decimal string."""

    sign = "-" if amount_minor < 0 else ""
    absolute = abs(amount_minor)
    return f"{sign}{absolute // 100}.{absolute % 100:02d}"


def optional_minor_units_to_string(amount_minor: int | None) -> str | None:
    """Render optional integer minor units without using floating point."""

    if amount_minor is None:
        return None
    return minor_units_to_string(amount_minor)
