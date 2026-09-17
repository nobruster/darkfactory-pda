from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from contract_loader import load_type_01_contract
from generators.type_01_card_settlement import (
    encode_detail,
    encode_header,
    encode_overpunch,
    encode_trailer,
    render_valid_minimal,
    valid_minimal_batch,
)
from models import ValidationError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts" / "types"


class Type01EncodingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_type_01_contract(CONTRACTS_ROOT)
        cls.batch = valid_minimal_batch()

    def test_positive_and_negative_overpunch(self) -> None:
        self.assertEqual(
            encode_overpunch(12_345, width=12, contract=self.contract),
            "00000001234E",
        )
        self.assertEqual(
            encode_overpunch(5_000, width=12, contract=self.contract),
            "00000000500{",
        )
        self.assertEqual(
            encode_overpunch(-1_234, width=12, contract=self.contract),
            "00000000123M",
        )

    def test_record_lengths_match_contract_bytes(self) -> None:
        header = encode_header(self.batch, contract=self.contract)
        details = [
            encode_detail(detail, contract=self.contract)
            for detail in self.batch.details
        ]
        trailer = encode_trailer(self.batch, contract=self.contract)

        self.assertEqual(len(header), 40)
        self.assertEqual([len(detail) for detail in details], [124, 124])
        self.assertEqual(len(trailer), 46)

    def test_purchase_rejects_negative_amount(self) -> None:
        invalid = replace(self.batch.details[0], amount_minor=-1)
        with self.assertRaisesRegex(
            ValidationError,
            "Purchase movement requires a positive amount",
        ):
            encode_detail(invalid, contract=self.contract)

    def test_sensitive_fields_are_redacted_from_dataclass_repr(self) -> None:
        detail_repr = repr(self.batch.details[0])
        if (
            self.batch.details[0].pan in detail_repr
            or self.batch.details[0].cpf in detail_repr
        ):
            self.fail("A restricted identifier appeared in the detail representation")
        generated_repr = repr(render_valid_minimal(self.contract))
        for detail in self.batch.details:
            self.assertNotIn(detail.pan, generated_repr)
            self.assertNotIn(detail.cpf, generated_repr)


if __name__ == "__main__":
    unittest.main()
