"""Pure contract tests for the live automatic-worker acceptance harness."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from raw_publisher import PublishedRaw


ROOT = Path(__file__).resolve().parents[2]
HARNESS_ROOT = ROOT / "tests" / "end-to-end"
sys.path.insert(0, str(HARNESS_ROOT))

from run_worker_suite import (  # noqa: E402
    BAD_CHECKSUM_BATCH,
    CACHE_CONFLICT_BATCH,
    DATABASE_COMMIT_RESTART_BATCH,
    DUPLICATE_ZONE_BATCH,
    INCOMPLETE_BATCH,
    ORACLE_MISMATCH_BATCH,
    QUARANTINE_UNCERTAIN_BATCH,
    RAW_ARCHIVE_RESTART_BATCH,
    RAW_QUARANTINE_RESTART_BATCH,
    RECOVERY_SCENARIO,
    RECOVERY_TYPE,
    RESERVED_BATCHES,
    RESTART_CANONICAL_BATCHES,
    TRANSPORT_ONLY_RESERVED_BATCHES,
    WORKER_TEST_HOOKS,
    RestartProbe,
    WorkerAcceptanceFailure,
    _bundle_transport_artifacts,
    _expected_summary,
    _prepare_empty_cache_root,
    _type01_sensitive_values,
    _type02_sensitive_values,
    canonical_cases,
    datagen_command,
    publisher_command,
    run_worker_once,
    sanitized_worker_environment,
    verify_duplicate_cycle_report,
    verify_first_cycle_report,
    verify_no_work_report,
    verify_retry_cycle_report,
    verify_terminal_cycle_report,
    worker_command,
)


class WorkerAcceptanceHarnessTest(unittest.TestCase):
    """Protect the suite's deterministic public boundary without live I/O."""

    def test_catalog_is_five_by_five_with_exact_outcome_split(self) -> None:
        cases = canonical_cases()

        self.assertEqual(len(cases), 25)
        self.assertEqual(len({case.batch_id for case in cases}), 25)
        self.assertFalse(
            {case.batch_id for case in cases} & RESERVED_BATCHES
        )
        self.assertEqual(
            Counter(case.type_number for case in cases),
            Counter({"01": 5, "02": 5, "03": 5, "04": 5, "05": 5}),
        )
        self.assertEqual(
            Counter(case.expected_status for case in cases),
            Counter({"succeeded": 15, "quarantined": 10}),
        )

    def test_commands_use_only_public_generator_publisher_and_worker(self) -> None:
        case = canonical_cases()[0]
        generation = datagen_command(case)
        publication = publisher_command(Path("/tmp/exact-bundle"))
        once = worker_command(once=True)
        daemon = worker_command(once=False)
        bounded = worker_command(once=True, max_batches=1)
        combined = " ".join((*generation, *publication, *once, *daemon))

        self.assertEqual(
            Path(generation[1]),
            ROOT / "gen" / "src" / "cli.py",
        )
        self.assertEqual(
            Path(publication[1]),
            ROOT / "legacy" / "runner" / "publish_raw_cli.py",
        )
        self.assertEqual(
            Path(once[1]),
            ROOT / "legacy" / "runner" / "worker.py",
        )
        self.assertIn("--once", once)
        self.assertNotIn("--once", daemon)
        self.assertEqual(
            bounded[bounded.index("--max-batches") + 1],
            "1",
        )
        with self.assertRaises(WorkerAcceptanceFailure):
            worker_command(once=True, max_batches=0)
        self.assertNotIn("run_type.py", combined)
        self.assertNotIn("run_type01.py", combined)

    def test_generator_receipt_is_local_only_not_a_transport_artifact(
        self,
    ) -> None:
        raw = PublishedRaw(
            batch_id="B202607230000001",
            file_type="01",
            filename="source.dat",
            sha256="a" * 64,
            size_bytes=1,
            manifest_sha256="b" * 64,
            source_controls={
                "currency": "BRL",
                "detail_count": 1,
                "net_amount": "1.00",
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            for name in (
                raw.filename,
                f"{raw.filename}.sha256",
                "source-manifest.json",
                "generation-receipt.json",
            ):
                (bundle / name).write_bytes(b"x")

            artifacts = _bundle_transport_artifacts(
                bundle,
                raw,
                allow_generation_receipt=True,
            )
            self.assertEqual(
                {name for name, _ in artifacts},
                {
                    raw.filename,
                    f"{raw.filename}.sha256",
                    "source-manifest.json",
                },
            )
            with self.assertRaises(WorkerAcceptanceFailure):
                _bundle_transport_artifacts(bundle, raw)

            (bundle / "unexpected.txt").write_bytes(b"x")
            with self.assertRaises(WorkerAcceptanceFailure):
                _bundle_transport_artifacts(
                    bundle,
                    raw,
                    allow_generation_receipt=True,
                )

    def test_recovery_staging_accepts_only_an_empty_private_cache_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "cache"
            with mock.patch("run_worker_suite.WORKER_CACHE", root):
                _prepare_empty_cache_root()
                self.assertTrue(root.is_dir())
                self.assertEqual(root.stat().st_mode & 0o777, 0o700)
                _prepare_empty_cache_root()
                (root / "unexpected").write_text(
                    "occupied",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    WorkerAcceptanceFailure,
                    "not an empty private directory",
                ):
                    _prepare_empty_cache_root()

    def test_first_cycle_contract_covers_recovery_and_integrity_fault(
        self,
    ) -> None:
        cases = tuple(
            case
            for case in canonical_cases()
            if case.batch_id not in RESTART_CANONICAL_BATCHES
        )
        recovery = next(
            case
            for case in cases
            if (
                case.type_number == RECOVERY_TYPE
                and case.scenario == RECOVERY_SCENARIO
            )
        )
        batches: list[dict[str, object]] = [
            {
                "batch_id": case.batch_id,
                "code": "TERMINAL",
                "file_type": case.type_number,
                "source_zone": (
                    "processing"
                    if case == recovery
                    else "incoming"
                ),
                "status": case.expected_status,
            }
            for case in cases
        ]
        batches.append(
            {
                "batch_id": BAD_CHECKSUM_BATCH,
                "code": "SOURCE_INTEGRITY_ERROR",
                "source_zone": "incoming",
                "status": "quarantined",
            }
        )
        batches.sort(
            key=lambda item: (
                item["source_zone"] != "processing",
                str(item["batch_id"]),
            )
        )
        report: dict[str, object] = {
            "batches": batches,
            "finished_at": "2026-07-24T12:00:01Z",
            "started_at": "2026-07-24T12:00:00Z",
            "status": "completed",
            "summary": _expected_summary(
                discovered=23,
                ignored=1,
                processed=23,
                quarantined=10,
                retry_pending=0,
                succeeded=13,
            ),
        }

        verify_first_cycle_report(report, cases, recovery)
        batches[-1] = {**batches[-1], "code": "WRONG"}
        with self.assertRaises(WorkerAcceptanceFailure):
            verify_first_cycle_report(report, cases, recovery)

    def test_empty_and_duplicate_cycle_contracts_fail_closed(self) -> None:
        empty: dict[str, object] = {
            "batches": [],
            "finished_at": "2026-07-24T12:00:01Z",
            "started_at": "2026-07-24T12:00:00Z",
            "status": "completed",
            "summary": _expected_summary(
                discovered=0,
                ignored=1,
                processed=0,
                quarantined=0,
                retry_pending=0,
                succeeded=0,
            ),
        }
        duplicate: dict[str, object] = {
            "batches": [
                {
                    "batch_id": DUPLICATE_ZONE_BATCH,
                    "code": "SFTP_ZONE_AMBIGUITY",
                    "source_zone": "processing",
                    "status": "retry_pending",
                }
            ],
            "finished_at": "2026-07-24T12:00:01Z",
            "started_at": "2026-07-24T12:00:00Z",
            "status": "completed",
            "summary": _expected_summary(
                discovered=1,
                ignored=1,
                processed=1,
                quarantined=0,
                retry_pending=1,
                succeeded=0,
            ),
        }

        verify_no_work_report(empty)
        verify_duplicate_cycle_report(duplicate)
        empty["unexpected_private_field"] = "must-not-pass"
        with self.assertRaises(WorkerAcceptanceFailure):
            verify_no_work_report(empty)
        empty.pop("unexpected_private_field")
        duplicate["unexpected_private_field"] = "must-not-pass"
        with self.assertRaises(WorkerAcceptanceFailure):
            verify_duplicate_cycle_report(duplicate)
        duplicate.pop("unexpected_private_field")
        duplicate["batches"] = []
        with self.assertRaises(WorkerAcceptanceFailure):
            verify_duplicate_cycle_report(duplicate)

    def test_reserved_probe_ids_are_valid_and_distinct(self) -> None:
        self.assertEqual(
            RESERVED_BATCHES,
            {
                BAD_CHECKSUM_BATCH,
                INCOMPLETE_BATCH,
                DUPLICATE_ZONE_BATCH,
                CACHE_CONFLICT_BATCH,
                QUARANTINE_UNCERTAIN_BATCH,
                ORACLE_MISMATCH_BATCH,
            },
        )
        self.assertEqual(len(RESERVED_BATCHES), 6)
        self.assertEqual(
            TRANSPORT_ONLY_RESERVED_BATCHES,
            RESERVED_BATCHES - {ORACLE_MISMATCH_BATCH},
        )
        self.assertTrue(
            all(
                batch_id.startswith("B20260723000")
                and len(batch_id) == 16
                for batch_id in RESERVED_BATCHES
            )
        )

    def test_restart_catalog_selects_exact_canonical_seams(self) -> None:
        selected = {
            case.batch_id: (
                case.type_number,
                case.scenario,
                case.expected_status,
            )
            for case in canonical_cases()
            if case.batch_id in RESTART_CANONICAL_BATCHES
        }
        self.assertEqual(
            selected,
            {
                DATABASE_COMMIT_RESTART_BATCH: (
                    "05",
                    "rounding-half-up",
                    "succeeded",
                ),
                RAW_ARCHIVE_RESTART_BATCH: (
                    "01",
                    "valid-minimal",
                    "succeeded",
                ),
                RAW_QUARANTINE_RESTART_BATCH: (
                    "01",
                    "malformed",
                    "quarantined",
                ),
            },
        )
        self.assertEqual(
            (RECOVERY_TYPE, RECOVERY_SCENARIO),
            ("01", "negative-overpunch"),
        )

    def test_worker_environment_clears_ambient_hooks_and_allowlists_explicit(
        self,
    ) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "NWP_TEST_INTERRUPT_AFTER": "raw_archive",
                "NWP_TEST_UNRECOGNIZED": "unsafe",
                "WORKER_ACCEPTANCE_SENTINEL": "kept",
            },
            clear=False,
        ):
            clean = sanitized_worker_environment()
            explicit = sanitized_worker_environment(
                {
                    "NWP_TEST_INTERRUPT_AFTER": "database_commit",
                    "NWP_TEST_INTERRUPT_BATCH_ID": (
                        DATABASE_COMMIT_RESTART_BATCH
                    ),
                }
            )

        self.assertEqual(
            {name for name in clean if name.startswith("NWP_TEST_")},
            set(),
        )
        self.assertEqual(
            explicit["NWP_TEST_INTERRUPT_AFTER"],
            "database_commit",
        )
        self.assertEqual(
            explicit["NWP_TEST_INTERRUPT_BATCH_ID"],
            DATABASE_COMMIT_RESTART_BATCH,
        )
        self.assertEqual(
            {
                name
                for name in explicit
                if name.startswith("NWP_TEST_")
            },
            {
                "NWP_TEST_INTERRUPT_AFTER",
                "NWP_TEST_INTERRUPT_BATCH_ID",
            },
        )
        self.assertEqual(explicit["WORKER_ACCEPTANCE_SENTINEL"], "kept")
        self.assertEqual(
            WORKER_TEST_HOOKS,
            {
                "NWP_TEST_FORCE_ORACLE_MISMATCH_BATCH_ID",
                "NWP_TEST_INTERRUPT_AFTER",
                "NWP_TEST_INTERRUPT_BATCH_ID",
            },
        )
        with self.assertRaises(WorkerAcceptanceFailure):
            sanitized_worker_environment(
                {"NWP_TEST_UNRECOGNIZED": "unsafe"}
            )
        with self.assertRaises(WorkerAcceptanceFailure):
            sanitized_worker_environment(
                {"NWP_TEST_INTERRUPT_AFTER": "not-a-boundary"}
            )
        with self.assertRaises(WorkerAcceptanceFailure):
            sanitized_worker_environment(
                {"NWP_TEST_INTERRUPT_AFTER": "raw_archive"}
            )
        with self.assertRaises(WorkerAcceptanceFailure):
            sanitized_worker_environment(
                {
                    "NWP_TEST_FORCE_ORACLE_MISMATCH_BATCH_ID": (
                        ORACLE_MISMATCH_BATCH
                    ),
                    "NWP_TEST_INTERRUPT_AFTER": "raw_quarantine",
                    "NWP_TEST_INTERRUPT_BATCH_ID": (
                        RAW_QUARANTINE_RESTART_BATCH
                    ),
                }
            )

    def test_run_worker_once_passes_explicit_bound_and_sanitized_hooks(
        self,
    ) -> None:
        result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                '{"batches":[],"finished_at":"2026-07-24T12:00:01Z",'
                '"started_at":"2026-07-24T12:00:00Z",'
                '"status":"completed","summary":{}}\n'
            ),
            stderr="",
        )
        with (
            mock.patch.dict(
                os.environ,
                {"NWP_TEST_UNRECOGNIZED": "must-be-cleared"},
                clear=False,
            ),
            mock.patch(
                "run_worker_suite._run_checked",
                return_value=result,
            ) as checked,
        ):
            report = run_worker_once(
                environment={
                    "NWP_TEST_INTERRUPT_AFTER": "raw_archive",
                    "NWP_TEST_INTERRUPT_BATCH_ID": (
                        RAW_ARCHIVE_RESTART_BATCH
                    ),
                },
                max_batches=1,
            )

        self.assertEqual(report["status"], "completed")
        call = checked.call_args
        command = call.args[0]
        environment = call.kwargs["environment"]
        self.assertEqual(
            command[command.index("--max-batches") + 1],
            "1",
        )
        self.assertNotIn("NWP_TEST_UNRECOGNIZED", environment)
        self.assertEqual(
            environment["NWP_TEST_INTERRUPT_AFTER"],
            "raw_archive",
        )
        self.assertEqual(
            environment["NWP_TEST_INTERRUPT_BATCH_ID"],
            RAW_ARCHIVE_RESTART_BATCH,
        )

    def test_restart_report_contracts_cover_retry_and_fresh_terminal_process(
        self,
    ) -> None:
        retry: dict[str, object] = {
            "batches": [
                {
                    "batch_id": DATABASE_COMMIT_RESTART_BATCH,
                    "code": "PIPELINE_RETRY_PENDING",
                    "file_type": "05",
                    "source_zone": "incoming",
                    "status": "retry_pending",
                }
            ],
            "finished_at": "2026-07-24T12:00:01Z",
            "started_at": "2026-07-24T12:00:00Z",
            "status": "completed",
            "summary": _expected_summary(
                discovered=1,
                ignored=0,
                processed=1,
                quarantined=0,
                retry_pending=1,
                succeeded=0,
            ),
        }
        terminal: dict[str, object] = {
            "batches": [
                {
                    "batch_id": ORACLE_MISMATCH_BATCH,
                    "code": "TERMINAL",
                    "file_type": "01",
                    "source_zone": "cache",
                    "status": "oracle_mismatch",
                }
            ],
            "finished_at": "2026-07-24T12:00:03Z",
            "started_at": "2026-07-24T12:00:02Z",
            "status": "completed",
            "summary": _expected_summary(
                discovered=1,
                ignored=0,
                processed=1,
                quarantined=0,
                retry_pending=0,
                succeeded=0,
                oracle_mismatch=1,
            ),
        }

        verify_retry_cycle_report(
            retry,
            batch_id=DATABASE_COMMIT_RESTART_BATCH,
            code="PIPELINE_RETRY_PENDING",
            source_zone="incoming",
            file_type="05",
            ignored=0,
        )
        verify_terminal_cycle_report(
            terminal,
            batch_id=ORACLE_MISMATCH_BATCH,
            file_type="01",
            status="oracle_mismatch",
            source_zone="cache",
        )
        retry["summary"] = {
            **retry["summary"],
            "retry_pending": 0,
        }
        with self.assertRaises(WorkerAcceptanceFailure):
            verify_retry_cycle_report(
                retry,
                batch_id=DATABASE_COMMIT_RESTART_BATCH,
                code="PIPELINE_RETRY_PENDING",
                source_zone="incoming",
                file_type="05",
                ignored=0,
            )

    def test_restart_probe_contract_rejects_unsafe_boundaries(self) -> None:
        valid = RestartProbe(
            name="database_commit",
            boundary="database_commit",
            batch_id=DATABASE_COMMIT_RESTART_BATCH,
            expected_status="succeeded",
            expected_code="TERMINAL",
            intermediate_raw_zone="processing",
            intermediate_csv_zone="processing",
            intermediate_database_status=(
                "database_committed_pending_archive"
            ),
            recovery_source_zone="processing",
            journal_route=None,
        )
        self.assertEqual(valid.batch_id, DATABASE_COMMIT_RESTART_BATCH)
        with self.assertRaises(ValueError):
            RestartProbe(
                name="unsafe",
                boundary="before_database_commit",
                batch_id=DATABASE_COMMIT_RESTART_BATCH,
                expected_status="succeeded",
                expected_code="TERMINAL",
                intermediate_raw_zone="processing",
                intermediate_csv_zone="processing",
                intermediate_database_status=None,
                recovery_source_zone="processing",
                journal_route=None,
            )

    def test_reserved_retry_contract_covers_cache_and_quarantine(self) -> None:
        for batch_id, code, zone in (
            (
                CACHE_CONFLICT_BATCH,
                "LOCAL_CACHE_CONFLICT",
                "processing",
            ),
            (
                QUARANTINE_UNCERTAIN_BATCH,
                "QUARANTINE_UNCERTAIN",
                "incoming",
            ),
        ):
            with self.subTest(code=code):
                report: dict[str, object] = {
                    "batches": [
                        {
                            "batch_id": batch_id,
                            "code": code,
                            "source_zone": zone,
                            "status": "retry_pending",
                        }
                    ],
                    "finished_at": "2026-07-24T12:00:01Z",
                    "started_at": "2026-07-24T12:00:00Z",
                    "status": "completed",
                    "summary": _expected_summary(
                        discovered=1,
                        ignored=1,
                        processed=1,
                        quarantined=0,
                        retry_pending=1,
                        succeeded=0,
                    ),
                }
                verify_retry_cycle_report(
                    report,
                    batch_id=batch_id,
                    code=code,
                    source_zone=zone,
                )

    def test_type01_and_type02_privacy_extractors_find_source_values(
        self,
    ) -> None:
        type01 = (
            ROOT
            / "contracts"
            / "types"
            / "01-card-settlement"
            / "main"
            / "valid-minimal.dat"
        ).read_bytes()
        type02 = (
            ROOT
            / "contracts"
            / "types"
            / "02-instant-payment-events"
            / "main"
            / "valid-minimal.txt"
        ).read_bytes()

        type01_values = _type01_sensitive_values(type01)
        type02_values = _type02_sensitive_values(type02)
        self.assertIn(b"4111111111111111", type01_values)
        self.assertIn(b"12345678909", type01_values)
        self.assertNotIn(b"TXN0000000000001", type01_values)
        self.assertFalse(
            any(
                value in b'{"transaction_id":"TXN0000000000001"}'
                for value in type01_values
            )
        )
        self.assertTrue(
            any(
                value in b'{"unsafe_pan":"4111111111111111"}'
                for value in type01_values
            )
        )
        self.assertIn(b"12345678000195", type02_values)
        self.assertIn(b"Invoice 1001", type02_values)


if __name__ == "__main__":
    unittest.main()
