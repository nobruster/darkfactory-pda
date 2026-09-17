"""Focused locale, HALF_UP, validation, and redaction tests for Type 05."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from contract_loader import load_type_05_contract
from generators.type_05_merchant_fee_assessment import (
    _validate_batch,
    encode_assessment,
    render_malformed,
    render_valid_minimal,
    rounding_half_up_batch,
    valid_boundary_batch,
    valid_minimal_batch,
)
from models import ValidationError


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts" / "types"


class Type05EncodingTest(unittest.TestCase):
    """Exercise Type 05 behavior below the artifact writer."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_type_05_contract(CONTRACTS)

    def test_integer_arithmetic_rounds_positive_ties_half_up(self) -> None:
        rows = rounding_half_up_batch().assessments
        self.assertEqual(rows[0].calculated_fee_minor, 1)
        self.assertEqual(rows[1].calculated_fee_minor, 3)
        self.assertEqual(
            rounding_half_up_batch().calculated_fee_minor,
            4,
        )
        boundary = valid_boundary_batch().assessments[0]
        self.assertEqual(
            boundary.calculated_fee_minor,
            99_999_999_999_999,
        )

    def test_description_is_quoted_and_embedded_quotes_are_doubled(self) -> None:
        row = valid_minimal_batch().assessments[0]
        encoded = encode_assessment(
            row,
            batch_id="B202607230000401",
            contract=self.contract,
        )
        self.assertIn(b';"Tarifa ""VIP""; julho, lote A";', encoded)
        self.assertIn(b";1000,00;1,235;12,35;", encoded)

    def test_malformed_omits_only_mandatory_description_quotes(self) -> None:
        generated = render_malformed(self.contract)
        self.assertIn(b";MDR;Tarifa sem aspas;10,00;", generated.raw_bytes)
        self.assertNotIn(
            b';MDR;"Tarifa sem aspas";10,00;',
            generated.raw_bytes,
        )

    def test_invalid_cnpj_or_description_failure_does_not_disclose(self) -> None:
        batch = valid_minimal_batch()
        restricted = "99999999999999"
        invalid_cnpj = replace(
            batch.assessments[0],
            merchant_tax_id=restricted,
        )
        decomposed = replace(
            batch.assessments[0],
            description="Arredondamento mi\u0301nimo",
        )
        formula = replace(
            batch.assessments[0],
            description="=SUM(A1:A2)",
        )
        for changed in (invalid_cnpj, decomposed, formula):
            with self.subTest():
                with self.assertRaises(ValidationError) as raised:
                    _validate_batch(
                        replace(
                            batch,
                            assessments=(
                                changed,
                                *batch.assessments[1:],
                            ),
                        ),
                        contract=self.contract,
                    )
                self.assertNotIn(restricted, str(raised.exception))

    def test_sensitive_models_are_frozen_and_redacted(self) -> None:
        row = valid_minimal_batch().assessments[0]
        rendered = repr(row)
        for secret in (row.merchant_tax_id, row.description):
            self.assertNotIn(secret, rendered)
        self.assertNotIn("merchant_tax_id=", rendered)
        self.assertNotIn("description=", rendered)
        generated = repr(render_valid_minimal(self.contract))
        self.assertNotIn(row.merchant_tax_id, generated)
        self.assertNotIn(row.description, generated)
        with self.assertRaises(FrozenInstanceError):
            row.gross_amount_minor = 1  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
