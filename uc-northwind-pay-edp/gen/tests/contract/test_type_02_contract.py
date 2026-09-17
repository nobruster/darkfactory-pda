"""Executable byte-for-byte contract tests for Type 02 DataGen."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from checksum import sha256_hex
from generation import generate


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_ROOT = REPOSITORY_ROOT / "contracts" / "types"
CANONICAL_ROOT = CONTRACTS_ROOT / "02-instant-payment-events" / "main"

CANONICAL_FIXTURES = {
    "valid-minimal": (
        "valid-minimal.txt",
        "a5c2ec1c586aaa2fd79c95555cc02a9d"
        "2596e473805c48c506201c18c6f7d5a9",
    ),
    "valid-boundary": (
        "valid-boundary.txt",
        "93c084cf65d48797eaaef4468d491ffb"
        "33403a750c9e691098bb6aa91e91e471",
    ),
    "escaped-content": (
        "escaped-content.txt",
        "1f2dac2f89f54893f44e9a8aea148971"
        "446429e6f621b6734c8632d6d64a0345",
    ),
    "malformed": (
        "malformed.txt",
        "f5a54cf908a9a2d256b1c98d991f569"
        "5fa829eccaf482ea555e3a1032692fd0b",
    ),
    "DF-SOURCE-002": (
        "df-source-002.txt",
        "685c2617e7f07951181eaf646f349f6d"
        "d798638a7d14e4d268ef8f9d87d0d87d",
    ),
}


class Type02ContractTest(unittest.TestCase):
    """Prove generated raw bytes equal the independent approved fixtures."""

    def assert_sensitive_bytes_equal(
        self,
        *,
        actual: bytes,
        expected: bytes,
        scenario: str,
    ) -> None:
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
            "Type 02 raw artifacts differ without exposing their contents: "
            f"scenario={scenario}, "
            f"actual_length={len(actual)}, "
            f"expected_length={len(expected)}, "
            f"actual_sha256={sha256_hex(actual)}, "
            f"expected_sha256={sha256_hex(expected)}, "
            f"first_mismatch_offset={mismatch}"
        )

    def test_all_five_scenarios_match_canonical_raw_bytes(self) -> None:
        for scenario, (filename, expected_hash) in CANONICAL_FIXTURES.items():
            with self.subTest(scenario=scenario):
                with tempfile.TemporaryDirectory() as output:
                    bundle = generate(
                        type_number="02",
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

    def test_transport_bytes_are_strict_utf8_lf_with_one_final_newline(
        self,
    ) -> None:
        for scenario in CANONICAL_FIXTURES:
            with self.subTest(scenario=scenario):
                with tempfile.TemporaryDirectory() as output:
                    bundle = generate(
                        type_number="02",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS_ROOT,
                    )
                    raw = bundle.raw_file.read_bytes()
                    raw.decode("utf-8", errors="strict")
                    self.assertNotIn(b"\r", raw)
                    self.assertTrue(raw.endswith(b"\n"))
                    self.assertFalse(raw.endswith(b"\n\n"))
                    self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
