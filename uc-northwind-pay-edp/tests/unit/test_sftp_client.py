from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "legacy" / "runner"))

from sftp_client import SftpBoundaryError, upload_manifest_last  # noqa: E402


class FailingManifestRenameSftp:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def put(self, local: str, remote: str, *, confirm: bool) -> None:
        if not confirm:
            raise AssertionError("test requires confirmed uploads")
        self.files[remote] = Path(local).read_bytes()

    def posix_rename(self, source: str, target: str) -> None:
        if target.endswith("/manifest.json"):
            raise OSError("injected final-manifest rename failure")
        self.files[target] = self.files.pop(source)

    def remove(self, path: str) -> None:
        try:
            del self.files[path]
        except KeyError as exc:
            raise OSError("missing") from exc


class ManifestLastCleanupTest(unittest.TestCase):
    def test_failure_removes_parts_and_already_finalized_artifacts(self) -> None:
        sftp = FailingManifestRenameSftp()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data.dat"
            checksum = root / "data.dat.sha256"
            manifest = root / "manifest.json"
            data.write_bytes(b"source\n")
            checksum.write_bytes(b"digest  data.dat\n")
            manifest.write_bytes(b"{}\n")

            with self.assertRaises(SftpBoundaryError):
                upload_manifest_last(
                    sftp,
                    "/incoming/B202607230000001",
                    (
                        ("data.dat", data),
                        ("data.dat.sha256", checksum),
                        ("manifest.json", manifest),
                    ),
                    manifest_name="manifest.json",
                )

        self.assertEqual(sftp.files, {})


if __name__ == "__main__":
    unittest.main()
