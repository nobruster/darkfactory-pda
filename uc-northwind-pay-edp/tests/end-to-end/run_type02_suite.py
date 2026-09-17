"""Complete Type 02 acceptance suite for the local legacy topology."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[2]
for module_directory in (
    ROOT / "legacy" / "runner",
    ROOT / "legacy" / "publisher",
    ROOT / "legacy" / "intake",
):
    sys.path.insert(0, str(module_directory))

from config import RuntimeConfiguration  # noqa: E402
from evidence import EvidenceWriter  # noqa: E402
from raw_publisher import RawPublicationError, publish_bundle  # noqa: E402
from sftp_client import connect_sftp, exists  # noqa: E402


SCENARIOS = (
    "malformed",
    "valid-minimal",
    "DF-SOURCE-002",
    "valid-boundary",
    "escaped-content",
)
EXPECTED = {
    "malformed": ("B202607230000103", "quarantined"),
    "valid-minimal": ("B202607230000101", "succeeded"),
    "DF-SOURCE-002": ("B202607230000105", "quarantined"),
    "valid-boundary": ("B202402290000102", "succeeded"),
    "escaped-content": ("B202607230000104", "succeeded"),
}
EXPECTED_SUCCESS_BATCHES = {
    "B202607230000101",
    "B202402290000102",
    "B202607230000104",
}
EXPECTED_QUARANTINE_BATCHES = {
    "B202607230000103",
    "B202607230000105",
}
EXPECTED_REJECTIONS = {
    ("B202607230000103", "INVALID_FIELD_COUNT"),
    ("B202607230000105", "SOURCE_CONTROL_NET_MISMATCH"),
}


def runner_command(
    scenario: str,
    *,
    output_root: Path,
    evidence_root: Path,
) -> list[str]:
    """Return the public typed command used by every acceptance case."""

    return [
        sys.executable,
        str(ROOT / "legacy" / "runner" / "run_type.py"),
        "--type",
        "02",
        "--scenario",
        scenario,
        "--output-root",
        str(output_root),
        "--evidence-root",
        str(evidence_root),
    ]


def run_scenario(
    scenario: str,
    *,
    output_root: Path,
    evidence_root: Path,
) -> None:
    """Run one scenario without exposing raw records on failure."""

    result = subprocess.run(
        runner_command(
            scenario,
            output_root=output_root,
            evidence_root=evidence_root,
        ),
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise AssertionError(f"Type 02 scenario failed: {scenario}")
    output = json.loads(result.stdout.splitlines()[-1])
    expected_batch, expected_status = EXPECTED[scenario]
    if (
        output.get("batch_id") != expected_batch
        or output.get("status") != expected_status
    ):
        raise AssertionError(
            f"Type 02 terminal state is incorrect: {scenario}"
        )


def interrupt_scenario(
    scenario: str,
    *,
    boundary: str,
    output_root: Path,
    evidence_root: Path,
) -> None:
    """Inject a crash after one durable boundary and require no evidence."""

    batch_id = EXPECTED[scenario][0]
    environment = os.environ.copy()
    environment["NWP_TEST_INTERRUPT_AFTER"] = boundary
    environment["NWP_TEST_INTERRUPT_BATCH_ID"] = batch_id
    result = subprocess.run(
        runner_command(
            scenario,
            output_root=output_root,
            evidence_root=evidence_root,
        ),
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        env=environment,
        timeout=180,
    )
    if result.returncode != 2 or (evidence_root / batch_id).exists():
        raise AssertionError(
            f"Type 02 interruption was not isolated: {scenario}/{boundary}"
        )


def verify_sftp(configuration: RuntimeConfiguration) -> None:
    """Verify terminal folders and absence of CSV for rejected batches."""

    with connect_sftp(configuration, configuration.operator) as sftp:
        for batch_id in EXPECTED_SUCCESS_BATCHES:
            if not exists(sftp, f"/raw/archive/{batch_id}"):
                raise AssertionError("Type 02 raw success was not archived")
            if not exists(sftp, f"/csv/archive/{batch_id}"):
                raise AssertionError("Type 02 CSV success was not archived")
        for batch_id in EXPECTED_QUARANTINE_BATCHES:
            if not exists(sftp, f"/raw/quarantine/{batch_id}"):
                raise AssertionError(
                    "Type 02 rejected raw batch was not quarantined"
                )
            if any(
                exists(sftp, f"/csv/{zone}/{batch_id}")
                for zone in ("outgoing", "processing", "archive")
            ):
                raise AssertionError(
                    "Type 02 rejected raw batch produced sanitized state"
                )


def verify_duplicate_refusal(
    configuration: RuntimeConfiguration,
    output_root: Path,
) -> None:
    """Prove immutable publication rejects an already terminal batch."""

    bundle = output_root / "B202607230000101"
    try:
        publish_bundle(bundle, configuration=configuration)
    except RawPublicationError:
        return
    raise AssertionError("Type 02 duplicate publication was accepted")


def verify_postgres(configuration: RuntimeConfiguration) -> None:
    """Verify controls, business isolation, reconciliation, and privacy."""

    with psycopg.connect(configuration.postgres_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT batch_id, status
                  FROM control.batches
                 WHERE file_type = '02'
                """
            )
            expected = {
                (batch_id, "succeeded")
                for batch_id in EXPECTED_SUCCESS_BATCHES
            }
            expected.update(
                (batch_id, "quarantined")
                for batch_id in EXPECTED_QUARANTINE_BATCHES
            )
            if set(cursor.fetchall()) != expected:
                raise AssertionError(
                    "Type 02 control-plane terminal states are incomplete"
                )

            cursor.execute(
                """
                SELECT reject.batch_id, reject.code
                  FROM control.rejects AS reject
                  JOIN control.batches AS batch
                    ON batch.batch_id = reject.batch_id
                 WHERE batch.file_type = '02'
                """
            )
            if set(cursor.fetchall()) != EXPECTED_REJECTIONS:
                raise AssertionError(
                    "Type 02 rejection history is incomplete"
                )

            cursor.execute(
                """
                SELECT batch_id, status
                  FROM reporting.instant_payment_reconciliation
                """
            )
            if set(cursor.fetchall()) != {
                (batch_id, "MATCHED")
                for batch_id in EXPECTED_SUCCESS_BATCHES
            }:
                raise AssertionError(
                    "Type 02 reconciliation is incomplete"
                )

            cursor.execute(
                r"""
                SELECT
                    count(*) FILTER (
                        WHERE payer_document_token
                            !~ '^doc_[0-9a-f]{24}$'
                           OR payee_document_token
                            !~ '^doc_[0-9a-f]{24}$'
                    ),
                    count(*) FILTER (
                        WHERE payer_document_masked
                            !~ '^(\*{7}|\*{10})[0-9]{4}$'
                           OR payee_document_masked
                            !~ '^(\*{7}|\*{10})[0-9]{4}$'
                    )
                  FROM legacy.instant_payment_event
                """
            )
            if cursor.fetchone() != (0, 0):
                raise AssertionError(
                    "Type 02 business table contains unsafe documents"
                )

            cursor.execute(
                """
                SELECT count(*)
                  FROM legacy.instant_payment_event
                 WHERE batch_id = ANY(%s)
                """,
                (list(EXPECTED_QUARANTINE_BATCHES),),
            )
            if cursor.fetchone()[0] != 0:
                raise AssertionError(
                    "Type 02 rejected batch mutated business state"
                )

            cursor.execute(
                """
                SELECT
                    has_table_privilege(
                        current_user,
                        'legacy.instant_payment_event',
                        'INSERT,UPDATE,DELETE'
                    ),
                    has_table_privilege(
                        current_user,
                        'reporting.instant_payment_reconciliation',
                        'INSERT,UPDATE,DELETE'
                    )
                """
            )
            if cursor.fetchone() != (False, False):
                raise AssertionError(
                    "Type 02 loader can bypass governed write functions"
                )


def write_suite_evidence(
    output_root: Path,
    evidence_root: Path,
) -> None:
    """Record that the source injected the defect and peers continued."""

    df_batch = "B202607230000105"
    receipt = json.loads(
        (
            output_root / df_batch / "generation-receipt.json"
        ).read_text(encoding="utf-8")
    )
    publication = json.loads(
        (
            evidence_root / df_batch / "raw-publication.json"
        ).read_text(encoding="utf-8")
    )
    continued = ("B202402290000102", "B202607230000104")
    for batch_id in continued:
        final = json.loads(
            (
                evidence_root / batch_id / "final-status.json"
            ).read_text(encoding="utf-8")
        )
        if final.get("status") != "succeeded":
            raise AssertionError(
                "A Type 02 batch following the source defect did not succeed"
            )
    if (
        receipt["generator"]["name"] != "northwind-pay-datagen"
        or receipt["fault"]["injected"] is not True
        or receipt["fault"]["code"] != "SOURCE_CONTROL_NET_MISMATCH"
        or receipt["artifacts"]["data_sha256"] != publication["sha256"]
    ):
        raise AssertionError(
            "Type 02 source-system ownership proof is inconsistent"
        )

    with EvidenceWriter(evidence_root, "type02-suite") as writer:
        writer.write_json(
            "source-isolation.json",
            {
                "df_batch_id": df_batch,
                "file_type": "02",
                "source_system_role": {
                    "actual": "system_of_record",
                    "basis": (
                        "DataGen injected the named fault before SFTP; "
                        "the publication hash matches its generated artifact"
                    ),
                    "status": "verified",
                },
                "unrelated_batches_continue": {
                    "basis": "two Type 02 scenarios executed after the defect",
                    "status": "verified",
                    "succeeded_batch_ids": list(continued),
                },
            },
        )
        writer.commit()


def verify_evidence(
    output_root: Path,
    evidence_root: Path,
) -> None:
    """Verify completeness, full controls, and absence of restricted text."""

    restricted: set[bytes] = set()
    for raw_path in output_root.rglob("*.txt"):
        raw = raw_path.read_bytes()
        restricted.update(
            match.group(0)
            for match in re.finditer(
                rb"(?<=\|)(?:[0-9]{11}|[0-9]{14})(?=\|)",
                raw,
            )
        )
    restricted.update(
        value.encode("utf-8")
        for value in (
            "Invoice 1001",
            "Invoice 1005",
            "Return|beneficiary",
            "Unescaped|delimiter",
            "Café, invoice",
        )
    )

    base_files = {
        "source-manifest.json",
        "generation-receipt.json",
        "raw-file.sha256",
        "raw-publication.json",
        "raw-intake.json",
        "java-run.json",
        "postgres-load.json",
        "procedure-run.json",
        "reconciliation.json",
        "expected-diff.json",
        "postgres-diagnostic.json",
        "final-status.json",
    }
    for scenario, (batch_id, status) in EXPECTED.items():
        packet = evidence_root / batch_id
        observed_files = {path.name for path in packet.iterdir()}
        expected_files = set(base_files)
        if status == "succeeded":
            expected_files.add("sanitized-csv.sha256")
        if observed_files != expected_files:
            raise AssertionError(
                f"Type 02 evidence packet is incomplete: {scenario}"
            )
        for path in packet.iterdir():
            content = path.read_bytes()
            if any(secret in content for secret in restricted):
                raise AssertionError(
                    "Restricted Type 02 source text leaked into evidence"
                )

        publication = json.loads(
            (packet / "raw-publication.json").read_text(encoding="utf-8")
        )
        final = json.loads(
            (packet / "final-status.json").read_text(encoding="utf-8")
        )
        if (
            publication.get("file_type") != "02"
            or final.get("file_type") != "02"
            or publication.get("source_controls")
            != final.get("source_controls")
        ):
            raise AssertionError(
                "Type 02 evidence lost file type or source controls"
            )

    df_packet = evidence_root / "B202607230000105"
    java = json.loads(
        (df_packet / "java-run.json").read_text(encoding="utf-8")
    )
    diagnostic = json.loads(
        (
            df_packet / "postgres-diagnostic.json"
        ).read_text(encoding="utf-8")
    )
    if (
        java.get("declared_net_amount") != "173.44"
        or java.get("computed_net_amount") != "173.45"
        or java.get("declared_event_count") != 2
        or java.get("computed_event_count") != 2
        or diagnostic.get("declared_credit_amount") != "200.00"
        or diagnostic.get("computed_debit_amount") != "26.55"
        or diagnostic.get("business_state_committed") is not False
    ):
        raise AssertionError(
            "Type 02 Dark Factory aggregate evidence is incomplete"
        )

    source_isolation = json.loads(
        (
            evidence_root
            / "type02-suite"
            / "source-isolation.json"
        ).read_text(encoding="utf-8")
    )
    if (
        source_isolation["source_system_role"]["actual"]
        != "system_of_record"
        or source_isolation["source_system_role"]["status"] != "verified"
        or source_isolation["unrelated_batches_continue"]["status"]
        != "verified"
        or set(
            source_isolation["unrelated_batches_continue"][
                "succeeded_batch_ids"
            ]
        )
        != {"B202402290000102", "B202607230000104"}
    ):
        raise AssertionError(
            "Type 02 suite-level source isolation proof is incomplete"
        )


def main() -> int:
    """Run five outcomes plus interruption recovery and exact replay."""

    configuration = RuntimeConfiguration.load()
    output_root = ROOT / ".runtime" / "e2e-type02-generated"
    evidence_root = ROOT / ".runtime" / "e2e-type02-evidence"
    if output_root.exists() or evidence_root.exists():
        print(
            "Type 02 end-to-end workspace exists; run guarded clean-runtime",
            file=sys.stderr,
        )
        return 2

    for scenario in SCENARIOS:
        if scenario == "valid-minimal":
            interrupt_scenario(
                scenario,
                boundary="database_commit",
                output_root=output_root,
                evidence_root=evidence_root,
            )
        elif scenario == "valid-boundary":
            interrupt_scenario(
                scenario,
                boundary="raw_archive",
                output_root=output_root,
                evidence_root=evidence_root,
            )
        run_scenario(
            scenario,
            output_root=output_root,
            evidence_root=evidence_root,
        )

    run_scenario(
        "valid-minimal",
        output_root=output_root,
        evidence_root=evidence_root,
    )
    write_suite_evidence(output_root, evidence_root)
    verify_sftp(configuration)
    verify_duplicate_refusal(configuration, output_root)
    verify_postgres(configuration)
    verify_evidence(output_root, evidence_root)
    print("Type 02 end-to-end suite passed: 3 succeeded, 2 quarantined")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
