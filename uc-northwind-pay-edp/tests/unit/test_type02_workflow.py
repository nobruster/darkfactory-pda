"""Unit contracts for the Type 02 workflow adapter.

Type 02 was the only implemented type whose workflow adapter had no unit test —
no file under `tests/` referenced `Type02WorkflowAdapter` at all. These are the
same four contracts the other types assert: routing, typed Java dispatch, the
oracle input, and evidence that carries aggregates only.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from config import RuntimeConfiguration, SftpRole
from run_type import build_parser
from type02_loader import PreparedType02Load
from workflow import run_java
from workflow_registry import TYPE02_WORKFLOW, workflow_for_type


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = (
    ROOT
    / "contracts"
    / "types"
    / "02-instant-payment-events"
    / "main"
    / "expected-sanitized.csv"
)
BATCH_ID = "B202607230000101"
SOURCE_FILENAME = "NW_INSTANT_PAYMENT_20260723_B202607230000101.txt"
SOURCE_CONTROLS: dict[str, int | str] = {
    "credit_amount": "200.00",
    "currency": "BRL",
    "debit_amount": "26.55",
    "event_count": 2,
    "net_amount": "173.45",
}
STAGE_CONTROLS: dict[str, int | str] = {
    "credit_amount": "200.00",
    "currency": "BRL",
    "debit_amount": "26.55",
    "net_amount": "173.45",
    "returned_count": 1,
    "row_count": 2,
}

# Every restricted value the sanitized Type 02 output must never carry, and
# which a diagnostic must never echo back.
RESTRICTED_MARKERS = ("cpf", "cnpj", "12345678909", "payer_document")


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


def _prepared() -> PreparedType02Load:
    csv_bytes = CSV_PATH.read_bytes()
    return PreparedType02Load(
        batch_id=BATCH_ID,
        raw_filename=SOURCE_FILENAME,
        raw_sha256="a" * 64,
        raw_manifest_sha256="b" * 64,
        source_controls=SOURCE_CONTROLS,
        csv_filename=SOURCE_FILENAME.removesuffix(".txt") + ".csv",
        csv_sha256=hashlib.sha256(csv_bytes).hexdigest(),
        csv_size_bytes=len(csv_bytes),
        stage_controls=STAGE_CONTROLS,
        csv_bytes=csv_bytes,
    )


class Type02WorkflowTest(unittest.TestCase):
    """Prove routing, typed dispatch, oracle input, and safe evidence."""

    def test_registry_parser_and_scenarios_expose_type02(self) -> None:
        self.assertIs(workflow_for_type("02"), TYPE02_WORKFLOW)
        parsed = build_parser().parse_args(
            ["--type", "02", "--scenario", "valid-minimal"]
        )
        self.assertEqual(parsed.type_number, "02")
        self.assertEqual(
            dict(TYPE02_WORKFLOW.scenario_batch_ids),
            {
                "valid-minimal": "B202607230000101",
                "valid-boundary": "B202402290000102",
                "escaped-content": "B202607230000104",
                "malformed": "B202607230000103",
                "DF-SOURCE-002": "B202607230000105",
            },
        )

    def test_java_command_has_exact_type02_dispatch(self) -> None:
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
        with patch("workflow.subprocess.run", return_value=completed) as invoked:
            run_java(TYPE02_WORKFLOW, BATCH_ID, _configuration())

        command = invoked.call_args.args[0]
        self.assertEqual(command.count("--rm"), 1)
        self.assertEqual(
            command[-4:],
            ["--batch-id", BATCH_ID, "--type", "02"],
        )

    def test_prepared_observation_exposes_only_aggregate_controls(self) -> None:
        observation = TYPE02_WORKFLOW.prepared_observation(_prepared())

        self.assertEqual(observation["batch_id"], BATCH_ID)
        self.assertEqual(observation["row_count"], 2)
        self.assertEqual(observation["credit_amount"], "200.00")
        self.assertEqual(observation["debit_amount"], "26.55")
        self.assertEqual(observation["net_amount"], "173.45")
        self.assertEqual(observation["returned_count"], 1)

        # The oracle input is aggregates and lineage only. A per-event field
        # here would put a document token into the comparison path.
        serialized = json.dumps(observation, sort_keys=True).lower()
        for marker in RESTRICTED_MARKERS:
            self.assertNotIn(marker, serialized)
        self.assertNotIn("end_to_end_id", serialized)
        self.assertNotIn("transaction_id", serialized)

    def test_java_evidence_allowlists_only_aggregate_fields(self) -> None:
        noisy = {
            "batch_id": BATCH_ID,
            "credit_amount": "200.00",
            "csv_file": "x.csv",
            "csv_sha256": "c" * 64,
            "debit_amount": "26.55",
            "net_amount": "173.45",
            "returned_count": 1,
            "row_count": 2,
            "status": "succeeded",
            # None of the following may survive the allowlist.
            "payer_document": "12345678909",
            "end_to_end_id": "E2026072300000000000000000000001",
            "stderr": "unexpected detail",
        }
        evidence = TYPE02_WORKFLOW.java_evidence(noisy)

        self.assertNotIn("payer_document", evidence)
        self.assertNotIn("end_to_end_id", evidence)
        self.assertNotIn("stderr", evidence)
        self.assertEqual(evidence["net_amount"], "173.45")
        self.assertEqual(evidence["returned_count"], 1)

    def test_source_defect_diagnostics_use_only_safe_controls(self) -> None:
        controls = TYPE02_WORKFLOW.diagnostic_controls(
            {
                "code": "SOURCE_CONTROL_NET_MISMATCH",
                "computed_event_count": 2,
                "computed_net_amount": "173.45",
                "declared_event_count": 2,
                "declared_net_amount": "173.44",
                "status": "quarantined",
                "payer_document": "12345678909",
            }
        )

        # The one-cent contradiction is preserved exactly as published.
        self.assertEqual(controls.computed_net_amount, "173.45")
        self.assertEqual(controls.declared_net_amount, "173.44")
        self.assertEqual(controls.computed_count, 2)
        self.assertEqual(controls.declared_count, 2)

        serialized = json.dumps(
            {
                "computed_count": controls.computed_count,
                "computed_net_amount": controls.computed_net_amount,
                "declared_count": controls.declared_count,
                "declared_net_amount": controls.declared_net_amount,
            },
            sort_keys=True,
        )
        for marker in RESTRICTED_MARKERS:
            self.assertNotIn(marker, serialized.lower())

    def test_malformed_declarations_are_dropped_rather_than_coerced(self) -> None:
        """A wrongly typed control becomes absent, never a guessed value."""

        controls = TYPE02_WORKFLOW.diagnostic_controls(
            {
                "computed_event_count": True,  # bool is not an int here
                "computed_net_amount": 173.45,  # float is not a money lexeme
                "declared_event_count": "2",
                "declared_net_amount": None,
            }
        )
        self.assertIsNone(controls.computed_count)
        self.assertIsNone(controls.computed_net_amount)
        self.assertIsNone(controls.declared_count)
        self.assertIsNone(controls.declared_net_amount)


if __name__ == "__main__":
    unittest.main()
