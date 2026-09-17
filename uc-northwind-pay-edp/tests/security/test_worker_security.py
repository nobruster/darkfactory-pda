"""Security and privacy regressions for the automatic SFTP worker."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from config import RuntimeConfiguration, SftpRole
from worker import (
    MAX_RAW_BYTES,
    BatchCandidate,
    WorkerCacheConflict,
    WorkerError,
    WorkerLock,
    WorkerSourceRejected,
    discover_ready_batches,
    download_processing_bundle,
    process_candidate,
    remove_cached_bundle,
)


ROOT = Path(__file__).resolve().parents[2]


def configuration(root: Path) -> RuntimeConfiguration:
    """Return inert settings whose runtime and schema live below one root."""

    role = SftpRole("test", "secret")
    return RuntimeConfiguration(
        root=root,
        sftp_host="127.0.0.1",
        sftp_port=22,
        known_hosts=root / ".runtime" / "known_hosts",
        raw_publisher=role,
        processor=role,
        loader=role,
        operator=role,
        postgres_app_user="test",
        postgres_dsn="postgresql://test:test@127.0.0.1/test",
        postgres_admin_dsn="postgresql://admin:test@127.0.0.1/test",
    )


def install_source_schema(root: Path) -> None:
    """Install only the executable schema needed by local bundle validation."""

    target = root / "contracts" / "common"
    target.mkdir(mode=0o700, parents=True)
    shutil.copy2(
        ROOT / "contracts" / "common" / "source-manifest.schema.json",
        target / "source-manifest.schema.json",
    )


def build_source_bundle(root: Path, batch_id: str) -> tuple[Path, str]:
    """Create one schema-valid Type 01 bundle entirely below a test root."""

    bundle = root / "source-fixture" / batch_id
    bundle.mkdir(mode=0o700, parents=True)
    filename = f"NW_CARD_SETTLEMENT_20260723_{batch_id}.dat"
    raw_bytes = b"synthetic worker security fixture\n"
    digest = hashlib.sha256(raw_bytes).hexdigest()
    manifest = {
        "batch_id": batch_id,
        "file_type": {
            "code": "CRD_SETTLE01",
            "contract_version": 1,
            "layout_version": "001",
            "number": "01",
        },
        "schema_version": 1,
        "source_controls": {
            "currency": "BRL",
            "detail_count": 1,
            "net_amount": "1.00",
        },
        "source_file": {
            "encoding": "ISO-8859-1",
            "final_newline": "required",
            "line_ending": "LF",
            "name": filename,
            "sha256": digest,
            "size_bytes": len(raw_bytes),
        },
    }
    (bundle / filename).write_bytes(raw_bytes)
    (bundle / f"{filename}.sha256").write_bytes(
        f"{digest}  {filename}\n".encode("ascii")
    )
    (bundle / "source-manifest.json").write_text(
        json.dumps(
            manifest,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return bundle, filename


def remote_bundle_files(
    bundle: Path,
    *,
    batch_id: str,
    filename: str,
) -> dict[str, bytes]:
    """Project one local fixture into the three remote transport artifacts."""

    remote_root = f"/raw/processing/{batch_id}"
    return {
        f"{remote_root}/source-manifest.json": (
            bundle / "source-manifest.json"
        ).read_bytes(),
        f"{remote_root}/{filename}": (bundle / filename).read_bytes(),
        f"{remote_root}/{filename}.sha256": (
            bundle / f"{filename}.sha256"
        ).read_bytes(),
    }


class ArtifactSftp:
    """Read-only in-memory SFTP artifact view with download accounting."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.downloaded: list[str] = []

    def lstat(self, path: str) -> SimpleNamespace:
        try:
            value = self.files[path]
        except KeyError as exc:
            raise FileNotFoundError(path) from exc
        return SimpleNamespace(
            st_mode=stat.S_IFREG | 0o600,
            st_size=len(value),
        )

    def get(self, remote: str, local: str) -> None:
        self.downloaded.append(remote)
        Path(local).write_bytes(self.files[remote])


def connected_to(fake: ArtifactSftp):
    """Return a context-manager factory compatible with connect_sftp."""

    @contextmanager
    def connected(*args, **kwargs):
        del args, kwargs
        yield fake

    return connected


class WorkerCacheSecurityTest(unittest.TestCase):
    """Protect exact private cache publication and path containment."""

    def test_exact_three_artifact_bundle_is_private_atomic_and_replayable(
        self,
    ) -> None:
        batch_id = "B202607230000001"

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, filename = build_source_bundle(root, batch_id)
            remote_root = f"/raw/processing/{batch_id}"
            files = remote_bundle_files(
                source,
                batch_id=batch_id,
                filename=filename,
            )
            files[f"{remote_root}/generation-receipt.json"] = (
                b'{"untrusted":"remote extra"}\n'
            )
            fake = ArtifactSftp(files)
            install_source_schema(root)
            config = configuration(root)
            self.assertFalse((root / ".runtime").exists())
            with patch(
                "worker.connect_sftp",
                connected_to(fake),
            ):
                bundle, raw = download_processing_bundle(
                    batch_id,
                    configuration=config,
                )
                replay_bundle, replay_raw = download_processing_bundle(
                    batch_id,
                    configuration=config,
                )

            self.assertEqual(bundle, replay_bundle)
            self.assertEqual(raw, replay_raw)
            self.assertEqual(
                {path.name for path in bundle.iterdir()},
                {
                    "source-manifest.json",
                    filename,
                    f"{filename}.sha256",
                },
            )
            self.assertFalse((bundle / "generation-receipt.json").exists())
            self.assertFalse(
                any(
                    "generation-receipt.json" in remote
                    for remote in fake.downloaded
                )
            )
            self.assertEqual(stat.S_IMODE(bundle.stat().st_mode), 0o700)
            for artifact in bundle.iterdir():
                self.assertEqual(
                    stat.S_IMODE(artifact.stat().st_mode),
                    0o600,
                )
            cache_root = root / ".runtime" / "intake-cache"
            self.assertEqual(
                tuple(path.name for path in cache_root.iterdir()),
                (batch_id,),
            )

    def test_replay_rejects_each_symlinked_cached_artifact(self) -> None:
        batch_id = "B202607230000976"
        for artifact_name in (
            "source-manifest.json",
            f"NW_CARD_SETTLEMENT_20260723_{batch_id}.dat",
            f"NW_CARD_SETTLEMENT_20260723_{batch_id}.dat.sha256",
        ):
            with self.subTest(artifact=artifact_name):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    source, filename = build_source_bundle(root, batch_id)
                    install_source_schema(root)
                    fake = ArtifactSftp(
                        remote_bundle_files(
                            source,
                            batch_id=batch_id,
                            filename=filename,
                        )
                    )
                    config = configuration(root)
                    with patch(
                        "worker.connect_sftp",
                        connected_to(fake),
                    ):
                        bundle, _ = download_processing_bundle(
                            batch_id,
                            configuration=config,
                        )
                    artifact = bundle / artifact_name
                    artifact_bytes = artifact.read_bytes()
                    victim = root / "same-bytes-victim"
                    victim.write_bytes(artifact_bytes)
                    artifact.unlink()
                    artifact.symlink_to(victim)

                    with (
                        patch(
                            "worker.connect_sftp",
                            connected_to(fake),
                        ),
                        self.assertRaises(WorkerCacheConflict),
                    ):
                        download_processing_bundle(
                            batch_id,
                            configuration=config,
                        )

                    self.assertEqual(victim.read_bytes(), artifact_bytes)

    def test_extra_cached_receipt_is_rejected_before_pipeline(self) -> None:
        batch_id = "B202607230000977"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, filename = build_source_bundle(root, batch_id)
            install_source_schema(root)
            fake = ArtifactSftp(
                remote_bundle_files(
                    source,
                    batch_id=batch_id,
                    filename=filename,
                )
            )
            config = configuration(root)
            with patch("worker.connect_sftp", connected_to(fake)):
                bundle, _ = download_processing_bundle(
                    batch_id,
                    configuration=config,
                )
            (bundle / "generation-receipt.json").write_text(
                '{"injected":true}\n',
                encoding="utf-8",
            )

            with (
                patch("worker.connect_sftp", connected_to(fake)),
                patch("worker.run_pipeline") as pipeline,
                patch(
                    "worker.quarantine_processing_batch"
                ) as quarantined,
            ):
                outcome = process_candidate(
                    BatchCandidate(batch_id, "processing"),
                    evidence_root=root / "evidence",
                    configuration=config,
                )

            self.assertEqual(outcome.status, "retry_pending")
            self.assertEqual(outcome.code, "LOCAL_CACHE_CONFLICT")
            pipeline.assert_not_called()
            quarantined.assert_not_called()

    def test_multiply_linked_cache_artifact_is_not_replayed(self) -> None:
        batch_id = "B202607230000978"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, filename = build_source_bundle(root, batch_id)
            install_source_schema(root)
            fake = ArtifactSftp(
                remote_bundle_files(
                    source,
                    batch_id=batch_id,
                    filename=filename,
                )
            )
            config = configuration(root)
            with patch("worker.connect_sftp", connected_to(fake)):
                bundle, _ = download_processing_bundle(
                    batch_id,
                    configuration=config,
                )
            os.link(bundle / filename, root / "outside-hardlink")

            with (
                patch("worker.connect_sftp", connected_to(fake)),
                self.assertRaises(WorkerCacheConflict),
            ):
                download_processing_bundle(
                    batch_id,
                    configuration=config,
                )

    def test_unsafe_cached_child_blocks_terminal_removal(self) -> None:
        batch_id = "B202607230000979"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, filename = build_source_bundle(root, batch_id)
            install_source_schema(root)
            fake = ArtifactSftp(
                remote_bundle_files(
                    source,
                    batch_id=batch_id,
                    filename=filename,
                )
            )
            config = configuration(root)
            with patch("worker.connect_sftp", connected_to(fake)):
                bundle, _ = download_processing_bundle(
                    batch_id,
                    configuration=config,
                )
            checksum = bundle / f"{filename}.sha256"
            checksum_bytes = checksum.read_bytes()
            victim = root / "checksum-victim"
            victim.write_bytes(checksum_bytes)
            checksum.unlink()
            checksum.symlink_to(victim)

            with self.assertRaises(WorkerCacheConflict):
                remove_cached_bundle(
                    batch_id,
                    configuration=config,
                )

            self.assertTrue(bundle.exists())
            self.assertEqual(victim.read_bytes(), checksum_bytes)

    def test_traversal_manifest_is_rejected_before_raw_download(self) -> None:
        batch_id = "B202607230000971"
        remote_manifest = (
            json.dumps(
                {
                    "batch_id": batch_id,
                    "source_file": {
                        "name": "../../private.txt",
                        "size_bytes": 10,
                    },
                }
            )
            + "\n"
        ).encode("utf-8")
        remote_root = f"/raw/processing/{batch_id}"
        fake = ArtifactSftp(
            {
                f"{remote_root}/source-manifest.json": remote_manifest,
            }
        )

        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(Path(temporary))
            with (
                patch(
                    "worker.connect_sftp",
                    connected_to(fake),
                ),
                self.assertRaises(WorkerSourceRejected),
            ):
                download_processing_bundle(
                    batch_id,
                    configuration=config,
                )

        self.assertEqual(
            fake.downloaded,
            [f"{remote_root}/source-manifest.json"],
        )

    def test_declared_raw_size_is_bounded_before_raw_download(self) -> None:
        batch_id = "B202607230000975"
        remote_manifest = (
            json.dumps(
                {
                    "batch_id": batch_id,
                    "source_file": {
                        "name": "bounded.dat",
                        "size_bytes": MAX_RAW_BYTES + 1,
                    },
                }
            )
            + "\n"
        ).encode("utf-8")
        remote_root = f"/raw/processing/{batch_id}"
        fake = ArtifactSftp(
            {
                f"{remote_root}/source-manifest.json": remote_manifest,
            }
        )

        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(Path(temporary))
            with (
                patch(
                    "worker.connect_sftp",
                    connected_to(fake),
                ),
                self.assertRaises(WorkerSourceRejected),
            ):
                download_processing_bundle(
                    batch_id,
                    configuration=config,
                )

        self.assertEqual(
            fake.downloaded,
            [f"{remote_root}/source-manifest.json"],
        )

    def test_cache_conflict_remains_for_retry_instead_of_quarantine(self) -> None:
        candidate = BatchCandidate("B202607230000972", "processing")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch(
                    "worker.download_processing_bundle",
                    side_effect=WorkerCacheConflict(
                        "private raw 12345678909"
                    ),
                ),
                patch("worker.quarantine_processing_batch") as quarantined,
            ):
                outcome = process_candidate(
                    candidate,
                    evidence_root=root / "evidence",
                    configuration=configuration(root),
                )

        self.assertEqual(outcome.status, "retry_pending")
        self.assertEqual(outcome.code, "LOCAL_CACHE_CONFLICT")
        quarantined.assert_not_called()
        self.assertNotIn("12345678909", json.dumps(outcome.as_dict()))

    def test_cache_recovery_is_local_and_revalidates_exact_private_bundle(
        self,
    ) -> None:
        batch_id = "B202607230000980"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, filename = build_source_bundle(root, batch_id)
            install_source_schema(root)
            fake = ArtifactSftp(
                remote_bundle_files(
                    source,
                    batch_id=batch_id,
                    filename=filename,
                )
            )
            config = configuration(root)
            with patch("worker.connect_sftp", connected_to(fake)):
                bundle, _ = download_processing_bundle(
                    batch_id,
                    configuration=config,
                )

            with (
                patch(
                    "worker.connect_sftp",
                    side_effect=AssertionError("cache replay used SFTP"),
                ) as connected,
                patch(
                    "worker.run_pipeline",
                    return_value=root / "evidence" / batch_id,
                ) as pipeline,
                patch(
                    "worker._read_terminal_status",
                    return_value="succeeded",
                ),
                patch("worker.remove_cached_bundle") as removed,
            ):
                outcome = process_candidate(
                    BatchCandidate(batch_id, "cache"),
                    evidence_root=root / "evidence",
                    configuration=config,
                )

            self.assertEqual(outcome.source_zone, "cache")
            self.assertEqual(outcome.status, "succeeded")
            self.assertEqual(outcome.code, "TERMINAL")
            connected.assert_not_called()
            self.assertEqual(pipeline.call_args.args[1], bundle)
            self.assertIs(
                pipeline.call_args.kwargs["recovery_only"],
                True,
            )
            removed.assert_called_once_with(
                batch_id,
                configuration=config,
            )

    def test_unsafe_cache_recovery_never_reaches_pipeline_or_quarantine(
        self,
    ) -> None:
        batch_id = "B202607230000981"
        mutations = (
            "extra",
            "hardlink",
            "symlink",
            "shared-directory",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    source, filename = build_source_bundle(root, batch_id)
                    install_source_schema(root)
                    fake = ArtifactSftp(
                        remote_bundle_files(
                            source,
                            batch_id=batch_id,
                            filename=filename,
                        )
                    )
                    config = configuration(root)
                    with patch(
                        "worker.connect_sftp",
                        connected_to(fake),
                    ):
                        bundle, _ = download_processing_bundle(
                            batch_id,
                            configuration=config,
                        )

                    if mutation == "extra":
                        (bundle / "generation-receipt.json").write_text(
                            '{"unsafe":true}\n',
                            encoding="utf-8",
                        )
                    elif mutation == "hardlink":
                        os.link(
                            bundle / filename,
                            root / "outside-hardlink",
                        )
                    elif mutation == "symlink":
                        manifest = bundle / "source-manifest.json"
                        victim = root / "manifest-victim"
                        victim.write_bytes(manifest.read_bytes())
                        manifest.unlink()
                        manifest.symlink_to(victim)
                    else:
                        bundle.chmod(0o750)

                    with (
                        patch("worker.run_pipeline") as pipeline,
                        patch(
                            "worker.quarantine_processing_batch"
                        ) as quarantined,
                    ):
                        outcome = process_candidate(
                            BatchCandidate(batch_id, "cache"),
                            evidence_root=root / "evidence",
                            configuration=config,
                        )

                    self.assertEqual(outcome.source_zone, "cache")
                    self.assertEqual(outcome.status, "retry_pending")
                    self.assertEqual(
                        outcome.code,
                        "LOCAL_CACHE_CONFLICT",
                    )
                    pipeline.assert_not_called()
                    quarantined.assert_not_called()

    def test_terminal_cache_replay_removes_bundle_and_leaves_no_candidate(
        self,
    ) -> None:
        batch_id = "B202607230000982"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, filename = build_source_bundle(root, batch_id)
            install_source_schema(root)
            fake = ArtifactSftp(
                remote_bundle_files(
                    source,
                    batch_id=batch_id,
                    filename=filename,
                )
            )
            config = configuration(root)
            with patch("worker.connect_sftp", connected_to(fake)):
                bundle, _ = download_processing_bundle(
                    batch_id,
                    configuration=config,
                )

            evidence = root / "evidence" / batch_id
            evidence.mkdir(mode=0o700, parents=True)
            (evidence / "final-status.json").write_text(
                json.dumps(
                    {
                        "batch_id": batch_id,
                        "status": "succeeded",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with patch("worker.run_pipeline", return_value=evidence):
                outcome = process_candidate(
                    BatchCandidate(batch_id, "cache"),
                    evidence_root=root / "evidence",
                    configuration=config,
                )

            self.assertEqual(outcome.status, "succeeded")
            self.assertEqual(outcome.code, "TERMINAL")
            self.assertFalse(bundle.exists())

            @contextmanager
            def connected(*args, **kwargs):
                del args, kwargs
                yield object()

            with (
                patch("worker.connect_sftp", connected),
                patch("worker._ready_in_zone", return_value=((), 0)),
            ):
                discovery = discover_ready_batches(
                    configuration=config,
                )
            self.assertEqual(discovery.candidates, ())
            self.assertEqual(discovery.ready_count, 0)

    def test_invalid_terminal_evidence_retains_recoverable_cache(self) -> None:
        batch_id = "B202607230000983"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, filename = build_source_bundle(root, batch_id)
            install_source_schema(root)
            fake = ArtifactSftp(
                remote_bundle_files(
                    source,
                    batch_id=batch_id,
                    filename=filename,
                )
            )
            config = configuration(root)
            with patch("worker.connect_sftp", connected_to(fake)):
                bundle, _ = download_processing_bundle(
                    batch_id,
                    configuration=config,
                )

            evidence = root / "evidence" / batch_id
            evidence.mkdir(mode=0o700, parents=True)
            (evidence / "final-status.json").write_text(
                json.dumps(
                    {
                        "batch_id": "B202607230000984",
                        "status": "succeeded",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with patch("worker.run_pipeline", return_value=evidence):
                outcome = process_candidate(
                    BatchCandidate(batch_id, "cache"),
                    evidence_root=root / "evidence",
                    configuration=config,
                )

            self.assertEqual(outcome.status, "retry_pending")
            self.assertEqual(outcome.code, "PIPELINE_RETRY_PENDING")
            self.assertTrue(bundle.is_dir())


class WorkerBoundarySecurityTest(unittest.TestCase):
    """Protect local lock targets and public diagnostic privacy."""

    def test_lock_refuses_a_symbolic_link_without_touching_its_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / ".runtime"
            runtime.mkdir(mode=0o700)
            victim = root / "victim.txt"
            victim.write_text("unchanged\n", encoding="utf-8")
            (runtime / "worker.lock").symlink_to(victim)

            with self.assertRaises(WorkerError):
                with WorkerLock(runtime / "worker.lock"):
                    pass

            self.assertEqual(victim.read_text(encoding="utf-8"), "unchanged\n")

    def test_candidate_rejects_path_traversal_and_unknown_zone(self) -> None:
        with self.assertRaises(ValueError):
            BatchCandidate("../../private", "incoming")
        with self.assertRaises(ValueError):
            BatchCandidate("B202607230000973", "../../raw")
        with self.assertRaises(ValueError):
            BatchCandidate("B202607230000973", "cache", True)

    def test_sensitive_exception_text_never_enters_batch_outcome(self) -> None:
        candidate = BatchCandidate("B202607230000974", "processing")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch(
                "worker.download_processing_bundle",
                side_effect=RuntimeError(
                    "merchant 12345678000195 account 987654321"
                ),
            ):
                outcome = process_candidate(
                    candidate,
                    evidence_root=root / "evidence",
                    configuration=configuration(root),
                )

        serialized = json.dumps(outcome.as_dict(), sort_keys=True)
        self.assertEqual(outcome.code, "SOURCE_DOWNLOAD_FAILED")
        self.assertNotIn("12345678000195", serialized)
        self.assertNotIn("987654321", serialized)


if __name__ == "__main__":
    unittest.main()
