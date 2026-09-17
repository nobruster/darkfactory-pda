"""Focused fixed-record, arithmetic, and redaction tests for Type 03."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from contract_loader import load_type_03_contract
from generators.type_03_payment_slip_settlement import (
    _validate_batch,
    encode_beneficiary_segment,
    multi_lot_batch,
    render_malformed,
    render_valid_minimal,
    valid_minimal_batch,
)
from models import ValidationError


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts" / "types"


class Type03EncodingTest(unittest.TestCase):
    """Exercise Type 03 behavior below the artifact writer."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_type_03_contract(CONTRACTS)

    def test_integer_minor_units_produce_exact_lot_controls(self) -> None:
        batch = valid_minimal_batch()
        self.assertEqual(batch.logical_count, 2)
        self.assertEqual(batch.physical_record_count, 8)
        self.assertEqual(batch.face_amount_minor, 20_000)
        self.assertEqual(batch.discount_amount_minor, 500)
        self.assertEqual(batch.fee_amount_minor, 350)
        self.assertEqual(batch.net_amount_minor, 19_850)
        multi = multi_lot_batch()
        self.assertEqual(len(multi.lots), 2)
        self.assertEqual(multi.physical_record_count, 10)

    def test_malformed_changes_only_the_b_pair_sequence(self) -> None:
        batch = valid_minimal_batch()
        lot = batch.lots[0]
        settlement = lot.settlements[0]
        normal = encode_beneficiary_segment(
            lot,
            settlement,
            contract=self.contract,
        )
        changed = encode_beneficiary_segment(
            lot,
            settlement,
            contract=self.contract,
            sequence_override="000002",
        )
        self.assertEqual(len(normal), 240)
        self.assertEqual(len(changed), 240)
        differences = [
            offset
            for offset, pair in enumerate(zip(normal, changed, strict=True))
            if pair[0] != pair[1]
        ]
        self.assertEqual(differences, [12])
        raw = render_malformed(self.contract).raw_bytes
        records = raw[:-2].split(b"\r\n")
        self.assertEqual(records[2][7:13], b"000001")
        self.assertEqual(records[3][7:13], b"000002")

    def test_invalid_document_failure_does_not_disclose_value(self) -> None:
        batch = valid_minimal_batch()
        secret = "00012345678900"
        changed = replace(
            batch.lots[0].settlements[0],
            beneficiary_tax_id=secret,
        )
        changed_lot = replace(
            batch.lots[0],
            settlements=(changed, *batch.lots[0].settlements[1:]),
        )
        with self.assertRaises(ValidationError) as raised:
            _validate_batch(
                replace(batch, lots=(changed_lot,)),
                contract=self.contract,
            )
        self.assertNotIn(secret, str(raised.exception))

    def test_sensitive_models_are_frozen_and_redacted(self) -> None:
        settlement = valid_minimal_batch().lots[0].settlements[0]
        rendered = repr(settlement)
        for secret in (
            settlement.payment_reference,
            settlement.beneficiary_tax_id,
            settlement.beneficiary_name,
            settlement.branch_number,
            settlement.account_number,
        ):
            self.assertNotIn(secret, rendered)
        for restricted_field in (
            "payment_reference",
            "beneficiary_tax_id",
            "beneficiary_name",
            "branch_number",
            "account_number",
            "account_check_digit",
        ):
            self.assertNotIn(f"{restricted_field}=", rendered)
        generated = repr(render_valid_minimal(self.contract))
        self.assertNotIn(settlement.payment_reference, generated)
        self.assertNotIn(settlement.beneficiary_tax_id, generated)
        self.assertNotIn(settlement.account_number, generated)
        with self.assertRaises(FrozenInstanceError):
            settlement.face_amount_minor = 1  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
