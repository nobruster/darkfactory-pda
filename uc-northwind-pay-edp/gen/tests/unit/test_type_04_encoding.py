"""Focused heterogeneous-record and redaction tests for Type 04."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from contract_loader import load_type_04_contract
from generators.type_04_ted_transfer_settlement import (
    _validate_batch,
    all_returned_zero_net_batch,
    encode_return,
    encode_transfer,
    render_malformed,
    render_valid_minimal,
    valid_minimal_batch,
)
from models import ValidationError


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts" / "types"


class Type04EncodingTest(unittest.TestCase):
    """Exercise Type 04 behavior below the artifact writer."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_type_04_contract(CONTRACTS)

    def test_integer_minor_units_produce_exact_signed_controls(self) -> None:
        batch = valid_minimal_batch()
        self.assertEqual(batch.transfer_count, 2)
        self.assertEqual(batch.return_count, 1)
        self.assertEqual(batch.movement_count, 3)
        self.assertEqual(batch.gross_amount_minor, 125_000)
        self.assertEqual(batch.return_amount_minor, -25_000)
        self.assertEqual(batch.net_amount_minor, 100_000)
        zero = all_returned_zero_net_batch()
        self.assertEqual(zero.return_count, 2)
        self.assertEqual(zero.net_amount_minor, 0)

    def test_record_variants_have_exact_heterogeneous_lengths(self) -> None:
        transfer = valid_minimal_batch().transfers[1]
        self.assertEqual(
            len(encode_transfer(transfer, contract=self.contract)),
            162,
        )
        self.assertEqual(
            len(encode_return(transfer, contract=self.contract)),
            91,
        )

    def test_malformed_changes_only_the_first_crlf_to_lf(self) -> None:
        valid = render_valid_minimal(self.contract).raw_bytes
        malformed = render_malformed(self.contract).raw_bytes
        expected = valid.replace(
            b"B202607230000301",
            b"B202607230000303",
        )
        expected = expected.replace(
            b"TED2026072300301",
            b"TED2026072300303",
        ).replace(
            b"TED2026072301301",
            b"TED2026072301303",
        ).replace(
            b"RET2026072300301",
            b"RET2026072300303",
        )
        self.assertEqual(
            malformed,
            expected.replace(b"\r\n", b"\n", 1),
        )

    def test_invalid_document_failure_does_not_disclose_value(self) -> None:
        batch = valid_minimal_batch()
        restricted = "99999999999999"
        changed = replace(
            batch.transfers[0],
            payer_tax_id=restricted,
        )
        with self.assertRaises(ValidationError) as raised:
            _validate_batch(
                replace(
                    batch,
                    transfers=(changed, *batch.transfers[1:]),
                ),
                contract=self.contract,
            )
        self.assertNotIn(restricted, str(raised.exception))

    def test_sensitive_models_are_frozen_and_redacted(self) -> None:
        transfer = valid_minimal_batch().transfers[1]
        rendered = repr(transfer)
        for secret in (
            transfer.payer_account,
            transfer.payer_tax_id,
            transfer.beneficiary_account,
            transfer.beneficiary_tax_id,
            transfer.beneficiary_name,
        ):
            self.assertNotIn(secret, rendered)
        for field_name in (
            "payer_branch",
            "payer_account",
            "payer_tax_id",
            "beneficiary_branch",
            "beneficiary_account",
            "beneficiary_tax_id",
            "beneficiary_name",
            "return_record",
        ):
            self.assertNotIn(f"{field_name}=", rendered)
        generated = repr(render_valid_minimal(self.contract))
        self.assertNotIn(transfer.payer_account, generated)
        self.assertNotIn(transfer.beneficiary_tax_id, generated)
        with self.assertRaises(FrozenInstanceError):
            transfer.amount_minor = 1  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
