"""Live acceptance suite for the automatic manifest-ready legacy worker.

The suite is intentionally destructive only to reserved artifacts that it
creates itself. It refuses any non-clean local workspace, SFTP lifecycle, or
PostgreSQL business state. Canonical data always enters through the public
DataGen and publisher CLIs, and every remote assertion uses verified SFTP.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[2]
HARNESS_ROOT = Path(__file__).resolve().parent
for module_directory in (
    ROOT / "legacy" / "runner",
    ROOT / "legacy" / "publisher",
    ROOT / "legacy" / "intake",
    ROOT / "legacy" / "postgres",
    ROOT / "validation" / "oracle",
    HARNESS_ROOT,
):
    sys.path.insert(0, str(module_directory))

import run_type02_suite as type02_acceptance  # noqa: E402
from config import RuntimeConfiguration, SftpRole  # noqa: E402
from lifecycle import (  # noqa: E402
    read_sanitized_observation,
)
from migrate import discover_migrations  # noqa: E402
from raw_intake import ClaimedRaw, claim_batch  # noqa: E402
from raw_publisher import PublishedRaw, validate_bundle  # noqa: E402
from recovery_journal import (  # noqa: E402
    load_terminal_recovery,
    recovery_journal_path,
)
from sftp_client import (  # noqa: E402
    connect_sftp,
    exists,
    mkdir_exact,
    upload_manifest_last,
)
from typed_acceptance import (  # noqa: E402
    BASE_EVIDENCE_FILES,
    TYPE_SPECS,
    _directory_snapshot,
    _walk_mapping_keys,
    load_expectations,
    suite_for_type,
    verify_postgres as verify_typed_postgres,
)
from workflow_registry import workflow_for_type  # noqa: E402


TYPE_SCENARIOS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "01": (
            "valid-minimal",
            "valid-boundary",
            "negative-overpunch",
            "malformed",
            "DF-SOURCE-001",
        ),
        "02": (
            "valid-minimal",
            "valid-boundary",
            "escaped-content",
            "malformed",
            "DF-SOURCE-002",
        ),
        "03": (
            "valid-minimal",
            "valid-boundary",
            "multi-lot",
            "malformed",
            "DF-SOURCE-003",
        ),
        "04": (
            "valid-minimal",
            "valid-boundary",
            "all-returned-zero-net",
            "malformed",
            "DF-SOURCE-004",
        ),
        "05": (
            "valid-minimal",
            "valid-boundary",
            "rounding-half-up",
            "malformed",
            "DF-SOURCE-005",
        ),
    }
)
SUCCESS_SCENARIOS = frozenset(
    {
        "valid-minimal",
        "valid-boundary",
        "negative-overpunch",
        "escaped-content",
        "multi-lot",
        "all-returned-zero-net",
        "rounding-half-up",
    }
)
RAW_ZONES = ("incoming", "processing", "quarantine", "archive")
CSV_ZONES = ("outgoing", "processing", "quarantine", "archive")
BATCH_ID_PATTERN = re.compile(r"B[0-9]{15}\Z")
SAFE_CODE_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")

OUTPUT_ROOT = ROOT / ".runtime" / "e2e-worker-generated"
EVIDENCE_ROOT = ROOT / ".runtime" / "e2e-worker-evidence"
RESERVED_ROOT = ROOT / ".runtime" / "e2e-worker-reserved"
WORKER_STATUS = ROOT / ".runtime" / "worker-status.json"
WORKER_CACHE = ROOT / ".runtime" / "intake-cache"
WORKER_LOCK = ROOT / ".runtime" / "worker.lock"
TERMINAL_RECOVERY_ROOT = ROOT / ".runtime" / "terminal-recovery"

RECOVERY_TYPE = "01"
RECOVERY_SCENARIO = "negative-overpunch"
BAD_CHECKSUM_BATCH = "B202607230009981"
INCOMPLETE_BATCH = "B202607230009982"
DUPLICATE_ZONE_BATCH = "B202607230009983"
CACHE_CONFLICT_BATCH = "B202607230009984"
QUARANTINE_UNCERTAIN_BATCH = "B202607230009985"
ORACLE_MISMATCH_BATCH = "B202607230009986"
DATABASE_COMMIT_RESTART_BATCH = "B202607230000404"
RAW_ARCHIVE_RESTART_BATCH = "B202607230000001"
RAW_QUARANTINE_RESTART_BATCH = "B202607230000003"
RESTART_CANONICAL_BATCHES = frozenset(
    {
        DATABASE_COMMIT_RESTART_BATCH,
        RAW_ARCHIVE_RESTART_BATCH,
        RAW_QUARANTINE_RESTART_BATCH,
    }
)
RESERVED_BATCHES = frozenset(
    {
        BAD_CHECKSUM_BATCH,
        INCOMPLETE_BATCH,
        DUPLICATE_ZONE_BATCH,
        CACHE_CONFLICT_BATCH,
        QUARANTINE_UNCERTAIN_BATCH,
        ORACLE_MISMATCH_BATCH,
    }
)
TRANSPORT_ONLY_RESERVED_BATCHES = RESERVED_BATCHES - {
    ORACLE_MISMATCH_BATCH
}
RESERVED_CLEANUP_TARGETS = frozenset(
    {
        (DUPLICATE_ZONE_BATCH, "incoming"),
        (DUPLICATE_ZONE_BATCH, "processing"),
        (CACHE_CONFLICT_BATCH, "processing"),
        (QUARANTINE_UNCERTAIN_BATCH, "incoming"),
        (QUARANTINE_UNCERTAIN_BATCH, "quarantine"),
    }
)
INCOMPLETE_PART_NAME = "reserved-source.dat.part"
WORKER_TEST_HOOKS = frozenset(
    {
        "NWP_TEST_FORCE_ORACLE_MISMATCH_BATCH_ID",
        "NWP_TEST_INTERRUPT_AFTER",
        "NWP_TEST_INTERRUPT_BATCH_ID",
    }
)
WORKER_INTERRUPT_BOUNDARIES = frozenset(
    {"database_commit", "raw_archive", "raw_quarantine"}
)

TYPE_RELATIONS: Mapping[str, tuple[str, str, str]] = MappingProxyType(
    {
        "01": (
            "staging.card_settlement",
            "legacy.card_settlement",
            "reporting.card_settlement_reconciliation",
        ),
        "02": (
            "staging.instant_payment_event",
            "legacy.instant_payment_event",
            "reporting.instant_payment_reconciliation",
        ),
        "03": (
            "staging.payment_slip_settlement",
            "legacy.payment_slip_settlement",
            "reporting.payment_slip_settlement_reconciliation",
        ),
        "04": (
            "staging.ted_transfer_movement",
            "legacy.ted_transfer_movement",
            "reporting.ted_transfer_reconciliation",
        ),
        "05": (
            "staging.merchant_fee_assessment",
            "legacy.merchant_fee_assessment",
            "reporting.merchant_fee_reconciliation",
        ),
    }
)
CONTROL_RELATIONS = (
    "control.batches",
    "control.files",
    "control.loads",
    "control.rejects",
    "control.procedure_runs",
)
STATE_RELATIONS = CONTROL_RELATIONS + tuple(
    relation
    for relations in TYPE_RELATIONS.values()
    for relation in relations
)

WORKER_BASE_EVIDENCE_FILES = (
    BASE_EVIDENCE_FILES - {"generation-receipt.json"}
)
WORKER_SUCCESS_EVIDENCE_FILES = (
    WORKER_BASE_EVIDENCE_FILES | {"sanitized-csv.sha256"}
)
FORBIDDEN_EVIDENCE_KEYS = frozenset(
    {
        "account_number",
        "bank_account",
        "beneficiary_account",
        "beneficiary_name",
        "beneficiary_tax_id",
        "card_number",
        "cpf",
        "merchant_tax_id",
        "pan",
        "payee_document",
        "payer_account",
        "payer_document",
        "payer_tax_id",
        "raw_record",
        "raw_row",
        "raw_value",
        "return_reason_text",
    }
) | frozenset(
    key
    for spec in TYPE_SPECS.values()
    for key in spec.forbidden_evidence_keys
)


class WorkerAcceptanceFailure(AssertionError):
    """A live worker boundary or invariant did not match its contract."""


@dataclass(frozen=True, slots=True)
class WorkerCase:
    """One canonical DataGen scenario expected in the worker cycle."""

    type_number: str
    scenario: str
    batch_id: str
    expected_status: str

    def __post_init__(self) -> None:
        if self.type_number not in TYPE_SCENARIOS:
            raise ValueError("Worker case file type is unsupported")
        if self.scenario not in TYPE_SCENARIOS[self.type_number]:
            raise ValueError("Worker case scenario is not canonical")
        if BATCH_ID_PATTERN.fullmatch(self.batch_id) is None:
            raise ValueError("Worker case batch ID is invalid")
        if self.expected_status not in {"succeeded", "quarantined"}:
            raise ValueError("Worker case status is unsupported")


@dataclass(frozen=True, slots=True)
class GeneratedCatalog:
    """Validated local identities and rejection codes for all cases."""

    raws: Mapping[str, PublishedRaw]
    rejection_codes: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class RestartProbe:
    """One process-interruption seam and its durable recovery contract."""

    name: str
    boundary: str
    batch_id: str
    expected_status: str
    expected_code: str
    intermediate_raw_zone: str
    intermediate_csv_zone: str | None
    intermediate_database_status: str | None
    recovery_source_zone: str
    journal_route: str | None
    force_oracle_mismatch: bool = False

    def __post_init__(self) -> None:
        if (
            self.boundary not in WORKER_INTERRUPT_BOUNDARIES
            or BATCH_ID_PATTERN.fullmatch(self.batch_id) is None
            or self.expected_status
            not in {"succeeded", "quarantined", "oracle_mismatch"}
            or SAFE_CODE_PATTERN.fullmatch(self.expected_code) is None
            or self.intermediate_raw_zone
            not in {"processing", "archive", "quarantine"}
            or self.intermediate_csv_zone
            not in {None, "processing", "quarantine"}
            or self.intermediate_database_status
            not in {None, "database_committed_pending_archive"}
            or self.recovery_source_zone not in {"processing", "cache"}
            or self.journal_route
            not in {None, "rejection", "oracle_mismatch"}
        ):
            raise ValueError("Restart probe contract is unsafe")


def canonical_cases() -> tuple[WorkerCase, ...]:
    """Resolve the exact 25-case catalog from registered workflow adapters."""

    cases: list[WorkerCase] = []
    for type_number, scenarios in TYPE_SCENARIOS.items():
        registered = workflow_for_type(type_number).scenario_batch_ids
        if set(registered) != set(scenarios):
            raise WorkerAcceptanceFailure(
                f"Type {type_number} worker catalog differs from DataGen"
            )
        for scenario in scenarios:
            cases.append(
                WorkerCase(
                    type_number=type_number,
                    scenario=scenario,
                    batch_id=registered[scenario],
                    expected_status=(
                        "succeeded"
                        if scenario in SUCCESS_SCENARIOS
                        else "quarantined"
                    ),
                )
            )

    batch_ids = {case.batch_id for case in cases}
    statuses = [case.expected_status for case in cases]
    if (
        len(cases) != 25
        or len(batch_ids) != 25
        or batch_ids & RESERVED_BATCHES
        or statuses.count("succeeded") != 15
        or statuses.count("quarantined") != 10
    ):
        raise WorkerAcceptanceFailure(
            "Worker catalog must contain 25 unique canonical outcomes"
        )
    return tuple(cases)


def datagen_command(case: WorkerCase) -> list[str]:
    """Build the public DataGen command for one canonical case."""

    return [
        sys.executable,
        str(ROOT / "gen" / "src" / "cli.py"),
        "--type",
        case.type_number,
        "--scenario",
        case.scenario,
        "--output",
        str(OUTPUT_ROOT),
        "--contracts-root",
        str(ROOT / "contracts" / "types"),
    ]


def publisher_command(bundle: Path) -> list[str]:
    """Build the public manifest-last publisher command."""

    return [
        sys.executable,
        str(ROOT / "legacy" / "runner" / "publish_raw_cli.py"),
        str(bundle),
    ]


def worker_command(
    *,
    once: bool,
    max_batches: int = 100,
) -> list[str]:
    """Build the public automatic-worker command."""

    if not 1 <= max_batches <= 100:
        raise WorkerAcceptanceFailure(
            "Worker command batch bound is unsafe"
        )
    command = [
        sys.executable,
        str(ROOT / "legacy" / "runner" / "worker.py"),
        "--poll-interval",
        "0.1",
        "--max-batches",
        str(max_batches),
        "--evidence-root",
        str(EVIDENCE_ROOT),
    ]
    if once:
        command.append("--once")
    return command


def _read_json_object(path: Path) -> dict[str, object]:
    """Read one bounded local JSON object without repairing its shape."""

    try:
        if path.lstat().st_size > 1_048_576:
            raise ValueError("JSON artifact is oversized")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise WorkerAcceptanceFailure(
            f"Required JSON artifact is not readable: {path.name}"
        ) from exc
    if not isinstance(value, dict):
        raise WorkerAcceptanceFailure(
            f"Required JSON artifact is not an object: {path.name}"
        )
    return value


def _run_checked(
    command: Sequence[str],
    *,
    label: str,
    timeout: float,
    environment: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one public command while keeping captured raw output private."""

    try:
        result = subprocess.run(
            list(command),
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
            env=None if environment is None else dict(environment),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkerAcceptanceFailure(
            f"Public command did not complete: {label}"
        ) from exc
    if result.returncode != 0:
        raise WorkerAcceptanceFailure(
            f"Public command returned failure: {label}"
        )
    return result


def _last_json_line(
    result: subprocess.CompletedProcess[str],
    *,
    label: str,
) -> dict[str, object]:
    """Parse the final non-empty stdout line as one privacy-safe object."""

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    try:
        value = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise WorkerAcceptanceFailure(
            f"Public command emitted no JSON result: {label}"
        ) from exc
    if not isinstance(value, dict):
        raise WorkerAcceptanceFailure(
            f"Public command JSON has an invalid shape: {label}"
        )
    return value


def _relation(identifier: str) -> sql.Composed:
    """Return one safely quoted schema-qualified relation."""

    schema_name, table_name = identifier.split(".", maxsplit=1)
    return sql.SQL("{}.{}").format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name),
    )


def _sftp_zone_snapshot(
    configuration: RuntimeConfiguration,
) -> dict[str, tuple[str, ...]]:
    """Return exact sorted batch-directory names from every lifecycle zone."""

    snapshot: dict[str, tuple[str, ...]] = {}
    with connect_sftp(configuration, configuration.operator) as sftp:
        for boundary, zones in (("raw", RAW_ZONES), ("csv", CSV_ZONES)):
            for zone in zones:
                remote = f"/{boundary}/{zone}"
                snapshot[f"{boundary}/{zone}"] = tuple(
                    sorted(sftp.listdir(remote))
                )
    return snapshot


def assert_clean_start(configuration: RuntimeConfiguration) -> None:
    """Refuse any pre-existing local, SFTP, or PostgreSQL acceptance state."""

    runtime = ROOT / ".runtime"
    if not runtime.is_dir() or not configuration.known_hosts.is_file():
        raise WorkerAcceptanceFailure(
            "Verified runtime is unavailable; deploy before acceptance"
        )
    unexpected_runtime = {
        path.name for path in runtime.iterdir()
    } - {configuration.known_hosts.name}
    if unexpected_runtime:
        raise WorkerAcceptanceFailure(
            "Local runtime is not clean; guarded cleanup is required"
        )
    if (ROOT / "evidence").exists():
        raise WorkerAcceptanceFailure(
            "Legacy evidence workspace is not clean"
        )

    snapshot = _sftp_zone_snapshot(configuration)
    if any(snapshot.values()):
        raise WorkerAcceptanceFailure(
            "SFTP lifecycle is not clean; refusing acceptance mutation"
        )

    with psycopg.connect(configuration.postgres_dsn) as connection:
        with connection.cursor() as cursor:
            for relation in STATE_RELATIONS:
                cursor.execute(
                    sql.SQL("SELECT count(*) FROM {}").format(
                        _relation(relation)
                    )
                )
                if cursor.fetchone() != (0,):
                    raise WorkerAcceptanceFailure(
                        "PostgreSQL business runtime is not clean"
                    )
    with psycopg.connect(configuration.postgres_admin_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT version, name, sha256
                  FROM control.schema_migrations
                 ORDER BY version
                """
            )
            migrations = discover_migrations(
                ROOT / "legacy" / "postgres"
            )
            expected_ledger = tuple(
                (migration.version, migration.name, migration.sha256)
                for migration in migrations
            )
            if (
                tuple(migration.version for migration in migrations)
                != tuple(f"{version:03d}" for version in range(1, 11))
                or tuple(cursor.fetchall()) != expected_ledger
            ):
                raise WorkerAcceptanceFailure(
                    "PostgreSQL migration ledger is not current"
                )


def generate_catalog(
    cases: Sequence[WorkerCase],
    configuration: RuntimeConfiguration,
) -> GeneratedCatalog:
    """Generate and validate all canonical bundles through public DataGen."""

    raw_by_batch: dict[str, PublishedRaw] = {}
    rejection_codes: dict[str, str] = {}
    for case in cases:
        _run_checked(
            datagen_command(case),
            label=f"DataGen Type {case.type_number}/{case.scenario}",
            timeout=60,
        )
        bundle = OUTPUT_ROOT / case.batch_id
        raw = validate_bundle(bundle, configuration=configuration)
        receipt = _read_json_object(bundle / "generation-receipt.json")
        expected_files = {
            "generation-receipt.json",
            "source-manifest.json",
            raw.filename,
            f"{raw.filename}.sha256",
        }
        observed_files = {path.name for path in bundle.iterdir()}
        contract = receipt.get("contract")
        expected_result = receipt.get("expected_contract_result")
        if (
            observed_files != expected_files
            or raw.batch_id != case.batch_id
            or raw.file_type != case.type_number
            or receipt.get("batch_id") != case.batch_id
            or receipt.get("scenario") != case.scenario
            or not isinstance(contract, Mapping)
            or contract.get("type_number") != case.type_number
            or not isinstance(expected_result, Mapping)
        ):
            raise WorkerAcceptanceFailure(
                f"Generated bundle identity is incomplete: {case.batch_id}"
            )
        fault = receipt.get("fault")
        if case.expected_status == "succeeded":
            if (
                expected_result.get("status") != "ACCEPTED"
                or fault is not None
            ):
                raise WorkerAcceptanceFailure(
                    f"Success receipt is inconsistent: {case.batch_id}"
                )
        else:
            code = fault.get("code") if isinstance(fault, Mapping) else None
            if (
                expected_result.get("status") != "REJECTED"
                or not isinstance(fault, Mapping)
                or fault.get("injected") is not True
                or not isinstance(code, str)
                or SAFE_CODE_PATTERN.fullmatch(code) is None
            ):
                raise WorkerAcceptanceFailure(
                    f"Rejection receipt is inconsistent: {case.batch_id}"
                )
            rejection_codes[case.batch_id] = code
        raw_by_batch[case.batch_id] = raw

    if (
        set(raw_by_batch) != {case.batch_id for case in cases}
        or len(rejection_codes) != 10
    ):
        raise WorkerAcceptanceFailure(
            "Generated worker catalog is incomplete"
        )
    return GeneratedCatalog(
        raws=MappingProxyType(raw_by_batch),
        rejection_codes=MappingProxyType(rejection_codes),
    )


def publish_catalog(cases: Sequence[WorkerCase]) -> None:
    """Publish all canonical bundles through the public publisher CLI."""

    for case in cases:
        result = _run_checked(
            publisher_command(OUTPUT_ROOT / case.batch_id),
            label=f"publisher Type {case.type_number}/{case.scenario}",
            timeout=60,
        )
        output = _last_json_line(result, label="publisher")
        if (
            set(output) != {"batch_id", "sha256", "status"}
            or output.get("batch_id") != case.batch_id
            or output.get("status") != "published"
        ):
            raise WorkerAcceptanceFailure(
                f"Publisher result is inconsistent: {case.batch_id}"
            )


def build_reserved_type01_bundle(
    source_bundle: Path,
    *,
    batch_id: str,
    configuration: RuntimeConfiguration,
    corrupt_checksum: bool,
) -> tuple[Path, PublishedRaw]:
    """Create one reserved Type 01 transport bundle from canonical bytes."""

    if batch_id not in RESERVED_BATCHES:
        raise WorkerAcceptanceFailure("Reserved bundle batch ID is unsafe")
    source_manifest = _read_json_object(
        source_bundle / "source-manifest.json"
    )
    source_batch = source_manifest.get("batch_id")
    source_file = source_manifest.get("source_file")
    if (
        not isinstance(source_batch, str)
        or not isinstance(source_file, Mapping)
        or not isinstance(source_file.get("name"), str)
    ):
        raise WorkerAcceptanceFailure(
            "Canonical Type 01 source manifest is incomplete"
        )
    source_filename = str(source_file["name"])
    raw_bytes = (source_bundle / source_filename).read_bytes()
    if raw_bytes.count(source_batch.encode("ascii")) < 2:
        raise WorkerAcceptanceFailure(
            "Canonical Type 01 raw bytes lack expected lineage"
        )
    reserved_bytes = raw_bytes.replace(
        source_batch.encode("ascii"),
        batch_id.encode("ascii"),
    )
    filename = source_filename.replace(source_batch, batch_id)
    if filename == source_filename:
        raise WorkerAcceptanceFailure(
            "Reserved Type 01 filename was not rewritten"
        )
    digest = hashlib.sha256(reserved_bytes).hexdigest()

    manifest = dict(source_manifest)
    rewritten_source = dict(source_file)
    rewritten_source.update(
        {
            "name": filename,
            "sha256": digest,
            "size_bytes": len(reserved_bytes),
        }
    )
    manifest["batch_id"] = batch_id
    manifest["source_file"] = rewritten_source

    bundle = RESERVED_ROOT / batch_id
    bundle.mkdir(mode=0o700, parents=True)
    RESERVED_ROOT.chmod(0o700)
    (bundle / filename).write_bytes(reserved_bytes)
    checksum_path = bundle / f"{filename}.sha256"
    checksum_path.write_bytes(
        f"{digest}  {filename}\n".encode("ascii")
    )
    (bundle / "source-manifest.json").write_text(
        json.dumps(
            manifest,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    for artifact in bundle.iterdir():
        artifact.chmod(0o600)
    validated = validate_bundle(bundle, configuration=configuration)
    if corrupt_checksum:
        checksum_path.write_bytes(
            f"{'0' * 64}  {filename}\n".encode("ascii")
        )
    return bundle, validated


def _bundle_transport_artifacts(
    bundle: Path,
    raw: PublishedRaw,
    *,
    allow_generation_receipt: bool = False,
) -> tuple[tuple[str, Path], ...]:
    """Return three transport artifacts from an exact local bundle shape."""

    artifacts = (
        (raw.filename, bundle / raw.filename),
        (
            f"{raw.filename}.sha256",
            bundle / f"{raw.filename}.sha256",
        ),
        ("source-manifest.json", bundle / "source-manifest.json"),
    )
    expected_names = {name for name, _ in artifacts}
    if allow_generation_receipt:
        expected_names.add("generation-receipt.json")
    if (
        expected_names != {path.name for path in bundle.iterdir()}
        or any(not path.is_file() for _, path in artifacts)
        or (
            allow_generation_receipt
            and not (bundle / "generation-receipt.json").is_file()
        )
    ):
        raise WorkerAcceptanceFailure(
            f"Local transport bundle is not exact: {raw.batch_id}"
        )
    return artifacts


def upload_reserved_bundle(
    bundle: Path,
    raw: PublishedRaw,
    *,
    zone: str,
    role: SftpRole,
    configuration: RuntimeConfiguration,
) -> None:
    """Upload one reserved exact bundle to a named raw zone."""

    if raw.batch_id not in RESERVED_BATCHES or zone not in RAW_ZONES:
        raise WorkerAcceptanceFailure(
            "Reserved SFTP publication target is unsafe"
        )
    remote = f"/raw/{zone}/{raw.batch_id}"
    artifacts = _bundle_transport_artifacts(bundle, raw)
    with connect_sftp(configuration, role) as sftp:
        mkdir_exact(sftp, remote)
        try:
            upload_manifest_last(
                sftp,
                remote,
                artifacts,
                manifest_name="source-manifest.json",
            )
        except Exception:
            try:
                sftp.rmdir(remote)
            except OSError:
                pass
            raise


def stage_incomplete_batch(
    configuration: RuntimeConfiguration,
) -> None:
    """Leave one manifest-less final ``.part`` artifact for discovery."""

    directory = RESERVED_ROOT / INCOMPLETE_BATCH
    directory.mkdir(mode=0o700)
    artifact = directory / INCOMPLETE_PART_NAME
    artifact.write_bytes(b"manifest-last acceptance marker\n")
    artifact.chmod(0o600)
    remote = f"/raw/incoming/{INCOMPLETE_BATCH}"
    with connect_sftp(
        configuration,
        configuration.raw_publisher,
    ) as sftp:
        mkdir_exact(sftp, remote)
        sftp.put(
            str(artifact),
            f"{remote}/{INCOMPLETE_PART_NAME}",
            confirm=True,
        )
        if (
            set(sftp.listdir(remote)) != {INCOMPLETE_PART_NAME}
            or exists(sftp, f"{remote}/source-manifest.json")
        ):
            raise WorkerAcceptanceFailure(
                "Incomplete batch accidentally became manifest-ready"
            )


def preclaim_recovery_batch(
    cases: Sequence[WorkerCase],
    catalog: GeneratedCatalog,
    configuration: RuntimeConfiguration,
) -> WorkerCase:
    """Move one published success into processing before worker startup."""

    recovery = next(
        case
        for case in cases
        if (
            case.type_number == RECOVERY_TYPE
            and case.scenario == RECOVERY_SCENARIO
        )
    )
    claimed: ClaimedRaw = claim_batch(
        recovery.batch_id,
        configuration=configuration,
    )
    raw = catalog.raws[recovery.batch_id]
    if (
        claimed.batch_id,
        claimed.file_type,
        claimed.filename,
        claimed.sha256,
        claimed.manifest_sha256,
    ) != (
        raw.batch_id,
        raw.file_type,
        raw.filename,
        raw.sha256,
        raw.manifest_sha256,
    ):
        raise WorkerAcceptanceFailure(
            "Preclaimed recovery identity differs from generated source"
        )
    return recovery


def stage_recovery_cache(
    recovery: WorkerCase,
    catalog: GeneratedCatalog,
    configuration: RuntimeConfiguration,
) -> Path:
    """Stage one exact private cache for validated processing recovery."""

    if (
        recovery.type_number != RECOVERY_TYPE
        or recovery.scenario != RECOVERY_SCENARIO
        or recovery.expected_status != "succeeded"
    ):
        raise WorkerAcceptanceFailure(
            "Retained-cache recovery case is not the designed success"
        )
    _prepare_empty_cache_root()

    raw = catalog.raws[recovery.batch_id]
    source = OUTPUT_ROOT / recovery.batch_id
    target = WORKER_CACHE / recovery.batch_id
    target.mkdir(mode=0o700)
    source_artifacts = (
        (raw.filename, source / raw.filename),
        (
            f"{raw.filename}.sha256",
            source / f"{raw.filename}.sha256",
        ),
        ("source-manifest.json", source / "source-manifest.json"),
    )
    for name, source_path in source_artifacts:
        destination = target / name
        content = source_path.read_bytes()
        with destination.open("xb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    if (
        {path.name for path in target.iterdir()}
        != {
            raw.filename,
            f"{raw.filename}.sha256",
            "source-manifest.json",
        }
        or (target / "generation-receipt.json").exists()
        or validate_bundle(target, configuration=configuration) != raw
    ):
        raise WorkerAcceptanceFailure(
            "Retained recovery cache is not an exact transport bundle"
        )
    for directory in (target, WORKER_CACHE):
        descriptor = os.open(
            directory,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    _require_private_tree(WORKER_CACHE)
    return target


def _prepare_empty_cache_root() -> None:
    """Accept only a missing or exact empty private worker cache root."""

    try:
        metadata = WORKER_CACHE.lstat()
    except FileNotFoundError:
        WORKER_CACHE.mkdir(mode=0o700)
        return
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or metadata.st_uid != os.geteuid()
        or any(WORKER_CACHE.iterdir())
    ):
        raise WorkerAcceptanceFailure(
            "Retained-cache root is not an empty private directory"
        )


def verify_recovery_cache_consumed(cache: Path) -> None:
    """Require terminal recovery to remove only its validated cache bundle."""

    try:
        cache.lstat()
    except FileNotFoundError:
        pass
    else:
        raise WorkerAcceptanceFailure(
            "Terminal retained cache was not removed"
        )
    if not WORKER_CACHE.is_dir() or tuple(WORKER_CACHE.iterdir()):
        raise WorkerAcceptanceFailure(
            "Retained-cache replay left local cache artifacts"
        )


def verify_pre_worker_sftp(
    pending_cases: Sequence[WorkerCase],
    recovery: WorkerCase,
    completed_cases: Sequence[WorkerCase],
    oracle_raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> None:
    """Require the exact ready/recovery/incomplete queue before execution."""

    pending = {case.batch_id for case in pending_cases}
    completed_successes = {
        case.batch_id
        for case in completed_cases
        if case.expected_status == "succeeded"
    }
    completed_quarantines = {
        case.batch_id
        for case in completed_cases
        if case.expected_status == "quarantined"
    }
    expected = {
        "raw/incoming": tuple(
            sorted(
                (pending - {recovery.batch_id})
                | {BAD_CHECKSUM_BATCH, INCOMPLETE_BATCH}
            )
        ),
        "raw/processing": (recovery.batch_id,),
        "raw/quarantine": tuple(
            sorted(completed_quarantines | {oracle_raw.batch_id})
        ),
        "raw/archive": tuple(sorted(completed_successes)),
        "csv/outgoing": (),
        "csv/processing": (),
        "csv/quarantine": (oracle_raw.batch_id,),
        "csv/archive": tuple(sorted(completed_successes)),
    }
    if _sftp_zone_snapshot(configuration) != expected:
        raise WorkerAcceptanceFailure(
            "Pre-worker SFTP queue does not match the designed topology"
        )


def sanitized_worker_environment(
    environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return the host environment with test seams cleared or allowlisted.

    Ambient ``NWP_TEST_*`` values can never affect an acceptance worker. A
    caller must explicitly provide one of the three production test seams,
    and every supplied value is validated before process creation.
    """

    sanitized = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("NWP_TEST_")
    }
    if environment is None:
        return sanitized
    if set(environment) - WORKER_TEST_HOOKS:
        raise WorkerAcceptanceFailure(
            "Worker test environment contains an unknown hook"
        )
    for name, value in environment.items():
        if not isinstance(value, str) or not value or "\x00" in value:
            raise WorkerAcceptanceFailure(
                "Worker test environment contains an unsafe value"
            )
        if (
            name == "NWP_TEST_INTERRUPT_AFTER"
            and value not in WORKER_INTERRUPT_BOUNDARIES
        ):
            raise WorkerAcceptanceFailure(
                "Worker interruption boundary is unsupported"
            )
        if (
            name
            in {
                "NWP_TEST_FORCE_ORACLE_MISMATCH_BATCH_ID",
                "NWP_TEST_INTERRUPT_BATCH_ID",
            }
            and BATCH_ID_PATTERN.fullmatch(value) is None
        ):
            raise WorkerAcceptanceFailure(
                "Worker test hook batch identity is invalid"
            )
        sanitized[name] = value
    has_boundary = "NWP_TEST_INTERRUPT_AFTER" in environment
    has_interrupt_id = "NWP_TEST_INTERRUPT_BATCH_ID" in environment
    if has_boundary != has_interrupt_id:
        raise WorkerAcceptanceFailure(
            "Worker interruption hook is not batch-scoped"
        )
    forced = environment.get(
        "NWP_TEST_FORCE_ORACLE_MISMATCH_BATCH_ID"
    )
    interrupted = environment.get("NWP_TEST_INTERRUPT_BATCH_ID")
    if forced is not None and interrupted is not None and forced != interrupted:
        raise WorkerAcceptanceFailure(
            "Worker test hooks select different batch identities"
        )
    return sanitized


def run_worker_once(
    *,
    environment: Mapping[str, str] | None = None,
    max_batches: int = 100,
) -> dict[str, object]:
    """Run one bounded worker with an explicitly sanitized environment."""

    result = _run_checked(
        worker_command(once=True, max_batches=max_batches),
        label="automatic worker once",
        timeout=900,
        environment=sanitized_worker_environment(environment),
    )
    return _last_json_line(result, label="automatic worker once")


def _expected_summary(
    *,
    discovered: int,
    ignored: int,
    processed: int,
    quarantined: int,
    retry_pending: int,
    succeeded: int,
    oracle_mismatch: int = 0,
) -> dict[str, int]:
    """Build the worker's exact public aggregate shape."""

    return {
        "deferred": 0,
        "discovered": discovered,
        "ignored": ignored,
        "not_ready": 0,
        "oracle_mismatch": oracle_mismatch,
        "processed": processed,
        "quarantined": quarantined,
        "retry_pending": retry_pending,
        "succeeded": succeeded,
    }


def _report_batches(
    report: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    """Return a report's batch mappings or fail closed on shape."""

    value = report.get("batches")
    if not isinstance(value, list) or any(
        not isinstance(item, Mapping) for item in value
    ):
        raise WorkerAcceptanceFailure("Worker report batches are malformed")
    return tuple(value)


def verify_first_cycle_report(
    report: Mapping[str, object],
    cases: Sequence[WorkerCase],
    recovery: WorkerCase,
) -> None:
    """Verify all canonical peers continued around isolated failures."""

    expected_summary = _expected_summary(
        discovered=len(cases) + 1,
        ignored=1,
        processed=len(cases) + 1,
        quarantined=(
            sum(
                case.expected_status == "quarantined"
                for case in cases
            )
            + 1
        ),
        retry_pending=0,
        succeeded=sum(
            case.expected_status == "succeeded"
            for case in cases
        ),
    )
    if (
        report.get("status") != "completed"
        or report.get("summary") != expected_summary
        or set(report)
        != {"batches", "finished_at", "started_at", "status", "summary"}
    ):
        raise WorkerAcceptanceFailure(
            "First worker cycle aggregate is incomplete"
        )

    expected: list[dict[str, object]] = []
    for case in cases:
        expected.append(
            {
                "batch_id": case.batch_id,
                "code": "TERMINAL",
                "file_type": case.type_number,
                "source_zone": (
                    "processing"
                    if case.batch_id == recovery.batch_id
                    else "incoming"
                ),
                "status": case.expected_status,
            }
        )
    expected.append(
        {
            "batch_id": BAD_CHECKSUM_BATCH,
            "code": "SOURCE_INTEGRITY_ERROR",
            "source_zone": "incoming",
            "status": "quarantined",
        }
    )
    expected.sort(
        key=lambda item: (
            item["source_zone"] != "processing",
            str(item["batch_id"]),
        )
    )
    observed = [dict(item) for item in _report_batches(report)]
    if observed != expected:
        raise WorkerAcceptanceFailure(
            "First worker cycle outcomes differ from the exact queue"
        )


def verify_no_work_report(
    report: Mapping[str, object],
    *,
    ignored: int = 1,
) -> None:
    """Require a completed cycle with no manifest-ready mutation."""

    if (
        report.get("status") != "completed"
        or set(report)
        != {"batches", "finished_at", "started_at", "status", "summary"}
        or report.get("summary")
        != _expected_summary(
            discovered=0,
            ignored=ignored,
            processed=0,
            quarantined=0,
            retry_pending=0,
            succeeded=0,
        )
        or _report_batches(report)
    ):
        raise WorkerAcceptanceFailure(
            "No-work worker cycle reported unexpected mutation"
        )


def verify_duplicate_cycle_report(
    report: Mapping[str, object],
) -> None:
    """Require one non-mutating retry for a duplicate-zone identity."""

    verify_retry_cycle_report(
        report,
        batch_id=DUPLICATE_ZONE_BATCH,
        code="SFTP_ZONE_AMBIGUITY",
        source_zone="processing",
    )


def verify_retry_cycle_report(
    report: Mapping[str, object],
    *,
    batch_id: str,
    code: str,
    source_zone: str,
    file_type: str | None = None,
    ignored: int = 1,
) -> None:
    """Require one isolated retry while the incomplete peer stays ignored."""

    if (
        batch_id not in RESERVED_BATCHES | RESTART_CANONICAL_BATCHES
        or SAFE_CODE_PATTERN.fullmatch(code) is None
        or source_zone not in {"incoming", "processing", "cache"}
        or (file_type is not None and file_type not in TYPE_SCENARIOS)
        or ignored not in {0, 1}
    ):
        raise WorkerAcceptanceFailure(
            "Reserved retry expectation is unsafe"
        )
    expected = {
        "batch_id": batch_id,
        "code": code,
        "source_zone": source_zone,
        "status": "retry_pending",
    }
    if file_type is not None:
        expected["file_type"] = file_type
    if (
        report.get("status") != "completed"
        or set(report)
        != {"batches", "finished_at", "started_at", "status", "summary"}
        or report.get("summary")
        != _expected_summary(
            discovered=1,
            ignored=ignored,
            processed=1,
            quarantined=0,
            retry_pending=1,
            succeeded=0,
        )
        or tuple(dict(item) for item in _report_batches(report))
        != (expected,)
    ):
        raise WorkerAcceptanceFailure(
            "Reserved batch was not isolated as one retry"
        )


def verify_terminal_cycle_report(
    report: Mapping[str, object],
    *,
    batch_id: str,
    file_type: str,
    status: str,
    source_zone: str,
    ignored: int = 0,
) -> None:
    """Require one exact terminal result from a fresh recovery process."""

    if (
        BATCH_ID_PATTERN.fullmatch(batch_id) is None
        or file_type not in TYPE_SCENARIOS
        or status not in {"succeeded", "quarantined", "oracle_mismatch"}
        or source_zone not in {"processing", "cache"}
        or ignored not in {0, 1}
    ):
        raise WorkerAcceptanceFailure(
            "Terminal recovery expectation is unsafe"
        )
    expected = {
        "batch_id": batch_id,
        "code": "TERMINAL",
        "file_type": file_type,
        "source_zone": source_zone,
        "status": status,
    }
    if (
        report.get("status") != "completed"
        or set(report)
        != {"batches", "finished_at", "started_at", "status", "summary"}
        or report.get("summary")
        != _expected_summary(
            discovered=1,
            ignored=ignored,
            processed=1,
            quarantined=int(status == "quarantined"),
            retry_pending=0,
            succeeded=int(status == "succeeded"),
            oracle_mismatch=int(status == "oracle_mismatch"),
        )
        or tuple(dict(item) for item in _report_batches(report))
        != (expected,)
    ):
        raise WorkerAcceptanceFailure(
            "Restart recovery did not publish one exact terminal outcome"
        )


def _remote_file_digest(
    sftp: object,
    remote_path: str,
) -> tuple[int, str]:
    """Hash one bounded regular remote artifact without retaining its bytes."""

    attributes = getattr(sftp, "lstat")(remote_path)
    mode = attributes.st_mode
    size = attributes.st_size
    if (
        not isinstance(mode, int)
        or not stat.S_ISREG(mode)
        or not isinstance(size, int)
        or size < 1
        or size > 64 * 1024 * 1024
    ):
        raise WorkerAcceptanceFailure(
            "Remote acceptance artifact violates file bounds"
        )
    digest = hashlib.sha256()
    observed = 0
    with getattr(sftp, "file")(remote_path, "rb") as stream:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            if not isinstance(chunk, bytes):
                raise WorkerAcceptanceFailure(
                    "Remote acceptance artifact is not binary"
                )
            observed += len(chunk)
            if observed > size:
                raise WorkerAcceptanceFailure(
                    "Remote acceptance artifact changed while hashing"
                )
            digest.update(chunk)
    if observed != size:
        raise WorkerAcceptanceFailure(
            "Remote acceptance artifact size changed while hashing"
        )
    return size, digest.hexdigest()


def _read_remote_json(
    sftp: object,
    remote_path: str,
) -> dict[str, object]:
    """Read one small remote JSON object through a verified connection."""

    attributes = getattr(sftp, "lstat")(remote_path)
    if (
        not isinstance(attributes.st_mode, int)
        or not stat.S_ISREG(attributes.st_mode)
        or not isinstance(attributes.st_size, int)
        or not 1 <= attributes.st_size <= 1_048_576
    ):
        raise WorkerAcceptanceFailure("Remote JSON artifact is unsafe")
    with getattr(sftp, "file")(remote_path, "rb") as stream:
        content = stream.read(1_048_577)
    try:
        value = json.loads(content)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkerAcceptanceFailure(
            "Remote JSON artifact is unreadable"
        ) from exc
    if not isinstance(value, dict):
        raise WorkerAcceptanceFailure(
            "Remote JSON artifact is not an object"
        )
    return value


def _assert_remote_bundle(
    sftp: object,
    *,
    bundle: Path,
    raw: PublishedRaw,
    zone: str,
    reason_code: str | None,
    allow_generation_receipt: bool = False,
) -> None:
    """Require byte-identical transport artifacts in one terminal raw zone."""

    remote = f"/raw/{zone}/{raw.batch_id}"
    artifacts = _bundle_transport_artifacts(
        bundle,
        raw,
        allow_generation_receipt=allow_generation_receipt,
    )
    expected_names = {name for name, _ in artifacts}
    if reason_code is not None:
        expected_names.add("quarantine-reason.json")
    if set(getattr(sftp, "listdir")(remote)) != expected_names:
        raise WorkerAcceptanceFailure(
            f"Raw terminal bundle is not exact: {raw.batch_id}"
        )
    for name, local_path in artifacts:
        local_content = local_path.read_bytes()
        size, digest = _remote_file_digest(sftp, f"{remote}/{name}")
        if (
            size != len(local_content)
            or digest != hashlib.sha256(local_content).hexdigest()
        ):
            raise WorkerAcceptanceFailure(
                f"Raw terminal bytes changed: {raw.batch_id}"
            )
    if reason_code is not None:
        reason = _read_remote_json(
            sftp,
            f"{remote}/quarantine-reason.json",
        )
        if reason != {
            "batch_id": raw.batch_id,
            "code": reason_code,
            "scope": "batch",
            "status": "quarantined",
        }:
            raise WorkerAcceptanceFailure(
                f"Quarantine reason is inconsistent: {raw.batch_id}"
            )


def sftp_deep_snapshot(
    configuration: RuntimeConfiguration,
) -> Mapping[str, tuple[tuple[str, str, int, str], ...]]:
    """Hash every lifecycle artifact for exact no-mutation comparisons."""

    snapshot: dict[str, tuple[tuple[str, str, int, str], ...]] = {}
    with connect_sftp(configuration, configuration.operator) as sftp:
        for boundary, zones in (("raw", RAW_ZONES), ("csv", CSV_ZONES)):
            for zone in zones:
                key = f"{boundary}/{zone}"
                rows: list[tuple[str, str, int, str]] = []
                for batch_id in sorted(sftp.listdir(f"/{key}")):
                    batch = f"/{key}/{batch_id}"
                    mode = sftp.lstat(batch).st_mode
                    if not isinstance(mode, int) or not stat.S_ISDIR(mode):
                        raise WorkerAcceptanceFailure(
                            "SFTP lifecycle contains a non-directory batch"
                        )
                    for name in sorted(sftp.listdir(batch)):
                        size, digest = _remote_file_digest(
                            sftp,
                            f"{batch}/{name}",
                        )
                        rows.append((batch_id, name, size, digest))
                snapshot[key] = tuple(rows)
    return MappingProxyType(snapshot)


def _without_sftp_batch(
    snapshot: Mapping[
        str,
        tuple[tuple[str, str, int, str], ...],
    ],
    batch_id: str,
) -> Mapping[str, tuple[tuple[str, str, int, str], ...]]:
    """Remove one batch identity from a deep snapshot for delta checks."""

    return MappingProxyType(
        {
            zone: tuple(
                row for row in rows if row[0] != batch_id
            )
            for zone, rows in snapshot.items()
        }
    )


def _assert_only_ready_batch(
    expected_batch_id: str | None,
    configuration: RuntimeConfiguration,
) -> None:
    """Require no active worker identity other than the selected probe."""

    active: set[str] = set()
    snapshot = _sftp_zone_snapshot(configuration)
    active.update(snapshot["raw/incoming"])
    active.update(snapshot["raw/processing"])
    if WORKER_CACHE.exists():
        active.update(path.name for path in WORKER_CACHE.iterdir())
    expected = set() if expected_batch_id is None else {expected_batch_id}
    if active != expected:
        raise WorkerAcceptanceFailure(
            "Restart probe was not the only active worker identity"
        )


def _batch_sftp_zones(
    batch_id: str,
    configuration: RuntimeConfiguration,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return exact raw and sanitized zones containing one batch."""

    snapshot = _sftp_zone_snapshot(configuration)
    raw = tuple(
        zone
        for zone in RAW_ZONES
        if batch_id in snapshot[f"raw/{zone}"]
    )
    csv = tuple(
        zone
        for zone in CSV_ZONES
        if batch_id in snapshot[f"csv/{zone}"]
    )
    return raw, csv


def _assert_sanitized_remote_bundle(
    raw: PublishedRaw,
    *,
    zone: str,
    reason_code: str | None,
    configuration: RuntimeConfiguration,
) -> None:
    """Verify one exact, lineage-bound sanitized bundle in a named zone."""

    remote = f"/csv/{zone}/{raw.batch_id}"
    with connect_sftp(configuration, configuration.operator) as sftp:
        manifest = _read_remote_json(
            sftp,
            f"{remote}/sanitized-manifest.json",
        )
        csv_file = manifest.get("csv_file")
        if not isinstance(csv_file, Mapping) or not isinstance(
            csv_file.get("name"),
            str,
        ):
            raise WorkerAcceptanceFailure(
                "Restart sanitized manifest is incomplete"
            )
        filename = str(csv_file["name"])
        expected_names = {
            filename,
            f"{filename}.sha256",
            "sanitized-manifest.json",
        }
        if reason_code is not None:
            expected_names.add("quarantine-reason.json")
        if set(sftp.listdir(remote)) != expected_names:
            raise WorkerAcceptanceFailure(
                "Restart sanitized bundle is not exact"
            )
        if reason_code is not None:
            reason = _read_remote_json(
                sftp,
                f"{remote}/quarantine-reason.json",
            )
            if reason != {
                "batch_id": raw.batch_id,
                "code": reason_code,
                "scope": "batch",
                "status": "quarantined",
            }:
                raise WorkerAcceptanceFailure(
                    "Restart sanitized quarantine reason is inconsistent"
                )
    observation = read_sanitized_observation(
        raw,
        zone=zone,
        configuration=configuration,
    )
    if (
        observation.get("batch_id") != raw.batch_id
        or observation.get("status") != "succeeded"
    ):
        raise WorkerAcceptanceFailure(
            "Restart sanitized bundle lost its source identity"
        )


def _assert_retained_cache(
    bundle: Path,
    raw: PublishedRaw,
    *,
    configuration: RuntimeConfiguration,
) -> None:
    """Require one private, exact three-artifact immutable worker cache."""

    target = WORKER_CACHE / raw.batch_id
    artifacts = _bundle_transport_artifacts(target, raw)
    source_artifacts = dict(
        _bundle_transport_artifacts(
            bundle,
            raw,
            allow_generation_receipt=(
                bundle.parent == OUTPUT_ROOT
            ),
        )
    )
    if validate_bundle(target, configuration=configuration) != raw:
        raise WorkerAcceptanceFailure(
            "Restart cache identity differs from its published source"
        )
    for name, cached_path in artifacts:
        if cached_path.read_bytes() != source_artifacts[name].read_bytes():
            raise WorkerAcceptanceFailure(
                "Restart cache bytes differ from their published source"
            )
    _require_private_tree(target)


def _assert_recovery_journal(
    probe: RestartProbe,
    raw: PublishedRaw,
    *,
    configuration: RuntimeConfiguration,
) -> None:
    """Require one exact private journal only for quarantine recoveries."""

    adapter = workflow_for_type(raw.file_type)
    path = recovery_journal_path(configuration, raw.batch_id)
    journal = load_terminal_recovery(
        adapter,
        raw,
        configuration=configuration,
    )
    if probe.journal_route is None:
        if (
            journal is not None
            or path.exists()
            or (
                TERMINAL_RECOVERY_ROOT.exists()
                and tuple(TERMINAL_RECOVERY_ROOT.iterdir())
            )
        ):
            raise WorkerAcceptanceFailure(
                "Non-quarantine restart created a recovery journal"
            )
        return
    if (
        journal is None
        or journal.batch_id != raw.batch_id
        or journal.file_type != raw.file_type
        or journal.route != probe.journal_route
        or journal.code != probe.expected_code
        or journal.raw_sha256 != raw.sha256
        or journal.manifest_sha256 != raw.manifest_sha256
        or not path.is_file()
        or {item.name for item in TERMINAL_RECOVERY_ROOT.iterdir()}
        != {path.name}
    ):
        raise WorkerAcceptanceFailure(
            "Restart recovery journal is incomplete"
        )
    _require_private_tree(TERMINAL_RECOVERY_ROOT)


def verify_terminal_sftp(
    cases: Sequence[WorkerCase],
    catalog: GeneratedCatalog,
    bad_bundle: Path,
    bad_raw: PublishedRaw,
    oracle_bundle: Path,
    oracle_raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> None:
    """Verify exact terminal zones, bytes, reasons, and sanitized integrity."""

    successes = {
        case.batch_id
        for case in cases
        if case.expected_status == "succeeded"
    }
    quarantines = {
        case.batch_id
        for case in cases
        if case.expected_status == "quarantined"
    }
    expected_zones = {
        "raw/incoming": (INCOMPLETE_BATCH,),
        "raw/processing": (),
        "raw/quarantine": tuple(
            sorted(
                quarantines
                | {BAD_CHECKSUM_BATCH, oracle_raw.batch_id}
            )
        ),
        "raw/archive": tuple(sorted(successes)),
        "csv/outgoing": (),
        "csv/processing": (),
        "csv/quarantine": (oracle_raw.batch_id,),
        "csv/archive": tuple(sorted(successes)),
    }
    if _sftp_zone_snapshot(configuration) != expected_zones:
        raise WorkerAcceptanceFailure(
            "Worker terminal SFTP topology is incomplete"
        )

    with connect_sftp(configuration, configuration.operator) as sftp:
        incomplete = f"/raw/incoming/{INCOMPLETE_BATCH}"
        if (
            set(sftp.listdir(incomplete)) != {INCOMPLETE_PART_NAME}
            or exists(sftp, f"{incomplete}/source-manifest.json")
        ):
            raise WorkerAcceptanceFailure(
                "Manifest-less batch did not remain invisible"
            )
        for case in cases:
            raw = catalog.raws[case.batch_id]
            zone = (
                "archive"
                if case.expected_status == "succeeded"
                else "quarantine"
            )
            _assert_remote_bundle(
                sftp,
                bundle=OUTPUT_ROOT / case.batch_id,
                raw=raw,
                zone=zone,
                reason_code=(
                    None
                    if case.expected_status == "succeeded"
                    else catalog.rejection_codes[case.batch_id]
                ),
                allow_generation_receipt=True,
            )
        _assert_remote_bundle(
            sftp,
            bundle=bad_bundle,
            raw=bad_raw,
            zone="quarantine",
            reason_code="SOURCE_INTEGRITY_ERROR",
        )
        _assert_remote_bundle(
            sftp,
            bundle=oracle_bundle,
            raw=oracle_raw,
            zone="quarantine",
            reason_code="ORACLE_MISMATCH",
        )

        for batch_id in sorted(successes):
            remote = f"/csv/archive/{batch_id}"
            manifest = _read_remote_json(
                sftp,
                f"{remote}/sanitized-manifest.json",
            )
            csv_file = manifest.get("csv_file")
            if (
                manifest.get("batch_id") != batch_id
                or not isinstance(csv_file, Mapping)
                or not isinstance(csv_file.get("name"), str)
            ):
                raise WorkerAcceptanceFailure(
                    f"Sanitized archive manifest is incomplete: {batch_id}"
                )
            filename = str(csv_file["name"])
            if set(sftp.listdir(remote)) != {
                filename,
                f"{filename}.sha256",
                "sanitized-manifest.json",
            }:
                raise WorkerAcceptanceFailure(
                    f"Sanitized archive bundle is not exact: {batch_id}"
                )

    _assert_sanitized_remote_bundle(
        oracle_raw,
        zone="quarantine",
        reason_code="ORACLE_MISMATCH",
        configuration=configuration,
    )
    for batch_id in sorted(successes):
        observation = read_sanitized_observation(
            catalog.raws[batch_id],
            zone="archive",
            configuration=configuration,
        )
        if (
            observation.get("batch_id") != batch_id
            or observation.get("status") != "succeeded"
        ):
            raise WorkerAcceptanceFailure(
                f"Sanitized archive identity is invalid: {batch_id}"
            )


def postgres_state_snapshot(
    configuration: RuntimeConfiguration,
) -> Mapping[str, tuple[str, ...]]:
    """Return a canonical JSON snapshot of all mutable business relations."""

    snapshot: dict[str, tuple[str, ...]] = {}
    with psycopg.connect(configuration.postgres_dsn) as connection:
        with connection.cursor() as cursor:
            for relation in STATE_RELATIONS:
                cursor.execute(
                    sql.SQL(
                        "SELECT to_jsonb(observed)::text FROM {} AS observed"
                    ).format(_relation(relation))
                )
                snapshot[relation] = tuple(
                    sorted(str(row[0]) for row in cursor.fetchall())
                )
    return MappingProxyType(snapshot)


def _without_postgres_batch(
    snapshot: Mapping[str, tuple[str, ...]],
    batch_id: str,
) -> Mapping[str, tuple[str, ...]]:
    """Remove one batch identity from relation snapshots for delta checks."""

    filtered: dict[str, tuple[str, ...]] = {}
    for relation, rows in snapshot.items():
        kept: list[str] = []
        for row in rows:
            try:
                value = json.loads(row)
            except json.JSONDecodeError as exc:
                raise WorkerAcceptanceFailure(
                    "PostgreSQL snapshot contains invalid JSON"
                ) from exc
            if (
                not isinstance(value, Mapping)
                or value.get("batch_id") != batch_id
            ):
                kept.append(row)
        filtered[relation] = tuple(kept)
    return MappingProxyType(filtered)


def _assert_database_batch_state(
    raw: PublishedRaw,
    *,
    status: str | None,
    failure_code: str | None,
    configuration: RuntimeConfiguration,
) -> None:
    """Require the exact per-batch PostgreSQL shape at a restart boundary."""

    counts: dict[str, int] = {}
    with psycopg.connect(configuration.postgres_dsn) as connection:
        with connection.cursor() as cursor:
            for relation in STATE_RELATIONS:
                cursor.execute(
                    sql.SQL(
                        "SELECT count(*) FROM {} WHERE batch_id = %s"
                    ).format(_relation(relation)),
                    (raw.batch_id,),
                )
                counts[relation] = int(cursor.fetchone()[0])
            cursor.execute(
                """
                SELECT
                    file_type,
                    source_filename,
                    source_sha256,
                    source_manifest_sha256,
                    source_count,
                    source_net_amount::text,
                    source_controls,
                    status,
                    failure_code
                  FROM control.batches
                 WHERE batch_id = %s
                """,
                (raw.batch_id,),
            )
            identity = cursor.fetchone()

    if status is None:
        if identity is not None or any(counts.values()):
            raise WorkerAcceptanceFailure(
                "Restart boundary mutated PostgreSQL before terminal control"
            )
        return

    expected_identity = (
        raw.file_type,
        raw.filename,
        raw.sha256,
        raw.manifest_sha256,
        raw.source_count,
        raw.source_net_amount,
        dict(raw.source_controls),
        status,
        failure_code,
    )
    if identity != expected_identity:
        raise WorkerAcceptanceFailure(
            "Restart PostgreSQL source identity or status is incomplete"
        )

    expected_counts = {relation: 0 for relation in STATE_RELATIONS}
    expected_counts["control.batches"] = 1
    if status in {"database_committed_pending_archive", "succeeded"}:
        staging, business, reporting = TYPE_RELATIONS[raw.file_type]
        expected_counts.update(
            {
                "control.files": 2,
                "control.loads": 1,
                "control.procedure_runs": 2,
                staging: raw.source_count,
                business: raw.source_count,
                reporting: 1,
            }
        )
    elif status in {"quarantined", "oracle_mismatch"}:
        expected_counts.update(
            {
                "control.files": 1,
                "control.rejects": 1,
            }
        )
    else:
        raise WorkerAcceptanceFailure(
            "Restart PostgreSQL expectation has an unsafe status"
        )
    if counts != expected_counts:
        raise WorkerAcceptanceFailure(
            "Restart PostgreSQL relation population is not exact"
        )


def verify_postgres_state(
    cases: Sequence[WorkerCase],
    catalog: GeneratedCatalog,
    oracle_raw: PublishedRaw,
    configuration: RuntimeConfiguration,
) -> None:
    """Reuse typed assertions and require an exact global batch population."""

    type02_acceptance.verify_postgres(configuration)
    for type_number in ("03", "04", "05"):
        spec = suite_for_type(type_number)
        verify_typed_postgres(
            spec,
            load_expectations(spec),
            configuration,
        )

    successes = {
        case.batch_id
        for case in cases
        if case.expected_status == "succeeded"
    }
    quarantines = {
        case.batch_id
        for case in cases
        if case.expected_status == "quarantined"
    }
    expected_batches = {
        (case.batch_id, case.type_number, case.expected_status)
        for case in cases
    } | {
        (oracle_raw.batch_id, oracle_raw.file_type, "oracle_mismatch")
    }
    with psycopg.connect(configuration.postgres_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT batch_id, file_type, status
                  FROM control.batches
                """
            )
            if set(cursor.fetchall()) != expected_batches:
                raise WorkerAcceptanceFailure(
                    "Global PostgreSQL batch controls are not exact"
                )
            cursor.execute(
                "SELECT batch_id, code FROM control.rejects"
            )
            if set(cursor.fetchall()) != {
                (batch_id, catalog.rejection_codes[batch_id])
                for batch_id in quarantines
            } | {(oracle_raw.batch_id, "ORACLE_MISMATCH")}:
                raise WorkerAcceptanceFailure(
                    "Global PostgreSQL rejection controls are not exact"
                )

            expected_by_relation = {
                "control.batches": (
                    successes | quarantines | {oracle_raw.batch_id}
                ),
                "control.files": (
                    successes | quarantines | {oracle_raw.batch_id}
                ),
                "control.loads": successes,
                "control.rejects": quarantines | {oracle_raw.batch_id},
                "control.procedure_runs": successes,
            }
            for type_relations in TYPE_RELATIONS.values():
                for relation in type_relations:
                    expected_by_relation[relation] = successes & {
                        case.batch_id
                        for case in cases
                        if relation in TYPE_RELATIONS[case.type_number]
                    }
            for relation, expected_ids in expected_by_relation.items():
                cursor.execute(
                    sql.SQL("SELECT DISTINCT batch_id FROM {}").format(
                        _relation(relation)
                    )
                )
                if {str(row[0]) for row in cursor.fetchall()} != expected_ids:
                    raise WorkerAcceptanceFailure(
                        f"PostgreSQL relation batch set differs: {relation}"
                    )

            cursor.execute(
                """
                SELECT count(*)
                  FROM control.batches
                 WHERE batch_id = ANY(%s)
                """,
                (list(TRANSPORT_ONLY_RESERVED_BATCHES),),
            )
            if cursor.fetchone() != (0,):
                raise WorkerAcceptanceFailure(
                    "Transport-only probes mutated PostgreSQL"
                )

            type01_successes = {
                case.batch_id
                for case in cases
                if (
                    case.type_number == "01"
                    and case.expected_status == "succeeded"
                )
            }
            cursor.execute(
                """
                SELECT batch_id, status
                  FROM reporting.card_settlement_reconciliation
                """
            )
            if set(cursor.fetchall()) != {
                (batch_id, "MATCHED")
                for batch_id in type01_successes
            }:
                raise WorkerAcceptanceFailure(
                    "Type 01 reconciliation is incomplete"
                )
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
                raise WorkerAcceptanceFailure(
                    "Type 01 PostgreSQL privacy fields are unsafe"
                )


def _type01_sensitive_values(raw: bytes) -> set[bytes]:
    """Extract clear PAN and CPF values prohibited from Type 01 evidence."""

    values: set[bytes] = set()
    for record in raw.splitlines():
        if record.startswith(b"D") and len(record) >= 60:
            values.update(
                {
                    record[33:49],
                    record[49:60],
                }
            )
    return values


def _type02_sensitive_values(raw: bytes) -> set[bytes]:
    """Extract source documents, event IDs, and known free text."""

    values = {
        match.group(0)
        for match in re.finditer(
            rb"(?<=\|)(?:[0-9]{11}|[0-9]{14})(?=\|)",
            raw,
        )
    }
    values.update(
        match.group(0)
        for match in re.finditer(rb"E[0-9]{31}", raw)
    )
    for candidate in (
        b"Invoice 1001",
        b"Invoice 1005",
        b"Return\\|beneficiary",
        b"Unescaped|delimiter",
        "Café, invoice".encode(),
    ):
        if candidate in raw:
            values.add(candidate)
    return values


def evidence_sensitive_values(
    cases: Sequence[WorkerCase],
    catalog: GeneratedCatalog,
) -> frozenset[bytes]:
    """Collect values that aggregate-only evidence must never contain."""

    values: set[bytes] = set()
    populated_types: set[str] = set()
    for case in cases:
        raw = catalog.raws[case.batch_id]
        content = (OUTPUT_ROOT / case.batch_id / raw.filename).read_bytes()
        extracted: set[bytes]
        if case.type_number == "01":
            extracted = _type01_sensitive_values(content)
        elif case.type_number == "02":
            extracted = _type02_sensitive_values(content)
        else:
            typed = TYPE_SPECS[case.type_number].extract_evidence_values(
                content
            )
            extracted = set(typed.restricted | typed.row_scoped)
        extracted = {
            value
            for value in extracted
            if len(value) >= 8 and value
        }
        if extracted:
            populated_types.add(case.type_number)
            values.update(extracted)
    if populated_types != set(TYPE_SCENARIOS) or not values:
        raise WorkerAcceptanceFailure(
            "Privacy extractors did not cover all five source types"
        )
    return frozenset(values)


def _require_private_tree(root: Path) -> None:
    """Require an owner-only, real local acceptance artifact tree."""

    if not root.exists():
        raise WorkerAcceptanceFailure(
            f"Private acceptance path is missing: {root.name}"
        )
    current_user = getattr(os, "geteuid", lambda: None)()
    for path in (root, *sorted(root.rglob("*"))):
        metadata = path.lstat()
        mode = metadata.st_mode
        if (
            stat.S_ISLNK(mode)
            or stat.S_IMODE(mode) & 0o077
            or (
                current_user is not None
                and metadata.st_uid != current_user
            )
            or (
                stat.S_ISDIR(mode)
                and not path.is_dir()
            )
            or (
                not stat.S_ISDIR(mode)
                and (
                    not stat.S_ISREG(mode)
                    or metadata.st_nlink != 1
                )
            )
        ):
            raise WorkerAcceptanceFailure(
                f"Local acceptance path is not private: {path.name}"
            )


def verify_worker_runtime(
    report: Mapping[str, object],
    *,
    expected_max_batches: int = 100,
    expected_cache_batches: frozenset[str] = frozenset(),
) -> None:
    """Verify the stopped heartbeat, private lock, and empty intake cache."""

    heartbeat = _read_json_object(WORKER_STATUS)
    if (
        heartbeat.get("version") != 1
        or heartbeat.get("state") != "stopped"
        or heartbeat.get("max_batches") != expected_max_batches
        or heartbeat.get("poll_interval_seconds") != 0.1
        or heartbeat.get("poll_sequence") != 1
        or heartbeat.get("last_cycle") != dict(report)
        or not isinstance(heartbeat.get("pid"), int)
    ):
        raise WorkerAcceptanceFailure(
            "Stopped worker heartbeat is incomplete"
        )
    try:
        lock_pid = int(WORKER_LOCK.read_text(encoding="ascii").strip())
    except (OSError, UnicodeError, ValueError) as exc:
        raise WorkerAcceptanceFailure(
            "Worker lock identity is unreadable"
        ) from exc
    if lock_pid != heartbeat["pid"]:
        raise WorkerAcceptanceFailure(
            "Worker heartbeat and lock identities differ"
        )
    if (
        not WORKER_CACHE.is_dir()
        or {path.name for path in WORKER_CACHE.iterdir()}
        != set(expected_cache_batches)
    ):
        raise WorkerAcceptanceFailure(
            "Worker cache population differs from its recovery state"
        )
    current_user = getattr(os, "geteuid", lambda: None)()
    for path in (WORKER_STATUS, WORKER_LOCK):
        metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or (
                current_user is not None
                and metadata.st_uid != current_user
            )
        ):
            raise WorkerAcceptanceFailure(
                f"Worker runtime file is not private: {path.name}"
            )
    _require_private_tree(OUTPUT_ROOT)
    _require_private_tree(RESERVED_ROOT)
    _require_private_tree(EVIDENCE_ROOT)
    _require_private_tree(WORKER_CACHE)


def _assert_terminal_restart_evidence(
    bundle: Path,
    raw: PublishedRaw,
    *,
    status: str,
    code: str,
) -> None:
    """Require one exact, immutable terminal packet after process restart."""

    packet = EVIDENCE_ROOT / raw.batch_id
    expected_files = (
        WORKER_SUCCESS_EVIDENCE_FILES
        if status == "succeeded"
        else WORKER_BASE_EVIDENCE_FILES
    )
    if (
        not packet.is_dir()
        or {path.name for path in packet.iterdir()} != expected_files
        or (packet / "generation-receipt.json").exists()
    ):
        raise WorkerAcceptanceFailure(
            "Restart terminal evidence packet is not exact"
        )
    final = _read_json_object(packet / "final-status.json")
    expected_final = workflow_for_type(raw.file_type).final_status_evidence(
        raw,
        status=status,
        code=None if status == "succeeded" else code,
    )
    if final != expected_final:
        raise WorkerAcceptanceFailure(
            "Restart terminal evidence status is incomplete"
        )
    if (
        (packet / "source-manifest.json").read_bytes()
        != (bundle / "source-manifest.json").read_bytes()
        or (packet / "raw-file.sha256").read_bytes()
        != (bundle / f"{raw.filename}.sha256").read_bytes()
    ):
        raise WorkerAcceptanceFailure(
            "Restart terminal evidence lost source identity"
        )
    objects = {
        path.name: _read_json_object(path)
        for path in packet.glob("*.json")
    }
    if any(
        FORBIDDEN_EVIDENCE_KEYS & _walk_mapping_keys(value)
        for value in objects.values()
    ):
        raise WorkerAcceptanceFailure(
            "Restart terminal evidence contains a prohibited source field"
        )
    raw_content = (bundle / raw.filename).read_bytes()
    if any(raw_content in path.read_bytes() for path in packet.iterdir()):
        raise WorkerAcceptanceFailure(
            "Restart terminal evidence contains the raw source payload"
        )
    _require_private_tree(packet)


def verify_evidence(
    cases: Sequence[WorkerCase],
    catalog: GeneratedCatalog,
    oracle_bundle: Path,
    oracle_raw: PublishedRaw,
) -> None:
    """Require exact, immutable, aggregate-only worker evidence packets."""

    expected_ids = {case.batch_id for case in cases} | {
        oracle_raw.batch_id
    }
    if (
        not EVIDENCE_ROOT.is_dir()
        or {path.name for path in EVIDENCE_ROOT.iterdir()}
        != expected_ids
    ):
        raise WorkerAcceptanceFailure(
            "Worker evidence root contains an unexpected packet"
        )
    prohibited = evidence_sensitive_values(cases, catalog)

    for case in cases:
        packet = EVIDENCE_ROOT / case.batch_id
        raw = catalog.raws[case.batch_id]
        expected_files = (
            WORKER_SUCCESS_EVIDENCE_FILES
            if case.expected_status == "succeeded"
            else WORKER_BASE_EVIDENCE_FILES
        )
        files = {
            path.name for path in packet.iterdir() if path.is_file()
        }
        if files != expected_files:
            raise WorkerAcceptanceFailure(
                f"Worker evidence packet is not exact: {case.batch_id}"
            )
        if "generation-receipt.json" in files:
            raise WorkerAcceptanceFailure(
                "Worker copied generator-only evidence across SFTP"
            )
        source_bundle = OUTPUT_ROOT / case.batch_id
        if (
            (packet / "source-manifest.json").read_bytes()
            != (source_bundle / "source-manifest.json").read_bytes()
            or (packet / "raw-file.sha256").read_bytes()
            != (
                source_bundle / f"{raw.filename}.sha256"
            ).read_bytes()
        ):
            raise WorkerAcceptanceFailure(
                f"Worker evidence lost source identity: {case.batch_id}"
            )

        objects = {
            path.name: _read_json_object(path)
            for path in packet.glob("*.json")
        }
        manifest = objects["source-manifest.json"]
        publication = objects["raw-publication.json"]
        intake = objects["raw-intake.json"]
        java = objects["java-run.json"]
        load = objects["postgres-load.json"]
        procedure = objects["procedure-run.json"]
        reconciliation = objects["reconciliation.json"]
        expected_diff = objects["expected-diff.json"]
        final = objects["final-status.json"]
        source_controls = manifest.get("source_controls")
        source_type = manifest.get("file_type")
        if (
            manifest.get("batch_id") != case.batch_id
            or not isinstance(source_type, Mapping)
            or source_type.get("number") != case.type_number
            or not isinstance(source_controls, Mapping)
            or publication.get("batch_id") != case.batch_id
            or publication.get("sha256") != raw.sha256
            or publication.get("status") != "verified_existing"
            or intake.get("batch_id") != case.batch_id
            or intake.get("sha256") != raw.sha256
            or intake.get("manifest_sha256") != raw.manifest_sha256
            or intake.get("status") != "verified_existing_claim"
            or java.get("batch_id") != case.batch_id
            or final.get("batch_id") != case.batch_id
            or final.get("scope") != "batch"
            or final.get("status") != case.expected_status
            or expected_diff.get("expected") is not None
            or expected_diff.get("matches") is not None
        ):
            raise WorkerAcceptanceFailure(
                f"Worker evidence lineage is incomplete: {case.batch_id}"
            )
        if case.type_number != "01" and (
            publication.get("file_type") != case.type_number
            or publication.get("source_controls") != source_controls
            or intake.get("file_type") != case.type_number
            or intake.get("source_controls") != source_controls
            or final.get("file_type") != case.type_number
            or final.get("source_controls") != source_controls
        ):
            raise WorkerAcceptanceFailure(
                f"Typed worker evidence lost controls: {case.batch_id}"
            )

        if case.expected_status == "succeeded":
            expected_load_status = (
                "recovered_committed_batch"
                if case.batch_id
                in {
                    DATABASE_COMMIT_RESTART_BATCH,
                    RAW_ARCHIVE_RESTART_BATCH,
                }
                else "database_committed_pending_archive"
            )
            if (
                java.get("status") != "succeeded"
                or load.get("status")
                != expected_load_status
                or procedure.get("status") != "succeeded"
                or reconciliation.get("batch_id") != case.batch_id
                or reconciliation.get("status") != "MATCHED"
                or expected_diff.get("oracle_status")
                != "internally_reconciled_unscored"
            ):
                raise WorkerAcceptanceFailure(
                    f"Worker success evidence is incomplete: {case.batch_id}"
                )
        else:
            code = catalog.rejection_codes[case.batch_id]
            if (
                java.get("status") != "rejected"
                or java.get("code") != code
                or final.get("code") != code
                or load
                != {
                    "business_state_committed": False,
                    "reason": code,
                    "status": "control_recorded",
                }
                or procedure
                != {"reason": code, "status": "not_run"}
                or reconciliation
                != {"reason": code, "status": "not_run"}
                or expected_diff.get("oracle_status")
                != "rejected_unscored"
            ):
                raise WorkerAcceptanceFailure(
                    f"Worker rejection evidence is incomplete: {case.batch_id}"
                )

        for value in objects.values():
            if FORBIDDEN_EVIDENCE_KEYS & _walk_mapping_keys(value):
                raise WorkerAcceptanceFailure(
                    f"Row-level key leaked into evidence: {case.batch_id}"
                )
        raw_content = (source_bundle / raw.filename).read_bytes()
        for path in packet.iterdir():
            content = path.read_bytes()
            if (
                raw_content in content
                or any(secret in content for secret in prohibited)
            ):
                raise WorkerAcceptanceFailure(
                    f"Source value leaked into evidence: {case.batch_id}"
                )

    packet = EVIDENCE_ROOT / oracle_raw.batch_id
    if (
        {path.name for path in packet.iterdir()}
        != WORKER_BASE_EVIDENCE_FILES
        or (packet / "source-manifest.json").read_bytes()
        != (oracle_bundle / "source-manifest.json").read_bytes()
        or (packet / "raw-file.sha256").read_bytes()
        != (oracle_bundle / f"{oracle_raw.filename}.sha256").read_bytes()
    ):
        raise WorkerAcceptanceFailure(
            "Oracle-mismatch evidence packet is not exact"
        )
    objects = {
        path.name: _read_json_object(path)
        for path in packet.glob("*.json")
    }
    publication = objects["raw-publication.json"]
    intake = objects["raw-intake.json"]
    java = objects["java-run.json"]
    load = objects["postgres-load.json"]
    diagnostic = objects["postgres-diagnostic.json"]
    procedure = objects["procedure-run.json"]
    reconciliation = objects["reconciliation.json"]
    expected_diff = objects["expected-diff.json"]
    final = objects["final-status.json"]
    if (
        publication.get("batch_id") != oracle_raw.batch_id
        or publication.get("status") != "verified_existing"
        or intake.get("batch_id") != oracle_raw.batch_id
        or intake.get("status") != "verified_existing_claim"
        or java.get("batch_id") != oracle_raw.batch_id
        or java.get("status") != "succeeded"
        or load
        != {
            "business_state_committed": False,
            "reason": "ORACLE_MISMATCH",
            "status": "rolled_back_or_not_started",
        }
        or diagnostic
        != {"reason": "ORACLE_MISMATCH", "status": "not_run"}
        or procedure
        != {"reason": "ORACLE_MISMATCH", "status": "not_run"}
        or reconciliation
        != {"reason": "ORACLE_MISMATCH", "status": "not_run"}
        or expected_diff
        != {
            "actual": None,
            "error": "test-only forced contract oracle mismatch",
            "expected": "approved Type 01 contract artifact",
            "matches": False,
            "oracle_status": "oracle_mismatch",
        }
        or final
        != {
            "batch_id": oracle_raw.batch_id,
            "code": "ORACLE_MISMATCH",
            "scope": "batch",
            "status": "oracle_mismatch",
        }
    ):
        raise WorkerAcceptanceFailure(
            "Oracle-mismatch evidence lineage is incomplete"
        )
    for value in objects.values():
        if FORBIDDEN_EVIDENCE_KEYS & _walk_mapping_keys(value):
            raise WorkerAcceptanceFailure(
                "Oracle-mismatch evidence contains a row-level key"
            )
    oracle_content = (oracle_bundle / oracle_raw.filename).read_bytes()
    for path in packet.iterdir():
        content = path.read_bytes()
        if (
            oracle_content in content
            or any(secret in content for secret in prohibited)
        ):
            raise WorkerAcceptanceFailure(
                "Oracle-mismatch evidence contains a source value"
            )


def _remove_exact_reserved_bundle(
    bundle: Path,
    raw: PublishedRaw,
    *,
    zone: str,
    configuration: RuntimeConfiguration,
) -> None:
    """Remove only one byte-identical, allowlisted live probe bundle."""

    if (raw.batch_id, zone) not in RESERVED_CLEANUP_TARGETS:
        raise WorkerAcceptanceFailure(
            "Reserved cleanup target is outside its exact allowlist"
        )
    remote = f"/raw/{zone}/{raw.batch_id}"
    with connect_sftp(configuration, configuration.operator) as sftp:
        if not exists(sftp, remote):
            return
        artifacts = _bundle_transport_artifacts(bundle, raw)
        if set(sftp.listdir(remote)) != {
            name for name, _ in artifacts
        }:
            raise WorkerAcceptanceFailure(
                "Reserved cleanup found unexpected remote artifacts"
            )
        for name, local_path in artifacts:
            local_content = local_path.read_bytes()
            size, digest = _remote_file_digest(
                sftp,
                f"{remote}/{name}",
            )
            if (
                size != len(local_content)
                or digest != hashlib.sha256(local_content).hexdigest()
            ):
                raise WorkerAcceptanceFailure(
                    "Reserved cleanup refused changed remote bytes"
                )
        for name, _ in artifacts:
            sftp.remove(f"{remote}/{name}")
        sftp.rmdir(remote)
        if exists(sftp, remote):
            raise WorkerAcceptanceFailure(
                "Reserved live-probe cleanup was not verified"
            )


def run_duplicate_zone_probe(
    bundle: Path,
    raw: PublishedRaw,
    *,
    baseline_sftp: Mapping[
        str,
        tuple[tuple[str, str, int, str], ...],
    ],
    baseline_postgres: Mapping[str, tuple[str, ...]],
    baseline_evidence: Mapping[str, str],
    configuration: RuntimeConfiguration,
) -> None:
    """Prove duplicate-zone discovery retries without mutating either copy."""

    try:
        upload_reserved_bundle(
            bundle,
            raw,
            zone="incoming",
            role=configuration.operator,
            configuration=configuration,
        )
        upload_reserved_bundle(
            bundle,
            raw,
            zone="processing",
            role=configuration.operator,
            configuration=configuration,
        )
        report = run_worker_once()
        verify_duplicate_cycle_report(report)
        if (
            postgres_state_snapshot(configuration) != baseline_postgres
            or _directory_snapshot(EVIDENCE_ROOT) != baseline_evidence
        ):
            raise WorkerAcceptanceFailure(
                "Duplicate-zone retry mutated downstream state"
            )
    finally:
        _remove_exact_reserved_bundle(
            bundle,
            raw,
            zone="incoming",
            configuration=configuration,
        )
        _remove_exact_reserved_bundle(
            bundle,
            raw,
            zone="processing",
            configuration=configuration,
        )

    if sftp_deep_snapshot(configuration) != baseline_sftp:
        raise WorkerAcceptanceFailure(
            "Duplicate-zone probe cleanup did not restore exact SFTP state"
        )


def _assert_probe_state_restored(
    *,
    baseline_sftp: Mapping[
        str,
        tuple[tuple[str, str, int, str], ...],
    ],
    baseline_postgres: Mapping[str, tuple[str, ...]],
    baseline_evidence: Mapping[str, str],
    configuration: RuntimeConfiguration,
) -> None:
    """Require an isolated live probe to restore every durable boundary."""

    if (
        sftp_deep_snapshot(configuration) != baseline_sftp
        or postgres_state_snapshot(configuration) != baseline_postgres
        or _directory_snapshot(EVIDENCE_ROOT) != baseline_evidence
    ):
        raise WorkerAcceptanceFailure(
            "Reserved live probe did not restore exact durable state"
        )


def _evidence_snapshot() -> Mapping[str, str]:
    """Return an empty snapshot before the first immutable packet exists."""

    if not EVIDENCE_ROOT.exists():
        return MappingProxyType({})
    return _directory_snapshot(EVIDENCE_ROOT)


def _assert_restart_sftp_state(
    probe: RestartProbe,
    bundle: Path,
    raw: PublishedRaw,
    *,
    terminal: bool,
    configuration: RuntimeConfiguration,
) -> None:
    """Require exact per-batch SFTP topology and byte identity."""

    if terminal:
        raw_zone = (
            "archive"
            if probe.expected_status == "succeeded"
            else "quarantine"
        )
        csv_zone = (
            "archive"
            if probe.expected_status == "succeeded"
            else (
                "quarantine"
                if probe.expected_status == "oracle_mismatch"
                else None
            )
        )
    else:
        raw_zone = probe.intermediate_raw_zone
        csv_zone = probe.intermediate_csv_zone

    observed_raw, observed_csv = _batch_sftp_zones(
        raw.batch_id,
        configuration,
    )
    if (
        observed_raw != (raw_zone,)
        or observed_csv != (() if csv_zone is None else (csv_zone,))
    ):
        raise WorkerAcceptanceFailure(
            "Restart SFTP lifecycle zones are not exact"
        )
    raw_reason = (
        probe.expected_code if raw_zone == "quarantine" else None
    )
    with connect_sftp(configuration, configuration.operator) as sftp:
        _assert_remote_bundle(
            sftp,
            bundle=bundle,
            raw=raw,
            zone=raw_zone,
            reason_code=raw_reason,
            allow_generation_receipt=(bundle.parent == OUTPUT_ROOT),
        )
    if csv_zone is not None:
        _assert_sanitized_remote_bundle(
            raw,
            zone=csv_zone,
            reason_code=(
                probe.expected_code
                if csv_zone == "quarantine"
                else None
            ),
            configuration=configuration,
        )


def run_restart_probe(
    probe: RestartProbe,
    bundle: Path,
    raw: PublishedRaw,
    *,
    configuration: RuntimeConfiguration,
) -> None:
    """Interrupt one real worker process and prove fresh-process recovery."""

    if probe.batch_id != raw.batch_id:
        raise WorkerAcceptanceFailure(
            "Restart probe source identity is inconsistent"
        )
    _assert_only_ready_batch(None, configuration)
    baseline_sftp = sftp_deep_snapshot(configuration)
    baseline_postgres = postgres_state_snapshot(configuration)
    baseline_evidence = _evidence_snapshot()

    result = _run_checked(
        publisher_command(bundle),
        label=f"publisher restart/{probe.name}",
        timeout=60,
    )
    output = _last_json_line(result, label="publisher restart")
    if (
        set(output) != {"batch_id", "sha256", "status"}
        or output.get("batch_id") != raw.batch_id
        or output.get("status") != "published"
        or output.get("sha256") != raw.sha256
    ):
        raise WorkerAcceptanceFailure(
            "Restart publication is inconsistent"
        )
    _assert_only_ready_batch(raw.batch_id, configuration)

    hooks = {
        "NWP_TEST_INTERRUPT_AFTER": probe.boundary,
        "NWP_TEST_INTERRUPT_BATCH_ID": raw.batch_id,
    }
    if probe.force_oracle_mismatch:
        hooks["NWP_TEST_FORCE_ORACLE_MISMATCH_BATCH_ID"] = raw.batch_id
    interrupted = run_worker_once(
        environment=hooks,
        max_batches=1,
    )
    verify_retry_cycle_report(
        interrupted,
        batch_id=raw.batch_id,
        code="PIPELINE_RETRY_PENDING",
        source_zone="incoming",
        file_type=raw.file_type,
        ignored=0,
    )
    verify_worker_runtime(
        interrupted,
        expected_max_batches=1,
        expected_cache_batches=frozenset({raw.batch_id}),
    )
    _assert_only_ready_batch(raw.batch_id, configuration)
    _assert_restart_sftp_state(
        probe,
        bundle,
        raw,
        terminal=False,
        configuration=configuration,
    )
    _assert_retained_cache(bundle, raw, configuration=configuration)
    _assert_recovery_journal(probe, raw, configuration=configuration)
    _assert_database_batch_state(
        raw,
        status=probe.intermediate_database_status,
        failure_code=None,
        configuration=configuration,
    )
    if (EVIDENCE_ROOT / raw.batch_id).exists():
        raise WorkerAcceptanceFailure(
            "Interrupted worker published premature final evidence"
        )
    if (
        _without_sftp_batch(
            sftp_deep_snapshot(configuration),
            raw.batch_id,
        )
        != baseline_sftp
        or _without_postgres_batch(
            postgres_state_snapshot(configuration),
            raw.batch_id,
        )
        != baseline_postgres
        or _evidence_snapshot() != baseline_evidence
    ):
        raise WorkerAcceptanceFailure(
            "Restart interruption mutated an unrelated durable identity"
        )

    recovered = run_worker_once(max_batches=1)
    verify_terminal_cycle_report(
        recovered,
        batch_id=raw.batch_id,
        file_type=raw.file_type,
        status=probe.expected_status,
        source_zone=probe.recovery_source_zone,
    )
    verify_worker_runtime(recovered, expected_max_batches=1)
    _assert_only_ready_batch(None, configuration)
    _assert_restart_sftp_state(
        probe,
        bundle,
        raw,
        terminal=True,
        configuration=configuration,
    )
    _assert_database_batch_state(
        raw,
        status=probe.expected_status,
        failure_code=(
            None
            if probe.expected_status == "succeeded"
            else probe.expected_code
        ),
        configuration=configuration,
    )
    if (WORKER_CACHE / raw.batch_id).exists():
        raise WorkerAcceptanceFailure(
            "Restart recovery did not consume its retained cache"
        )
    journal_path = recovery_journal_path(
        configuration,
        raw.batch_id,
    )
    if (
        journal_path.exists()
        or (
            TERMINAL_RECOVERY_ROOT.exists()
            and tuple(TERMINAL_RECOVERY_ROOT.iterdir())
        )
    ):
        raise WorkerAcceptanceFailure(
            "Restart recovery did not remove its terminal journal"
        )
    _assert_terminal_restart_evidence(
        bundle,
        raw,
        status=probe.expected_status,
        code=probe.expected_code,
    )

    stable_sftp = sftp_deep_snapshot(configuration)
    stable_postgres = postgres_state_snapshot(configuration)
    stable_evidence = _evidence_snapshot()
    no_work = run_worker_once(max_batches=1)
    verify_no_work_report(no_work, ignored=0)
    verify_worker_runtime(no_work, expected_max_batches=1)
    _assert_unchanged(
        expected_sftp=stable_sftp,
        expected_postgres=stable_postgres,
        expected_evidence=stable_evidence,
        configuration=configuration,
    )


def run_cache_conflict_probe(
    bundle: Path,
    raw: PublishedRaw,
    *,
    baseline_sftp: Mapping[
        str,
        tuple[tuple[str, str, int, str], ...],
    ],
    baseline_postgres: Mapping[str, tuple[str, ...]],
    baseline_evidence: Mapping[str, str],
    configuration: RuntimeConfiguration,
) -> None:
    """Prove an unsafe immutable-cache target remains a retryable batch."""

    if raw.batch_id != CACHE_CONFLICT_BATCH:
        raise WorkerAcceptanceFailure(
            "Cache-conflict probe has an unexpected identity"
        )
    cache_target = WORKER_CACHE / raw.batch_id
    try:
        cache_target.lstat()
    except FileNotFoundError:
        pass
    else:
        raise WorkerAcceptanceFailure(
            "Reserved cache-conflict target already exists"
        )

    upload_reserved_bundle(
        bundle,
        raw,
        zone="processing",
        role=configuration.operator,
        configuration=configuration,
    )
    try:
        os.symlink(
            str(bundle.resolve()),
            cache_target,
            target_is_directory=True,
        )
        metadata = cache_target.lstat()
        if (
            not stat.S_ISLNK(metadata.st_mode)
            or cache_target.readlink() != bundle.resolve()
        ):
            raise WorkerAcceptanceFailure(
                "Unsafe cache probe was not created exactly"
            )

        report = run_worker_once()
        verify_retry_cycle_report(
            report,
            batch_id=raw.batch_id,
            code="LOCAL_CACHE_CONFLICT",
            source_zone="processing",
        )
        with connect_sftp(
            configuration,
            configuration.operator,
        ) as sftp:
            _assert_remote_bundle(
                sftp,
                bundle=bundle,
                raw=raw,
                zone="processing",
                reason_code=None,
            )
        if (
            postgres_state_snapshot(configuration) != baseline_postgres
            or _directory_snapshot(EVIDENCE_ROOT) != baseline_evidence
        ):
            raise WorkerAcceptanceFailure(
                "Cache-conflict retry mutated downstream state"
            )
    finally:
        try:
            metadata = cache_target.lstat()
        except FileNotFoundError:
            pass
        else:
            if (
                not stat.S_ISLNK(metadata.st_mode)
                or cache_target.readlink() != bundle.resolve()
            ):
                raise WorkerAcceptanceFailure(
                    "Cache-conflict cleanup refused changed local state"
                )
            cache_target.unlink()
        _remove_exact_reserved_bundle(
            bundle,
            raw,
            zone="processing",
            configuration=configuration,
        )

    _assert_probe_state_restored(
        baseline_sftp=baseline_sftp,
        baseline_postgres=baseline_postgres,
        baseline_evidence=baseline_evidence,
        configuration=configuration,
    )
    if tuple(WORKER_CACHE.iterdir()):
        raise WorkerAcceptanceFailure(
            "Cache-conflict probe left local cache state"
        )


def run_quarantine_uncertain_probe(
    bundle: Path,
    raw: PublishedRaw,
    *,
    baseline_sftp: Mapping[
        str,
        tuple[tuple[str, str, int, str], ...],
    ],
    baseline_postgres: Mapping[str, tuple[str, ...]],
    baseline_evidence: Mapping[str, str],
    configuration: RuntimeConfiguration,
) -> None:
    """Prove an unverified quarantine leaves source intact and retryable."""

    if raw.batch_id != QUARANTINE_UNCERTAIN_BATCH:
        raise WorkerAcceptanceFailure(
            "Quarantine-uncertainty probe has an unexpected identity"
        )
    try:
        upload_reserved_bundle(
            bundle,
            raw,
            zone="quarantine",
            role=configuration.operator,
            configuration=configuration,
        )
        upload_reserved_bundle(
            bundle,
            raw,
            zone="incoming",
            role=configuration.operator,
            configuration=configuration,
        )
        report = run_worker_once()
        verify_retry_cycle_report(
            report,
            batch_id=raw.batch_id,
            code="QUARANTINE_UNCERTAIN",
            source_zone="incoming",
        )
        with connect_sftp(
            configuration,
            configuration.operator,
        ) as sftp:
            for zone in ("incoming", "quarantine"):
                _assert_remote_bundle(
                    sftp,
                    bundle=bundle,
                    raw=raw,
                    zone=zone,
                    reason_code=None,
                )
        if (
            postgres_state_snapshot(configuration) != baseline_postgres
            or _directory_snapshot(EVIDENCE_ROOT) != baseline_evidence
        ):
            raise WorkerAcceptanceFailure(
                "Uncertain quarantine mutated downstream state"
            )
    finally:
        _remove_exact_reserved_bundle(
            bundle,
            raw,
            zone="incoming",
            configuration=configuration,
        )
        _remove_exact_reserved_bundle(
            bundle,
            raw,
            zone="quarantine",
            configuration=configuration,
        )

    _assert_probe_state_restored(
        baseline_sftp=baseline_sftp,
        baseline_postgres=baseline_postgres,
        baseline_evidence=baseline_evidence,
        configuration=configuration,
    )


def _running_heartbeat(
    process: subprocess.Popen[str],
    *,
    timeout: float,
) -> dict[str, object]:
    """Wait for this daemon PID to publish at least one running cycle."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise WorkerAcceptanceFailure(
                "Worker daemon exited before its running heartbeat"
            )
        try:
            heartbeat = _read_json_object(WORKER_STATUS)
        except WorkerAcceptanceFailure:
            time.sleep(0.05)
            continue
        if (
            heartbeat.get("pid") == process.pid
            and heartbeat.get("state") == "running"
            and isinstance(heartbeat.get("poll_sequence"), int)
            and int(heartbeat["poll_sequence"]) >= 1
            and isinstance(heartbeat.get("last_cycle"), Mapping)
        ):
            verify_no_work_report(
                heartbeat["last_cycle"],
            )
            return heartbeat
        time.sleep(0.05)
    raise WorkerAcceptanceFailure(
        "Worker daemon did not publish a running heartbeat in time"
    )


def run_daemon_signal_probe(
    *,
    baseline_sftp: Mapping[
        str,
        tuple[tuple[str, str, int, str], ...],
    ],
    baseline_postgres: Mapping[str, tuple[str, ...]],
    baseline_evidence: Mapping[str, str],
    configuration: RuntimeConfiguration,
) -> None:
    """Start the daemon, stop it with SIGTERM, then reacquire its lock."""

    try:
        process = subprocess.Popen(
            worker_command(once=False),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=sanitized_worker_environment(),
        )
    except OSError as exc:
        raise WorkerAcceptanceFailure(
            "Worker daemon could not start"
        ) from exc

    stdout = ""
    stderr = ""
    try:
        running = _running_heartbeat(process, timeout=15)
        contender = subprocess.run(
            worker_command(once=True),
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
            env=sanitized_worker_environment(),
        )
        try:
            contender_error = json.loads(contender.stderr.strip())
        except json.JSONDecodeError as exc:
            raise WorkerAcceptanceFailure(
                "Simultaneous worker refusal was not structured"
            ) from exc
        if (
            contender.returncode != 2
            or contender.stdout.strip()
            or contender_error
            != {
                "code": "WORKER_ALREADY_RUNNING",
                "status": "worker_failed",
            }
            or process.poll() is not None
        ):
            raise WorkerAcceptanceFailure(
                "A simultaneous worker was not safely refused"
            )
        process.send_signal(signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise WorkerAcceptanceFailure(
                "Worker daemon did not stop after SIGTERM"
            ) from exc
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    if process.returncode != 0 or stderr.strip():
        raise WorkerAcceptanceFailure(
            "Worker daemon did not exit cleanly after SIGTERM"
        )
    reports: list[dict[str, object]] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorkerAcceptanceFailure(
                "Worker daemon emitted non-JSON output"
            ) from exc
        if not isinstance(value, dict):
            raise WorkerAcceptanceFailure(
                "Worker daemon emitted a non-object report"
            )
        verify_no_work_report(value)
        reports.append(value)
    if not reports:
        raise WorkerAcceptanceFailure(
            "Worker daemon emitted no completed cycle"
        )

    stopped = _read_json_object(WORKER_STATUS)
    if (
        stopped.get("pid") != process.pid
        or stopped.get("state") != "stopped"
        or stopped.get("started_at") != running.get("started_at")
        or not isinstance(stopped.get("poll_sequence"), int)
        or int(stopped["poll_sequence"]) < 1
        or not isinstance(stopped.get("last_cycle"), Mapping)
    ):
        raise WorkerAcceptanceFailure(
            "SIGTERM did not publish a stopped worker heartbeat"
        )
    verify_no_work_report(stopped["last_cycle"])

    lock_release_report = run_worker_once()
    verify_no_work_report(lock_release_report)
    verify_worker_runtime(lock_release_report)
    if (
        sftp_deep_snapshot(configuration) != baseline_sftp
        or postgres_state_snapshot(configuration) != baseline_postgres
        or _directory_snapshot(EVIDENCE_ROOT) != baseline_evidence
    ):
        raise WorkerAcceptanceFailure(
            "Daemon or lock-release cycle mutated terminal state"
        )


def _assert_unchanged(
    *,
    expected_sftp: Mapping[
        str,
        tuple[tuple[str, str, int, str], ...],
    ],
    expected_postgres: Mapping[str, tuple[str, ...]],
    expected_evidence: Mapping[str, str],
    configuration: RuntimeConfiguration,
) -> None:
    """Compare all durable boundaries after an idempotent worker cycle."""

    if (
        sftp_deep_snapshot(configuration) != expected_sftp
        or postgres_state_snapshot(configuration) != expected_postgres
        or _directory_snapshot(EVIDENCE_ROOT) != expected_evidence
    ):
        raise WorkerAcceptanceFailure(
            "Idempotent worker cycle changed durable state"
        )


def run_worker_acceptance(
    configuration: RuntimeConfiguration,
) -> None:
    """Execute the complete clean-room automatic-worker acceptance story."""

    cases = canonical_cases()
    assert_clean_start(configuration)
    catalog = generate_catalog(cases, configuration)

    source = OUTPUT_ROOT / next(
        case.batch_id
        for case in cases
        if (
            case.type_number == "01"
            and case.scenario == "valid-minimal"
        )
    )
    oracle_bundle, oracle_raw = build_reserved_type01_bundle(
        source,
        batch_id=ORACLE_MISMATCH_BATCH,
        configuration=configuration,
        corrupt_checksum=False,
    )
    restart_cases = tuple(
        case for case in cases if case.batch_id in RESTART_CANONICAL_BATCHES
    )
    if (
        len(restart_cases) != 3
        or {
            (case.type_number, case.scenario, case.expected_status)
            for case in restart_cases
        }
        != {
            ("05", "rounding-half-up", "succeeded"),
            ("01", "valid-minimal", "succeeded"),
            ("01", "malformed", "quarantined"),
        }
    ):
        raise WorkerAcceptanceFailure(
            "Canonical restart cases do not match the designed seams"
        )
    restart_by_batch = {
        case.batch_id: case for case in restart_cases
    }
    restart_probes = (
        (
            RestartProbe(
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
            ),
            OUTPUT_ROOT / DATABASE_COMMIT_RESTART_BATCH,
            catalog.raws[DATABASE_COMMIT_RESTART_BATCH],
        ),
        (
            RestartProbe(
                name="raw_archive",
                boundary="raw_archive",
                batch_id=RAW_ARCHIVE_RESTART_BATCH,
                expected_status="succeeded",
                expected_code="TERMINAL",
                intermediate_raw_zone="archive",
                intermediate_csv_zone="processing",
                intermediate_database_status=(
                    "database_committed_pending_archive"
                ),
                recovery_source_zone="cache",
                journal_route=None,
            ),
            OUTPUT_ROOT / RAW_ARCHIVE_RESTART_BATCH,
            catalog.raws[RAW_ARCHIVE_RESTART_BATCH],
        ),
        (
            RestartProbe(
                name="raw_quarantine",
                boundary="raw_quarantine",
                batch_id=RAW_QUARANTINE_RESTART_BATCH,
                expected_status="quarantined",
                expected_code=catalog.rejection_codes[
                    RAW_QUARANTINE_RESTART_BATCH
                ],
                intermediate_raw_zone="quarantine",
                intermediate_csv_zone=None,
                intermediate_database_status=None,
                recovery_source_zone="cache",
                journal_route="rejection",
            ),
            OUTPUT_ROOT / RAW_QUARANTINE_RESTART_BATCH,
            catalog.raws[RAW_QUARANTINE_RESTART_BATCH],
        ),
        (
            RestartProbe(
                name="oracle_mismatch",
                boundary="raw_quarantine",
                batch_id=ORACLE_MISMATCH_BATCH,
                expected_status="oracle_mismatch",
                expected_code="ORACLE_MISMATCH",
                intermediate_raw_zone="quarantine",
                intermediate_csv_zone="quarantine",
                intermediate_database_status=None,
                recovery_source_zone="cache",
                journal_route="oracle_mismatch",
                force_oracle_mismatch=True,
            ),
            oracle_bundle,
            oracle_raw,
        ),
    )
    for probe, bundle, raw in restart_probes:
        run_restart_probe(
            probe,
            bundle,
            raw,
            configuration=configuration,
        )

    pending_cases = tuple(
        case
        for case in cases
        if case.batch_id not in RESTART_CANONICAL_BATCHES
    )
    if (
        len(pending_cases) != 22
        or len(restart_by_batch) != 3
    ):
        raise WorkerAcceptanceFailure(
            "Bulk worker catalog was not reduced by the restart cases"
        )
    publish_catalog(pending_cases)

    bad_bundle, bad_raw = build_reserved_type01_bundle(
        source,
        batch_id=BAD_CHECKSUM_BATCH,
        configuration=configuration,
        corrupt_checksum=True,
    )
    duplicate_bundle, duplicate_raw = build_reserved_type01_bundle(
        source,
        batch_id=DUPLICATE_ZONE_BATCH,
        configuration=configuration,
        corrupt_checksum=False,
    )
    cache_bundle, cache_raw = build_reserved_type01_bundle(
        source,
        batch_id=CACHE_CONFLICT_BATCH,
        configuration=configuration,
        corrupt_checksum=False,
    )
    uncertain_bundle, uncertain_raw = build_reserved_type01_bundle(
        source,
        batch_id=QUARANTINE_UNCERTAIN_BATCH,
        configuration=configuration,
        corrupt_checksum=True,
    )
    upload_reserved_bundle(
        bad_bundle,
        bad_raw,
        zone="incoming",
        role=configuration.raw_publisher,
        configuration=configuration,
    )
    stage_incomplete_batch(configuration)
    recovery = preclaim_recovery_batch(
        pending_cases,
        catalog,
        configuration,
    )
    recovery_cache = stage_recovery_cache(
        recovery,
        catalog,
        configuration,
    )
    verify_pre_worker_sftp(
        pending_cases,
        recovery,
        restart_cases,
        oracle_raw,
        configuration,
    )

    first_report = run_worker_once()
    verify_first_cycle_report(first_report, pending_cases, recovery)
    verify_recovery_cache_consumed(recovery_cache)
    verify_worker_runtime(first_report)
    verify_terminal_sftp(
        cases,
        catalog,
        bad_bundle,
        bad_raw,
        oracle_bundle,
        oracle_raw,
        configuration,
    )
    verify_postgres_state(
        cases,
        catalog,
        oracle_raw,
        configuration,
    )
    verify_evidence(
        cases,
        catalog,
        oracle_bundle,
        oracle_raw,
    )

    stable_sftp = sftp_deep_snapshot(configuration)
    stable_postgres = postgres_state_snapshot(configuration)
    stable_evidence = _directory_snapshot(EVIDENCE_ROOT)

    second_report = run_worker_once()
    verify_no_work_report(second_report)
    verify_worker_runtime(second_report)
    _assert_unchanged(
        expected_sftp=stable_sftp,
        expected_postgres=stable_postgres,
        expected_evidence=stable_evidence,
        configuration=configuration,
    )

    run_cache_conflict_probe(
        cache_bundle,
        cache_raw,
        baseline_sftp=stable_sftp,
        baseline_postgres=stable_postgres,
        baseline_evidence=stable_evidence,
        configuration=configuration,
    )
    run_quarantine_uncertain_probe(
        uncertain_bundle,
        uncertain_raw,
        baseline_sftp=stable_sftp,
        baseline_postgres=stable_postgres,
        baseline_evidence=stable_evidence,
        configuration=configuration,
    )
    run_duplicate_zone_probe(
        duplicate_bundle,
        duplicate_raw,
        baseline_sftp=stable_sftp,
        baseline_postgres=stable_postgres,
        baseline_evidence=stable_evidence,
        configuration=configuration,
    )
    run_daemon_signal_probe(
        baseline_sftp=stable_sftp,
        baseline_postgres=stable_postgres,
        baseline_evidence=stable_evidence,
        configuration=configuration,
    )


def main() -> int:
    """Run the live suite without cleaning or repairing pre-existing state."""

    try:
        configuration = RuntimeConfiguration.load()
        run_worker_acceptance(configuration)
    except WorkerAcceptanceFailure as exc:
        print(f"worker acceptance failed: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print(
            "worker acceptance failed at an unexpected private boundary",
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            {
                "canonical_quarantines": 10,
                "canonical_successes": 15,
                "cache_conflict": "verified_retry",
                "daemon_sigterm": "verified",
                "integrity_quarantines": 1,
                "lock_contention": "verified",
                "oracle_mismatches": 1,
                "quarantine_uncertainty": "verified_retry",
                "retained_cache_replay": "verified",
                "restart_database_commit": "verified",
                "restart_oracle_mismatch": "verified",
                "restart_raw_archive": "verified",
                "restart_raw_quarantine": "verified",
                "status": "passed",
                "worker_cases": 25,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
