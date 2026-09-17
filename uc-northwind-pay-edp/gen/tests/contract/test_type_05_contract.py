"""Executable byte-for-byte contract tests for Type 05 DataGen."""

from __future__ import annotations

import tempfile
import unicodedata
import unittest
from pathlib import Path

from checksum import sha256_hex
from generation import generate


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts" / "types"
MAIN = CONTRACTS / "05-merchant-fee-assessment" / "main"
CANONICAL = {
    "valid-minimal": (
        "valid-minimal.csv",
        "457e1737d6540850e9543766c3ffdfd608"
        "141d06c9f1cc484d67458753f5df53",
    ),
    "valid-boundary": (
        "valid-boundary.csv",
        "fd3cc536e1d61fca14e397a50d194d3f0"
        "037680756df69350f0f03a140ca594b",
    ),
    "malformed": (
        "malformed.csv",
        "f9b1478fa6407aff4f45a04ec3261dac26"
        "4a0254f7bfec356c1380906c0929cb",
    ),
    "rounding-half-up": (
        "rounding-half-up.csv",
        "7964eb84cb89816e814ef790c4feb4add9"
        "0350f3a8d3aca31875427241e474a5",
    ),
    "DF-SOURCE-005": (
        "df-source-005.csv",
        "f6e018b1b3bec55d6b56c4ae46ea650790"
        "53176644502c51d384acb9498ef145",
    ),
}


class Type05ContractTest(unittest.TestCase):
    """Prove generated UTF-8 bytes equal independently approved fixtures."""

    def test_all_five_scenarios_match_pinned_raw_bytes(self) -> None:
        for scenario, (filename, expected_hash) in CANONICAL.items():
            with self.subTest(scenario=scenario):
                with tempfile.TemporaryDirectory() as output:
                    bundle = generate(
                        type_number="05",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS,
                    )
                    actual = bundle.raw_file.read_bytes()
                    expected = (MAIN / filename).read_bytes()
                    if actual != expected:
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
                            "Type 05 raw bytes differ without disclosure: "
                            f"scenario={scenario}, "
                            f"actual_sha256={sha256_hex(actual)}, "
                            f"expected_sha256={sha256_hex(expected)}, "
                            f"first_mismatch_offset={mismatch}"
                        )
                    self.assertEqual(sha256_hex(actual), expected_hash)

    def test_transport_is_strict_utf8_nfc_lf_with_bounded_lines(self) -> None:
        for scenario in CANONICAL:
            with self.subTest(scenario=scenario):
                with tempfile.TemporaryDirectory() as output:
                    raw = generate(
                        type_number="05",
                        scenario=scenario,
                        output_root=Path(output),
                        contracts_root=CONTRACTS,
                    ).raw_file.read_bytes()
                text = raw.decode("utf-8", errors="strict")
                self.assertEqual(unicodedata.normalize("NFC", text), text)
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                self.assertTrue(raw.endswith(b"\n"))
                self.assertNotIn(b"\n\n", raw)
                self.assertTrue(
                    all(len(line) <= 512 for line in raw.splitlines())
                )


if __name__ == "__main__":
    unittest.main()
