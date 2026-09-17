"""Continuously dispatch manifest-ready SFTP batches through typed workflows."""

from __future__ import annotations

import argparse
import errno
import fcntl
import json
import os
import re
import shutil
import signal
import stat
import sys
import tempfile
import threading
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from types import FrameType, TracebackType
from typing import Iterator

import paramiko  # type: ignore[import-untyped]


ROOT = Path(__file__).resolve().parents[2]
for module_directory in (
    ROOT / "legacy" / "runner",
    ROOT / "legacy" / "publisher",
    ROOT / "legacy" / "intake",
    ROOT / "legacy" / "postgres",
    ROOT / "validation" / "oracle",
):
    sys.path.insert(0, str(module_directory))

from config import (  # noqa: E402
    RuntimeConfiguration,
    RuntimeConfigurationError,
)
from raw_intake import (  # noqa: E402
    ClaimedRaw,
    RawIntakeError,
    claim_batch,
    quarantine_batch,
    quarantine_processing_batch,
)
from raw_publisher import (  # noqa: E402
    PublishedRaw,
    RawPublicationError,
    validate_bundle,
)
from sftp_client import (  # noqa: E402
    SftpBoundaryError,
    connect_sftp,
)
from workflow import run_pipeline  # noqa: E402
from workflow_registry import workflow_for_type  # noqa: E402


BATCH_ID_PATTERN = re.compile(r"B[0-9]{15}\Z")
TYPE_NUMBER_PATTERN = re.compile(r"[0-9]{2}\Z")
SAFE_CODE_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")
RAW_ZONES = ("processing", "incoming")
CANDIDATE_ZONES = (*RAW_ZONES, "cache")
TERMINAL_STATUSES = {"succeeded", "quarantined", "oracle_mismatch"}

MAX_REMOTE_DIRECTORY_ENTRIES = 4096
MAX_CACHE_DIRECTORY_ENTRIES = 4096
MAX_BATCHES_PER_CYCLE = 100
MAX_MANIFEST_BYTES = 64 * 1024
MAX_CHECKSUM_BYTES = 512
MAX_RAW_BYTES = 64 * 1024 * 1024
MAX_SOURCE_FILENAME_BYTES = 255
MIN_POLL_INTERVAL_SECONDS = 0.1
MAX_POLL_INTERVAL_SECONDS = 3600.0
DEFAULT_POLL_INTERVAL_SECONDS = 5.0


class WorkerError(Exception):
    """The automatic worker cannot continue safely."""


class WorkerAlreadyRunningError(WorkerError):
    """Another host worker holds the private process lock."""


class WorkerSourceRejected(WorkerError):
    """A deterministic source envelope violates worker safety bounds."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class WorkerCacheConflict(WorkerError):
    """An immutable local cache path contains different source bytes."""


@dataclass(frozen=True, slots=True)
class BatchCandidate:
    """One safe batch identity discovered in SFTP or retained local cache."""

    batch_id: str
    zone: str
    zone_ambiguous: bool = False

    def __post_init__(self) -> None:
        if BATCH_ID_PATTERN.fullmatch(self.batch_id) is None:
            raise ValueError("Worker candidate batch ID is unsafe")
        if self.zone not in CANDIDATE_ZONES:
            raise ValueError("Worker candidate zone is unsupported")
        if not isinstance(self.zone_ambiguous, bool):
            raise ValueError("Worker candidate ambiguity flag is invalid")
        if self.zone == "cache" and self.zone_ambiguous:
            raise ValueError("A cache candidate cannot have SFTP ambiguity")


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Bounded deterministic view of SFTP work and retained recoveries."""

    candidates: tuple[BatchCandidate, ...]
    ready_count: int
    deferred_count: int
    ignored_count: int


@dataclass(frozen=True, slots=True)
class BatchOutcome:
    """Privacy-safe result for one independently handled batch."""

    batch_id: str
    source_zone: str
    status: str
    code: str
    file_type: str | None = None

    def as_dict(self) -> dict[str, object]:
        """Return only safe identity and aggregate outcome fields."""

        value: dict[str, object] = {
            "batch_id": self.batch_id,
            "code": self.code,
            "source_zone": self.source_zone,
            "status": self.status,
        }
        if self.file_type is not None:
            value["file_type"] = self.file_type
        return value


@dataclass(frozen=True, slots=True)
class CycleReport:
    """Privacy-safe aggregate report for one polling iteration."""

    started_at: str
    finished_at: str
    ready_count: int
    deferred_count: int
    ignored_count: int
    outcomes: tuple[BatchOutcome, ...]
    error_code: str | None = None

    @property
    def status(self) -> str:
        """Return whether queue discovery itself completed."""

        return "error" if self.error_code is not None else "completed"

    def summary(self) -> dict[str, int]:
        """Count safe batch outcomes without exposing source values."""

        summary = {
            "deferred": self.deferred_count,
            "discovered": self.ready_count,
            "ignored": self.ignored_count,
            "not_ready": 0,
            "oracle_mismatch": 0,
            "processed": len(self.outcomes),
            "quarantined": 0,
            "retry_pending": 0,
            "succeeded": 0,
        }
        for outcome in self.outcomes:
            if outcome.status in summary:
                summary[outcome.status] += 1
        return summary

    def as_dict(self) -> dict[str, object]:
        """Serialize the report without raw records or exception messages."""

        value: dict[str, object] = {
            "batches": [outcome.as_dict() for outcome in self.outcomes],
            "finished_at": self.finished_at,
            "started_at": self.started_at,
            "status": self.status,
            "summary": self.summary(),
        }
        if self.error_code is not None:
            value["error_code"] = self.error_code
        return value


def utc_now() -> str:
    """Return a canonical UTC heartbeat timestamp."""

    return datetime.now(UTC).isoformat(timespec="seconds").replace(
        "+00:00",
        "Z",
    )


def _safe_code(value: object, *, fallback: str) -> str:
    """Allow only bounded machine codes in logs and status artifacts."""

    if isinstance(value, str) and SAFE_CODE_PATTERN.fullmatch(value):
        return value
    return fallback


def _safe_type_number(value: object) -> str | None:
    """Return a bounded type label or omit it from public outcomes."""

    if isinstance(value, str) and TYPE_NUMBER_PATTERN.fullmatch(value):
        return value
    return None


def _is_safe_source_filename(value: object) -> bool:
    """Reject remote names capable of escaping one batch directory."""

    if not isinstance(value, str):
        return False
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    path = PurePosixPath(value)
    return (
        0 < len(encoded) <= MAX_SOURCE_FILENAME_BYTES
        and value not in {".", "..", "source-manifest.json"}
        and "\x00" not in value
        and "\\" not in value
        and path.name == value
        and not path.is_absolute()
    )


def _ensure_private_directory(path: Path) -> None:
    """Create or verify a real directory and restrict it to its owner."""

    try:
        if path.exists():
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise WorkerError("Private worker path is not a directory")
        else:
            path.mkdir(mode=0o700, parents=True)
        path.chmod(0o700)
    except OSError as exc:
        raise WorkerError("Cannot establish a private worker directory") from exc


def _runtime_path(configuration: RuntimeConfiguration, name: str) -> Path:
    """Resolve one fixed private runtime child without caller path input."""

    root = Path(configuration.root).resolve()
    runtime_root = root / ".runtime"
    if runtime_root.parent != root:
        raise WorkerError("Worker runtime path escaped the repository")
    _ensure_private_directory(runtime_root)
    target = runtime_root / name
    if target.parent != runtime_root:
        raise WorkerError("Worker runtime child path is unsafe")
    return target


def _remote_regular_file(
    sftp: paramiko.SFTPClient,
    remote_path: str,
) -> bool:
    """Return readiness only for a final regular SFTP artifact."""

    try:
        attributes = sftp.lstat(remote_path)
    except OSError as exc:
        if exc.errno in {errno.ENOENT, 2}:
            return False
        raise
    mode = attributes.st_mode
    return isinstance(mode, int) and stat.S_ISREG(mode)


def _ready_in_zone(
    sftp: paramiko.SFTPClient,
    zone: str,
) -> tuple[tuple[BatchCandidate, ...], int]:
    """Discover safe directories containing the final readiness manifest."""

    remote_zone = f"/raw/{zone}"
    attributes = sftp.listdir_attr(remote_zone)
    if len(attributes) > MAX_REMOTE_DIRECTORY_ENTRIES:
        raise WorkerError("SFTP discovery exceeded its bounded directory size")

    candidates: list[BatchCandidate] = []
    ignored = 0
    for attribute in attributes:
        name = attribute.filename
        mode = attribute.st_mode
        if (
            not isinstance(name, str)
            or BATCH_ID_PATTERN.fullmatch(name) is None
            or not isinstance(mode, int)
            or not stat.S_ISDIR(mode)
        ):
            ignored += 1
            continue
        manifest = f"{remote_zone}/{name}/source-manifest.json"
        if not _remote_regular_file(sftp, manifest):
            ignored += 1
            continue
        candidates.append(BatchCandidate(name, zone))
    return tuple(sorted(candidates, key=lambda item: item.batch_id)), ignored


def _ready_in_cache(
    configuration: RuntimeConfiguration,
) -> tuple[tuple[BatchCandidate, ...], int]:
    """Discover bounded cache identities without trusting their contents.

    Exact artifact, privacy, ownership, link, size, and schema validation is
    intentionally deferred to per-batch dispatch. That keeps one unsafe cache
    bundle isolated as ``LOCAL_CACHE_CONFLICT`` instead of blocking unrelated
    recoveries during queue discovery.
    """

    cache_root = _runtime_path(configuration, "intake-cache")
    try:
        cache_root.lstat()
    except FileNotFoundError:
        return (), 0
    except OSError as exc:
        raise WorkerError("Worker cache root cannot be inspected") from exc

    _require_private_cache_directory(cache_root)
    try:
        entries = tuple(cache_root.iterdir())
    except OSError as exc:
        raise WorkerError("Worker cache contents cannot be inspected") from exc
    if len(entries) > MAX_CACHE_DIRECTORY_ENTRIES:
        raise WorkerError(
            "Worker cache discovery exceeded its bounded directory size"
        )

    candidates: list[BatchCandidate] = []
    ignored = 0
    for entry in entries:
        if BATCH_ID_PATTERN.fullmatch(entry.name) is None:
            ignored += 1
            continue
        candidates.append(BatchCandidate(entry.name, "cache"))
    return tuple(sorted(candidates, key=lambda item: item.batch_id)), ignored


def discover_ready_batches(
    *,
    configuration: RuntimeConfiguration,
    max_batches: int = MAX_BATCHES_PER_CYCLE,
) -> DiscoveryResult:
    """Find processing, cache recovery, then incoming work deterministically."""

    if not 1 <= max_batches <= MAX_BATCHES_PER_CYCLE:
        raise WorkerError("Worker batch bound is outside the safe range")
    with connect_sftp(configuration, configuration.processor) as sftp:
        processing, processing_ignored = _ready_in_zone(
            sftp,
            "processing",
        )
        incoming, incoming_ignored = _ready_in_zone(sftp, "incoming")
    cached, cache_ignored = _ready_in_cache(configuration)

    processing_ids = {candidate.batch_id for candidate in processing}
    incoming_ids = {candidate.batch_id for candidate in incoming}
    sftp_ids = processing_ids | incoming_ids
    ambiguous_ids = processing_ids & incoming_ids
    ordered = tuple(
        BatchCandidate(
            candidate.batch_id,
            candidate.zone,
            candidate.batch_id in ambiguous_ids,
        )
        for candidate in processing
    ) + tuple(
        candidate
        for candidate in cached
        if candidate.batch_id not in sftp_ids
    ) + tuple(
        candidate
        for candidate in incoming
        if candidate.batch_id not in ambiguous_ids
    )
    selected = ordered[:max_batches]
    return DiscoveryResult(
        candidates=selected,
        ready_count=len(ordered),
        deferred_count=len(ordered) - len(selected),
        ignored_count=(
            processing_ignored
            + cache_ignored
            + incoming_ignored
        ),
    )


def _read_remote_bounded(
    sftp: paramiko.SFTPClient,
    remote_path: str,
    *,
    maximum_bytes: int,
) -> bytes:
    """Read a small remote control artifact with an explicit upper bound."""

    attributes = sftp.lstat(remote_path)
    mode = attributes.st_mode
    size = attributes.st_size
    if (
        not isinstance(mode, int)
        or not stat.S_ISREG(mode)
        or not isinstance(size, int)
        or size < 1
        or size > maximum_bytes
    ):
        raise WorkerSourceRejected("SOURCE_ARTIFACT_BOUNDS_EXCEEDED")
    with sftp.file(remote_path, "rb") as stream:
        value = stream.read(maximum_bytes + 1)
    if not isinstance(value, bytes) or not 1 <= len(value) <= maximum_bytes:
        raise WorkerSourceRejected("SOURCE_ARTIFACT_BOUNDS_EXCEEDED")
    return value


def _manifest_envelope(
    manifest_bytes: bytes,
    *,
    expected_batch_id: str,
    allow_invalid: bool,
) -> tuple[str, int] | None:
    """Extract only the bounded transport envelope before raw download."""

    try:
        manifest = json.loads(manifest_bytes)
        if not isinstance(manifest, Mapping):
            raise ValueError("manifest is not an object")
        source_file = manifest["source_file"]
        if not isinstance(source_file, Mapping):
            raise ValueError("source_file is not an object")
        filename = source_file["name"]
        size_bytes = source_file["size_bytes"]
        batch_id = manifest["batch_id"]
    except (
        KeyError,
        RecursionError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ):
        if allow_invalid:
            return None
        raise WorkerSourceRejected("SOURCE_MANIFEST_INVALID") from None

    if batch_id != expected_batch_id:
        if allow_invalid:
            return None
        raise WorkerSourceRejected("BATCH_ID_MISMATCH")
    if not _is_safe_source_filename(filename):
        raise WorkerSourceRejected("SOURCE_FILENAME_UNSAFE")
    if (
        not isinstance(size_bytes, int)
        or isinstance(size_bytes, bool)
        or not 1 <= size_bytes <= MAX_RAW_BYTES
    ):
        raise WorkerSourceRejected("SOURCE_SIZE_BOUNDS_EXCEEDED")
    return filename, size_bytes


def preflight_incoming_bounds(
    batch_id: str,
    *,
    configuration: RuntimeConfiguration,
) -> None:
    """Bound an incoming manifest before existing intake reads its raw file."""

    remote = f"/raw/incoming/{batch_id}/source-manifest.json"
    with connect_sftp(configuration, configuration.processor) as sftp:
        manifest_bytes = _read_remote_bounded(
            sftp,
            remote,
            maximum_bytes=MAX_MANIFEST_BYTES,
        )
        envelope = _manifest_envelope(
            manifest_bytes,
            expected_batch_id=batch_id,
            allow_invalid=True,
        )
        if envelope is not None:
            filename, size_bytes = envelope
            try:
                raw_attributes = sftp.lstat(
                    f"/raw/incoming/{batch_id}/{filename}"
                )
                checksum_attributes = sftp.lstat(
                    f"/raw/incoming/{batch_id}/{filename}.sha256"
                )
            except OSError as exc:
                if exc.errno in {errno.ENOENT, 2}:
                    raise WorkerSourceRejected(
                        "SOURCE_ARTIFACT_MISSING"
                    ) from exc
                raise
            raw_mode = raw_attributes.st_mode
            raw_size = raw_attributes.st_size
            if (
                not isinstance(raw_mode, int)
                or not stat.S_ISREG(raw_mode)
                or raw_size != size_bytes
            ):
                raise WorkerSourceRejected(
                    "SOURCE_ARTIFACT_BOUNDS_EXCEEDED"
                )
            checksum_mode = checksum_attributes.st_mode
            checksum_size = checksum_attributes.st_size
            if (
                not isinstance(checksum_mode, int)
                or not stat.S_ISREG(checksum_mode)
                or not isinstance(checksum_size, int)
                or not 1 <= checksum_size <= MAX_CHECKSUM_BYTES
            ):
                raise WorkerSourceRejected(
                    "SOURCE_ARTIFACT_BOUNDS_EXCEEDED"
                )


def quarantine_incoming_batch(
    batch_id: str,
    *,
    code: str,
    configuration: RuntimeConfiguration,
) -> None:
    """Quarantine an envelope rejected before the normal claim operation."""

    with connect_sftp(configuration, configuration.processor) as sftp:
        quarantine_batch(
            sftp,
            batch_id,
            source_zone="/raw/incoming",
            code=code,
        )


def _download_remote_exact(
    sftp: paramiko.SFTPClient,
    remote_path: str,
    local_path: Path,
    *,
    maximum_bytes: int,
    exact_bytes: int | None = None,
) -> None:
    """Download one regular remote file and verify its transport size."""

    attributes = sftp.lstat(remote_path)
    mode = attributes.st_mode
    size = attributes.st_size
    if (
        not isinstance(mode, int)
        or not stat.S_ISREG(mode)
        or not isinstance(size, int)
        or size < 1
        or size > maximum_bytes
        or (exact_bytes is not None and size != exact_bytes)
    ):
        raise WorkerSourceRejected("SOURCE_ARTIFACT_BOUNDS_EXCEEDED")
    sftp.get(remote_path, str(local_path))
    observed_size = local_path.stat().st_size
    if (
        observed_size != size
        or observed_size > maximum_bytes
        or (exact_bytes is not None and observed_size != exact_bytes)
    ):
        raise WorkerSourceRejected("SOURCE_DOWNLOAD_SIZE_MISMATCH")
    local_path.chmod(0o600)
    with local_path.open("rb") as stream:
        os.fsync(stream.fileno())


def _owned_by_worker(metadata: os.stat_result) -> bool:
    """Return whether local metadata has the current owner when supported."""

    get_effective_user = getattr(os, "geteuid", None)
    return (
        get_effective_user is None
        or metadata.st_uid == get_effective_user()
    )


def _require_private_cache_directory(bundle: Path) -> None:
    """Reject a cache directory that is linked, shared, or not worker-owned."""

    try:
        metadata = bundle.lstat()
    except OSError as exc:
        raise WorkerCacheConflict(
            "Immutable cache directory cannot be inspected"
        ) from exc
    mode = metadata.st_mode
    if (
        stat.S_ISLNK(mode)
        or not stat.S_ISDIR(mode)
        or stat.S_IMODE(mode) & 0o077
        or not _owned_by_worker(metadata)
    ):
        raise WorkerCacheConflict(
            "Immutable cache directory is not private and worker-owned"
        )


def _require_private_cache_file(
    path: Path,
    *,
    maximum_bytes: int,
    exact_bytes: int | None = None,
) -> None:
    """Require one private, single-link, worker-owned regular cache file."""

    try:
        metadata = path.lstat()
    except OSError as exc:
        raise WorkerCacheConflict(
            "Immutable cache artifact cannot be inspected"
        ) from exc
    mode = metadata.st_mode
    size = metadata.st_size
    if (
        stat.S_ISLNK(mode)
        or not stat.S_ISREG(mode)
        or stat.S_IMODE(mode) & 0o077
        or metadata.st_nlink != 1
        or not _owned_by_worker(metadata)
        or size < 1
        or size > maximum_bytes
        or (exact_bytes is not None and size != exact_bytes)
    ):
        raise WorkerCacheConflict(
            "Immutable cache artifact is not a safe private regular file"
        )


def _assert_exact_cache_bundle(
    bundle: Path,
    *,
    filename: str,
    raw_size: int,
) -> None:
    """Require exactly the three immutable, private transport artifacts."""

    _require_private_cache_directory(bundle)
    expected = {
        "source-manifest.json",
        filename,
        f"{filename}.sha256",
    }
    try:
        entries = tuple(bundle.iterdir())
    except OSError as exc:
        raise WorkerCacheConflict(
            "Immutable cache contents cannot be inspected"
        ) from exc
    if (
        len(entries) != len(expected)
        or {entry.name for entry in entries} != expected
    ):
        raise WorkerCacheConflict(
            "Immutable cache must contain exactly three source artifacts"
        )
    _require_private_cache_file(
        bundle / "source-manifest.json",
        maximum_bytes=MAX_MANIFEST_BYTES,
    )
    _require_private_cache_file(
        bundle / filename,
        maximum_bytes=MAX_RAW_BYTES,
        exact_bytes=raw_size,
    )
    _require_private_cache_file(
        bundle / f"{filename}.sha256",
        maximum_bytes=MAX_CHECKSUM_BYTES,
    )


def _cached_bundle_envelope(
    bundle: Path,
    *,
    batch_id: str,
) -> tuple[str, int]:
    """Read a cache manifest only after its local file metadata is safe."""

    _require_private_cache_directory(bundle)
    manifest_path = bundle / "source-manifest.json"
    _require_private_cache_file(
        manifest_path,
        maximum_bytes=MAX_MANIFEST_BYTES,
    )
    try:
        manifest_bytes = manifest_path.read_bytes()
        envelope = _manifest_envelope(
            manifest_bytes,
            expected_batch_id=batch_id,
            allow_invalid=False,
        )
    except (OSError, WorkerSourceRejected) as exc:
        raise WorkerCacheConflict(
            "Immutable cache manifest is not safely reusable"
        ) from exc
    assert envelope is not None
    return envelope


def _same_cached_bundle(
    first: Path,
    second: Path,
    raw: PublishedRaw,
) -> bool:
    """Compare all three immutable transport artifacts byte-for-byte."""

    names = (
        "source-manifest.json",
        raw.filename,
        f"{raw.filename}.sha256",
    )
    try:
        _assert_exact_cache_bundle(
            first,
            filename=raw.filename,
            raw_size=raw.size_bytes,
        )
        _assert_exact_cache_bundle(
            second,
            filename=raw.filename,
            raw_size=raw.size_bytes,
        )
        return all(
            (first / name).read_bytes() == (second / name).read_bytes()
            for name in names
        )
    except (OSError, WorkerCacheConflict):
        return False


def download_processing_bundle(
    batch_id: str,
    *,
    configuration: RuntimeConfiguration,
) -> tuple[Path, PublishedRaw]:
    """Atomically cache and validate one exact claimed SFTP source bundle."""

    cache_root = _runtime_path(configuration, "intake-cache")
    _ensure_private_directory(cache_root)
    final_bundle = cache_root / batch_id
    if final_bundle.parent != cache_root:
        raise WorkerError("Worker cache path escaped its root")

    staging_parent = Path(
        tempfile.mkdtemp(prefix=f".{batch_id}.", dir=cache_root)
    )
    staging_parent.chmod(0o700)
    staging_bundle = staging_parent / batch_id
    staging_bundle.mkdir(mode=0o700)
    remote = f"/raw/processing/{batch_id}"

    try:
        manifest_path = staging_bundle / "source-manifest.json"
        with connect_sftp(configuration, configuration.processor) as sftp:
            _download_remote_exact(
                sftp,
                f"{remote}/source-manifest.json",
                manifest_path,
                maximum_bytes=MAX_MANIFEST_BYTES,
            )
            _require_private_cache_file(
                manifest_path,
                maximum_bytes=MAX_MANIFEST_BYTES,
            )
            envelope = _manifest_envelope(
                manifest_path.read_bytes(),
                expected_batch_id=batch_id,
                allow_invalid=False,
            )
            assert envelope is not None
            filename, size_bytes = envelope
            raw_path = staging_bundle / filename
            checksum_path = staging_bundle / f"{filename}.sha256"
            if (
                raw_path.parent != staging_bundle
                or checksum_path.parent != staging_bundle
            ):
                raise WorkerSourceRejected("SOURCE_FILENAME_UNSAFE")
            _download_remote_exact(
                sftp,
                f"{remote}/{filename}",
                raw_path,
                maximum_bytes=MAX_RAW_BYTES,
                exact_bytes=size_bytes,
            )
            _download_remote_exact(
                sftp,
                f"{remote}/{filename}.sha256",
                checksum_path,
                maximum_bytes=MAX_CHECKSUM_BYTES,
            )

        _assert_exact_cache_bundle(
            staging_bundle,
            filename=filename,
            raw_size=size_bytes,
        )
        raw = validate_bundle(
            staging_bundle,
            configuration=configuration,
        )
        if final_bundle.is_symlink():
            raise WorkerCacheConflict(
                "Immutable cache target cannot be a symbolic link"
            )
        if final_bundle.exists():
            mode = final_bundle.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise WorkerCacheConflict(
                    "Immutable cache target is not a real directory"
                )
            _assert_exact_cache_bundle(
                final_bundle,
                filename=raw.filename,
                raw_size=raw.size_bytes,
            )
            try:
                cached = validate_bundle(
                    final_bundle,
                    configuration=configuration,
                )
            except RawPublicationError as exc:
                raise WorkerCacheConflict(
                    "Immutable cache is no longer valid"
                ) from exc
            if cached != raw or not _same_cached_bundle(
                final_bundle,
                staging_bundle,
                raw,
            ):
                raise WorkerCacheConflict(
                    "Immutable cache identity changed"
                )
            return final_bundle, cached

        staging_bundle.rename(final_bundle)
        final_bundle.chmod(0o700)
        _assert_exact_cache_bundle(
            final_bundle,
            filename=raw.filename,
            raw_size=raw.size_bytes,
        )
        directory_descriptor = os.open(
            cache_root,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        return final_bundle, raw
    finally:
        if staging_parent.exists():
            shutil.rmtree(staging_parent, ignore_errors=True)


def load_cached_bundle(
    batch_id: str,
    *,
    configuration: RuntimeConfiguration,
) -> tuple[Path, PublishedRaw]:
    """Validate and return one exact immutable retained source bundle.

    This path performs no SFTP access. It is used only when discovery found a
    safe batch ID absent from both active SFTP zones, allowing ``run_pipeline``
    to reconcile its durable SFTP/PostgreSQL state after an interrupted
    terminal move.
    """

    cache_root = _runtime_path(configuration, "intake-cache")
    target = cache_root / batch_id
    if (
        BATCH_ID_PATTERN.fullmatch(batch_id) is None
        or target.parent != cache_root
    ):
        raise WorkerCacheConflict("Immutable cache identity is unsafe")

    _require_private_cache_directory(cache_root)
    filename, raw_size = _cached_bundle_envelope(
        target,
        batch_id=batch_id,
    )
    _assert_exact_cache_bundle(
        target,
        filename=filename,
        raw_size=raw_size,
    )
    try:
        raw = validate_bundle(
            target,
            configuration=configuration,
        )
    except (OSError, RawPublicationError) as exc:
        raise WorkerCacheConflict(
            "Immutable cache is no longer valid"
        ) from exc
    if (
        raw.batch_id != batch_id
        or raw.filename != filename
        or raw.size_bytes != raw_size
    ):
        raise WorkerCacheConflict("Immutable cache identity changed")
    _assert_exact_cache_bundle(
        target,
        filename=raw.filename,
        raw_size=raw.size_bytes,
    )
    return target, raw


def remove_cached_bundle(
    batch_id: str,
    *,
    configuration: RuntimeConfiguration,
) -> None:
    """Remove only one validated terminal batch from the private raw cache."""

    cache_root = _runtime_path(configuration, "intake-cache")
    target = cache_root / batch_id
    if (
        BATCH_ID_PATTERN.fullmatch(batch_id) is None
        or target.parent != cache_root
    ):
        return
    try:
        mode = target.lstat().st_mode
    except FileNotFoundError:
        return
    except OSError as exc:
        raise WorkerError("Worker cache target cannot be inspected") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise WorkerError("Worker cache target is unsafe to remove")
    filename, raw_size = _cached_bundle_envelope(
        target,
        batch_id=batch_id,
    )
    _assert_exact_cache_bundle(
        target,
        filename=filename,
        raw_size=raw_size,
    )
    shutil.rmtree(target)


def _claimed_identity_matches(
    claimed: ClaimedRaw,
    raw: PublishedRaw,
) -> bool:
    """Verify the claimed SFTP identity did not change before download."""

    return bool(
        claimed.batch_id == raw.batch_id
        and claimed.file_type == raw.file_type
        and claimed.filename == raw.filename
        and claimed.sha256 == raw.sha256
        and claimed.manifest_sha256 == raw.manifest_sha256
    )


def _read_terminal_status(evidence: Path, batch_id: str) -> str:
    """Read one bounded final evidence status after pipeline completion."""

    path = evidence / "final-status.json"
    try:
        if not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
            raise ValueError("terminal evidence is missing or oversized")
        value = json.loads(path.read_text(encoding="utf-8"))
        status_value = value["status"]
        if value["batch_id"] != batch_id or status_value not in TERMINAL_STATUSES:
            raise ValueError("terminal evidence identity is invalid")
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise WorkerError("Pipeline returned unsafe terminal evidence") from exc
    return str(status_value)


def _quarantine_source_failure(
    candidate: BatchCandidate,
    *,
    code: str,
    file_type: str | None,
    configuration: RuntimeConfiguration,
) -> BatchOutcome:
    """Quarantine one deterministic processing-source failure if possible."""

    try:
        quarantine_processing_batch(
            candidate.batch_id,
            code=code,
            configuration=configuration,
        )
    except Exception:
        return BatchOutcome(
            candidate.batch_id,
            candidate.zone,
            "retry_pending",
            "QUARANTINE_FAILED",
            file_type,
        )
    try:
        remove_cached_bundle(
            candidate.batch_id,
            configuration=configuration,
        )
    except WorkerError:
        pass
    return BatchOutcome(
        candidate.batch_id,
        candidate.zone,
        "quarantined",
        code,
        file_type,
    )


def process_candidate(
    candidate: BatchCandidate,
    *,
    evidence_root: Path,
    configuration: RuntimeConfiguration,
) -> BatchOutcome:
    """Process one batch without allowing its failure to escape the cycle."""

    if candidate.zone_ambiguous:
        return BatchOutcome(
            candidate.batch_id,
            candidate.zone,
            "retry_pending",
            "SFTP_ZONE_AMBIGUITY",
        )

    claimed: ClaimedRaw | None = None
    if candidate.zone == "incoming":
        try:
            preflight_incoming_bounds(
                candidate.batch_id,
                configuration=configuration,
            )
        except WorkerSourceRejected as exc:
            code = _safe_code(
                exc.code,
                fallback="SOURCE_ENVELOPE_REJECTED",
            )
            try:
                quarantine_incoming_batch(
                    candidate.batch_id,
                    code=code,
                    configuration=configuration,
                )
            except Exception:
                return BatchOutcome(
                    candidate.batch_id,
                    candidate.zone,
                    "retry_pending",
                    "QUARANTINE_FAILED",
                )
            return BatchOutcome(
                candidate.batch_id,
                candidate.zone,
                "quarantined",
                code,
            )
        except Exception:
            return BatchOutcome(
                candidate.batch_id,
                candidate.zone,
                "retry_pending",
                "INCOMING_PREFLIGHT_FAILED",
            )

        try:
            claimed = claim_batch(
                candidate.batch_id,
                configuration=configuration,
            )
        except RawIntakeError as exc:
            code = _safe_code(exc.code, fallback="RAW_INTAKE_REJECTED")
            if code == "BATCH_NOT_READY":
                status = "not_ready"
            elif exc.quarantine_verified:
                status = "quarantined"
            else:
                status = "retry_pending"
                code = "QUARANTINE_UNCERTAIN"
            return BatchOutcome(
                candidate.batch_id,
                candidate.zone,
                status,
                code,
            )
        except Exception:
            return BatchOutcome(
                candidate.batch_id,
                candidate.zone,
                "retry_pending",
                "RAW_CLAIM_FAILED",
            )

    if candidate.zone == "cache":
        try:
            bundle, raw = load_cached_bundle(
                candidate.batch_id,
                configuration=configuration,
            )
        except Exception:
            return BatchOutcome(
                candidate.batch_id,
                candidate.zone,
                "retry_pending",
                "LOCAL_CACHE_CONFLICT",
            )
    else:
        try:
            bundle, raw = download_processing_bundle(
                candidate.batch_id,
                configuration=configuration,
            )
        except WorkerSourceRejected as exc:
            return _quarantine_source_failure(
                candidate,
                code=_safe_code(
                    exc.code,
                    fallback="SOURCE_ENVELOPE_REJECTED",
                ),
                file_type=None,
                configuration=configuration,
            )
        except RawPublicationError:
            return _quarantine_source_failure(
                candidate,
                code="SOURCE_INTEGRITY_ERROR",
                file_type=None,
                configuration=configuration,
            )
        except WorkerCacheConflict:
            return BatchOutcome(
                candidate.batch_id,
                candidate.zone,
                "retry_pending",
                "LOCAL_CACHE_CONFLICT",
            )
        except Exception:
            return BatchOutcome(
                candidate.batch_id,
                candidate.zone,
                "retry_pending",
                "SOURCE_DOWNLOAD_FAILED",
            )

    file_type = _safe_type_number(raw.file_type)
    if claimed is not None and not _claimed_identity_matches(claimed, raw):
        return _quarantine_source_failure(
            candidate,
            code="SOURCE_IDENTITY_CHANGED",
            file_type=file_type,
            configuration=configuration,
        )

    try:
        adapter = workflow_for_type(raw.file_type)
    except ValueError:
        if candidate.zone == "cache":
            return BatchOutcome(
                candidate.batch_id,
                candidate.zone,
                "retry_pending",
                "LOCAL_CACHE_CONFLICT",
                file_type,
            )
        return _quarantine_source_failure(
            candidate,
            code="UNSUPPORTED_FILE_TYPE",
            file_type=file_type,
            configuration=configuration,
        )

    try:
        if candidate.zone == "cache":
            evidence = run_pipeline(
                adapter,
                bundle,
                scenario=None,
                evidence_root=evidence_root,
                configuration=configuration,
                recovery_only=True,
            )
        else:
            evidence = run_pipeline(
                adapter,
                bundle,
                scenario=None,
                evidence_root=evidence_root,
                configuration=configuration,
            )
        status = _read_terminal_status(evidence, candidate.batch_id)
    except Exception:
        return BatchOutcome(
            candidate.batch_id,
            candidate.zone,
            "retry_pending",
            "PIPELINE_RETRY_PENDING",
            file_type,
        )

    terminal_code = "TERMINAL"
    try:
        remove_cached_bundle(
            candidate.batch_id,
            configuration=configuration,
        )
    except WorkerError:
        terminal_code = "TERMINAL_CACHE_RETAINED"

    return BatchOutcome(
        candidate.batch_id,
        candidate.zone,
        status,
        terminal_code,
        file_type,
    )


def run_cycle(
    *,
    evidence_root: Path,
    configuration: RuntimeConfiguration,
    max_batches: int = MAX_BATCHES_PER_CYCLE,
) -> CycleReport:
    """Run one bounded queue iteration and isolate every batch outcome."""

    started_at = utc_now()
    try:
        discovery = discover_ready_batches(
            configuration=configuration,
            max_batches=max_batches,
        )
    except Exception:
        return CycleReport(
            started_at=started_at,
            finished_at=utc_now(),
            ready_count=0,
            deferred_count=0,
            ignored_count=0,
            outcomes=(),
            error_code="DISCOVERY_FAILED",
        )

    outcomes: list[BatchOutcome] = []
    for candidate in discovery.candidates:
        try:
            outcome = process_candidate(
                candidate,
                evidence_root=evidence_root,
                configuration=configuration,
            )
        except Exception:
            outcome = BatchOutcome(
                candidate.batch_id,
                candidate.zone,
                "retry_pending",
                "UNEXPECTED_BATCH_ERROR",
            )
        outcomes.append(outcome)
    return CycleReport(
        started_at=started_at,
        finished_at=utc_now(),
        ready_count=discovery.ready_count,
        deferred_count=discovery.deferred_count,
        ignored_count=discovery.ignored_count,
        outcomes=tuple(outcomes),
    )


def write_atomic_status(path: Path, value: Mapping[str, object]) -> None:
    """Publish one private heartbeat JSON document by atomic replacement."""

    _ensure_private_directory(path.parent)
    content = (
        json.dumps(
            dict(value),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".part",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        path.chmod(0o600)
        parent_descriptor = os.open(
            path.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


class WorkerLock:
    """Non-blocking private file lock for one host-side worker."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._descriptor: int | None = None

    def __enter__(self) -> WorkerLock:
        _ensure_private_directory(self._path.parent)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor: int | None = None
        try:
            descriptor = os.open(self._path, flags, 0o600)
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.ftruncate(descriptor, 0)
            os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
            os.fsync(descriptor)
        except BlockingIOError as exc:
            if descriptor is not None:
                os.close(descriptor)
            raise WorkerAlreadyRunningError(
                "Another worker is already running"
            ) from exc
        except OSError as exc:
            if descriptor is not None:
                os.close(descriptor)
            raise WorkerError("Cannot acquire the private worker lock") from exc
        assert descriptor is not None
        self._descriptor = descriptor
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback
        if self._descriptor is not None:
            try:
                fcntl.flock(self._descriptor, fcntl.LOCK_UN)
            finally:
                os.close(self._descriptor)
                self._descriptor = None


@contextmanager
def clean_signal_stop(stop_event: threading.Event) -> Iterator[None]:
    """Translate SIGINT and SIGTERM into a clean poll-loop stop request."""

    def request_stop(
        signum: int,
        frame: FrameType | None,
    ) -> None:
        del signum, frame
        stop_event.set()

    previous = {
        signal_number: signal.getsignal(signal_number)
        for signal_number in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        for signal_number in previous:
            signal.signal(signal_number, request_stop)
        yield
    finally:
        for signal_number, handler in previous.items():
            signal.signal(signal_number, handler)


class WorkerService:
    """Own the polling loop, heartbeat, and aggregate JSON reporting."""

    def __init__(
        self,
        *,
        configuration: RuntimeConfiguration,
        evidence_root: Path,
        max_batches: int = MAX_BATCHES_PER_CYCLE,
    ) -> None:
        if not 1 <= max_batches <= MAX_BATCHES_PER_CYCLE:
            raise WorkerError("Worker batch bound is outside the safe range")
        self._configuration = configuration
        self._evidence_root = evidence_root.resolve()
        self._max_batches = max_batches
        self._status_path = _runtime_path(
            configuration,
            "worker-status.json",
        )

    @property
    def status_path(self) -> Path:
        """Expose the fixed heartbeat path for status integrations."""

        return self._status_path

    def _heartbeat(
        self,
        *,
        state: str,
        started_at: str,
        poll_sequence: int,
        poll_interval: float,
        report: CycleReport | None,
    ) -> None:
        value: dict[str, object] = {
            "heartbeat_at": utc_now(),
            "max_batches": self._max_batches,
            "pid": os.getpid(),
            "poll_interval_seconds": poll_interval,
            "poll_sequence": poll_sequence,
            "started_at": started_at,
            "state": state,
            "version": 1,
        }
        if report is not None:
            value["last_cycle"] = report.as_dict()
        write_atomic_status(self._status_path, value)

    def run(
        self,
        *,
        once: bool,
        poll_interval: float,
        stop_event: threading.Event,
        emit: Callable[[str], None],
    ) -> bool:
        """Run one or many cycles and return the final cycle health."""

        if not (
            MIN_POLL_INTERVAL_SECONDS
            <= poll_interval
            <= MAX_POLL_INTERVAL_SECONDS
        ):
            raise WorkerError("Worker poll interval is outside the safe range")
        started_at = utc_now()
        poll_sequence = 0
        last_report: CycleReport | None = None
        self._heartbeat(
            state="running",
            started_at=started_at,
            poll_sequence=poll_sequence,
            poll_interval=poll_interval,
            report=None,
        )
        while not stop_event.is_set():
            poll_sequence += 1
            last_report = run_cycle(
                evidence_root=self._evidence_root,
                configuration=self._configuration,
                max_batches=self._max_batches,
            )
            self._heartbeat(
                state="running",
                started_at=started_at,
                poll_sequence=poll_sequence,
                poll_interval=poll_interval,
                report=last_report,
            )
            emit(json.dumps(last_report.as_dict(), sort_keys=True))
            if once or stop_event.wait(poll_interval):
                break
        self._heartbeat(
            state="stopped",
            started_at=started_at,
            poll_sequence=poll_sequence,
            poll_interval=poll_interval,
            report=last_report,
        )
        return last_report is None or last_report.error_code is None


def _bounded_poll_interval(value: str) -> float:
    """Parse a CLI poll interval inside operational safety bounds."""

    try:
        interval = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "poll interval must be numeric"
        ) from exc
    if not (
        MIN_POLL_INTERVAL_SECONDS
        <= interval
        <= MAX_POLL_INTERVAL_SECONDS
    ):
        raise argparse.ArgumentTypeError(
            "poll interval is outside the safe range"
        )
    return interval


def _bounded_batch_count(value: str) -> int:
    """Parse a CLI per-cycle batch bound."""

    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "max batches must be an integer"
        ) from exc
    if not 1 <= count <= MAX_BATCHES_PER_CYCLE:
        raise argparse.ArgumentTypeError(
            "max batches is outside the safe range"
        )
    return count


def build_parser() -> argparse.ArgumentParser:
    """Build the automatic worker command-line interface."""

    parser = argparse.ArgumentParser(
        description="Process manifest-ready legacy SFTP batches.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one deterministic polling iteration.",
    )
    parser.add_argument(
        "--poll-interval",
        type=_bounded_poll_interval,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        metavar="SECONDS",
    )
    parser.add_argument(
        "--max-batches",
        type=_bounded_batch_count,
        default=MAX_BATCHES_PER_CYCLE,
        metavar="COUNT",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=ROOT / "evidence",
    )
    return parser


def _safe_worker_error(code: str) -> str:
    """Serialize a startup failure without its potentially sensitive message."""

    return json.dumps(
        {
            "code": code,
            "status": "worker_failed",
        },
        sort_keys=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Load configuration, hold the worker lock, and run until stopped."""

    args = build_parser().parse_args(argv)
    try:
        configuration = RuntimeConfiguration.load()
        lock_path = _runtime_path(configuration, "worker.lock")
        service = WorkerService(
            configuration=configuration,
            evidence_root=args.evidence_root,
            max_batches=args.max_batches,
        )
        stop_event = threading.Event()
        with WorkerLock(lock_path), clean_signal_stop(stop_event):
            healthy = service.run(
                once=args.once,
                poll_interval=args.poll_interval,
                stop_event=stop_event,
                emit=print,
            )
        return 0 if healthy else 2
    except WorkerAlreadyRunningError:
        print(
            _safe_worker_error("WORKER_ALREADY_RUNNING"),
            file=sys.stderr,
        )
    except (
        OSError,
        RuntimeConfigurationError,
        SftpBoundaryError,
        WorkerError,
    ):
        print(
            _safe_worker_error("WORKER_STARTUP_FAILED"),
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
