"""Focused grammar, arithmetic, validation, and privacy tests for Type 02."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from contract_loader import load_type_02_contract
from generators.type_02_instant_payment_events import (
    _validate_batch,
    encode_event,
    escape_field,
    malformed_batch,
    render_valid_minimal,
    valid_minimal_batch,
)
from models import ValidationError, minor_units_to_string


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts" / "types"


class Type02EncodingTest(unittest.TestCase):
    """Exercise Type 02 behavior below the artifact-publication boundary."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_type_02_contract(CONTRACTS_ROOT)

    def test_escape_encoding_is_exactly_once(self) -> None:
        self.assertEqual(
            escape_field(
                "Café, invoice | folder \\2026",
                contract=self.contract,
            ),
            "Café, invoice \\| folder \\\\2026",
        )
        event = valid_minimal_batch().events[1]
        encoded = encode_event(event, contract=self.contract)
        self.assertIn(b"Return\\|beneficiary", encoded)
        self.assertNotIn(b"Return\\\\\\|beneficiary", encoded)

    def test_minor_unit_controls_never_use_binary_floating_point(self) -> None:
        batch = valid_minimal_batch()
        self.assertEqual(batch.event_count, 2)
        self.assertEqual(batch.credit_amount_minor, 20_000)
        self.assertEqual(batch.debit_amount_minor, 2_655)
        self.assertEqual(batch.net_amount_minor, 17_345)
        self.assertEqual(minor_units_to_string(batch.net_amount_minor), "173.45")
        self.assertTrue(
            all(type(event.amount_minor) is int for event in batch.events)
        )

    def test_malformed_injection_creates_one_extra_lexical_field(self) -> None:
        def lexical_field_count(record: bytes) -> int:
            delimiters = 0
            escaped = False
            for byte in record:
                if escaped:
                    escaped = False
                elif byte == ord("\\"):
                    escaped = True
                elif byte == ord("|"):
                    delimiters += 1
            return delimiters + 1

        event = malformed_batch().events[0]
        valid = encode_event(event, contract=self.contract)
        malformed = encode_event(
            event,
            contract=self.contract,
            escape_description=False,
        )
        self.assertEqual(lexical_field_count(valid), 13)
        self.assertEqual(lexical_field_count(malformed), 14)
        self.assertEqual(len(malformed), len(valid) - 1)

    def test_invalid_document_failure_does_not_disclose_value(self) -> None:
        batch = valid_minimal_batch()
        invalid_value = "12345678900"
        invalid_event = replace(
            batch.events[0],
            payer_document=invalid_value,
        )
        invalid_batch = replace(batch, events=(invalid_event, *batch.events[1:]))
        with self.assertRaises(ValidationError) as raised:
            _validate_batch(invalid_batch, contract=self.contract)
        self.assertNotIn(invalid_value, str(raised.exception))

    def test_sensitive_fields_are_redacted_and_models_are_frozen(self) -> None:
        event = valid_minimal_batch().events[0]
        rendered = repr(event)
        self.assertNotIn(event.end_to_end_id, rendered)
        self.assertNotIn(event.transaction_id, rendered)
        self.assertNotIn(event.payer_document, rendered)
        self.assertNotIn(event.payee_document, rendered)
        self.assertNotIn(event.description, rendered)
        generated_repr = repr(render_valid_minimal(self.contract))
        self.assertNotIn(event.end_to_end_id, generated_repr)
        self.assertNotIn(event.transaction_id, generated_repr)
        self.assertNotIn(event.payer_document, generated_repr)
        self.assertNotIn(event.payee_document, generated_repr)
        self.assertNotIn(event.description, generated_repr)
        with self.assertRaises(FrozenInstanceError):
            event.amount_minor = 1  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
