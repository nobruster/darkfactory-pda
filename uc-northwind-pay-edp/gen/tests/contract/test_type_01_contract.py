"""Executable byte-for-byte contract tests for Type 01 DataGen."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from checksum import sha256_hex
from contract_loader import load_type_01_contract
from generation import generate
from generators.type_01_card_settlement import render_valid_minimal


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts" / "types"
CANONICAL_ROOT = CONTRACTS_ROOT / "01-card-settlement" / "main"
CANONICAL_FIXTURES = {
    "valid-minimal": (
        "valid-minimal.dat",
        "66c2d02217d133e88ec28486f170a90fc"
        "134ff7a70e63e8096b8be37dacbd82f",
    ),
    "valid-boundary": (
        "valid-boundary.dat",
        "b1bcb59bcc8e0163c1cdc853f8354c88"
        "1630ffbd1091385a2a368eea09b4f23d",
    ),
    "negative-overpunch": (
        "negative-overpunch.dat",
        "0c773790558e429aeaaf9beeb9e8ed8d"
        "ef45061b0804c9a4cb3e84825cac1de2",
    ),
    "malformed": (
        "malformed.dat",
        "c4b7815f3ae95d3259064a7a9afe52d"
        "0f30b6a289d456e09b896351294308934",
    ),
    "DF-SOURCE-001": (
        "df-source-001.dat",
        "4b72707c859c755fe9aeba6ec67996fb7"
        "b084ab0992231c8d60358bdfdd13980",
    ),
}
RECORD_LENGTHS = {
    b"H": 40,
    b"D": 124,
    b"T": 46,
}


class Type01ContractTest(unittest.TestCase):
    """Prove generated Type 01 bytes equal approved independent fixtures."""

    def assert_sensitive_bytes_equal(
        self,
        *,
        actual: bytes,
        expected: bytes,
        scenario: str,
    ) -> None:
        """Compare restricted fixtures without printing their contents."""

        if actual == expected:
            return
        mismatch = next(
            (
                offset
                for offset, pair in enumerate(
                    zip(actual, expected, strict=False)
                )
                if pair[0] != pair[1]
            ),
            min(len(actual), len(expected)),
        )
        self.fail(
            "Type 01 raw artifacts differ without exposing their contents: "
            f"scenario={scenario}, "
            f"actual_length={len(actual)}, "
            f"expected_length={len(expected)}, "
            f"actual_sha256={sha256_hex(actual)}, "
            f"expected_sha256={sha256_hex(expected)}, "
            f"first_mismatch_offset={mismatch}"
        )

    def test_all_five_scenarios_match_canonical_raw_bytes(self) -> None:
        for scenario, (filename, expected_hash) in (
            CANONICAL_FIXTURES.items()
        ):
            with self.subTest(scenario=scenario):
                with tempfile.TemporaryDirectory() as output:
                    bundle = generate(
                        type_number="01",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS_ROOT,
                    )
                    actual = bundle.raw_file.read_bytes()
                    expected = (CANONICAL_ROOT / filename).read_bytes()
                    self.assert_sensitive_bytes_equal(
                        actual=actual,
                        expected=expected,
                        scenario=scenario,
                    )
                    self.assertEqual(sha256_hex(actual), expected_hash)

    def test_transport_is_exact_iso_8859_1_lf_fixed_width_records(
        self,
    ) -> None:
        for scenario in CANONICAL_FIXTURES:
            with self.subTest(scenario=scenario):
                with tempfile.TemporaryDirectory() as output:
                    raw = generate(
                        type_number="01",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS_ROOT,
                    ).raw_file.read_bytes()

                raw.decode("iso-8859-1", errors="strict")
                self.assertNotIn(b"\r", raw)
                self.assertTrue(raw.endswith(b"\n"))
                self.assertFalse(raw.endswith(b"\n\n"))
                self.assertNotIn(b"\n\n", raw)

                records = raw[:-1].split(b"\n")
                self.assertGreaterEqual(len(records), 3)
                self.assertEqual(records[0][:1], b"H")
                self.assertEqual(records[-1][:1], b"T")
                self.assertTrue(
                    all(record[:1] == b"D" for record in records[1:-1])
                )
                self.assertTrue(
                    all(
                        len(record)
                        == RECORD_LENGTHS.get(record[:1], -1)
                        for record in records
                    )
                )
                self.assertEqual(
                    len(raw),
                    sum(len(record) + 1 for record in records),
                )

    def test_valid_minimal_retains_original_model_controls(self) -> None:
        contract = load_type_01_contract(CONTRACTS_ROOT)
        generated = render_valid_minimal(contract)
        expected = (CANONICAL_ROOT / "valid-minimal.dat").read_bytes()

        self.assert_sensitive_bytes_equal(
            actual=generated.raw_bytes,
            expected=expected,
            scenario="valid-minimal",
        )
        self.assertEqual(len(generated.raw_bytes), 338)
        self.assertEqual(
            sha256_hex(generated.raw_bytes),
            CANONICAL_FIXTURES["valid-minimal"][1],
        )
        self.assertEqual(
            [len(record) for record in generated.raw_bytes.splitlines()],
            [40, 124, 124, 46],
        )
        self.assertEqual(generated.batch.detail_count, 2)
        self.assertEqual(generated.batch.net_amount_minor, 17_345)


if __name__ == "__main__":
    unittest.main()
