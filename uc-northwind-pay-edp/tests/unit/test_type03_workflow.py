"""Unit contracts for the Type 03 workflow adapter."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from config import RuntimeConfiguration, SftpRole
from loader_common import DiagnosticControls
from run_type import build_parser
from type03_loader import PreparedType03Load
from workflow import run_java
from workflow_registry import TYPE03_WORKFLOW, workflow_for_type


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = (
    ROOT
    / "contracts"
    / "types"
    / "03-payment-slip-settlement"
    / "main"
    / "expected-sanitized.csv"
)
BATCH_ID = "B202607230000201"
SOURCE_FILENAME = (
    "NW_PAYMENT_SLIP_20260723_B202607230000201.rem"
)
SOURCE_CONTROLS: dict[str, int | str] = {
    "currency": "BRL",
    "discount_amount": "5.00",
    "face_amount": "200.00",
    "fee_amount": "3.50",
    "logical_count": 2,
    "lot_count": 1,
    "net_amount": "198.50",
    "orphan_segment_count": 0,
    "physical_record_count": 8,
}
STAGE_CONTROLS: dict[str, int | str] = {
    "currency": "BRL",
    "discount_amount": "5.00",
    "face_amount": "200.00",
    "fee_amount": "3.50",
    "net_amount": "198.50",
    "orphan_segment_count": 0,
    "row_count": 2,
}


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


def _prepared() -> PreparedType03Load:
    csv_bytes = CSV_PATH.read_bytes()
    return PreparedType03Load(
        batch_id=BATCH_ID,
        raw_filename=SOURCE_FILENAME,
        raw_sha256="a" * 64,
        raw_manifest_sha256="b" * 64,
        source_controls=SOURCE_CONTROLS,
        csv_filename=SOURCE_FILENAME.removesuffix(".rem") + ".csv",
        csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
        csv_size_bytes=len(csv_bytes),
        stage_controls=STAGE_CONTROLS,
        csv_bytes=csv_bytes,
    )


class Type03WorkflowTest(unittest.TestCase):
    """Prove routing, typed dispatch, oracle input, and safe evidence."""

    def test_registry_parser_and_scenarios_expose_type03(self) -> None:
        self.assertIs(workflow_for_type("03"), TYPE03_WORKFLOW)
        parsed = build_parser().parse_args(
            ["--type", "03", "--scenario", "valid-minimal"]
        )
        self.assertEqual(parsed.type_number, "03")
        self.assertEqual(
            TYPE03_WORKFLOW.scenario_batch_ids,
            {
                "valid-minimal": "B202607230000201",
                "valid-boundary": "B202402290000202",
                "malformed": "B202607230000203",
                "multi-lot": "B202607230000204",
                "DF-SOURCE-003": "B202607230000205",
            },
        )

    def test_java_command_has_exact_type03_dispatch(self) -> None:
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
            run_java(TYPE03_WORKFLOW, BATCH_ID, _configuration())

        command = invoked.call_args.args[0]
        self.assertEqual(command.count("--rm"), 1)
        self.assertEqual(
            command[-4:],
            ["--batch-id", BATCH_ID, "--type", "03"],
        )

    def test_prepared_observation_matches_approved_oracle(self) -> None:
        observation = TYPE03_WORKFLOW.prepared_observation(_prepared())

        self.assertEqual(
            observation,
            {
                "batch_id": BATCH_ID,
                "csv_sha256": hashlib.sha256(
                    CSV_PATH.read_bytes()
                ).hexdigest(),
                "discount_amount": "5.00",
                "face_amount": "200.00",
                "fee_amount": "3.50",
                "net_amount": "198.50",
                "orphan_segment_count": 0,
                "row_count": 2,
                "status": "succeeded",
            },
        )
        result = TYPE03_WORKFLOW.compare_sanitized(
            "valid-minimal",
            batch_id=BATCH_ID,
            observation=observation,
        )
        self.assertTrue(result.matches)
        self.assertEqual(result.oracle_status, "oracle_matched")

    def test_java_evidence_allowlists_only_aggregate_fields(self) -> None:
        observed = TYPE03_WORKFLOW.java_evidence(
            {
                "batch_id": BATCH_ID,
                "csv_file": "sanitized.csv",
                "csv_sha256": "c" * 64,
                "discount_amount": "5.00",
                "face_amount": "200.00",
                "fee_amount": "3.50",
                "net_amount": "198.50",
                "orphan_segment_count": 0,
                "payment_reference": "1" * 48,
                "beneficiary_tax_id": "00012345678909",
                "row_count": 2,
                "status": "succeeded",
            }
        )

        self.assertEqual(observed["file_type"], "03")
        self.assertEqual(observed["face_amount"], "200.00")
        self.assertNotIn("payment_reference", observed)
        self.assertNotIn("beneficiary_tax_id", observed)

    def test_source_defect_diagnostics_use_only_safe_controls(self) -> None:
        java_result: dict[str, object] = {
            "computed_discount_amount": "5.00",
            "computed_face_amount": "200.00",
            "computed_fee_amount": "3.50",
            "computed_logical_count": 2,
            "computed_lot_count": 1,
            "computed_net_amount": "198.50",
            "computed_orphan_segment_count": 0,
            "computed_physical_record_count": 8,
            "declared_discount_amount": "5.00",
            "declared_face_amount": "200.00",
            "declared_fee_amount": "3.50",
            "declared_logical_count": 2,
            "declared_lot_count": 1,
            "declared_net_amount": "198.49",
            "declared_physical_record_count": 8,
            "beneficiary_tax_id": "00012345678909",
        }

        self.assertEqual(
            TYPE03_WORKFLOW.diagnostic_controls(java_result),
            DiagnosticControls(
                computed_count=2,
                computed_net_amount="198.50",
                declared_count=2,
                declared_net_amount="198.49",
            ),
        )
        evidence = TYPE03_WORKFLOW.rejection_diagnostic(
            java_result,
            code="SOURCE_CONTROL_NET_MISMATCH",
            configuration=_configuration(),
        )
        self.assertEqual(evidence["file_type"], "03")
        self.assertEqual(evidence["status"], "completed")
        self.assertNotIn("beneficiary_tax_id", evidence)

    def test_pair_mismatch_diagnostic_does_not_claim_parser_rerun(self) -> None:
        evidence = TYPE03_WORKFLOW.rejection_diagnostic(
            {"beneficiary_tax_id": "00012345678909"},
            code="SEGMENT_PAIR_MISMATCH",
            configuration=_configuration(),
        )

        self.assertEqual(
            evidence,
            {
                "file_type": "03",
                "reason": "SEGMENT_PAIR_MISMATCH",
                "status": "not_run",
            },
        )


if __name__ == "__main__":
    unittest.main()
