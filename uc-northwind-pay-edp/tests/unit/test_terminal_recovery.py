"""Focused contracts for privacy-safe terminal quarantine recovery."""

from __future__ import annotations

import errno
import hashlib
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from config import RuntimeConfiguration, SftpRole
from evidence import EvidenceError, EvidenceWriter
from lifecycle import (
    LifecycleError,
    LifecycleState,
    ensure_remote_quarantine_reason,
)
from raw_publisher import PublishedRaw
from recovery_journal import (
    RecoveryJournalError,
    load_terminal_recovery,
    publish_terminal_recovery,
    recovery_journal_path,
)
from workflow import (
    FORCED_ORACLE_REASON,
    PipelineError,
    _finish_rejection,
    _interrupt_after,
    existing_terminal_evidence,
    finish_oracle_mismatch,
    run_pipeline,
)
from workflow_registry import TYPE01_WORKFLOW, TYPE02_WORKFLOW


def configuration(root: Path) -> RuntimeConfiguration:
    """Return inert topology settings rooted in one private temp directory."""

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


def published(
    *,
    batch_id: str = "B202607230000991",
    sha256: str = "a" * 64,
) -> PublishedRaw:
    """Build one safe Type 02 source identity."""

    return PublishedRaw(
        batch_id=batch_id,
        file_type="02",
        filename=f"NW_INSTANT_PAYMENT_20260723_{batch_id}.txt",
        sha256=sha256,
        size_bytes=200,
        manifest_sha256="b" * 64,
        source_controls={
            "currency": "BRL",
            "event_count": 2,
            "credit_amount": "200.00",
            "debit_amount": "26.55",
            "net_amount": "173.45",
            "returned_count": 0,
        },
    )


def rejected_java(batch_id: str) -> dict[str, object]:
    """Return one aggregate-only rejected Java result."""

    return {
        "batch_id": batch_id,
        "code": "CONTROL_TOTAL_MISMATCH",
        "computed_credit_amount": "200.00",
        "computed_debit_amount": "26.55",
        "computed_event_count": 2,
        "computed_net_amount": "173.45",
        "declared_credit_amount": "200.00",
        "declared_debit_amount": "20.00",
        "declared_event_count": 2,
        "declared_net_amount": "180.00",
        "record_number": 4,
        "status": "rejected",
    }


def succeeded_java(batch_id: str) -> dict[str, object]:
    """Return one aggregate-only successful Java result."""

    return {
        "batch_id": batch_id,
        "code": None,
        "credit_amount": "200.00",
        "csv_file": f"sanitized_{batch_id}.csv",
        "csv_sha256": "c" * 64,
        "debit_amount": "26.55",
        "net_amount": "173.45",
        "returned_count": 0,
        "row_count": 2,
        "status": "succeeded",
    }


def bundle_for(root: Path, raw: PublishedRaw) -> Path:
    """Create only the local source metadata copied into evidence."""

    bundle = root / raw.batch_id
    bundle.mkdir(mode=0o700, parents=True)
    (bundle / "source-manifest.json").write_bytes(b"safe manifest\n")
    (bundle / f"{raw.filename}.sha256").write_bytes(b"safe checksum\n")
    return bundle


def rewrite_with_valid_digest(path: Path, value: dict[str, object]) -> None:
    """Rewrite a test journal after recomputing its non-secret payload digest."""

    payload = value["payload"]
    assert isinstance(payload, dict)
    canonical = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
    ).encode("utf-8")
    value["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class RecoveryJournalSecurityTest(unittest.TestCase):
    """Prove private metadata, integrity, identity, and adapter allowlisting."""

    def test_private_journal_projects_out_unallowlisted_java_values(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published()
            java_result = {
                **rejected_java(raw.batch_id),
                "raw_account_secret": "12345678909",
            }
            observed = publish_terminal_recovery(
                TYPE02_WORKFLOW,
                raw,
                route="rejection",
                java_result=java_result,
                code="CONTROL_TOTAL_MISMATCH",
                configuration=config,
            )
            path = recovery_journal_path(config, raw.batch_id)

            self.assertNotIn("raw_account_secret", observed.java_result)
            self.assertNotIn(b"12345678909", path.read_bytes())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(
                stat.S_IMODE(path.parent.stat().st_mode),
                0o700,
            )

    def test_type01_journal_drops_pan_cpf_and_unallowlisted_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            batch_id = "B202607230000003"
            raw = PublishedRaw(
                batch_id=batch_id,
                file_type="01",
                filename=f"NW_CARD_SETTLEMENT_20260723_{batch_id}.dat",
                sha256="a" * 64,
                size_bytes=300,
                manifest_sha256="b" * 64,
                source_controls={
                    "currency": "BRL",
                    "detail_count": 2,
                    "net_amount": "173.45",
                },
            )
            java_result: dict[str, object] = {
                "batch_id": batch_id,
                "code": "INVALID_RECORD",
                "computed_detail_count": None,
                "computed_net_amount": None,
                "csv_file": None,
                "csv_sha256": None,
                "declared_detail_count": None,
                "declared_net_amount": None,
                "detail_amounts": None,
                "net_amount": None,
                "record_number": 3,
                "row_count": None,
                "status": "rejected",
                "transaction_id": "TXN0000000000004",
                "pan": "4111111111111111",
                "cpf": "12345678909",
                "unexpected_source_value": "restricted",
            }
            publish_terminal_recovery(
                TYPE01_WORKFLOW,
                raw,
                route="rejection",
                java_result=java_result,
                code="INVALID_RECORD",
                configuration=config,
            )
            content = recovery_journal_path(config, batch_id).read_bytes()

            self.assertIn(b"TXN0000000000004", content)
            self.assertNotIn(b"4111111111111111", content)
            self.assertNotIn(b"12345678909", content)
            self.assertNotIn(b"unexpected_source_value", content)

    def test_exact_interrupted_publication_link_is_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published()
            publish_terminal_recovery(
                TYPE02_WORKFLOW,
                raw,
                route="rejection",
                java_result=rejected_java(raw.batch_id),
                code="CONTROL_TOTAL_MISMATCH",
                configuration=config,
            )
            path = recovery_journal_path(config, raw.batch_id)
            interrupted = path.parent / f".{raw.batch_id}.crash.part"
            os.link(path, interrupted)

            observed = load_terminal_recovery(
                TYPE02_WORKFLOW,
                raw,
                configuration=config,
            )

            self.assertIsNotNone(observed)
            self.assertFalse(interrupted.exists())
            self.assertEqual(path.stat().st_nlink, 1)

    def test_integrity_and_identity_tampering_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published()
            publish_terminal_recovery(
                TYPE02_WORKFLOW,
                raw,
                route="rejection",
                java_result=rejected_java(raw.batch_id),
                code="CONTROL_TOTAL_MISMATCH",
                configuration=config,
            )
            path = recovery_journal_path(config, raw.batch_id)
            envelope = json.loads(path.read_text(encoding="utf-8"))
            envelope["payload"]["code"] = "OTHER_SAFE_CODE"
            path.write_text(
                json.dumps(envelope) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(RecoveryJournalError):
                load_terminal_recovery(
                    TYPE02_WORKFLOW,
                    raw,
                    configuration=config,
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published()
            publish_terminal_recovery(
                TYPE02_WORKFLOW,
                raw,
                route="rejection",
                java_result=rejected_java(raw.batch_id),
                code="CONTROL_TOTAL_MISMATCH",
                configuration=config,
            )
            with self.assertRaises(RecoveryJournalError):
                load_terminal_recovery(
                    TYPE02_WORKFLOW,
                    published(sha256="d" * 64),
                    configuration=config,
                )

    def test_recomputed_digest_cannot_expand_adapter_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published()
            publish_terminal_recovery(
                TYPE02_WORKFLOW,
                raw,
                route="rejection",
                java_result=rejected_java(raw.batch_id),
                code="CONTROL_TOTAL_MISMATCH",
                configuration=config,
            )
            path = recovery_journal_path(config, raw.batch_id)
            envelope = json.loads(path.read_text(encoding="utf-8"))
            envelope["payload"]["java_result"]["raw_value"] = "4111111111111111"
            rewrite_with_valid_digest(path, envelope)

            with self.assertRaises(RecoveryJournalError):
                load_terminal_recovery(
                    TYPE02_WORKFLOW,
                    raw,
                    configuration=config,
                )

    def test_forced_oracle_reason_cannot_be_moved_to_rejection_route(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published()
            publish_terminal_recovery(
                TYPE02_WORKFLOW,
                raw,
                route="rejection",
                java_result=rejected_java(raw.batch_id),
                code="CONTROL_TOTAL_MISMATCH",
                configuration=config,
            )
            path = recovery_journal_path(config, raw.batch_id)
            envelope = json.loads(path.read_text(encoding="utf-8"))
            envelope["payload"]["reason"] = FORCED_ORACLE_REASON
            rewrite_with_valid_digest(path, envelope)

            with self.assertRaises(RecoveryJournalError):
                load_terminal_recovery(
                    TYPE02_WORKFLOW,
                    raw,
                    configuration=config,
                )

    def test_oracle_route_requires_the_fixed_terminal_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published()
            publish_terminal_recovery(
                TYPE02_WORKFLOW,
                raw,
                route="oracle_mismatch",
                java_result=succeeded_java(raw.batch_id),
                code="ORACLE_MISMATCH",
                configuration=config,
            )
            path = recovery_journal_path(config, raw.batch_id)
            envelope = json.loads(path.read_text(encoding="utf-8"))
            envelope["payload"]["code"] = "OTHER_SAFE_CODE"
            rewrite_with_valid_digest(path, envelope)

            with self.assertRaises(RecoveryJournalError):
                load_terminal_recovery(
                    TYPE02_WORKFLOW,
                    raw,
                    configuration=config,
                )

    def test_symlink_shared_mode_and_hardlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published()
            publish_terminal_recovery(
                TYPE02_WORKFLOW,
                raw,
                route="rejection",
                java_result=rejected_java(raw.batch_id),
                code="CONTROL_TOTAL_MISMATCH",
                configuration=config,
            )
            path = recovery_journal_path(config, raw.batch_id)
            path.chmod(0o644)
            with self.assertRaises(RecoveryJournalError):
                load_terminal_recovery(
                    TYPE02_WORKFLOW,
                    raw,
                    configuration=config,
                )

            path.chmod(0o600)
            peer = path.parent / "hardlink.json"
            os.link(path, peer)
            with self.assertRaises(RecoveryJournalError):
                load_terminal_recovery(
                    TYPE02_WORKFLOW,
                    raw,
                    configuration=config,
                )
            peer.unlink()

            target = path.parent / "target.json"
            path.rename(target)
            path.symlink_to(target)
            with self.assertRaises(RecoveryJournalError):
                load_terminal_recovery(
                    TYPE02_WORKFLOW,
                    raw,
                    configuration=config,
                )


class QuarantineReasonTest(unittest.TestCase):
    """Prove a moved batch's bounded safe reason is repairable and immutable."""

    def test_missing_reason_is_created_then_verified_idempotently(self) -> None:
        batch_id = "B202607230000990"
        target = f"/raw/quarantine/{batch_id}"
        reason = f"{target}/quarantine-reason.json"
        files = {target: b""}
        writes: list[str] = []

        class FakeSftp:
            def lstat(self, path: str) -> SimpleNamespace:
                if path == target:
                    return SimpleNamespace(
                        st_mode=stat.S_IFDIR | 0o700,
                        st_size=0,
                    )
                if path not in files:
                    raise FileNotFoundError(errno.ENOENT, "missing", path)
                content = files[path]
                return SimpleNamespace(
                    st_mode=stat.S_IFREG | 0o600,
                    st_size=len(content),
                )

            def file(self, path: str, mode: str) -> io.BytesIO:
                self.assert_read_mode(mode)
                return io.BytesIO(files[path])

            @staticmethod
            def assert_read_mode(mode: str) -> None:
                if mode != "r":
                    raise AssertionError("unexpected fake SFTP mode")

        fake = FakeSftp()

        def connected(*args: object, **kwargs: object):
            del args, kwargs

            class Connection:
                def __enter__(self) -> FakeSftp:
                    return fake

                def __exit__(self, *exc: object) -> None:
                    del exc

            return Connection()

        def exists(*args: object) -> bool:
            return str(args[1]) in files

        def write(*args: object) -> None:
            remote = str(args[1])
            value = args[2]
            writes.append(remote)
            files[remote] = (
                json.dumps(
                    value,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=True,
                )
                + "\n"
            ).encode("utf-8")

        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(Path(temporary))
            with (
                patch("lifecycle.connect_sftp", side_effect=connected),
                patch("lifecycle.exists", side_effect=exists),
                patch("lifecycle.write_safe_json", side_effect=write),
            ):
                ensure_remote_quarantine_reason(
                    batch_id,
                    plane="raw",
                    code="CONTROL_TOTAL_MISMATCH",
                    configuration=config,
                )
                ensure_remote_quarantine_reason(
                    batch_id,
                    plane="raw",
                    code="CONTROL_TOTAL_MISMATCH",
                    configuration=config,
                )

        self.assertEqual(writes, [reason])

    def test_existing_different_reason_is_never_replaced(self) -> None:
        batch_id = "B202607230000990"
        target = f"/raw/quarantine/{batch_id}"
        reason = f"{target}/quarantine-reason.json"
        wrong = {
            "batch_id": batch_id,
            "code": "OTHER_SAFE_CODE",
            "scope": "batch",
            "status": "quarantined",
        }
        content = (
            json.dumps(wrong, sort_keys=True) + "\n"
        ).encode("utf-8")
        fake = SimpleNamespace(
            lstat=lambda path: (
                SimpleNamespace(
                    st_mode=stat.S_IFDIR | 0o700,
                    st_size=0,
                )
                if path == target
                else SimpleNamespace(
                    st_mode=stat.S_IFREG | 0o600,
                    st_size=len(content),
                )
            ),
            file=lambda path, mode: io.BytesIO(content),
        )

        class Connection:
            def __enter__(self) -> object:
                return fake

            def __exit__(self, *exc: object) -> None:
                del exc

        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(Path(temporary))
            with (
                patch("lifecycle.connect_sftp", return_value=Connection()),
                patch(
                    "lifecycle.exists",
                    side_effect=lambda sftp, path: path in {target, reason},
                ),
                patch("lifecycle.write_safe_json") as write,
            ):
                with self.assertRaises(LifecycleError):
                    ensure_remote_quarantine_reason(
                        batch_id,
                        plane="raw",
                        code="CONTROL_TOTAL_MISMATCH",
                        configuration=config,
                    )
            write.assert_not_called()

    def test_stale_reason_parts_are_completed_replaced_or_rejected(
        self,
    ) -> None:
        batch_id = "B202607230000990"
        target = f"/raw/quarantine/{batch_id}"
        reason = f"{target}/quarantine-reason.json"
        part = f"{reason}.part"
        expected = {
            "batch_id": batch_id,
            "code": "CONTROL_TOTAL_MISMATCH",
            "scope": "batch",
            "status": "quarantined",
        }
        expected_bytes = (
            json.dumps(
                expected,
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8")

        class FakeSftp:
            def __init__(self, part_mode: int, part_content: bytes) -> None:
                self.entries = {
                    target: (stat.S_IFDIR | 0o700, b""),
                    part: (part_mode, part_content),
                }
                self.removed: list[str] = []
                self.renamed: list[tuple[str, str]] = []

            def lstat(self, path: str) -> SimpleNamespace:
                try:
                    mode, content = self.entries[path]
                except KeyError as exc:
                    raise FileNotFoundError(
                        errno.ENOENT,
                        "missing",
                        path,
                    ) from exc
                return SimpleNamespace(st_mode=mode, st_size=len(content))

            def file(self, path: str, mode: str) -> io.BytesIO:
                if mode != "r":
                    raise AssertionError("unexpected fake SFTP mode")
                return io.BytesIO(self.entries[path][1])

            def posix_rename(self, source: str, destination: str) -> None:
                self.renamed.append((source, destination))
                self.entries[destination] = self.entries.pop(source)

            def remove(self, path: str) -> None:
                self.removed.append(path)
                del self.entries[path]

        class Connection:
            def __init__(self, fake: FakeSftp) -> None:
                self.fake = fake

            def __enter__(self) -> FakeSftp:
                return self.fake

            def __exit__(self, *exc: object) -> None:
                del exc

        def exercise(fake: FakeSftp) -> int:
            writes = 0

            def write(*args: object) -> None:
                nonlocal writes
                writes += 1
                remote = str(args[1])
                fake.entries[remote] = (
                    stat.S_IFREG | 0o600,
                    expected_bytes,
                )

            with tempfile.TemporaryDirectory() as temporary:
                config = configuration(Path(temporary))
                with (
                    patch(
                        "lifecycle.connect_sftp",
                        return_value=Connection(fake),
                    ),
                    patch(
                        "lifecycle.write_safe_json",
                        side_effect=write,
                    ),
                ):
                    ensure_remote_quarantine_reason(
                        batch_id,
                        plane="raw",
                        code="CONTROL_TOTAL_MISMATCH",
                        configuration=config,
                    )
            return writes

        complete = FakeSftp(stat.S_IFREG | 0o600, expected_bytes)
        self.assertEqual(exercise(complete), 0)
        self.assertEqual(complete.renamed, [(part, reason)])

        partial = FakeSftp(stat.S_IFREG | 0o600, b"{")
        self.assertEqual(exercise(partial), 1)
        self.assertEqual(partial.removed, [part])

        linked = FakeSftp(stat.S_IFLNK | 0o777, b"")
        with tempfile.TemporaryDirectory() as temporary:
            config = configuration(Path(temporary))
            with (
                patch(
                    "lifecycle.connect_sftp",
                    return_value=Connection(linked),
                ),
                patch("lifecycle.write_safe_json") as write,
            ):
                with self.assertRaises(LifecycleError):
                    ensure_remote_quarantine_reason(
                        batch_id,
                        plane="raw",
                        code="CONTROL_TOTAL_MISMATCH",
                        configuration=config,
                    )
            write.assert_not_called()


class TerminalWorkflowRecoveryTest(unittest.TestCase):
    """Prove retained-cache rejection and oracle mismatch complete once."""

    def test_existing_terminal_evidence_must_match_database_failure_code(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = published()
            bundle = bundle_for(root / "cache", raw)
            evidence = root / "evidence" / raw.batch_id
            evidence.mkdir(mode=0o700, parents=True)
            (evidence / "source-manifest.json").write_bytes(
                (bundle / "source-manifest.json").read_bytes()
            )
            (evidence / "raw-file.sha256").write_bytes(
                (bundle / f"{raw.filename}.sha256").read_bytes()
            )
            (evidence / "final-status.json").write_text(
                json.dumps(
                    {
                        "batch_id": raw.batch_id,
                        "code": "CONTROL_TOTAL_MISMATCH",
                        "file_type": raw.file_type,
                        "source_controls": dict(raw.source_controls),
                        "status": "quarantined",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                EvidenceError,
                "failure code disagrees with PostgreSQL",
            ):
                existing_terminal_evidence(
                    TYPE02_WORKFLOW,
                    root / "evidence",
                    bundle=bundle,
                    raw=raw,
                    state=LifecycleState(
                        raw_zone="quarantine",
                        csv_zone=None,
                        database_status="quarantined",
                        failure_code="INVALID_RECORD",
                    ),
                )

    def test_success_evidence_cannot_carry_a_failure_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = published()
            bundle = bundle_for(root / "cache", raw)
            evidence = root / "evidence" / raw.batch_id
            evidence.mkdir(mode=0o700, parents=True)
            (evidence / "source-manifest.json").write_bytes(
                (bundle / "source-manifest.json").read_bytes()
            )
            (evidence / "raw-file.sha256").write_bytes(
                (bundle / f"{raw.filename}.sha256").read_bytes()
            )
            final = TYPE02_WORKFLOW.final_status_evidence(
                raw,
                status="succeeded",
            )
            final["code"] = "UNEXPECTED_FAILURE"
            (evidence / "final-status.json").write_text(
                json.dumps(final),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                EvidenceError,
                "success evidence has a failure code",
            ):
                existing_terminal_evidence(
                    TYPE02_WORKFLOW,
                    root / "evidence",
                    bundle=bundle,
                    raw=raw,
                    state=LifecycleState(
                        raw_zone="archive",
                        csv_zone="archive",
                        database_status="succeeded",
                        failure_code=None,
                    ),
                )

    def test_interrupt_hook_is_inert_without_exact_batch_selector(self) -> None:
        batch_id = "B202607230000991"
        with patch.dict(
            os.environ,
            {"NWP_TEST_INTERRUPT_AFTER": "raw_archive"},
            clear=True,
        ):
            _interrupt_after("raw_archive", batch_id)

        with patch.dict(
            os.environ,
            {
                "NWP_TEST_INTERRUPT_AFTER": "raw_archive",
                "NWP_TEST_INTERRUPT_BATCH_ID": "not-a-batch",
            },
            clear=True,
        ):
            _interrupt_after("raw_archive", batch_id)

        with patch.dict(
            os.environ,
            {
                "NWP_TEST_INTERRUPT_AFTER": "raw_archive",
                "NWP_TEST_INTERRUPT_BATCH_ID": batch_id,
            },
            clear=True,
        ):
            with self.assertRaisesRegex(
                PipelineError,
                "Injected interruption after raw_archive",
            ):
                _interrupt_after("raw_archive", batch_id)

    def test_rejection_resumes_after_verified_raw_quarantine_without_java(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published()
            bundle = bundle_for(root / "cache", raw)
            evidence_root = root / "evidence"
            state = {
                "raw": "processing",
                "csv": None,
                "database": None,
                "failure_code": None,
            }
            record_calls: list[dict[str, object]] = []

            def inspected(*args: object, **kwargs: object) -> LifecycleState:
                del args, kwargs
                return LifecycleState(
                    raw_zone=state["raw"],
                    csv_zone=state["csv"],
                    database_status=state["database"],
                    failure_code=state["failure_code"],
                )

            def quarantined(*args: object, **kwargs: object) -> None:
                del args, kwargs
                self.assertTrue(
                    recovery_journal_path(config, raw.batch_id).is_file()
                )
                state["raw"] = "quarantine"

            def recorded(*args: object, **kwargs: object) -> None:
                del args
                record_calls.append(dict(kwargs))
                state["database"] = "quarantined"
                state["failure_code"] = "CONTROL_TOTAL_MISMATCH"

            environment = {
                "NWP_TEST_INTERRUPT_AFTER": "raw_quarantine",
                "NWP_TEST_INTERRUPT_BATCH_ID": raw.batch_id,
            }
            with (
                patch("workflow.validate_bundle", return_value=raw),
                patch("workflow.inspect_lifecycle", side_effect=inspected),
                patch("workflow.verify_remote_raw"),
                patch(
                    "workflow.run_java",
                    return_value=rejected_java(raw.batch_id),
                ) as java,
                patch(
                    "workflow.quarantine_processing_batch",
                    side_effect=quarantined,
                ),
                patch("workflow.ensure_remote_quarantine_reason"),
                patch("workflow.record_rejected_batch", side_effect=recorded),
                patch.dict(os.environ, environment, clear=False),
            ):
                with self.assertRaises(PipelineError):
                    run_pipeline(
                        TYPE02_WORKFLOW,
                        bundle,
                        scenario=None,
                        evidence_root=evidence_root,
                        configuration=config,
                    )
                self.assertEqual(record_calls, [])
                self.assertFalse((evidence_root / raw.batch_id).exists())
                journal = load_terminal_recovery(
                    TYPE02_WORKFLOW,
                    raw,
                    configuration=config,
                )
                self.assertIsNotNone(journal)

                java.reset_mock()
                result = run_pipeline(
                    TYPE02_WORKFLOW,
                    bundle,
                    scenario=None,
                    evidence_root=evidence_root,
                    configuration=config,
                    recovery_only=True,
                )

            java.assert_not_called()
            self.assertEqual(len(record_calls), 1)
            self.assertEqual(
                json.loads(
                    (result / "final-status.json").read_text(
                        encoding="utf-8"
                    )
                )["status"],
                "quarantined",
            )
            self.assertFalse(
                recovery_journal_path(config, raw.batch_id).exists()
            )

    def test_terminal_evidence_replay_retries_journal_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published(batch_id="B202607230000994")
            bundle = bundle_for(root / "cache", raw)
            evidence_root = root / "evidence"
            state = {
                "raw": "processing",
                "csv": None,
                "database": None,
                "failure_code": None,
            }

            def inspected(*args: object, **kwargs: object) -> LifecycleState:
                del args, kwargs
                return LifecycleState(
                    raw_zone=state["raw"],
                    csv_zone=state["csv"],
                    database_status=state["database"],
                    failure_code=state["failure_code"],
                )

            def quarantined(*args: object, **kwargs: object) -> None:
                del args, kwargs
                state["raw"] = "quarantine"

            def recorded(*args: object, **kwargs: object) -> None:
                del args, kwargs
                state["database"] = "quarantined"
                state["failure_code"] = "CONTROL_TOTAL_MISMATCH"

            with (
                patch("workflow.validate_bundle", return_value=raw),
                patch("workflow.inspect_lifecycle", side_effect=inspected),
                patch("workflow.verify_remote_raw"),
                patch(
                    "workflow.run_java",
                    return_value=rejected_java(raw.batch_id),
                ) as java,
                patch(
                    "workflow.quarantine_processing_batch",
                    side_effect=quarantined,
                ),
                patch("workflow.ensure_remote_quarantine_reason"),
                patch("workflow.record_rejected_batch", side_effect=recorded),
                patch(
                    "workflow.remove_terminal_recovery",
                    side_effect=RecoveryJournalError("cleanup unavailable"),
                ),
                patch.dict(os.environ, {}, clear=True),
            ):
                with self.assertRaises(RecoveryJournalError):
                    run_pipeline(
                        TYPE02_WORKFLOW,
                        bundle,
                        scenario=None,
                        evidence_root=evidence_root,
                        configuration=config,
                    )

            evidence = evidence_root / raw.batch_id
            self.assertTrue(evidence.is_dir())
            self.assertTrue(
                recovery_journal_path(config, raw.batch_id).is_file()
            )
            java.reset_mock()
            with (
                patch("workflow.validate_bundle", return_value=raw),
                patch("workflow.inspect_lifecycle", side_effect=inspected),
                patch("workflow.verify_remote_raw"),
                patch("workflow.run_java") as replay_java,
            ):
                result = run_pipeline(
                    TYPE02_WORKFLOW,
                    bundle,
                    scenario=None,
                    evidence_root=evidence_root,
                    configuration=config,
                    recovery_only=True,
                )

            replay_java.assert_not_called()
            self.assertEqual(result, evidence.resolve())
            self.assertFalse(
                recovery_journal_path(config, raw.batch_id).exists()
            )

    def test_forced_oracle_mismatch_resumes_with_zero_business_mutation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published(batch_id="B202607230000992")
            bundle = bundle_for(root / "cache", raw)
            evidence_root = root / "evidence"
            state = {
                "raw": "processing",
                "csv": None,
                "database": None,
            }
            record_calls: list[dict[str, object]] = []
            reason_planes: list[str] = []

            def inspected(*args: object, **kwargs: object) -> LifecycleState:
                del args, kwargs
                return LifecycleState(
                    raw_zone=state["raw"],
                    csv_zone=state["csv"],
                    database_status=state["database"],
                    failure_code=None,
                )

            def java_result(*args: object, **kwargs: object) -> dict[str, object]:
                del args, kwargs
                state["csv"] = "outgoing"
                return succeeded_java(raw.batch_id)

            def csv_quarantined(*args: object, **kwargs: object) -> None:
                del args, kwargs
                if state["csv"] in {"outgoing", "processing"}:
                    state["csv"] = "quarantine"

            def raw_quarantined(*args: object, **kwargs: object) -> None:
                del args, kwargs
                self.assertTrue(
                    recovery_journal_path(config, raw.batch_id).is_file()
                )
                state["raw"] = "quarantine"

            def reason_verified(
                *args: object,
                **kwargs: object,
            ) -> None:
                del args
                reason_planes.append(str(kwargs["plane"]))

            def recorded(*args: object, **kwargs: object) -> None:
                del args
                record_calls.append(dict(kwargs))
                state["database"] = "oracle_mismatch"

            environment = {
                "NWP_TEST_FORCE_ORACLE_MISMATCH_BATCH_ID": raw.batch_id,
                "NWP_TEST_INTERRUPT_AFTER": "raw_quarantine",
                "NWP_TEST_INTERRUPT_BATCH_ID": raw.batch_id,
            }
            with (
                patch("workflow.validate_bundle", return_value=raw),
                patch("workflow.inspect_lifecycle", side_effect=inspected),
                patch("workflow.verify_remote_raw"),
                patch("workflow.run_java", side_effect=java_result) as java,
                patch(
                    "workflow.quarantine_prepared_batch",
                    side_effect=csv_quarantined,
                ),
                patch(
                    "workflow.quarantine_processing_batch",
                    side_effect=raw_quarantined,
                ),
                patch(
                    "workflow.ensure_remote_quarantine_reason",
                    side_effect=reason_verified,
                ),
                patch("workflow.record_rejected_batch", side_effect=recorded),
                patch.object(TYPE02_WORKFLOW, "prepare") as prepared,
                patch.object(TYPE02_WORKFLOW, "commit") as committed,
                patch.dict(os.environ, environment, clear=False),
            ):
                with self.assertRaises(PipelineError):
                    run_pipeline(
                        TYPE02_WORKFLOW,
                        bundle,
                        scenario=None,
                        evidence_root=evidence_root,
                        configuration=config,
                    )
                journal = load_terminal_recovery(
                    TYPE02_WORKFLOW,
                    raw,
                    configuration=config,
                )
                self.assertIsNotNone(journal)
                assert journal is not None
                self.assertEqual(journal.route, "oracle_mismatch")
                self.assertEqual(journal.reason, FORCED_ORACLE_REASON)
                self.assertEqual(record_calls, [])

                java.reset_mock()
                result = run_pipeline(
                    TYPE02_WORKFLOW,
                    bundle,
                    scenario=None,
                    evidence_root=evidence_root,
                    configuration=config,
                    recovery_only=True,
                )

            java.assert_not_called()
            prepared.assert_not_called()
            committed.assert_not_called()
            self.assertEqual(len(record_calls), 1)
            self.assertEqual(
                record_calls[0]["status"],
                "oracle_mismatch",
            )
            self.assertIn("raw", reason_planes)
            self.assertIn("csv", reason_planes)
            expected_diff = json.loads(
                (result / "expected-diff.json").read_text(encoding="utf-8")
            )
            self.assertEqual(expected_diff["error"], FORCED_ORACLE_REASON)
            self.assertEqual(
                json.loads(
                    (result / "final-status.json").read_text(
                        encoding="utf-8"
                    )
                )["status"],
                "oracle_mismatch",
            )

    def test_recovery_only_orphan_cache_never_republishes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            raw = published(batch_id="B202607230000993")
            bundle = bundle_for(root / "cache", raw)
            with (
                patch("workflow.validate_bundle", return_value=raw),
                patch(
                    "workflow.inspect_lifecycle",
                    return_value=LifecycleState(None, None, None, None),
                ),
                patch("workflow.publish_bundle") as publish,
            ):
                with self.assertRaisesRegex(
                    LifecycleError,
                    "cannot republish an orphan cache",
                ):
                    run_pipeline(
                        TYPE02_WORKFLOW,
                        bundle,
                        scenario=None,
                        evidence_root=root / "evidence",
                        configuration=config,
                        recovery_only=True,
                    )
            publish.assert_not_called()

    def test_terminal_state_mismatch_blocks_both_evidence_commits(
        self,
    ) -> None:
        for route in ("rejection", "oracle_mismatch"):
            with self.subTest(route=route):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    config = configuration(root)
                    raw = published(
                        batch_id=(
                            "B202607230000995"
                            if route == "rejection"
                            else "B202607230000996"
                        )
                    )
                    state = {"raw": "processing", "csv": None}

                    def inspected(
                        *args: object,
                        **kwargs: object,
                    ) -> LifecycleState:
                        del args, kwargs
                        return LifecycleState(
                            raw_zone=state["raw"],
                            csv_zone=state["csv"],
                            database_status=None,
                            failure_code=None,
                        )

                    def raw_quarantined(
                        *args: object,
                        **kwargs: object,
                    ) -> None:
                        del args, kwargs
                        state["raw"] = "quarantine"

                    with (
                        patch(
                            "workflow.inspect_lifecycle",
                            side_effect=inspected,
                        ),
                        patch(
                            "workflow.quarantine_processing_batch",
                            side_effect=raw_quarantined,
                        ),
                        patch(
                            "workflow.quarantine_prepared_batch",
                        ),
                        patch(
                            "workflow.ensure_remote_quarantine_reason",
                        ),
                        patch("workflow.record_rejected_batch"),
                        patch.dict(os.environ, {}, clear=True),
                    ):
                        with self.assertRaises(LifecycleError):
                            with EvidenceWriter(
                                root / "evidence",
                                raw.batch_id,
                            ) as writer:
                                if route == "rejection":
                                    java_result = rejected_java(raw.batch_id)
                                    oracle = (
                                        TYPE02_WORKFLOW.compare_rejection(
                                            None,
                                            batch_id=raw.batch_id,
                                            java_result=java_result,
                                        )
                                    )
                                    diagnostic = (
                                        TYPE02_WORKFLOW.rejection_diagnostic(
                                            java_result,
                                            code="CONTROL_TOTAL_MISMATCH",
                                            configuration=config,
                                        )
                                    )
                                    _finish_rejection(
                                        TYPE02_WORKFLOW,
                                        writer,
                                        raw=raw,
                                        java_result=java_result,
                                        oracle=oracle,
                                        postgres_diagnostic=diagnostic,
                                        configuration=config,
                                    )
                                else:
                                    finish_oracle_mismatch(
                                        TYPE02_WORKFLOW,
                                        writer,
                                        raw=raw,
                                        java_result=succeeded_java(
                                            raw.batch_id
                                        ),
                                        reason=FORCED_ORACLE_REASON,
                                        configuration=config,
                                    )

                    self.assertFalse(
                        (root / "evidence" / raw.batch_id).exists()
                    )
                    self.assertTrue(
                        recovery_journal_path(
                            config,
                            raw.batch_id,
                        ).exists()
                    )


if __name__ == "__main__":
    unittest.main()
