"""Validate DataGen bundles and publish them to raw SFTP manifest-last."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from config import RuntimeConfiguration
from sftp_client import (
    SftpBoundaryError,
    connect_sftp,
    exists,
    mkdir_exact,
    upload_manifest_last,
)


class RawPublicationError(Exception):
    """A generated bundle is not safe to publish."""


CHECKSUM_PATTERN = re.compile(
    rb"(?P<digest>[0-9a-f]{64})  (?P<filename>[^/\r\n]+)\n"
)


@dataclass(frozen=True, slots=True)
class PublishedRaw:
    """Verified source identity transported through the raw SFTP boundary.

    ``source_controls`` contains only the privacy-safe scalar controls from the
    executable manifest. The compatibility properties expose the common count
    and net controls used by the original Type 01 loader.
    """

    batch_id: str
    file_type: str
    filename: str
    sha256: str
    size_bytes: int
    manifest_sha256: str
    source_controls: Mapping[str, int | str]

    def __post_init__(self) -> None:
        """Defensively freeze the caller-provided controls mapping."""

        object.__setattr__(
            self,
            "source_controls",
            MappingProxyType(dict(self.source_controls)),
        )

    @property
    def source_count(self) -> int:
        """Return the type's primary business-row count control."""

        for name in (
            "detail_count",
            "event_count",
            "logical_count",
            "transfer_count",
            "assessment_count",
            "row_count",
        ):
            value = self.source_controls.get(name)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        raise RawPublicationError(
            f"Type {self.file_type} has no primary count control"
        )

    @property
    def source_net_amount(self) -> str:
        """Return the legacy control plane's compatibility money scalar.

        Types 01-04 expose a true net amount. Type 05 has no net concept, so
        its assessed fee is the explicit compatibility projection. Type 06
        projects chargeback amount the same way. The full immutable
        ``source_controls`` mapping remains authoritative.
        """

        value = self.source_controls.get("net_amount")
        if value is None and self.file_type == "05":
            value = self.source_controls.get("assessed_fee")
        if value is None and self.file_type == "06":
            value = self.source_controls.get("chargeback_amount")
        if not isinstance(value, str):
            raise RawPublicationError(
                f"Type {self.file_type} has no compatibility money control"
            )
        return value


def sha256(content: bytes) -> str:
    """Return the lowercase SHA-256 identity of one immutable artifact."""

    return hashlib.sha256(content).hexdigest()


def validate_bundle(
    bundle_directory: Path,
    *,
    configuration: RuntimeConfiguration,
) -> PublishedRaw:
    """Validate a local bundle against schema, sidecar, bytes, and path.

    This function is read-only. It returns only privacy-safe identity and
    aggregate controls; raw file contents are never attached to the result.
    """

    if not bundle_directory.is_dir():
        raise RawPublicationError("Generated bundle directory does not exist")

    manifest_path = bundle_directory / "source-manifest.json"
    try:
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
    except (OSError, json.JSONDecodeError) as exc:
        raise RawPublicationError("Source manifest cannot be loaded safely") from exc
    except Exception as exc:
        raise RawPublicationError("Source manifest violates its executable schema") from exc

    batch_id = manifest["batch_id"]
    filename = manifest["source_file"]["name"]
    raw_path = bundle_directory / filename
    checksum_path = bundle_directory / f"{filename}.sha256"
    try:
        raw_bytes = raw_path.read_bytes()
        checksum_bytes = checksum_path.read_bytes()
    except OSError as exc:
        raise RawPublicationError("Generated bundle is incomplete") from exc

    digest = sha256(raw_bytes)
    checksum_match = CHECKSUM_PATTERN.fullmatch(checksum_bytes)
    if (
        digest != manifest["source_file"]["sha256"]
        or len(raw_bytes) != manifest["source_file"]["size_bytes"]
        or checksum_match is None
        or checksum_match.group("digest").decode("ascii") != digest
        or checksum_match.group("filename").decode("ascii") != filename
        or bundle_directory.name != batch_id
    ):
        raise RawPublicationError("Generated bundle integrity validation failed")

    return PublishedRaw(
        batch_id=batch_id,
        file_type=manifest["file_type"]["number"],
        filename=filename,
        sha256=digest,
        size_bytes=len(raw_bytes),
        manifest_sha256=sha256(manifest_bytes),
        source_controls=manifest["source_controls"],
    )


def publish_bundle(
    bundle_directory: Path,
    *,
    configuration: RuntimeConfiguration,
) -> PublishedRaw:
    """Publish a new immutable raw batch through SFTP.

    The data and checksum are finalized before ``source-manifest.json``, which
    is the readiness marker. Any batch ID already visible in a lifecycle zone
    is rejected instead of overwritten.
    """

    published = validate_bundle(
        bundle_directory,
        configuration=configuration,
    )
    with connect_sftp(configuration, configuration.operator) as sftp:
        for zone in (
            "/raw/incoming",
            "/raw/processing",
            "/raw/quarantine",
            "/raw/archive",
        ):
            if exists(sftp, f"{zone}/{published.batch_id}"):
                raise RawPublicationError(
                    f"Batch ID already exists in the raw lifecycle: {published.batch_id}"
                )
    remote_directory = f"/raw/incoming/{published.batch_id}"
    with connect_sftp(configuration, configuration.raw_publisher) as sftp:
        mkdir_exact(sftp, remote_directory)
        try:
            upload_manifest_last(
                sftp,
                remote_directory,
                (
                    (published.filename, bundle_directory / published.filename),
                    (
                        f"{published.filename}.sha256",
                        bundle_directory / f"{published.filename}.sha256",
                    ),
                    (
                        "source-manifest.json",
                        bundle_directory / "source-manifest.json",
                    ),
                ),
                manifest_name="source-manifest.json",
            )
        except SftpBoundaryError:
            try:
                sftp.rmdir(remote_directory)
            except OSError:
                pass
            raise
    return published
