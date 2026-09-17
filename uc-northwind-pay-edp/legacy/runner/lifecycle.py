from __future__ import annotations

import errno
import hashlib
import json
import re
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal

import psycopg
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from config import RuntimeConfiguration
from raw_publisher import PublishedRaw, validate_bundle
from sftp_client import connect_sftp, exists, write_safe_json


class LifecycleError(Exception):
    """Durable batch state is ambiguous or does not match its identity."""


RAW_ZONES = ("incoming", "processing", "quarantine", "archive")
CSV_ZONES = ("outgoing", "processing", "quarantine", "archive")
CHECKSUM_PATTERN = re.compile(
    rb"(?P<digest>[0-9a-f]{64})  (?P<filename>[^/\r\n]+)\n"
)
SAFE_CODE_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{2,63}\Z")
SAFE_BATCH_PATTERN = re.compile(r"B[0-9]{15}\Z")
MAX_QUARANTINE_REASON_BYTES = 2 * 1024


@dataclass(frozen=True, slots=True)
class LifecycleState:
    raw_zone: str | None
    csv_zone: str | None
    database_status: str | None
    failure_code: str | None


def ensure_remote_quarantine_reason(
    batch_id: str,
    *,
    plane: Literal["raw", "csv"],
    code: str,
    configuration: RuntimeConfiguration,
) -> None:
    """Create if absent, then verify, bounded manifest-last quarantine metadata.

    This is the idempotent completion step for the narrow failure window where
    an SFTP directory move succeeded but its safe reason artifact did not.
    Existing metadata is never replaced and must match the requested identity.
    """

    if (
        SAFE_BATCH_PATTERN.fullmatch(batch_id) is None
        or SAFE_CODE_PATTERN.fullmatch(code) is None
    ):
        raise LifecycleError("Quarantine reason identity is unsafe")
    role = (
        configuration.processor
        if plane == "raw"
        else configuration.loader
    )
    target = f"/{plane}/quarantine/{batch_id}"
    reason_path = f"{target}/quarantine-reason.json"
    expected = {
        "batch_id": batch_id,
        "code": code,
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
    with connect_sftp(configuration, role) as sftp:
        try:
            target_metadata = sftp.lstat(target)
        except OSError as exc:
            raise LifecycleError(
                "Quarantine directory is missing after terminal move"
            ) from exc
        if (
            not isinstance(target_metadata.st_mode, int)
            or not stat.S_ISDIR(target_metadata.st_mode)
        ):
            raise LifecycleError(
                "Quarantine target is not a real directory"
            )

        try:
            reason_metadata = sftp.lstat(reason_path)
        except OSError as exc:
            if exc.errno not in {errno.ENOENT, 2}:
                raise LifecycleError(
                    "Quarantine reason cannot be inspected safely"
                ) from exc
            reason_metadata = None
        if reason_metadata is None:
            part_path = f"{reason_path}.part"
            try:
                part_metadata = sftp.lstat(part_path)
            except OSError as exc:
                if exc.errno not in {errno.ENOENT, 2}:
                    raise LifecycleError(
                        "Quarantine reason part cannot be inspected safely"
                    ) from exc
                part_metadata = None
            if part_metadata is not None:
                if (
                    not isinstance(part_metadata.st_mode, int)
                    or not stat.S_ISREG(part_metadata.st_mode)
                    or stat.S_IMODE(part_metadata.st_mode) & 0o022
                    or not isinstance(part_metadata.st_size, int)
                    or part_metadata.st_size < 0
                    or part_metadata.st_size
                    > MAX_QUARANTINE_REASON_BYTES
                ):
                    raise LifecycleError(
                        "Quarantine reason part is not a bounded regular file"
                    )
                try:
                    with sftp.file(part_path, "r") as stream:
                        part_content = stream.read(
                            MAX_QUARANTINE_REASON_BYTES + 1
                        )
                    part_bytes = (
                        part_content.encode("utf-8")
                        if isinstance(part_content, str)
                        else bytes(part_content)
                    )
                    if part_bytes == expected_bytes:
                        sftp.posix_rename(part_path, reason_path)
                    else:
                        sftp.remove(part_path)
                except OSError as exc:
                    raise LifecycleError(
                        "Quarantine reason part cannot be recovered safely"
                    ) from exc
            try:
                reason_metadata = sftp.lstat(reason_path)
            except OSError as exc:
                if exc.errno not in {errno.ENOENT, 2}:
                    raise LifecycleError(
                        "Quarantine reason cannot be inspected safely"
                    ) from exc
                reason_metadata = None
        if reason_metadata is None:
            write_safe_json(sftp, reason_path, expected)
        try:
            metadata = sftp.lstat(reason_path)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_size < 1
                or metadata.st_size > MAX_QUARANTINE_REASON_BYTES
            ):
                raise ValueError("unsafe quarantine reason metadata")
            with sftp.file(reason_path, "r") as stream:
                content = stream.read(MAX_QUARANTINE_REASON_BYTES + 1)
            if isinstance(content, str):
                encoded = content.encode("utf-8")
            else:
                encoded = bytes(content)
            if len(encoded) > MAX_QUARANTINE_REASON_BYTES:
                raise ValueError("oversized quarantine reason")
            observed = json.loads(encoded)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LifecycleError(
                "Quarantine reason cannot be verified safely"
            ) from exc
    if observed != expected:
        raise LifecycleError(
            "Quarantine reason disagrees with terminal recovery intent"
        )


def inspect_lifecycle(
    raw: PublishedRaw,
    *,
    configuration: RuntimeConfiguration,
) -> LifecycleState:
    with connect_sftp(configuration, configuration.operator) as sftp:
        raw_zones = [
            zone
            for zone in RAW_ZONES
            if exists(sftp, f"/raw/{zone}/{raw.batch_id}")
        ]
        csv_zones = [
            zone
            for zone in CSV_ZONES
            if exists(sftp, f"/csv/{zone}/{raw.batch_id}")
        ]
    if len(raw_zones) > 1 or len(csv_zones) > 1:
        raise LifecycleError("Batch exists in multiple SFTP lifecycle zones")

    try:
        with psycopg.connect(configuration.postgres_dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        file_type,
                        source_filename,
                        source_sha256,
                        source_manifest_sha256,
                        source_count,
                        source_net_amount,
                        source_controls,
                        status,
                        failure_code
                      FROM control.batches
                     WHERE batch_id = %s
                    """,
                    (raw.batch_id,),
                )
                database = cursor.fetchone()
    except psycopg.Error as exc:
        raise LifecycleError("Cannot inspect PostgreSQL lifecycle state") from exc

    if database is None:
        database_status = None
        failure_code = None
    else:
        database_controls = database[6]
        if (
            database[:6]
            != (
                raw.file_type,
                raw.filename,
                raw.sha256,
                raw.manifest_sha256,
                raw.source_count,
                Decimal(raw.source_net_amount),
            )
            or not isinstance(database_controls, Mapping)
            or dict(database_controls) != dict(raw.source_controls)
        ):
            raise LifecycleError(
                "Batch ID exists in PostgreSQL with different source identity"
            )
        database_status = str(database[7])
        failure_code = database[8]

    return LifecycleState(
        raw_zone=raw_zones[0] if raw_zones else None,
        csv_zone=csv_zones[0] if csv_zones else None,
        database_status=database_status,
        failure_code=failure_code,
    )


def verify_remote_raw(
    raw: PublishedRaw,
    *,
    zone: str,
    configuration: RuntimeConfiguration,
) -> None:
    if zone not in RAW_ZONES:
        raise LifecycleError("Raw lifecycle zone is invalid")
    with tempfile.TemporaryDirectory(prefix="northwind-resume-raw-") as temporary:
        bundle = Path(temporary) / raw.batch_id
        bundle.mkdir(mode=0o700)
        remote = f"/raw/{zone}/{raw.batch_id}"
        with connect_sftp(configuration, configuration.operator) as sftp:
            for name in (
                raw.filename,
                f"{raw.filename}.sha256",
                "source-manifest.json",
            ):
                sftp.get(f"{remote}/{name}", str(bundle / name))
        observed = validate_bundle(bundle, configuration=configuration)
    if observed != raw:
        raise LifecycleError("Remote raw batch differs from the local source")


def read_sanitized_observation(
    raw: PublishedRaw,
    *,
    zone: str,
    configuration: RuntimeConfiguration,
) -> dict[str, object]:
    if zone not in CSV_ZONES:
        raise LifecycleError("CSV lifecycle zone is invalid")
    with tempfile.TemporaryDirectory(prefix="northwind-resume-csv-") as temporary:
        root = Path(temporary)
        manifest_path = root / "sanitized-manifest.json"
        remote = f"/csv/{zone}/{raw.batch_id}"
        with connect_sftp(configuration, configuration.operator) as sftp:
            sftp.get(
                f"{remote}/sanitized-manifest.json",
                str(manifest_path),
            )
            try:
                manifest = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )
                schema = json.loads(
                    (
                        configuration.root
                        / "contracts"
                        / "common"
                        / "sanitized-manifest.schema.json"
                    ).read_text(encoding="utf-8")
                )
                Draft202012Validator(schema).validate(manifest)
            except Exception as exc:
                raise LifecycleError(
                    "Sanitized recovery manifest is invalid"
                ) from exc

            filename = manifest["csv_file"]["name"]
            csv_path = root / filename
            checksum_path = root / f"{filename}.sha256"
            sftp.get(f"{remote}/{filename}", str(csv_path))
            sftp.get(
                f"{remote}/{filename}.sha256",
                str(checksum_path),
            )

        content = csv_path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        checksum = CHECKSUM_PATTERN.fullmatch(checksum_path.read_bytes())
        if (
            manifest["batch_id"] != raw.batch_id
            or manifest["file_type"]["number"] != raw.file_type
            or manifest["source_lineage"]["raw_file"] != raw.filename
            or manifest["source_lineage"]["raw_sha256"] != raw.sha256
            or manifest["source_lineage"]["manifest_sha256"]
            != raw.manifest_sha256
            or digest != manifest["csv_file"]["sha256"]
            or len(content) != manifest["csv_file"]["size_bytes"]
            or checksum is None
            or checksum.group("digest").decode("ascii") != digest
            or checksum.group("filename").decode("ascii") != filename
        ):
            raise LifecycleError(
                "Sanitized recovery artifacts fail identity validation"
            )

    return _build_sanitized_observation(
        raw,
        manifest=manifest,
        filename=filename,
        digest=digest,
    )


def _build_sanitized_observation(
    raw: PublishedRaw,
    *,
    manifest: Mapping[str, object],
    filename: str,
    digest: str,
) -> dict[str, object]:
    """Build one typed aggregate observation from a validated manifest."""

    stage_controls = manifest.get("stage_controls")
    if not isinstance(stage_controls, Mapping):
        raise LifecycleError(
            "Sanitized recovery manifest has invalid stage controls"
        )

    common: dict[str, object] = {
        "batch_id": raw.batch_id,
        "code": None,
        "csv_file": filename,
        "csv_sha256": digest,
        "status": "succeeded",
    }
    try:
        if raw.file_type == "01":
            return {
                **common,
                "net_amount": stage_controls["net_amount"],
                "record_number": None,
                "row_count": stage_controls["row_count"],
                "transaction_id": None,
            }
        if raw.file_type == "02":
            return {
                **common,
                "credit_amount": stage_controls["credit_amount"],
                "debit_amount": stage_controls["debit_amount"],
                "net_amount": stage_controls["net_amount"],
                "returned_count": stage_controls["returned_count"],
                "row_count": stage_controls["row_count"],
            }
        if raw.file_type == "03":
            return {
                **common,
                "discount_amount": stage_controls["discount_amount"],
                "face_amount": stage_controls["face_amount"],
                "fee_amount": stage_controls["fee_amount"],
                "net_amount": stage_controls["net_amount"],
                "orphan_segment_count": stage_controls[
                    "orphan_segment_count"
                ],
                "row_count": stage_controls["row_count"],
            }
        if raw.file_type == "04":
            return {
                **common,
                "gross_amount": stage_controls["gross_amount"],
                "net_amount": stage_controls["net_amount"],
                "return_amount": stage_controls["return_amount"],
                "return_count": stage_controls["return_count"],
                "row_count": stage_controls["row_count"],
                "transfer_count": stage_controls["transfer_count"],
            }
        if raw.file_type == "05":
            return {
                **common,
                "assessed_fee": stage_controls["assessed_fee"],
                "calculated_fee": stage_controls["calculated_fee"],
                "gross_amount": stage_controls["gross_amount"],
                "row_count": stage_controls["row_count"],
            }
    except KeyError as exc:
        raise LifecycleError(
            "Sanitized recovery manifest has incomplete stage controls"
        ) from exc

    raise LifecycleError("Sanitized recovery file type is unsupported")


def verify_terminal_state(
    state: LifecycleState,
    *,
    final_status: str,
) -> None:
    expected: tuple[str | None, str | None, str | None]
    if final_status == "succeeded":
        expected = ("archive", "archive", "succeeded")
    elif final_status == "quarantined":
        expected = ("quarantine", None, "quarantined")
    elif final_status == "oracle_mismatch":
        if state.csv_zone not in {None, "quarantine"}:
            raise LifecycleError(
                "Oracle-mismatch CSV is not safely quarantined"
            )
        expected = (
            "quarantine",
            state.csv_zone,
            "oracle_mismatch",
        )
    else:
        raise LifecycleError("Evidence terminal status is unsupported")
    actual = (state.raw_zone, state.csv_zone, state.database_status)
    if actual != expected:
        raise LifecycleError(
            "Terminal evidence disagrees with live SFTP/PostgreSQL state"
        )
