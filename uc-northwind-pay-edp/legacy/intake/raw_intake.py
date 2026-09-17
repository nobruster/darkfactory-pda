"""Claim, archive, or quarantine ready raw batches through SFTP."""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import paramiko  # type: ignore[import-untyped]
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from config import RuntimeConfiguration
from raw_publisher import CHECKSUM_PATTERN
from sftp_client import (
    SftpBoundaryError,
    connect_sftp,
    exists,
    move_batch,
    write_safe_json,
)


class RawIntakeError(Exception):
    """A ready raw batch failed intake validation."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        quarantine_verified: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.quarantine_verified = quarantine_verified


@dataclass(frozen=True, slots=True)
class ClaimedRaw:
    """Integrity-verified raw identity after an atomic SFTP claim."""

    batch_id: str
    file_type: str
    filename: str
    sha256: str
    manifest_sha256: str


def claim_batch(
    batch_id: str,
    *,
    configuration: RuntimeConfiguration,
) -> ClaimedRaw:
    """Validate a manifest-ready batch and atomically claim it for Java.

    A validation failure quarantines only this batch with a privacy-safe code.
    The returned identity contains no source record content.
    """

    incoming = f"/raw/incoming/{batch_id}"
    with connect_sftp(configuration, configuration.processor) as sftp:
        manifest_remote = f"{incoming}/source-manifest.json"
        if not exists(sftp, manifest_remote):
            raise RawIntakeError(
                "BATCH_NOT_READY",
                "Batch has no final readiness manifest",
            )

        try:
            with tempfile.TemporaryDirectory(prefix="northwind-intake-") as temporary:
                temporary_root = Path(temporary)
                manifest_path = temporary_root / "source-manifest.json"
                sftp.get(manifest_remote, str(manifest_path))
                manifest_bytes = manifest_path.read_bytes()
                manifest = json.loads(manifest_bytes)
                schema = json.loads(
                    (
                        configuration.root
                        / "contracts"
                        / "common"
                        / "source-manifest.schema.json"
                    ).read_text(encoding="utf-8")
                )
                Draft202012Validator(schema).validate(manifest)
                if manifest["batch_id"] != batch_id:
                    raise RawIntakeError(
                        "BATCH_ID_MISMATCH",
                        "Manifest batch ID does not match its SFTP path",
                    )

                filename = manifest["source_file"]["name"]
                raw_path = temporary_root / filename
                checksum_path = temporary_root / f"{filename}.sha256"
                sftp.get(f"{incoming}/{filename}", str(raw_path))
                sftp.get(f"{incoming}/{filename}.sha256", str(checksum_path))
                raw_bytes = raw_path.read_bytes()
                checksum = CHECKSUM_PATTERN.fullmatch(checksum_path.read_bytes())
                digest = hashlib.sha256(raw_bytes).hexdigest()
                if (
                    checksum is None
                    or digest != manifest["source_file"]["sha256"]
                    or len(raw_bytes) != manifest["source_file"]["size_bytes"]
                    or checksum.group("digest").decode("ascii") != digest
                    or checksum.group("filename").decode("ascii") != filename
                ):
                    raise RawIntakeError(
                        "SOURCE_INTEGRITY_ERROR",
                        "Ready raw artifacts fail integrity validation",
                    )

                move_batch(
                    sftp,
                    batch_id,
                    source_zone="/raw/incoming",
                    target_zone="/raw/processing",
                )
                return ClaimedRaw(
                    batch_id=batch_id,
                    file_type=manifest["file_type"]["number"],
                    filename=filename,
                    sha256=digest,
                    manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                )
        except RawIntakeError as exc:
            try:
                quarantine_batch(
                    sftp,
                    batch_id,
                    source_zone="/raw/incoming",
                    code=exc.code,
                )
            except SftpBoundaryError as quarantine_error:
                exc.add_note(
                    "The original intake rejection was preserved, but "
                    f"quarantine finalization also failed: {quarantine_error}"
                )
            else:
                exc.quarantine_verified = True
            raise
        except Exception as exc:
            intake_error = RawIntakeError(
                "RAW_INTAKE_REJECTED",
                "Ready raw batch failed safe intake validation",
            )
            try:
                quarantine_batch(
                    sftp,
                    batch_id,
                    source_zone="/raw/incoming",
                    code=intake_error.code,
                )
            except SftpBoundaryError as quarantine_error:
                intake_error.add_note(
                    "The original intake rejection was preserved, but "
                    f"quarantine finalization also failed: {quarantine_error}"
                )
            else:
                intake_error.quarantine_verified = True
            raise intake_error from exc


def quarantine_processing_batch(
    batch_id: str,
    *,
    code: str,
    configuration: RuntimeConfiguration,
) -> None:
    """Move a claimed raw batch to quarantine with a safe reason artifact."""

    with connect_sftp(configuration, configuration.processor) as sftp:
        quarantine_batch(
            sftp,
            batch_id,
            source_zone="/raw/processing",
            code=code,
        )


def archive_processing_batch(
    batch_id: str,
    *,
    configuration: RuntimeConfiguration,
) -> None:
    """Archive a successfully reconciled raw batch without reading its bytes."""

    with connect_sftp(configuration, configuration.operator) as sftp:
        move_batch(
            sftp,
            batch_id,
            source_zone="/raw/processing",
            target_zone="/raw/archive",
        )


def quarantine_batch(
    sftp: paramiko.SFTPClient,
    batch_id: str,
    *,
    source_zone: str,
    code: str,
) -> None:
    """Finalize one SFTP quarantine and write its manifest-last reason."""

    try:
        source = f"{source_zone}/{batch_id}"
        target = f"/raw/quarantine/{batch_id}"
        reason = f"{target}/quarantine-reason.json"
        move_batch(
            sftp,
            batch_id,
            source_zone=source_zone,
            target_zone="/raw/quarantine",
        )
        write_safe_json(
            sftp,
            reason,
            {
                "batch_id": batch_id,
                "code": code,
                "scope": "batch",
                "status": "quarantined",
            },
        )
        if exists(sftp, source) or not exists(sftp, target) or not exists(
            sftp,
            reason,
        ):
            raise SftpBoundaryError(
                "SFTP quarantine terminal state could not be verified"
            )
    except SftpBoundaryError:
        raise
    except OSError as exc:
        raise SftpBoundaryError(
            "SFTP quarantine terminal state could not be verified"
        ) from exc
