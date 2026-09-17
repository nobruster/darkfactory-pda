"""Unit tests for strict Type 04 sanitized CSV validation."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from loader_common import PostgresLoadError
from raw_publisher import PublishedRaw
from type04_loader import (
    PreparedType04Load,
    _parse_csv,
    _validate_prepared_lineage,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = (
    ROOT
    / "contracts"
    / "types"
    / "04-ted-transfer-settlement"
    / "main"
)
MINIMAL_BATCH = "B202607230000301"
MINIMAL_SOURCE = (
    "NW_TED_SETTLEMENT_20260723_B202607230000301.dat"
)
MINIMAL_SOURCE_CONTROLS: dict[str, int | str] = {
    "currency": "BRL",
    "gross_amount": "1250.00",
    "net_amount": "1000.00",
    "return_amount": "-250.00",
    "return_count": 1,
    "transfer_count": 2,
}
MINIMAL_STAGE_CONTROLS: dict[str, int | str] = {
    **MINIMAL_SOURCE_CONTROLS,
    "row_count": 3,
}


class Type04CsvValidationTest(unittest.TestCase):
    """Prove conditional linkage, signed controls, and privacy fail closed."""

    def test_three_approved_csvs_recompute_exact_controls(self) -> None:
        cases = (
            (
                "expected-sanitized.csv",
                MINIMAL_BATCH,
                MINIMAL_SOURCE,
                MINIMAL_STAGE_CONTROLS,
            ),
            (
                "expected-valid-boundary-sanitized.csv",
                "B200002290000302",
                (
                    "NW_TED_SETTLEMENT_20000229_"
                    "B200002290000302.dat"
                ),
                {
                    "currency": "BRL",
                    "gross_amount": "999999999999.99",
                    "net_amount": "999999999999.99",
                    "return_amount": "0.00",
                    "return_count": 0,
                    "row_count": 1,
                    "transfer_count": 1,
                },
            ),
            (
                "expected-all-returned-zero-net-sanitized.csv",
                "B202607230000304",
                (
                    "NW_TED_SETTLEMENT_20260723_"
                    "B202607230000304.dat"
                ),
                {
                    "currency": "BRL",
                    "gross_amount": "1250.00",
                    "net_amount": "0.00",
                    "return_amount": "-1250.00",
                    "return_count": 2,
                    "row_count": 4,
                    "transfer_count": 2,
                },
            ),
        )
        for filename, batch_id, source_filename, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(
                    _parse_csv(
                        (FIXTURES / filename).read_bytes(),
                        batch_id=batch_id,
                        source_filename=source_filename,
                    ),
                    expected,
                )

    def test_return_must_be_immediate_full_and_inherit_context(self) -> None:
        canonical = (FIXTURES / "expected-sanitized.csv").read_text(
            encoding="utf-8"
        )
        lines = canonical.splitlines()
        cases = (
            "\n".join((lines[0], lines[1], lines[3], lines[2])) + "\n",
            canonical.replace("-250.00", "-249.99", 1),
            canonical.replace(
                "tedacct_c693ea67cef5d1ca5363f9b6",
                "tedacct_aaaaaaaaaaaaaaaaaaaaaaaa",
                1,
            ),
        )

        for contaminated in cases:
            with self.subTest():
                with self.assertRaises(PostgresLoadError):
                    _parse_csv(
                        contaminated.encode("utf-8"),
                        batch_id=MINIMAL_BATCH,
                        source_filename=MINIMAL_SOURCE,
                    )

    def test_noncanonical_money_offset_and_extra_field_are_rejected(
        self,
    ) -> None:
        canonical = (FIXTURES / "expected-sanitized.csv").read_text(
            encoding="utf-8"
        )
        lines = canonical.splitlines()
        extra = "\n".join(
            (f"{lines[0]},unexpected", f"{lines[1]},secret", *lines[2:])
        ) + "\n"
        cases = (
            canonical.replace(",1000.00,", ",01000.00,", 1),
            canonical.replace("-03:00", "-02:00", 1),
            extra,
        )

        for contaminated in cases:
            with self.subTest():
                with self.assertRaises(PostgresLoadError):
                    _parse_csv(
                        contaminated.encode("utf-8"),
                        batch_id=MINIMAL_BATCH,
                        source_filename=MINIMAL_SOURCE,
                    )

    def test_rejection_does_not_disclose_restricted_value(self) -> None:
        restricted = "000123456789"
        canonical = (FIXTURES / "expected-sanitized.csv").read_text(
            encoding="utf-8"
        )
        contaminated = canonical.replace(
            "tedacct_903cfb06cbf3f346ab30aec7",
            restricted,
            1,
        )

        with self.assertRaises(PostgresLoadError) as raised:
            _parse_csv(
                contaminated.encode("utf-8"),
                batch_id=MINIMAL_BATCH,
                source_filename=MINIMAL_SOURCE,
            )
        self.assertNotIn(restricted, str(raised.exception))

    def test_commit_boundary_revalidates_bytes_and_all_stage_controls(
        self,
    ) -> None:
        csv_bytes = (FIXTURES / "expected-sanitized.csv").read_bytes()
        raw = PublishedRaw(
            batch_id=MINIMAL_BATCH,
            file_type="04",
            filename=MINIMAL_SOURCE,
            sha256="a" * 64,
            size_bytes=563,
            manifest_sha256="b" * 64,
            source_controls=MINIMAL_SOURCE_CONTROLS,
        )
        prepared = PreparedType04Load(
            batch_id=MINIMAL_BATCH,
            raw_filename=MINIMAL_SOURCE,
            raw_sha256=raw.sha256,
            raw_manifest_sha256=raw.manifest_sha256,
            source_controls=MINIMAL_SOURCE_CONTROLS,
            csv_filename=MINIMAL_SOURCE.removesuffix(".dat") + ".csv",
            csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
            csv_size_bytes=len(csv_bytes),
            stage_controls=MINIMAL_STAGE_CONTROLS,
            csv_bytes=csv_bytes,
        )
        _validate_prepared_lineage(prepared, raw=raw)

        contaminated = PreparedType04Load(
            batch_id=prepared.batch_id,
            raw_filename=prepared.raw_filename,
            raw_sha256=prepared.raw_sha256,
            raw_manifest_sha256=prepared.raw_manifest_sha256,
            source_controls=prepared.source_controls,
            csv_filename=prepared.csv_filename,
            csv_sha256=prepared.csv_sha256,
            csv_size_bytes=prepared.csv_size_bytes,
            stage_controls={
                **MINIMAL_STAGE_CONTROLS,
                "return_amount": "-249.99",
            },
            csv_bytes=prepared.csv_bytes,
        )
        with self.assertRaises(PostgresLoadError):
            _validate_prepared_lineage(contaminated, raw=raw)


if __name__ == "__main__":
    unittest.main()
