"""Private, identity-bound recovery journal for terminal quarantine paths.

The raw intake cache deliberately contains exactly three transport artifacts.
Terminal recovery metadata therefore lives in a separate private directory.
The journal contains only immutable source identity, a bounded safe reason,
and the workflow adapter's evidence-safe Java projection.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

from config import RuntimeConfiguration
from raw_publisher import PublishedRaw
from workflow_registry import WorkflowAdapter


class RecoveryJournalError(Exception):
    """Terminal recovery metadata is unsafe, ambiguous, or unavailable."""


RecoveryRoute = Literal["rejection", "oracle_mismatch"]

BATCH_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"B[0-9]{15}\Z")
SAFE_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[A-Z][A-Z0-9_]{2,63}\Z"
)
SHA256_PATTERN: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}\Z")
MAX_JOURNAL_BYTES: Final[int] = 64 * 1024
MAX_SAFE_STRING: Final[int] = 512
MAX_RECOVERY_DIRECTORY_ENTRIES: Final[int] = 4_096
JOURNAL_VERSION: Final[int] = 1
FORCED_ORACLE_REASON: Final[str] = (
    "test-only forced contract oracle mismatch"
)
SAFE_REASONS: Final[Mapping[RecoveryRoute, str]] = {
    "rejection": "approved Java rejection",
    "oracle_mismatch": "approved contract oracle mismatch",
}


@dataclass(frozen=True, slots=True)
class TerminalRecovery:
    """Validated terminal recovery intent with privacy-safe Java evidence."""

    batch_id: str
    file_type: str
    raw_sha256: str
    manifest_sha256: str
    route: RecoveryRoute
    code: str
    reason: str
    java_result: Mapping[str, object]


def recovery_journal_path(
    configuration: RuntimeConfiguration,
    batch_id: str,
) -> Path:
    """Return the contained journal path for one syntactically safe batch."""

    if BATCH_ID_PATTERN.fullmatch(batch_id) is None:
        raise RecoveryJournalError("Recovery journal batch ID is unsafe")
    root = configuration.root / ".runtime" / "terminal-recovery"
    path = root / f"{batch_id}.json"
    if path.parent != root:
        raise RecoveryJournalError("Recovery journal path escaped its root")
    return path


def publish_terminal_recovery(
    adapter: WorkflowAdapter,
    raw: PublishedRaw,
    *,
    route: RecoveryRoute,
    java_result: Mapping[str, object],
    code: str,
    configuration: RuntimeConfiguration,
    reason: str | None = None,
) -> TerminalRecovery:
    """Atomically persist or verify one immutable terminal recovery intent."""

    journal = _build_recovery(
        adapter,
        raw,
        route=route,
        java_result=java_result,
        code=code,
        reason=reason,
    )
    path = recovery_journal_path(configuration, raw.batch_id)
    root = path.parent
    _ensure_private_directory(root.parent)
    _ensure_private_directory(root)

    existing = load_terminal_recovery(
        adapter,
        raw,
        configuration=configuration,
    )
    if existing is not None:
        if existing != journal:
            raise RecoveryJournalError(
                "Existing recovery journal has different terminal intent"
            )
        return existing

    content = _encode_journal(journal)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{raw.batch_id}.",
        suffix=".part",
        dir=root,
    )
    temporary = Path(temporary_name)
    linked = False
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
            linked = True
        except FileExistsError:
            existing = load_terminal_recovery(
                adapter,
                raw,
                configuration=configuration,
            )
            if existing != journal:
                raise RecoveryJournalError(
                    "Concurrent recovery journal has different terminal intent"
                )
            return journal
        temporary.unlink()
        _fsync_directory(root)
        _require_private_file(path)
        return journal
    except RecoveryJournalError:
        raise
    except OSError as exc:
        raise RecoveryJournalError(
            "Cannot publish private terminal recovery journal"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass
        if linked and path.exists():
            _require_private_file(path)


def load_terminal_recovery(
    adapter: WorkflowAdapter,
    raw: PublishedRaw,
    *,
    configuration: RuntimeConfiguration,
) -> TerminalRecovery | None:
    """Load and validate one journal against source identity and adapter policy."""

    path = recovery_journal_path(configuration, raw.batch_id)
    root = path.parent
    if not root.exists() and not root.is_symlink():
        return None
    _require_private_directory(root.parent)
    _require_private_directory(root)
    try:
        _repair_interrupted_publication(path)
        _require_private_file(path)
    except FileNotFoundError:
        return None
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise RecoveryJournalError(
            "Cannot read private terminal recovery journal"
        ) from exc
    if not content or len(content) > MAX_JOURNAL_BYTES:
        raise RecoveryJournalError("Recovery journal size is unsafe")
    try:
        decoded = cast(object, json.loads(content))
    except json.JSONDecodeError as exc:
        raise RecoveryJournalError("Recovery journal JSON is invalid") from exc
    journal = _decode_journal(decoded)
    expected_identity = (
        raw.batch_id,
        raw.file_type,
        raw.sha256,
        raw.manifest_sha256,
    )
    observed_identity = (
        journal.batch_id,
        journal.file_type,
        journal.raw_sha256,
        journal.manifest_sha256,
    )
    if observed_identity != expected_identity:
        raise RecoveryJournalError(
            "Recovery journal belongs to different source identity"
        )
    _validate_java_projection(adapter, raw, journal)
    return journal


def remove_terminal_recovery(
    adapter: WorkflowAdapter,
    raw: PublishedRaw,
    *,
    expected_route: RecoveryRoute | None,
    configuration: RuntimeConfiguration,
) -> None:
    """Remove one journal only when evidence confirms the same terminal route."""

    path = recovery_journal_path(configuration, raw.batch_id)
    journal = load_terminal_recovery(
        adapter,
        raw,
        configuration=configuration,
    )
    if journal is None:
        return
    if expected_route is None or journal.route != expected_route:
        raise RecoveryJournalError(
            "Recovery journal route disagrees with terminal evidence"
        )
    try:
        path.unlink()
        _fsync_directory(path.parent)
    except OSError as exc:
        raise RecoveryJournalError(
            "Cannot remove completed terminal recovery journal"
        ) from exc


def _build_recovery(
    adapter: WorkflowAdapter,
    raw: PublishedRaw,
    *,
    route: RecoveryRoute,
    java_result: Mapping[str, object],
    code: str,
    reason: str | None,
) -> TerminalRecovery:
    if route not in SAFE_REASONS:
        raise RecoveryJournalError("Recovery route is unsupported")
    if SAFE_CODE_PATTERN.fullmatch(code) is None:
        raise RecoveryJournalError("Recovery code is unsafe")
    safe_reason = SAFE_REASONS[route] if reason is None else reason
    if (
        not safe_reason
        or len(safe_reason) > MAX_SAFE_STRING
        or any(character in safe_reason for character in "\r\n\t")
        or (
            safe_reason != SAFE_REASONS[route]
            and not (
                route == "oracle_mismatch"
                and safe_reason == FORCED_ORACLE_REASON
            )
        )
    ):
        raise RecoveryJournalError("Recovery reason is unsafe")
    safe_java = adapter.java_evidence(java_result)
    journal = TerminalRecovery(
        batch_id=raw.batch_id,
        file_type=raw.file_type,
        raw_sha256=raw.sha256,
        manifest_sha256=raw.manifest_sha256,
        route=route,
        code=code,
        reason=safe_reason,
        java_result=dict(safe_java),
    )
    _validate_java_projection(adapter, raw, journal)
    return journal


def _validate_java_projection(
    adapter: WorkflowAdapter,
    raw: PublishedRaw,
    journal: TerminalRecovery,
) -> None:
    java_result = dict(journal.java_result)
    _validate_json_value(java_result)
    if adapter.type_number != raw.file_type:
        raise RecoveryJournalError("Recovery adapter belongs to another type")
    if java_result.get("batch_id") != raw.batch_id:
        raise RecoveryJournalError(
            "Recovery Java projection belongs to another batch"
        )
    status = java_result.get("status")
    if journal.route == "rejection" and status != "rejected":
        raise RecoveryJournalError(
            "Rejection recovery requires a rejected Java result"
        )
    if journal.route == "oracle_mismatch" and status not in {
        "rejected",
        "succeeded",
    }:
        raise RecoveryJournalError(
            "Oracle recovery has an unsupported Java status"
        )
    if (
        journal.route == "rejection"
        and java_result.get("code") != journal.code
    ):
        raise RecoveryJournalError(
            "Recovery rejection code disagrees with Java evidence"
        )
    if (
        journal.route == "oracle_mismatch"
        and journal.code != "ORACLE_MISMATCH"
    ):
        raise RecoveryJournalError(
            "Oracle recovery code is not the terminal mismatch code"
        )
    if adapter.java_evidence(java_result) != java_result:
        raise RecoveryJournalError(
            "Recovery Java result exceeds the adapter evidence allowlist"
        )


def _encode_journal(journal: TerminalRecovery) -> bytes:
    payload: dict[str, object] = {
        "batch_id": journal.batch_id,
        "code": journal.code,
        "file_type": journal.file_type,
        "java_result": dict(journal.java_result),
        "manifest_sha256": journal.manifest_sha256,
        "raw_sha256": journal.raw_sha256,
        "reason": journal.reason,
        "route": journal.route,
        "version": JOURNAL_VERSION,
    }
    payload_bytes = _canonical_json(payload)
    envelope = {
        "payload": payload,
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
    }
    content = (
        json.dumps(
            envelope,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")
    if len(content) > MAX_JOURNAL_BYTES:
        raise RecoveryJournalError("Recovery journal exceeds its size bound")
    return content


def _decode_journal(value: object) -> TerminalRecovery:
    if not isinstance(value, dict) or set(value) != {
        "payload",
        "payload_sha256",
    }:
        raise RecoveryJournalError("Recovery journal envelope is invalid")
    payload = value.get("payload")
    payload_sha256 = value.get("payload_sha256")
    if not isinstance(payload, dict) or set(payload) != {
        "batch_id",
        "code",
        "file_type",
        "java_result",
        "manifest_sha256",
        "raw_sha256",
        "reason",
        "route",
        "version",
    }:
        raise RecoveryJournalError("Recovery journal payload is invalid")
    if (
        not isinstance(payload_sha256, str)
        or SHA256_PATTERN.fullmatch(payload_sha256) is None
        or hashlib.sha256(_canonical_json(payload)).hexdigest()
        != payload_sha256
    ):
        raise RecoveryJournalError("Recovery journal integrity check failed")

    batch_id = payload.get("batch_id")
    code = payload.get("code")
    file_type = payload.get("file_type")
    java_result = payload.get("java_result")
    manifest_sha256 = payload.get("manifest_sha256")
    raw_sha256 = payload.get("raw_sha256")
    reason = payload.get("reason")
    route = payload.get("route")
    version = payload.get("version")
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version != JOURNAL_VERSION
        or not isinstance(batch_id, str)
        or BATCH_ID_PATTERN.fullmatch(batch_id) is None
        or not isinstance(file_type, str)
        or not re.fullmatch(r"0[1-6]", file_type)
        or not isinstance(raw_sha256, str)
        or SHA256_PATTERN.fullmatch(raw_sha256) is None
        or not isinstance(manifest_sha256, str)
        or SHA256_PATTERN.fullmatch(manifest_sha256) is None
        or not isinstance(route, str)
        or route not in SAFE_REASONS
        or not isinstance(code, str)
        or SAFE_CODE_PATTERN.fullmatch(code) is None
        or not isinstance(reason, str)
        or not reason
        or len(reason) > MAX_SAFE_STRING
        or any(character in reason for character in "\r\n\t")
        or not isinstance(java_result, dict)
    ):
        raise RecoveryJournalError("Recovery journal fields are invalid")
    typed_route = cast(RecoveryRoute, route)
    expected_reason = SAFE_REASONS[typed_route]
    if (
        reason != expected_reason
        and not (
            typed_route == "oracle_mismatch"
            and reason == FORCED_ORACLE_REASON
        )
    ):
        raise RecoveryJournalError("Recovery journal reason is not allowlisted")
    return TerminalRecovery(
        batch_id=batch_id,
        file_type=file_type,
        raw_sha256=raw_sha256,
        manifest_sha256=manifest_sha256,
        route=typed_route,
        code=code,
        reason=reason,
        java_result=cast(dict[str, object], java_result),
    )


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RecoveryJournalError(
            "Recovery journal contains a non-JSON value"
        ) from exc


def _validate_json_value(value: object, *, depth: int = 0) -> None:
    if depth > 5:
        raise RecoveryJournalError("Recovery Java projection is too deep")
    if value is None:
        return
    if isinstance(value, bool):
        raise RecoveryJournalError(
            "Recovery Java projection contains a boolean"
        )
    if isinstance(value, int):
        if abs(value) > 10**18:
            raise RecoveryJournalError(
                "Recovery Java projection integer is unbounded"
            )
        return
    if isinstance(value, str):
        if len(value) > MAX_SAFE_STRING or any(
            character in value for character in "\r\n\t"
        ):
            raise RecoveryJournalError(
                "Recovery Java projection string is unsafe"
            )
        return
    if isinstance(value, list):
        if len(value) > 512:
            raise RecoveryJournalError(
                "Recovery Java projection list is unbounded"
            )
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 128 or not all(
            isinstance(key, str) and 0 < len(key) <= 128
            for key in value
        ):
            raise RecoveryJournalError(
                "Recovery Java projection object is unsafe"
            )
        for item in value.values():
            _validate_json_value(item, depth=depth + 1)
        return
    raise RecoveryJournalError(
        "Recovery Java projection contains an unsupported value"
    )


def _owned_by_current_user(metadata: os.stat_result) -> bool:
    get_effective_user = getattr(os, "geteuid", None)
    return (
        get_effective_user is None
        or metadata.st_uid == get_effective_user()
    )


def _ensure_private_directory(path: Path) -> None:
    try:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise RecoveryJournalError(
            "Cannot create private recovery journal directory"
        ) from exc
    _require_private_directory(path)


def _require_private_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise RecoveryJournalError(
            "Recovery journal directory cannot be inspected"
        ) from exc
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) & 0o077
        or not _owned_by_current_user(metadata)
    ):
        raise RecoveryJournalError(
            "Recovery journal directory is not private and worker-owned"
        )


def _require_private_file(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise RecoveryJournalError(
            "Recovery journal file cannot be inspected"
        ) from exc
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) & 0o077
        or metadata.st_nlink != 1
        or not _owned_by_current_user(metadata)
        or metadata.st_size < 1
        or metadata.st_size > MAX_JOURNAL_BYTES
    ):
        raise RecoveryJournalError(
            "Recovery journal file is not a safe private regular file"
        )


def _repair_interrupted_publication(path: Path) -> None:
    """Finish the one safe two-link state left by an interrupted publication.

    Publication links a fully fsynced private temporary file to the immutable
    final name before unlinking the temporary name. A crash in that tiny
    interval is recoverable only when exactly one bounded, private ``.part``
    sibling names the same inode. Arbitrary hard links remain rejected.
    """

    try:
        final = path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise RecoveryJournalError(
            "Recovery journal file cannot be inspected"
        ) from exc
    if final.st_nlink == 1:
        return
    if (
        final.st_nlink != 2
        or stat.S_ISLNK(final.st_mode)
        or not stat.S_ISREG(final.st_mode)
        or stat.S_IMODE(final.st_mode) & 0o077
        or not _owned_by_current_user(final)
        or final.st_size < 1
        or final.st_size > MAX_JOURNAL_BYTES
    ):
        raise RecoveryJournalError(
            "Recovery journal has an unsafe interrupted publication state"
        )

    prefix = f".{path.stem}."
    candidates: list[Path] = []
    try:
        entries = tuple(path.parent.iterdir())
    except OSError as exc:
        raise RecoveryJournalError(
            "Recovery journal directory cannot be inspected"
        ) from exc
    if len(entries) > MAX_RECOVERY_DIRECTORY_ENTRIES:
        raise RecoveryJournalError(
            "Recovery journal directory exceeds its recovery bound"
        )
    for entry in entries:
        if (
            not entry.name.startswith(prefix)
            or not entry.name.endswith(".part")
        ):
            continue
        try:
            metadata = entry.lstat()
        except OSError as exc:
            raise RecoveryJournalError(
                "Interrupted recovery artifact cannot be inspected"
            ) from exc
        if (
            metadata.st_dev == final.st_dev
            and metadata.st_ino == final.st_ino
            and metadata.st_nlink == 2
            and stat.S_ISREG(metadata.st_mode)
            and not stat.S_ISLNK(metadata.st_mode)
            and not stat.S_IMODE(metadata.st_mode) & 0o077
            and _owned_by_current_user(metadata)
            and metadata.st_size == final.st_size
        ):
            candidates.append(entry)
    if len(candidates) != 1:
        raise RecoveryJournalError(
            "Interrupted recovery journal cannot be repaired unambiguously"
        )
    try:
        candidates[0].unlink()
        _fsync_directory(path.parent)
    except OSError as exc:
        raise RecoveryJournalError(
            "Interrupted recovery journal cannot be finalized"
        ) from exc


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise RecoveryJournalError(
            "Recovery journal directory cannot be synchronized"
        ) from exc
