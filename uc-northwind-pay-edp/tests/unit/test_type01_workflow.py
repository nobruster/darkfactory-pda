"""Unit contracts for the Type 01 workflow adapter."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import RuntimeConfiguration, SftpRole
from loader_common import DiagnosticControls
from raw_publisher import PublishedRaw
from run_type import build_parser
from type01_loader import PreparedType01Load
from workflow import run_java, scenario_from_bundle
from workflow_registry import TYPE01_WORKFLOW, workflow_for_type


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = (
    ROOT
    / "contracts"
    / "types"
    / "01-card-settlement"
    / "main"
    / "expected-sanitized.csv"
)
BATCH_ID = "B202607230000001"
SOURCE_FILENAME = (
    "NW_CARD_SETTLEMENT_20260723_B202607230000001.dat"
)


def _configuration() -> RuntimeConfiguration:
    role = SftpRole("test", "secret")
    return RuntimeConfiguration(
        root=ROOT,
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


def _raw() -> PublishedRaw:
    return PublishedRaw(
        batch_id=BATCH_ID,
        file_type="01",
        filename=SOURCE_FILENAME,
        sha256="a" * 64,
        size_bytes=338,
        manifest_sha256="b" * 64,
        source_controls={
            "currency": "BRL",
            "detail_count": 2,
            "net_amount": "173.45",
        },
    )


def _prepared() -> PreparedType01Load:
    csv_bytes = CSV_PATH.read_bytes()
    return PreparedType01Load(
        batch_id=BATCH_ID,
        raw_filename=SOURCE_FILENAME,
        raw_sha256="a" * 64,
        raw_manifest_sha256="b" * 64,
        source_count=2,
        source_net_amount="173.45",
        csv_filename=SOURCE_FILENAME.removesuffix(".dat") + ".csv",
        csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
        csv_size_bytes=len(csv_bytes),
        row_count=2,
        net_amount="173.45",
        rows=(),
    )


class Type01WorkflowTest(unittest.TestCase):
    """Prove typed dispatch, receipt identity, oracle input, and evidence."""

    def test_registry_parser_and_scenarios_expose_type01(self) -> None:
        self.assertIs(workflow_for_type("01"), TYPE01_WORKFLOW)
        self.assertTrue(TYPE01_WORKFLOW.pass_type_to_java)
        self.assertTrue(TYPE01_WORKFLOW.receipt_requires_type)
        parsed = build_parser().parse_args(
            ["--type", "01", "--scenario", "valid-minimal"]
        )
        self.assertEqual(parsed.type_number, "01")
        self.assertEqual(
            TYPE01_WORKFLOW.scenario_batch_ids,
            {
                "valid-minimal": "B202607230000001",
                "valid-boundary": "B202402290000001",
                "negative-overpunch": "B202607230000002",
                "malformed": "B202607230000003",
                "DF-SOURCE-001": "B202607230000004",
            },
        )

    def test_receipt_requires_matching_type01_contract_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            receipt = bundle / "generation-receipt.json"
            receipt.write_text(
                json.dumps({"scenario": "valid-minimal"}),
                encoding="utf-8",
            )
            self.assertIsNone(
                scenario_from_bundle(TYPE01_WORKFLOW, bundle)
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
            self.assertIsNone(
                scenario_from_bundle(TYPE01_WORKFLOW, bundle)
            )
            receipt.write_text(
                json.dumps(
                    {
                        "contract": {"type_number": "01"},
                        "scenario": "valid-minimal",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                scenario_from_bundle(TYPE01_WORKFLOW, bundle),
                "valid-minimal",
            )

    def test_java_command_has_exact_type01_dispatch(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                json.dumps(
                    {
                        "batch_id": BATCH_ID,
                        "row_count": 2,
                        "status": "succeeded",
                    }
                )
                + "\n"
            ),
            stderr="",
        )
        with patch(
            "workflow.subprocess.run",
            return_value=completed,
        ) as invoked:
            run_java(TYPE01_WORKFLOW, BATCH_ID, _configuration())

        command = invoked.call_args.args[0]
        self.assertEqual(command.count("--rm"), 1)
        self.assertEqual(
            command[-4:],
            ["--batch-id", BATCH_ID, "--type", "01"],
        )

    def test_prepared_observation_matches_approved_oracle(self) -> None:
        observation = TYPE01_WORKFLOW.prepared_observation(_prepared())

        self.assertEqual(
            observation,
            {
                "batch_id": BATCH_ID,
                "csv_sha256": hashlib.sha256(
                    CSV_PATH.read_bytes()
                ).hexdigest(),
                "net_amount": "173.45",
                "row_count": 2,
                "status": "succeeded",
            },
        )
        result = TYPE01_WORKFLOW.compare_sanitized(
            "valid-minimal",
            batch_id=BATCH_ID,
            observation=observation,
        )
        self.assertTrue(result.matches)
        self.assertEqual(result.oracle_status, "oracle_matched")

    def test_evidence_shapes_remain_compatible(self) -> None:
        raw = _raw()
        self.assertEqual(
            TYPE01_WORKFLOW.raw_publication_evidence(
                raw,
                status="published",
            ),
            {
                "batch_id": raw.batch_id,
                "manifest_last": True,
                "sha256": raw.sha256,
                "status": "published",
            },
        )
        self.assertEqual(
            TYPE01_WORKFLOW.final_status_evidence(
                raw,
                status="quarantined",
                code="INVALID_OVERPUNCH",
            ),
            {
                "batch_id": raw.batch_id,
                "code": "INVALID_OVERPUNCH",
                "scope": "batch",
                "status": "quarantined",
            },
        )

    def test_java_evidence_and_diagnostics_exclude_raw_identifiers(
        self,
    ) -> None:
        java_result: dict[str, object] = {
            "batch_id": BATCH_ID,
            "computed_detail_count": 2,
            "computed_net_amount": "173.45",
            "declared_detail_count": 2,
            "declared_net_amount": "173.44",
            "detail_amounts": ["123.45", "50.00"],
            "pan": "4111111111111111",
            "cpf": "12345678909",
            "record_number": None,
            "status": "rejected",
            "transaction_id": None,
        }

        evidence = TYPE01_WORKFLOW.java_evidence(java_result)
        self.assertEqual(evidence["computed_detail_count"], 2)
        self.assertEqual(evidence["detail_amounts"], ["123.45", "50.00"])
        self.assertNotIn("pan", evidence)
        self.assertNotIn("cpf", evidence)
        self.assertEqual(
            TYPE01_WORKFLOW.diagnostic_controls(java_result),
            DiagnosticControls(
                computed_count=2,
                computed_net_amount="173.45",
                declared_count=2,
                declared_net_amount="173.44",
            ),
        )


if __name__ == "__main__":
    unittest.main()
