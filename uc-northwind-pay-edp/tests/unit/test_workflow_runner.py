"""Unit contracts for typed orchestration without external mutation."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import RuntimeConfiguration, SftpRole
from loader_common import DiagnosticControls, LoadResult
from raw_publisher import PublishedRaw
from run_type import build_parser as build_public_parser
from type02_loader import PreparedType02Load
from workflow import PipelineError, run_java, scenario_from_bundle
from workflow_registry import (
    TYPE01_WORKFLOW,
    TYPE02_WORKFLOW,
    TYPE03_WORKFLOW,
    TYPE04_WORKFLOW,
    TYPE05_WORKFLOW,
    TYPE06_WORKFLOW,
    workflow_for_type,
)


def configuration() -> RuntimeConfiguration:
    """Return inert connection settings for pure runner unit tests."""

    role = SftpRole("test", "secret")
    return RuntimeConfiguration(
        root=Path("/tmp/northwind-runner-unit"),
        sftp_host="127.0.0.1",
        sftp_port=22,
        known_hosts=Path("/tmp/northwind-known-hosts"),
        raw_publisher=role,
        processor=role,
        loader=role,
        operator=role,
        postgres_app_user="test",
        postgres_dsn="postgresql://test:test@127.0.0.1/test",
        postgres_admin_dsn="postgresql://admin:test@127.0.0.1/test",
    )


def published_type02_raw() -> PublishedRaw:
    """Build one privacy-safe Type 02 source identity."""

    return PublishedRaw(
        batch_id="B202607230000101",
        file_type="02",
        filename="NW_INSTANT_PAYMENT_20260723_B202607230000101.txt",
        sha256="a" * 64,
        size_bytes=200,
        manifest_sha256="b" * 64,
        source_controls={
            "currency": "BRL",
            "event_count": 2,
            "credit_amount": "200.00",
            "debit_amount": "26.55",
            "net_amount": "173.45",
        },
    )


class WorkflowRegistryTest(unittest.TestCase):
    """Prove routing is explicit and closed to unsupported types."""

    def test_registry_dispatches_only_implemented_types(self) -> None:
        self.assertIs(workflow_for_type("01"), TYPE01_WORKFLOW)
        self.assertIs(workflow_for_type("02"), TYPE02_WORKFLOW)
        self.assertIs(workflow_for_type("03"), TYPE03_WORKFLOW)
        self.assertIs(workflow_for_type("04"), TYPE04_WORKFLOW)
        self.assertIs(workflow_for_type("05"), TYPE05_WORKFLOW)
        self.assertIs(workflow_for_type("06"), TYPE06_WORKFLOW)
        with self.assertRaises(ValueError):
            workflow_for_type("99")

    def test_scenario_batch_ids_are_type_owned_and_distinct(self) -> None:
        self.assertEqual(
            TYPE01_WORKFLOW.scenario_batch_ids["valid-minimal"],
            "B202607230000001",
        )
        self.assertEqual(
            TYPE02_WORKFLOW.scenario_batch_ids["valid-minimal"],
            "B202607230000101",
        )
        self.assertEqual(
            set(TYPE02_WORKFLOW.scenario_batch_ids),
            {
                "valid-minimal",
                "valid-boundary",
                "escaped-content",
                "malformed",
                "DF-SOURCE-002",
            },
        )

    def test_public_parser_requires_a_type_and_one_source(self) -> None:
        parsed = build_public_parser().parse_args(
            ["--type", "02", "--scenario", "valid-minimal"]
        )
        self.assertEqual(parsed.type_number, "02")
        self.assertEqual(parsed.scenario, "valid-minimal")
        with self.assertRaises(SystemExit):
            build_public_parser().parse_args(
                ["--type", "99", "--scenario", "valid-minimal"]
            )


class ReceiptDispatchTest(unittest.TestCase):
    """Require Type 02 receipts to carry matching contract identity."""

    def test_type02_receipt_requires_matching_contract_type(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            receipt = bundle / "generation-receipt.json"
            receipt.write_text(
                json.dumps({"scenario": "valid-minimal"}),
                encoding="utf-8",
            )
            self.assertIsNone(
                scenario_from_bundle(TYPE02_WORKFLOW, bundle)
            )
            receipt.write_text(
                json.dumps(
                    {
                        "contract": {"type_number": "02"},
                        "scenario": "valid-minimal",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                scenario_from_bundle(TYPE02_WORKFLOW, bundle),
                "valid-minimal",
            )


class JavaDispatchTest(unittest.TestCase):
    """Prove Java receives the type only when its interface requires it."""

    @staticmethod
    def completed(batch_id: str) -> subprocess.CompletedProcess[str]:
        result = {
            "batch_id": batch_id,
            "row_count": 2,
            "status": "succeeded",
        }
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(result) + "\n",
            stderr="",
        )

    def test_type02_java_command_has_exact_typed_dispatch(self) -> None:
        batch_id = "B202607230000101"
        with patch(
            "workflow.subprocess.run",
            return_value=self.completed(batch_id),
        ) as invoked:
            run_java(TYPE02_WORKFLOW, batch_id, configuration())

        command = invoked.call_args.args[0]
        self.assertEqual(command.count("--rm"), 1)
        self.assertEqual(command[-4:], ["--batch-id", batch_id, "--type", "02"])

    def test_java_cannot_return_another_batch_identity(self) -> None:
        with patch(
            "workflow.subprocess.run",
            return_value=self.completed("B202607230000999"),
        ):
            with self.assertRaises(PipelineError):
                run_java(
                    TYPE02_WORKFLOW,
                    "B202607230000101",
                    configuration(),
                )


class EvidenceAdapterTest(unittest.TestCase):
    """Prove evidence compatibility, complete controls, and privacy."""

    def test_type02_success_evidence_allowlists_aggregate_fields(self) -> None:
        observed = TYPE02_WORKFLOW.java_evidence(
            {
                "batch_id": "B202607230000101",
                "credit_amount": "200.00",
                "csv_file": "sanitized.csv",
                "csv_sha256": "c" * 64,
                "debit_amount": "26.55",
                "description": "private description",
                "net_amount": "173.45",
                "payer_document": "12345678901",
                "returned_count": 1,
                "row_count": 2,
                "status": "succeeded",
            }
        )

        self.assertEqual(observed["file_type"], "02")
        self.assertEqual(observed["credit_amount"], "200.00")
        self.assertNotIn("description", observed)
        self.assertNotIn("payer_document", observed)

    def test_type02_rejection_normalizes_only_safe_common_controls(
        self,
    ) -> None:
        java_result: dict[str, object] = {
            "computed_event_count": 2,
            "computed_net_amount": "173.45",
            "declared_event_count": 3,
            "declared_net_amount": "200.00",
            "payer_document": "12345678901",
        }
        self.assertEqual(
            TYPE02_WORKFLOW.diagnostic_controls(java_result),
            DiagnosticControls(
                computed_count=2,
                computed_net_amount="173.45",
                declared_count=3,
                declared_net_amount="200.00",
            ),
        )
        diagnostic = TYPE02_WORKFLOW.rejection_diagnostic(
            java_result,
            code="SOURCE_CONTROL_TOTAL_MISMATCH",
            configuration=configuration(),
        )
        self.assertNotIn("payer_document", diagnostic)
        self.assertEqual(diagnostic["file_type"], "02")
        self.assertEqual(diagnostic["status"], "completed")

    def test_type02_evidence_keeps_full_source_and_stage_controls(
        self,
    ) -> None:
        raw = published_type02_raw()
        reconciliation: dict[str, object] = {
            "currency": "BRL",
            "staged_count": 2,
            "staged_credit_amount": "200.00",
            "staged_debit_amount": "26.55",
            "staged_net_amount": "173.45",
            "staged_returned_count": 1,
        }
        load = LoadResult(
            batch_id=raw.batch_id,
            csv_filename="sanitized.csv",
            csv_sha256="c" * 64,
            row_count=2,
            net_amount="173.45",
            procedure_runs=(),
            reconciliation=reconciliation,
        )

        observed = TYPE02_WORKFLOW.postgres_load_evidence(
            load,
            raw=raw,
            status="database_committed_pending_archive",
        )
        self.assertEqual(
            observed["source_controls"],
            dict(raw.source_controls),
        )
        self.assertEqual(
            observed["stage_controls"],
            {
                "credit_amount": "200.00",
                "currency": "BRL",
                "debit_amount": "26.55",
                "net_amount": "173.45",
                "returned_count": 1,
                "row_count": 2,
            },
        )

    def test_type02_loader_observation_is_complete(self) -> None:
        prepared = PreparedType02Load(
            batch_id="B202607230000101",
            raw_filename="raw.txt",
            raw_sha256="a" * 64,
            raw_manifest_sha256="b" * 64,
            source_controls={
                "currency": "BRL",
                "event_count": 2,
                "credit_amount": "200.00",
                "debit_amount": "26.55",
                "net_amount": "173.45",
            },
            csv_filename="sanitized.csv",
            csv_sha256="c" * 64,
            csv_size_bytes=100,
            stage_controls={
                "currency": "BRL",
                "row_count": 2,
                "credit_amount": "200.00",
                "debit_amount": "26.55",
                "net_amount": "173.45",
                "returned_count": 1,
            },
            csv_bytes=b"safe",
        )

        self.assertEqual(
            TYPE02_WORKFLOW.prepared_observation(prepared),
            {
                "batch_id": "B202607230000101",
                "credit_amount": "200.00",
                "csv_sha256": "c" * 64,
                "debit_amount": "26.55",
                "net_amount": "173.45",
                "returned_count": 1,
                "row_count": 2,
                "status": "succeeded",
            },
        )


if __name__ == "__main__":
    unittest.main()
