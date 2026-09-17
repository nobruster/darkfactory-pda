"""Unit contracts for the Type 04 workflow adapter."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from config import RuntimeConfiguration, SftpRole
from loader_common import DiagnosticControls, LoadResult
from raw_publisher import PublishedRaw
from run_type import build_parser
from type04_loader import PreparedType04Load
from workflow import run_java
from workflow_registry import TYPE04_WORKFLOW, workflow_for_type


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = (
    ROOT
    / "contracts"
    / "types"
    / "04-ted-transfer-settlement"
    / "main"
    / "expected-sanitized.csv"
)
BATCH_ID = "B202607230000301"
SOURCE_FILENAME = (
    "NW_TED_SETTLEMENT_20260723_B202607230000301.dat"
)
SOURCE_CONTROLS: dict[str, int | str] = {
    "currency": "BRL",
    "gross_amount": "1250.00",
    "net_amount": "1000.00",
    "return_amount": "-250.00",
    "return_count": 1,
    "transfer_count": 2,
}
STAGE_CONTROLS: dict[str, int | str] = {
    **SOURCE_CONTROLS,
    "row_count": 3,
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


def _prepared() -> PreparedType04Load:
    csv_bytes = CSV_PATH.read_bytes()
    return PreparedType04Load(
        batch_id=BATCH_ID,
        raw_filename=SOURCE_FILENAME,
        raw_sha256="a" * 64,
        raw_manifest_sha256="b" * 64,
        source_controls=SOURCE_CONTROLS,
        csv_filename=SOURCE_FILENAME.removesuffix(".dat") + ".csv",
        csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
        csv_size_bytes=len(csv_bytes),
        stage_controls=STAGE_CONTROLS,
        csv_bytes=csv_bytes,
    )


class Type04WorkflowTest(unittest.TestCase):
    """Prove routing, typed dispatch, oracle input, and safe evidence."""

    def test_registry_parser_and_scenarios_expose_type04(self) -> None:
        self.assertIs(workflow_for_type("04"), TYPE04_WORKFLOW)
        parsed = build_parser().parse_args(
            ["--type", "04", "--scenario", "valid-minimal"]
        )
        self.assertEqual(parsed.type_number, "04")
        self.assertEqual(
            TYPE04_WORKFLOW.scenario_batch_ids,
            {
                "valid-minimal": "B202607230000301",
                "valid-boundary": "B200002290000302",
                "malformed": "B202607230000303",
                "all-returned-zero-net": "B202607230000304",
                "DF-SOURCE-004": "B202607230000305",
            },
        )

    def test_java_command_has_exact_type04_dispatch(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                json.dumps(
                    {
                        "batch_id": BATCH_ID,
                        "row_count": 3,
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
            run_java(TYPE04_WORKFLOW, BATCH_ID, _configuration())

        self.assertEqual(
            invoked.call_args.args[0][-4:],
            ["--batch-id", BATCH_ID, "--type", "04"],
        )

    def test_prepared_observation_matches_approved_oracle(self) -> None:
        observation = TYPE04_WORKFLOW.prepared_observation(_prepared())

        self.assertEqual(
            observation,
            {
                "batch_id": BATCH_ID,
                "csv_sha256": hashlib.sha256(
                    CSV_PATH.read_bytes()
                ).hexdigest(),
                "gross_amount": "1250.00",
                "net_amount": "1000.00",
                "return_amount": "-250.00",
                "return_count": 1,
                "row_count": 3,
                "status": "succeeded",
                "transfer_count": 2,
            },
        )
        result = TYPE04_WORKFLOW.compare_sanitized(
            "valid-minimal",
            batch_id=BATCH_ID,
            observation=observation,
        )
        self.assertTrue(result.matches)
        self.assertEqual(result.oracle_status, "oracle_matched")

    def test_java_evidence_allowlists_only_aggregate_fields(self) -> None:
        observed = TYPE04_WORKFLOW.java_evidence(
            {
                "batch_id": BATCH_ID,
                "csv_file": "sanitized.csv",
                "csv_sha256": "c" * 64,
                "gross_amount": "1250.00",
                "net_amount": "1000.00",
                "return_amount": "-250.00",
                "return_count": 1,
                "row_count": 3,
                "status": "succeeded",
                "transfer_count": 2,
                "payer_account_token": "restricted token",
                "payer_tax_id_masked": "restricted mask",
            }
        )

        self.assertEqual(observed["file_type"], "04")
        self.assertEqual(observed["return_amount"], "-250.00")
        self.assertNotIn("payer_account_token", observed)
        self.assertNotIn("payer_tax_id_masked", observed)

    def test_source_defect_diagnostics_use_only_safe_controls(self) -> None:
        java_result: dict[str, object] = {
            "computed_gross_amount": "1250.00",
            "computed_net_amount": "1000.00",
            "computed_return_amount": "-250.00",
            "computed_return_count": 1,
            "computed_transfer_count": 2,
            "declared_gross_amount": "1250.00",
            "declared_net_amount": "999.99",
            "declared_return_amount": "-250.00",
            "declared_return_count": 1,
            "declared_transfer_count": 2,
            "payer_account_token": "restricted token",
        }

        self.assertEqual(
            TYPE04_WORKFLOW.diagnostic_controls(java_result),
            DiagnosticControls(
                computed_count=2,
                computed_net_amount="1000.00",
                declared_count=2,
                declared_net_amount="999.99",
            ),
        )
        evidence = TYPE04_WORKFLOW.rejection_diagnostic(
            java_result,
            code="SOURCE_CONTROL_NET_MISMATCH",
            configuration=_configuration(),
        )
        self.assertEqual(evidence["file_type"], "04")
        self.assertEqual(evidence["status"], "completed")
        self.assertNotIn("payer_account_token", evidence)

    def test_postgres_evidence_keeps_complete_control_sets(self) -> None:
        raw = PublishedRaw(
            batch_id=BATCH_ID,
            file_type="04",
            filename=SOURCE_FILENAME,
            sha256="a" * 64,
            size_bytes=563,
            manifest_sha256="b" * 64,
            source_controls=SOURCE_CONTROLS,
        )
        reconciliation: dict[str, object] = {
            "currency": "BRL",
            "staged_transfer_count": 2,
            "staged_return_count": 1,
            "staged_gross_amount": "1250.00",
            "staged_return_amount": "-250.00",
            "staged_net_amount": "1000.00",
        }
        load = LoadResult(
            batch_id=BATCH_ID,
            csv_filename="sanitized.csv",
            csv_sha256="c" * 64,
            row_count=3,
            net_amount="1000.00",
            procedure_runs=(),
            reconciliation=reconciliation,
        )

        evidence = TYPE04_WORKFLOW.postgres_load_evidence(
            load,
            raw=raw,
            status="database_committed_pending_archive",
        )
        self.assertEqual(
            evidence["source_controls"],
            SOURCE_CONTROLS,
        )
        self.assertEqual(
            evidence["stage_controls"],
            STAGE_CONTROLS,
        )


if __name__ == "__main__":
    unittest.main()
