"""Unit contracts for the Type 05 workflow adapter."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from config import RuntimeConfiguration, SftpRole
from lifecycle import _build_sanitized_observation
from loader_common import DiagnosticControls, LoadResult
from raw_publisher import PublishedRaw
from run_type import build_parser
from type05_loader import PreparedType05Load
from workflow import run_java
from workflow_registry import TYPE05_WORKFLOW, workflow_for_type


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = (
    ROOT
    / "contracts"
    / "types"
    / "05-merchant-fee-assessment"
    / "main"
    / "expected-sanitized.csv"
)
BATCH_ID = "B202607230000401"
SOURCE_FILENAME = (
    "NW_MERCHANT_FEES_20260723_B202607230000401.csv"
)
CONTROLS: dict[str, int | str] = {
    "assessed_fee": "12.36",
    "calculated_fee": "12.36",
    "currency": "BRL",
    "gross_amount": "1001.00",
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


def _prepared() -> PreparedType05Load:
    csv_bytes = CSV_PATH.read_bytes()
    return PreparedType05Load(
        batch_id=BATCH_ID,
        raw_filename=SOURCE_FILENAME,
        raw_sha256="a" * 64,
        raw_manifest_sha256="b" * 64,
        source_controls=CONTROLS,
        csv_filename=(
            SOURCE_FILENAME.removesuffix(".csv") + "_SANITIZED.csv"
        ),
        csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
        csv_size_bytes=len(csv_bytes),
        stage_controls=CONTROLS,
        csv_bytes=csv_bytes,
    )


class Type05WorkflowTest(unittest.TestCase):
    """Prove routing, typed dispatch, oracle input, and safe evidence."""

    def test_registry_parser_and_scenarios_expose_type05(self) -> None:
        self.assertIs(workflow_for_type("05"), TYPE05_WORKFLOW)
        parsed = build_parser().parse_args(
            ["--type", "05", "--scenario", "valid-minimal"]
        )
        self.assertEqual(parsed.type_number, "05")
        self.assertEqual(
            TYPE05_WORKFLOW.scenario_batch_ids,
            {
                "valid-minimal": "B202607230000401",
                "valid-boundary": "B200002290000402",
                "malformed": "B202607230000403",
                "rounding-half-up": "B202607230000404",
                "DF-SOURCE-005": "B202607230000405",
            },
        )

    def test_java_command_has_exact_type05_dispatch(self) -> None:
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
            run_java(TYPE05_WORKFLOW, BATCH_ID, _configuration())

        self.assertEqual(
            invoked.call_args.args[0][-4:],
            ["--batch-id", BATCH_ID, "--type", "05"],
        )

    def test_prepared_observation_matches_approved_oracle(self) -> None:
        observation = TYPE05_WORKFLOW.prepared_observation(_prepared())
        self.assertEqual(
            observation,
            {
                "assessed_fee": "12.36",
                "batch_id": BATCH_ID,
                "calculated_fee": "12.36",
                "csv_sha256": hashlib.sha256(
                    CSV_PATH.read_bytes()
                ).hexdigest(),
                "gross_amount": "1001.00",
                "row_count": 2,
                "status": "succeeded",
            },
        )
        result = TYPE05_WORKFLOW.compare_sanitized(
            "valid-minimal",
            batch_id=BATCH_ID,
            observation=observation,
        )
        self.assertTrue(result.matches)
        self.assertEqual(result.oracle_status, "oracle_matched")

    def test_sanitized_recovery_uses_type05_controls_without_net_amount(
        self,
    ) -> None:
        """Protect committed recovery from assuming another type's controls."""

        raw = PublishedRaw(
            batch_id=BATCH_ID,
            file_type="05",
            filename=SOURCE_FILENAME,
            sha256="a" * 64,
            size_bytes=390,
            manifest_sha256="b" * 64,
            source_controls=CONTROLS,
        )
        csv_filename = (
            SOURCE_FILENAME.removesuffix(".csv") + "_SANITIZED.csv"
        )
        csv_sha256 = hashlib.sha256(CSV_PATH.read_bytes()).hexdigest()
        observation = _build_sanitized_observation(
            raw,
            manifest={"stage_controls": CONTROLS},
            filename=csv_filename,
            digest=csv_sha256,
        )

        self.assertEqual(
            observation,
            {
                "assessed_fee": "12.36",
                "batch_id": BATCH_ID,
                "calculated_fee": "12.36",
                "code": None,
                "csv_file": csv_filename,
                "csv_sha256": csv_sha256,
                "gross_amount": "1001.00",
                "row_count": 2,
                "status": "succeeded",
            },
        )
        self.assertNotIn("net_amount", observation)
        self.assertTrue(
            TYPE05_WORKFLOW.compare_sanitized(
                "valid-minimal",
                batch_id=BATCH_ID,
                observation=observation,
            ).matches
        )

    def test_java_evidence_allowlists_only_aggregate_fields(self) -> None:
        observed = TYPE05_WORKFLOW.java_evidence(
            {
                "assessed_fee": "12.36",
                "batch_id": BATCH_ID,
                "calculated_fee": "12.36",
                "csv_file": "sanitized.csv",
                "csv_sha256": "c" * 64,
                "description": "restricted description",
                "gross_amount": "1001.00",
                "merchant_tax_id_masked": "restricted mask",
                "row_count": 2,
                "status": "succeeded",
            }
        )
        self.assertEqual(observed["file_type"], "05")
        self.assertEqual(observed["assessed_fee"], "12.36")
        self.assertNotIn("description", observed)
        self.assertNotIn("merchant_tax_id_masked", observed)

    def test_source_defect_diagnostics_use_only_safe_controls(self) -> None:
        java_result: dict[str, object] = {
            "computed_assessed_fee": "1.00",
            "computed_calculated_fee": "1.00",
            "computed_gross_amount": "100.00",
            "computed_row_count": 1,
            "declared_assessed_fee": "0.99",
            "declared_calculated_fee": "1.00",
            "declared_gross_amount": "100.00",
            "declared_row_count": 1,
            "description": "restricted description",
        }
        self.assertEqual(
            TYPE05_WORKFLOW.diagnostic_controls(java_result),
            DiagnosticControls(
                computed_count=1,
                computed_net_amount="1.00",
                declared_count=1,
                declared_net_amount="0.99",
            ),
        )
        evidence = TYPE05_WORKFLOW.rejection_diagnostic(
            java_result,
            code="SOURCE_CONTROL_ASSESSED_FEE_MISMATCH",
            configuration=_configuration(),
        )
        self.assertEqual(evidence["file_type"], "05")
        self.assertEqual(evidence["status"], "completed")
        self.assertNotIn("description", evidence)
        malformed = TYPE05_WORKFLOW.rejection_diagnostic(
            {},
            code="INVALID_CSV_QUOTING",
            configuration=_configuration(),
        )
        self.assertEqual(malformed["status"], "not_run")

    def test_postgres_evidence_keeps_complete_control_sets(self) -> None:
        raw = PublishedRaw(
            batch_id=BATCH_ID,
            file_type="05",
            filename=SOURCE_FILENAME,
            sha256="a" * 64,
            size_bytes=390,
            manifest_sha256="b" * 64,
            source_controls=CONTROLS,
        )
        reconciliation: dict[str, object] = {
            "currency": "BRL",
            "staged_count": 2,
            "staged_gross_amount": "1001.00",
            "staged_assessed_fee": "12.36",
            "staged_calculated_fee": "12.36",
        }
        load = LoadResult(
            batch_id=BATCH_ID,
            csv_filename="sanitized.csv",
            csv_sha256="c" * 64,
            row_count=2,
            net_amount="12.36",
            procedure_runs=(),
            reconciliation=reconciliation,
        )
        evidence = TYPE05_WORKFLOW.postgres_load_evidence(
            load,
            raw=raw,
            status="database_committed_pending_archive",
        )
        self.assertEqual(evidence["source_controls"], CONTROLS)
        self.assertEqual(evidence["stage_controls"], CONTROLS)


if __name__ == "__main__":
    unittest.main()
