from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
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
from raw_intake import RawIntakeError, claim_batch  # noqa: E402
from raw_publisher import RawPublicationError, publish_bundle  # noqa: E402
from sftp_client import connect_sftp, exists  # noqa: E402


SCENARIOS = (
    "malformed",
    "valid-minimal",
    "DF-SOURCE-001",
    "valid-boundary",
    "negative-overpunch",
)
EXPECTED = {
    "malformed": ("B202607230000003", "quarantined"),
    "valid-minimal": ("B202607230000001", "succeeded"),
    "DF-SOURCE-001": ("B202607230000004", "quarantined"),
    "valid-boundary": ("B202402290000001", "succeeded"),
    "negative-overpunch": ("B202607230000002", "succeeded"),
}
EXPECTED_SUCCESS_BATCHES = {
    "B202607230000001",
    "B202402290000001",
    "B202607230000002",
}
EXPECTED_QUARANTINE_BATCHES = {
    "B202607230000003",
    "B202607230000004",
}
EXPECTED_REJECTIONS = {
    ("B202607230000003", "INVALID_OVERPUNCH"),
    ("B202607230000004", "SOURCE_CONTROL_TOTAL_MISMATCH"),
}


def runner_command(
    scenario: str,
    *,
    output_root: Path,
    evidence_root: Path,
) -> list[str]:
    """Return the same public typed command used by every file type."""

    return [
        sys.executable,
        str(ROOT / "legacy" / "runner" / "run_type.py"),
        "--type",
        "01",
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
        raise AssertionError(
            f"scenario failed without raw output disclosure: {scenario}"
        )
    output = json.loads(result.stdout.splitlines()[-1])
    expected_batch, expected_status = EXPECTED[scenario]
    if (
        output["batch_id"] != expected_batch
        or output["status"] != expected_status
    ):
        raise AssertionError(f"unexpected terminal state: {scenario}")


def interrupt_scenario(
    scenario: str,
    *,
    boundary: str,
    output_root: Path,
    evidence_root: Path,
) -> None:
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
            f"fault injection did not stop cleanly: {scenario}/{boundary}"
        )


def verify_sftp(configuration: RuntimeConfiguration) -> None:
    with connect_sftp(configuration, configuration.operator) as sftp:
        for batch_id in EXPECTED_SUCCESS_BATCHES:
            if not exists(sftp, f"/raw/archive/{batch_id}"):
                raise AssertionError("successful raw batch was not archived")
            if not exists(sftp, f"/csv/archive/{batch_id}"):
                raise AssertionError("successful CSV batch was not archived")
        for batch_id in EXPECTED_QUARANTINE_BATCHES:
            if not exists(sftp, f"/raw/quarantine/{batch_id}"):
                raise AssertionError("rejected raw batch was not quarantined")
            if exists(sftp, f"/csv/outgoing/{batch_id}"):
                raise AssertionError("rejected raw batch produced CSV")


def verify_permissions_and_readiness(
    configuration: RuntimeConfiguration,
) -> None:
    unauthorized = "/raw/processing/B209901010000001"
    with connect_sftp(configuration, configuration.raw_publisher) as sftp:
        try:
            sftp.mkdir(unauthorized)
        except OSError:
            pass
        else:
            sftp.rmdir(unauthorized)
            raise AssertionError("raw publisher crossed its role boundary")

    role_boundaries = (
        (
            configuration.processor,
            "/csv/processing/B209901010000003",
            "processor crossed into the loader lane",
        ),
        (
            configuration.loader,
            "/raw/processing/B209901010000004",
            "loader crossed into the raw processor lane",
        ),
        (
            configuration.processor,
            "/csv/archive/B202607230000001/forbidden",
            "processor could mutate the CSV archive",
        ),
        (
            configuration.loader,
            "/raw/archive/B202607230000001/forbidden",
            "loader could mutate the raw archive",
        ),
    )
    for role, path, message in role_boundaries:
        with connect_sftp(configuration, role) as sftp:
            try:
                sftp.mkdir(path)
            except OSError:
                continue
            sftp.rmdir(path)
            raise AssertionError(message)

    partial_batch = "B209901010000002"
    partial_directory = f"/raw/incoming/{partial_batch}"
    with tempfile.TemporaryDirectory() as temporary:
        harmless = Path(temporary) / "partial.part"
        harmless.write_bytes(b"not-ready\n")
        with connect_sftp(configuration, configuration.raw_publisher) as sftp:
            sftp.mkdir(partial_directory)
            sftp.put(
                str(harmless),
                f"{partial_directory}/source.dat.part",
            )
        try:
            claim_batch(partial_batch, configuration=configuration)
        except RawIntakeError as exc:
            if exc.code != "BATCH_NOT_READY":
                raise AssertionError("partial batch returned the wrong state") from exc
        else:
            raise AssertionError("partial batch became visible before its manifest")
        with connect_sftp(configuration, configuration.raw_publisher) as sftp:
            sftp.remove(f"{partial_directory}/source.dat.part")
            sftp.rmdir(partial_directory)


def verify_duplicate_refusal(
    configuration: RuntimeConfiguration,
    output_root: Path,
) -> None:
    bundle = output_root / "B202607230000001"
    try:
        publish_bundle(bundle, configuration=configuration)
    except RawPublicationError:
        return
    raise AssertionError("duplicate batch publication was not refused")


def verify_postgres(configuration: RuntimeConfiguration) -> None:
    with psycopg.connect(configuration.postgres_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT batch_id, status
                  FROM control.batches
                 WHERE file_type = '01'
                 ORDER BY batch_id
                """
            )
            observed = set(cursor.fetchall())
            expected = {
                (batch_id, "succeeded")
                for batch_id in EXPECTED_SUCCESS_BATCHES
            }
            expected.update(
                (batch_id, "quarantined")
                for batch_id in EXPECTED_QUARANTINE_BATCHES
            )
            if observed != expected:
                raise AssertionError(
                    "PostgreSQL contains unexpected batch control state"
                )
            cursor.execute(
                """
                SELECT reject.batch_id, reject.code
                  FROM control.rejects AS reject
                  JOIN control.batches AS batch
                    ON batch.batch_id = reject.batch_id
                 WHERE batch.file_type = '01'
                 ORDER BY reject.batch_id
                """
            )
            if set(cursor.fetchall()) != EXPECTED_REJECTIONS:
                raise AssertionError("PostgreSQL rejection history is incomplete")
            cursor.execute(
                """
                SELECT batch_id, status
                  FROM reporting.card_settlement_reconciliation
                 ORDER BY batch_id
                """
            )
            reports = set(cursor.fetchall())
            if reports != {
                (batch_id, "MATCHED")
                for batch_id in EXPECTED_SUCCESS_BATCHES
            }:
                raise AssertionError("PostgreSQL reconciliation is incomplete")
            cursor.execute(
                r"""
                SELECT
                    count(*) FILTER (
                        WHERE card_token !~ '^tok_[0-9a-f]{24}$'
                    ),
                    count(*) FILTER (
                        WHERE cpf_masked !~ '^\*{7}[0-9]{4}$'
                    )
                  FROM legacy.card_settlement
                """
            )
            if cursor.fetchone() != (0, 0):
                raise AssertionError("PostgreSQL contains unsafe privacy fields")
            cursor.execute(
                """
                SELECT count(*)
                  FROM legacy.card_settlement
                 WHERE batch_id = ANY(%s)
                """,
                (list(EXPECTED_QUARANTINE_BATCHES),),
            )
            if cursor.fetchone()[0] != 0:
                raise AssertionError("rejected batch mutated business state")
            cursor.execute(
                """
                SELECT
                    has_table_privilege(
                        current_user,
                        'legacy.card_settlement',
                        'INSERT,UPDATE,DELETE'
                    ),
                    has_table_privilege(
                        current_user,
                        'reporting.card_settlement_reconciliation',
                        'INSERT,UPDATE,DELETE'
                    ),
                    has_table_privilege(
                        current_user,
                        'control.files',
                        'UPDATE,DELETE'
                    ),
                    has_table_privilege(
                        current_user,
                        'control.procedure_runs',
                        'INSERT,UPDATE,DELETE'
                    )
                """
            )
            if cursor.fetchone() != (False, False, False, False):
                raise AssertionError(
                    "PostgreSQL loader can bypass governed write functions"
                )
            cursor.execute(
                """
                SELECT rolcanlogin, rolsuper
                  FROM pg_roles
                 WHERE rolname = 'northwind_legacy_owner'
                """
            )
            if cursor.fetchone() != (False, False):
                raise AssertionError("secured function owner is not NOLOGIN")
            cursor.execute(
                """
                SELECT count(*)
                  FROM pg_proc AS procedure
                  JOIN pg_namespace AS namespace
                    ON namespace.oid = procedure.pronamespace
                 WHERE namespace.nspname IN (
                           'control', 'legacy', 'reporting'
                       )
                   AND procedure.proname IN (
                           'register_batch',
                           'register_file',
                           'register_load',
                           'register_reject',
                           'mark_batch_committed',
                           'mark_batch_succeeded',
                           'apply_card_settlement_batch',
                           'refresh_card_settlement_reconciliation'
                       )
                   AND procedure.prosecdef
                   AND 'search_path=pg_catalog'
                       = ANY(procedure.proconfig)
                   AND NOT EXISTS (
                           SELECT 1
                             FROM aclexplode(
                                 coalesce(
                                     procedure.proacl,
                                     acldefault('f', procedure.proowner)
                                 )
                             ) AS grant_entry
                            WHERE grant_entry.grantee = 0
                              AND grant_entry.privilege_type = 'EXECUTE'
                       )
                """
            )
            if cursor.fetchone()[0] != 8:
                raise AssertionError(
                    "governed PostgreSQL functions are not safely defined"
                )

    forbidden_mutations = (
        "UPDATE legacy.card_settlement SET merchant_id = merchant_id",
        (
            "UPDATE reporting.card_settlement_reconciliation "
            "SET status = status"
        ),
        "UPDATE control.files SET sha256 = sha256",
        (
            "INSERT INTO control.procedure_runs "
            "(batch_id, sequence_number, procedure_name, status) "
            "VALUES ('B202607230000001', 99, 'forbidden', 'succeeded')"
        ),
    )
    for statement in forbidden_mutations:
        with psycopg.connect(configuration.postgres_dsn) as connection:
            try:
                connection.execute(statement)
            except psycopg.errors.InsufficientPrivilege:
                connection.rollback()
            else:
                connection.rollback()
                raise AssertionError(
                    "PostgreSQL loader performed a forbidden direct mutation"
                )


def verify_evidence(
    output_root: Path,
    evidence_root: Path,
) -> None:
    sensitive: list[bytes] = []
    for raw_path in output_root.rglob("*.dat"):
        for record in raw_path.read_bytes().splitlines():
            if record[:1] == b"D" and len(record) >= 60:
                sensitive.extend((record[33:49], record[49:60]))

    expected_files = {
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
        batch_evidence = evidence_root / batch_id
        files = {path.name for path in batch_evidence.iterdir()}
        if status == "succeeded":
            files.remove("sanitized-csv.sha256")
        if files != expected_files:
            raise AssertionError(f"evidence packet is incomplete: {scenario}")
        for path in batch_evidence.iterdir():
            content = path.read_bytes()
            if any(identifier in content for identifier in sensitive):
                raise AssertionError("restricted identifier leaked into evidence")
            if re.search(rb"\b[3456][0-9]{15}\b", content):
                raise AssertionError("possible clear PAN leaked into evidence")

    df_evidence = evidence_root / "B202607230000004"
    java = json.loads((df_evidence / "java-run.json").read_text())
    diagnostic = json.loads(
        (df_evidence / "postgres-diagnostic.json").read_text()
    )
    if (
        java["declared_net_amount"] != "173.44"
        or java["computed_net_amount"] != "173.45"
        or java["declared_detail_count"] != 2
        or java["computed_detail_count"] != 2
        or diagnostic["computed_net_amount"] != "173.45"
        or diagnostic["computed_detail_count"] != 2
        or diagnostic["business_state_committed"] is not False
    ):
        raise AssertionError("Dark Factory source-isolation evidence is incomplete")

    suite = json.loads(
        (
            evidence_root
            / "type01-suite"
            / "source-isolation.json"
        ).read_text(encoding="utf-8")
    )
    if (
        suite["source_system_role"]["actual"] != "system_of_record"
        or suite["source_system_role"]["status"] != "verified"
        or suite["unrelated_batches_continue"]["status"] != "verified"
        or set(suite["unrelated_batches_continue"]["succeeded_batch_ids"])
        != {"B202402290000001", "B202607230000002"}
    ):
        raise AssertionError("suite-level Dark Factory proof is incomplete")


def write_suite_evidence(
    output_root: Path,
    evidence_root: Path,
) -> None:
    df_batch = "B202607230000004"
    receipt = json.loads(
        (
            output_root
            / df_batch
            / "generation-receipt.json"
        ).read_text(encoding="utf-8")
    )
    publication = json.loads(
        (
            evidence_root
            / df_batch
            / "raw-publication.json"
        ).read_text(encoding="utf-8")
    )
    continued = ("B202402290000001", "B202607230000002")
    for batch_id in continued:
        final = json.loads(
            (
                evidence_root
                / batch_id
                / "final-status.json"
            ).read_text(encoding="utf-8")
        )
        if final.get("status") != "succeeded":
            raise AssertionError("post-DF control batch did not succeed")
    if (
        receipt["generator"]["name"] != "northwind-pay-datagen"
        or receipt["fault"]["injected"] is not True
        or receipt["fault"]["code"] != "SOURCE_CONTROL_TOTAL_MISMATCH"
        or receipt["artifacts"]["data_sha256"] != publication["sha256"]
    ):
        raise AssertionError("source ownership evidence is inconsistent")

    with EvidenceWriter(evidence_root, "type01-suite") as writer:
        writer.write_json(
            "source-isolation.json",
            {
                "df_batch_id": df_batch,
                "source_system_role": {
                    "actual": "system_of_record",
                    "basis": (
                        "DataGen injected the named fault before SFTP; "
                        "the publication hash matches its generated artifact"
                    ),
                    "status": "verified",
                },
                "unrelated_batches_continue": {
                    "basis": "two scenarios executed after DF-SOURCE-001",
                    "status": "verified",
                    "succeeded_batch_ids": list(continued),
                },
            },
        )
        writer.commit()


def main() -> int:
    configuration = RuntimeConfiguration.load()
    output_root = ROOT / ".runtime" / "e2e-generated"
    evidence_root = ROOT / ".runtime" / "e2e-evidence"
    if output_root.exists() or evidence_root.exists():
        print(
            "end-to-end workspace already exists; run guarded clean-runtime",
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
    verify_permissions_and_readiness(configuration)
    verify_sftp(configuration)
    verify_duplicate_refusal(configuration, output_root)
    verify_postgres(configuration)
    verify_evidence(output_root, evidence_root)
    print("Type 01 end-to-end suite passed: 3 succeeded, 2 quarantined")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
