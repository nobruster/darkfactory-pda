"""Unit tests for type-neutral raw publication identity."""

from __future__ import annotations

import unittest

from raw_publisher import PublishedRaw, RawPublicationError


def published_raw(
    *,
    file_type: str,
    source_controls: dict[str, int | str],
) -> PublishedRaw:
    """Build a safe synthetic identity without touching SFTP."""

    return PublishedRaw(
        batch_id="B202607230009999",
        file_type=file_type,
        filename="fixture.dat",
        sha256="a" * 64,
        size_bytes=1,
        manifest_sha256="b" * 64,
        source_controls=source_controls,
    )


class PublishedRawTest(unittest.TestCase):
    """Protect compatibility controls while adding multi-type identity."""

    def test_type_01_compatibility_controls_are_preserved(self) -> None:
        raw = published_raw(
            file_type="01",
            source_controls={
                "currency": "BRL",
                "detail_count": 2,
                "net_amount": "173.45",
            },
        )

        self.assertEqual(raw.source_count, 2)
        self.assertEqual(raw.source_net_amount, "173.45")

    def test_type_02_uses_event_count_without_losing_full_controls(self) -> None:
        controls: dict[str, int | str] = {
            "currency": "BRL",
            "event_count": 2,
            "credit_amount": "200.00",
            "debit_amount": "26.55",
            "net_amount": "173.45",
        }
        raw = published_raw(file_type="02", source_controls=controls)
        controls["event_count"] = 99

        self.assertEqual(raw.source_count, 2)
        self.assertEqual(raw.source_net_amount, "173.45")
        self.assertEqual(raw.source_controls["credit_amount"], "200.00")
        with self.assertRaises(TypeError):
            raw.source_controls["event_count"] = 3  # type: ignore[index]

    def test_missing_primary_controls_fail_closed(self) -> None:
        raw = published_raw(
            file_type="99",
            source_controls={"currency": "BRL"},
        )

        with self.assertRaises(RawPublicationError):
            _ = raw.source_count
        with self.assertRaises(RawPublicationError):
            _ = raw.source_net_amount


if __name__ == "__main__":
    unittest.main()
