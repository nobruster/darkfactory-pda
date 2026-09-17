"""Focused unit contracts for the automatic host-side SFTP worker."""

from __future__ import annotations

import errno
import io
import json
import signal
import stat
import tempfile
import threading
import unittest
from contextlib import contextmanager, redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from config import RuntimeConfiguration, SftpRole
from raw_intake import ClaimedRaw, RawIntakeError
from raw_publisher import PublishedRaw, RawPublicationError
from worker import (
    BatchCandidate,
    BatchOutcome,
    CycleReport,
    DiscoveryResult,
    WorkerAlreadyRunningError,
    WorkerError,
    WorkerLock,
    WorkerService,
    WorkerSourceRejected,
    build_parser,
    clean_signal_stop,
    discover_ready_batches,
    process_candidate,
    run_cycle,
)


def configuration(root: Path) -> RuntimeConfiguration:
    """Return inert connection settings rooted in one temporary directory."""

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


def published(batch_id: str, file_type: str) -> PublishedRaw:
    """Build a safe source identity for a mocked processing download."""

    return PublishedRaw(
        batch_id=batch_id,
        file_type=file_type,
        filename=f"worker-{batch_id}.dat",
        sha256="a" * 64,
        size_bytes=10,
        manifest_sha256="b" * 64,
        source_controls={},
    )


class DiscoverySftp:
    """Minimal SFTP directory view for readiness and ordering tests."""

    def __init__(
        self,
        entries: dict[str, tuple[SimpleNamespace, ...]],
        regular_files: set[str],
    ) -> None:
        self.entries = entries
        self.regular_files = regular_files

    def listdir_attr(self, path: str) -> list[SimpleNamespace]:
        return list(self.entries[path])

    def lstat(self, path: str) -> SimpleNamespace:
        if path not in self.regular_files:
            raise FileNotFoundError(errno.ENOENT, "not found", path)
        return SimpleNamespace(
            st_mode=stat.S_IFREG | 0o600,
            st_size=10,
        )


def directory(name: str) -> SimpleNamespace:
    """Return one fake SFTP directory attribute."""

    return SimpleNamespace(
        filename=name,
        st_mode=stat.S_IFDIR | 0o770,
    )


def regular(name: str) -> SimpleNamespace:
    """Return one fake non-directory SFTP attribute."""

    return SimpleNamespace(
        filename=name,
        st_mode=stat.S_IFREG | 0o660,
    )


class WorkerDiscoveryTest(unittest.TestCase):
    """Prove readiness, sorting, recovery priority, and bounded selection."""

    def test_only_final_manifests_are_ready_in_stable_zone_order(self) -> None:
        processing_batch = "B202607230000904"
        incoming_first = "B202607230000902"
        incoming_second = "B202607230000903"
        incomplete = "B202607230000901"
        fake = DiscoverySftp(
            {
                "/raw/processing": (
                    directory(processing_batch),
                    regular("source-manifest.json.part"),
                ),
                "/raw/incoming": (
                    directory(incoming_second),
                    directory(incomplete),
                    directory(incoming_first),
                    directory("../unsafe"),
                ),
            },
            {
                (
                    f"/raw/processing/{processing_batch}/"
                    "source-manifest.json"
                ),
                f"/raw/incoming/{incoming_first}/source-manifest.json",
                f"/raw/incoming/{incoming_second}/source-manifest.json",
            },
        )

        @contextmanager
        def connected(*args, **kwargs):
            del args, kwargs
            yield fake

        with tempfile.TemporaryDirectory() as temporary:
            with patch("worker.connect_sftp", connected):
                result = discover_ready_batches(
                    configuration=configuration(Path(temporary)),
                    max_batches=2,
                )

        self.assertEqual(
            result.candidates,
            (
                BatchCandidate(processing_batch, "processing"),
                BatchCandidate(incoming_first, "incoming"),
            ),
        )
        self.assertEqual(result.ready_count, 3)
        self.assertEqual(result.deferred_count, 1)
        self.assertEqual(result.ignored_count, 3)

    def test_batch_in_both_zones_becomes_one_fail_closed_outcome(
        self,
    ) -> None:
        batch_id = "B202607230000905"
        fake = DiscoverySftp(
            {
                "/raw/processing": (directory(batch_id),),
                "/raw/incoming": (directory(batch_id),),
            },
            {
                f"/raw/processing/{batch_id}/source-manifest.json",
                f"/raw/incoming/{batch_id}/source-manifest.json",
            },
        )

        @contextmanager
        def connected(*args, **kwargs):
            del args, kwargs
            yield fake

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            cache_root = root / ".runtime" / "intake-cache"
            cache_root.mkdir(mode=0o700, parents=True)
            cache_root.chmod(0o700)
            cached = cache_root / batch_id
            cached.mkdir(mode=0o700)
            cached.chmod(0o700)
            with patch("worker.connect_sftp", connected):
                result = discover_ready_batches(configuration=config)
            outcome = process_candidate(
                result.candidates[0],
                evidence_root=root / "evidence",
                configuration=config,
            )

        self.assertEqual(
            result.candidates,
            (BatchCandidate(batch_id, "processing", True),),
        )
        self.assertEqual(result.ready_count, 1)
        self.assertEqual(result.deferred_count, 0)
        self.assertEqual(outcome.status, "retry_pending")
        self.assertEqual(outcome.code, "SFTP_ZONE_AMBIGUITY")

    def test_retained_cache_is_deduplicated_and_prioritized_before_incoming(
        self,
    ) -> None:
        processing_batch = "B202607230000906"
        cache_batch = "B202607230000907"
        incoming_batch = "B202607230000908"
        fake = DiscoverySftp(
            {
                "/raw/processing": (directory(processing_batch),),
                "/raw/incoming": (directory(incoming_batch),),
            },
            {
                (
                    f"/raw/processing/{processing_batch}/"
                    "source-manifest.json"
                ),
                f"/raw/incoming/{incoming_batch}/source-manifest.json",
            },
        )

        @contextmanager
        def connected(*args, **kwargs):
            del args, kwargs
            yield fake

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache_root = root / ".runtime" / "intake-cache"
            cache_root.mkdir(mode=0o700, parents=True)
            cache_root.chmod(0o700)
            for name in (
                processing_batch,
                cache_batch,
                incoming_batch,
            ):
                entry = cache_root / name
                entry.mkdir(mode=0o700)
                entry.chmod(0o700)
            (cache_root / ".partial-download").mkdir(mode=0o700)

            with patch("worker.connect_sftp", connected):
                result = discover_ready_batches(
                    configuration=configuration(root),
                    max_batches=2,
                )

        self.assertEqual(
            result.candidates,
            (
                BatchCandidate(processing_batch, "processing"),
                BatchCandidate(cache_batch, "cache"),
            ),
        )
        self.assertEqual(result.ready_count, 3)
        self.assertEqual(result.deferred_count, 1)
        self.assertEqual(result.ignored_count, 1)

    def test_cache_discovery_has_an_independent_hard_entry_bound(self) -> None:
        fake = DiscoverySftp(
            {
                "/raw/processing": (),
                "/raw/incoming": (),
            },
            set(),
        )

        @contextmanager
        def connected(*args, **kwargs):
            del args, kwargs
            yield fake

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache_root = root / ".runtime" / "intake-cache"
            cache_root.mkdir(mode=0o700, parents=True)
            cache_root.chmod(0o700)
            for batch_id in (
                "B202607230000909",
                "B202607230000910",
            ):
                entry = cache_root / batch_id
                entry.mkdir(mode=0o700)
                entry.chmod(0o700)

            with (
                patch("worker.connect_sftp", connected),
                patch("worker.MAX_CACHE_DIRECTORY_ENTRIES", 1),
                self.assertRaises(WorkerError),
            ):
                discover_ready_batches(configuration=configuration(root))


class WorkerDispatchTest(unittest.TestCase):
    """Prove closed type routing and batch-scoped failure isolation."""

    def test_all_five_manifest_types_dispatch_with_no_scenario(self) -> None:
        batch_types = {
            f"B20260723000090{number}": f"0{number}"
            for number in range(1, 6)
        }
        observed_types: list[str] = []

        def downloaded(
            batch_id: str,
            *,
            configuration: RuntimeConfiguration,
        ) -> tuple[Path, PublishedRaw]:
            del configuration
            return Path("/private/cache") / batch_id, published(
                batch_id,
                batch_types[batch_id],
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)

            def checked_pipeline(adapter, bundle, **kwargs):
                observed_types.append(adapter.type_number)
                self.assertIsNone(kwargs["scenario"])
                self.assertIn(bundle.name, batch_types)
                self.assertIs(kwargs["configuration"], config)
                return Path("/private/evidence")

            with (
                patch(
                    "worker.download_processing_bundle",
                    side_effect=downloaded,
                ),
                patch("worker.run_pipeline", side_effect=checked_pipeline),
                patch(
                    "worker._read_terminal_status",
                    return_value="succeeded",
                ),
                patch("worker.remove_cached_bundle"),
            ):
                outcomes = tuple(
                    process_candidate(
                        BatchCandidate(batch_id, "processing"),
                        evidence_root=root / "evidence",
                        configuration=config,
                    )
                    for batch_id in batch_types
                )

        self.assertEqual(observed_types, ["01", "02", "03", "04", "05"])
        self.assertEqual(
            tuple(outcome.status for outcome in outcomes),
            ("succeeded",) * 5,
        )

    def test_bad_peer_does_not_block_the_next_ready_batch(self) -> None:
        first = BatchCandidate("B202607230000911", "processing")
        second = BatchCandidate("B202607230000912", "incoming")
        discovery = DiscoveryResult((first, second), 2, 0, 0)
        successful = BatchOutcome(
            second.batch_id,
            second.zone,
            "succeeded",
            "TERMINAL",
            "02",
        )

        def handled(candidate, **kwargs):
            del kwargs
            if candidate == first:
                raise RuntimeError("private raw value 12345678909")
            return successful

        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch(
                    "worker.discover_ready_batches",
                    return_value=discovery,
                ),
                patch("worker.process_candidate", side_effect=handled),
            ):
                report = run_cycle(
                    evidence_root=Path(temporary) / "evidence",
                    configuration=configuration(Path(temporary)),
                )

        self.assertEqual(
            tuple(outcome.status for outcome in report.outcomes),
            ("retry_pending", "succeeded"),
        )
        self.assertNotIn("12345678909", json.dumps(report.as_dict()))

    def test_incoming_success_claims_before_manifest_type_dispatch(self) -> None:
        batch_id = "B202607230000913"
        raw = published(batch_id, "03")
        claimed_raw = ClaimedRaw(
            batch_id=batch_id,
            file_type=raw.file_type,
            filename=raw.filename,
            sha256=raw.sha256,
            manifest_sha256=raw.manifest_sha256,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch("worker.preflight_incoming_bounds") as preflight,
                patch(
                    "worker.claim_batch",
                    return_value=claimed_raw,
                ) as claimed,
                patch(
                    "worker.download_processing_bundle",
                    return_value=(root / batch_id, raw),
                ) as downloaded,
                patch(
                    "worker.run_pipeline",
                    return_value=root / "evidence" / batch_id,
                ) as pipeline,
                patch(
                    "worker._read_terminal_status",
                    return_value="succeeded",
                ),
                patch("worker.remove_cached_bundle"),
            ):
                outcome = process_candidate(
                    BatchCandidate(batch_id, "incoming"),
                    evidence_root=root / "evidence",
                    configuration=configuration(root),
                )

        self.assertEqual(outcome.status, "succeeded")
        preflight.assert_called_once()
        claimed.assert_called_once()
        downloaded.assert_called_once()
        self.assertEqual(
            pipeline.call_args.args[0].type_number,
            "03",
        )
        self.assertIsNone(pipeline.call_args.kwargs["scenario"])

    def test_processing_recovery_skips_claim_and_retains_transient_failure(
        self,
    ) -> None:
        batch_id = "B202607230000921"
        candidate = BatchCandidate(batch_id, "processing")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch(
                    "worker.download_processing_bundle",
                    return_value=(
                        root / batch_id,
                        published(batch_id, "01"),
                    ),
                ),
                patch(
                    "worker.run_pipeline",
                    side_effect=RuntimeError(
                        "transient failure with 12345678909"
                    ),
                ),
                patch("worker.claim_batch") as claimed,
                patch("worker.quarantine_processing_batch") as quarantined,
            ):
                outcome = process_candidate(
                    candidate,
                    evidence_root=root / "evidence",
                    configuration=configuration(root),
                )

        self.assertEqual(outcome.status, "retry_pending")
        self.assertEqual(outcome.code, "PIPELINE_RETRY_PENDING")
        claimed.assert_not_called()
        quarantined.assert_not_called()
        self.assertNotIn("12345678909", json.dumps(outcome.as_dict()))

    def test_cache_recovery_runs_pipeline_directly_then_removes_cache(
        self,
    ) -> None:
        batch_id = "B202607230000922"
        candidate = BatchCandidate(batch_id, "cache")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            bundle = root / ".runtime" / "intake-cache" / batch_id
            raw = published(batch_id, "05")
            with (
                patch(
                    "worker.load_cached_bundle",
                    return_value=(bundle, raw),
                ) as loaded,
                patch("worker.download_processing_bundle") as downloaded,
                patch("worker.preflight_incoming_bounds") as preflight,
                patch("worker.claim_batch") as claimed,
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
                    candidate,
                    evidence_root=root / "evidence",
                    configuration=config,
                )

        self.assertEqual(outcome.source_zone, "cache")
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.code, "TERMINAL")
        self.assertEqual(outcome.file_type, "05")
        loaded.assert_called_once_with(batch_id, configuration=config)
        downloaded.assert_not_called()
        preflight.assert_not_called()
        claimed.assert_not_called()
        self.assertEqual(pipeline.call_args.args[1], bundle)
        self.assertIs(
            pipeline.call_args.kwargs["recovery_only"],
            True,
        )
        removed.assert_called_once_with(batch_id, configuration=config)

    def test_cache_pipeline_failure_is_retryable_and_retains_bundle(
        self,
    ) -> None:
        batch_id = "B202607230000923"
        candidate = BatchCandidate(batch_id, "cache")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch(
                    "worker.load_cached_bundle",
                    return_value=(
                        root / batch_id,
                        published(batch_id, "01"),
                    ),
                ),
                patch(
                    "worker.run_pipeline",
                    side_effect=RuntimeError(
                        "transient recovery failure 12345678909"
                    ),
                ),
                patch("worker.remove_cached_bundle") as removed,
            ):
                outcome = process_candidate(
                    candidate,
                    evidence_root=root / "evidence",
                    configuration=configuration(root),
                )

        self.assertEqual(outcome.source_zone, "cache")
        self.assertEqual(outcome.status, "retry_pending")
        self.assertEqual(outcome.code, "PIPELINE_RETRY_PENDING")
        removed.assert_not_called()
        self.assertNotIn("12345678909", json.dumps(outcome.as_dict()))

    def test_unsafe_cache_peer_does_not_block_the_next_recovery(self) -> None:
        unsafe = BatchCandidate("B202607230000924", "cache")
        safe = BatchCandidate("B202607230000925", "cache")
        discovery = DiscoveryResult((unsafe, safe), 2, 0, 0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)

            def loaded(
                batch_id: str,
                *,
                configuration: RuntimeConfiguration,
            ) -> tuple[Path, PublishedRaw]:
                self.assertIs(configuration, config)
                if batch_id == unsafe.batch_id:
                    raise WorkerError("unsafe cache secret 12345678909")
                return root / batch_id, published(batch_id, "02")

            with (
                patch(
                    "worker.discover_ready_batches",
                    return_value=discovery,
                ),
                patch(
                    "worker.load_cached_bundle",
                    side_effect=loaded,
                ),
                patch(
                    "worker.run_pipeline",
                    return_value=root / "evidence" / safe.batch_id,
                ),
                patch(
                    "worker._read_terminal_status",
                    return_value="succeeded",
                ),
                patch("worker.remove_cached_bundle"),
            ):
                report = run_cycle(
                    evidence_root=root / "evidence",
                    configuration=config,
                )

        self.assertEqual(
            tuple(outcome.status for outcome in report.outcomes),
            ("retry_pending", "succeeded"),
        )
        self.assertEqual(
            tuple(outcome.code for outcome in report.outcomes),
            ("LOCAL_CACHE_CONFLICT", "TERMINAL"),
        )
        self.assertNotIn("12345678909", json.dumps(report.as_dict()))

    def test_terminal_cleanup_failure_is_replayed_until_cache_is_removed(
        self,
    ) -> None:
        batch_id = "B202607230000926"
        candidate = BatchCandidate(batch_id, "cache")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            with (
                patch(
                    "worker.load_cached_bundle",
                    return_value=(
                        root / batch_id,
                        published(batch_id, "04"),
                    ),
                ),
                patch(
                    "worker.run_pipeline",
                    return_value=root / "evidence" / batch_id,
                ) as pipeline,
                patch(
                    "worker._read_terminal_status",
                    return_value="succeeded",
                ),
                patch(
                    "worker.remove_cached_bundle",
                    side_effect=(
                        WorkerError("temporary cleanup failure"),
                        None,
                    ),
                ) as removed,
            ):
                first = process_candidate(
                    candidate,
                    evidence_root=root / "evidence",
                    configuration=config,
                )
                second = process_candidate(
                    candidate,
                    evidence_root=root / "evidence",
                    configuration=config,
                )

        self.assertEqual(first.status, "succeeded")
        self.assertEqual(first.code, "TERMINAL_CACHE_RETAINED")
        self.assertEqual(second.status, "succeeded")
        self.assertEqual(second.code, "TERMINAL")
        self.assertEqual(pipeline.call_count, 2)
        self.assertEqual(removed.call_count, 2)

    def test_verified_intake_rejection_is_a_quarantine_outcome(self) -> None:
        candidate = BatchCandidate("B202607230000931", "incoming")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch("worker.preflight_incoming_bounds"),
                patch(
                    "worker.claim_batch",
                    side_effect=RawIntakeError(
                        "SOURCE_INTEGRITY_ERROR",
                        "raw account 12345678909",
                        quarantine_verified=True,
                    ),
                ),
                patch("worker.download_processing_bundle") as downloaded,
            ):
                outcome = process_candidate(
                    candidate,
                    evidence_root=root / "evidence",
                    configuration=configuration(root),
                )

        self.assertEqual(outcome.status, "quarantined")
        self.assertEqual(outcome.code, "SOURCE_INTEGRITY_ERROR")
        downloaded.assert_not_called()
        self.assertNotIn("12345678909", json.dumps(outcome.as_dict()))

    def test_unverified_intake_quarantine_remains_retry_pending(self) -> None:
        candidate = BatchCandidate("B202607230000933", "incoming")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch("worker.preflight_incoming_bounds"),
                patch(
                    "worker.claim_batch",
                    side_effect=RawIntakeError(
                        "SOURCE_INTEGRITY_ERROR",
                        "raw account 12345678909",
                    ),
                ),
                patch("worker.download_processing_bundle") as downloaded,
            ):
                outcome = process_candidate(
                    candidate,
                    evidence_root=root / "evidence",
                    configuration=configuration(root),
                )

        self.assertEqual(outcome.status, "retry_pending")
        self.assertEqual(outcome.code, "QUARANTINE_UNCERTAIN")
        downloaded.assert_not_called()
        self.assertNotIn("12345678909", json.dumps(outcome.as_dict()))

    def test_preflight_bound_rejection_quarantines_before_claim(self) -> None:
        candidate = BatchCandidate("B202607230000932", "incoming")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch(
                    "worker.preflight_incoming_bounds",
                    side_effect=WorkerSourceRejected(
                        "SOURCE_SIZE_BOUNDS_EXCEEDED"
                    ),
                ),
                patch("worker.quarantine_incoming_batch") as quarantined,
                patch("worker.claim_batch") as claimed,
            ):
                outcome = process_candidate(
                    candidate,
                    evidence_root=root / "evidence",
                    configuration=configuration(root),
                )

        self.assertEqual(outcome.status, "quarantined")
        self.assertEqual(outcome.code, "SOURCE_SIZE_BOUNDS_EXCEEDED")
        quarantined.assert_called_once()
        claimed.assert_not_called()

    def test_invalid_or_unknown_processing_source_is_quarantined(self) -> None:
        invalid = BatchCandidate("B202607230000941", "processing")
        unknown = BatchCandidate("B202607230000942", "processing")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            with (
                patch(
                    "worker.download_processing_bundle",
                    side_effect=RawPublicationError("invalid raw secret"),
                ),
                patch("worker.quarantine_processing_batch") as quarantined,
                patch("worker.remove_cached_bundle"),
            ):
                invalid_outcome = process_candidate(
                    invalid,
                    evidence_root=root / "evidence",
                    configuration=config,
                )
            with (
                patch(
                    "worker.download_processing_bundle",
                    return_value=(
                        root / unknown.batch_id,
                        published(unknown.batch_id, "99"),
                    ),
                ),
                patch(
                    "worker.workflow_for_type",
                    side_effect=ValueError("unsupported"),
                ),
                patch("worker.quarantine_processing_batch") as unknown_q,
                patch("worker.remove_cached_bundle"),
            ):
                unknown_outcome = process_candidate(
                    unknown,
                    evidence_root=root / "evidence",
                    configuration=config,
                )

        self.assertEqual(invalid_outcome.status, "quarantined")
        self.assertEqual(invalid_outcome.code, "SOURCE_INTEGRITY_ERROR")
        quarantined.assert_called_once()
        self.assertEqual(unknown_outcome.status, "quarantined")
        self.assertEqual(unknown_outcome.code, "UNSUPPORTED_FILE_TYPE")
        unknown_q.assert_called_once()


class WorkerControlTest(unittest.TestCase):
    """Protect single-worker ownership and atomic heartbeat behavior."""

    def test_private_lock_refuses_a_simultaneous_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / ".runtime"
            lock_path = runtime / "worker.lock"
            with WorkerLock(lock_path):
                with self.assertRaises(WorkerAlreadyRunningError):
                    with WorkerLock(lock_path):
                        pass
            with WorkerLock(lock_path):
                pass

            self.assertEqual(
                stat.S_IMODE(runtime.stat().st_mode),
                0o700,
            )
            self.assertEqual(
                stat.S_IMODE(lock_path.stat().st_mode),
                0o600,
            )

    def test_once_writes_a_private_atomic_stopped_heartbeat(self) -> None:
        report = CycleReport(
            started_at="2026-07-24T10:00:00Z",
            finished_at="2026-07-24T10:00:01Z",
            ready_count=1,
            deferred_count=0,
            ignored_count=2,
            outcomes=(
                BatchOutcome(
                    "B202607230000951",
                    "incoming",
                    "succeeded",
                    "TERMINAL",
                    "05",
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = WorkerService(
                configuration=configuration(root),
                evidence_root=root / "evidence",
            )
            emitted: list[str] = []
            with patch("worker.run_cycle", return_value=report):
                healthy = service.run(
                    once=True,
                    poll_interval=0.1,
                    stop_event=threading.Event(),
                    emit=emitted.append,
                )
            heartbeat = json.loads(
                service.status_path.read_text(encoding="utf-8")
            )

            self.assertTrue(healthy)
            self.assertEqual(heartbeat["state"], "stopped")
            self.assertEqual(heartbeat["poll_sequence"], 1)
            self.assertEqual(
                heartbeat["last_cycle"]["summary"]["succeeded"],
                1,
            )
            self.assertEqual(
                stat.S_IMODE(service.status_path.stat().st_mode),
                0o600,
            )
            self.assertFalse(
                any(
                    path.name.endswith(".part")
                    for path in service.status_path.parent.iterdir()
                )
            )
            self.assertEqual(len(emitted), 1)

    def test_signal_context_requests_a_clean_stop_and_restores_handler(
        self,
    ) -> None:
        stop_event = threading.Event()
        original = signal.getsignal(signal.SIGTERM)
        with clean_signal_stop(stop_event):
            handler = signal.getsignal(signal.SIGTERM)
            self.assertTrue(callable(handler))
            assert callable(handler)
            handler(signal.SIGTERM, None)
            self.assertTrue(stop_event.is_set())
        self.assertIs(signal.getsignal(signal.SIGTERM), original)

    def test_cli_bounds_polling_and_supports_once(self) -> None:
        parsed = build_parser().parse_args(
            ["--once", "--poll-interval", "0.5", "--max-batches", "5"]
        )
        self.assertTrue(parsed.once)
        self.assertEqual(parsed.poll_interval, 0.5)
        self.assertEqual(parsed.max_batches, 5)
        with (
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            build_parser().parse_args(["--poll-interval", "0"])


if __name__ == "__main__":
    unittest.main()
