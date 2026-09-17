from __future__ import annotations

import json
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from briefspec.artifacts import canonical_json_bytes, sha256_bytes
from briefspec.events import validate_event
from briefspec.state import atomic_write

from brief_spec_chronicle.derive import build_snapshot, validate_snapshot
from brief_spec_chronicle.rendering import deterministic_zip, pretty_json_bytes
from brief_spec_chronicle.storage import (
    atomic_external_write,
    chronicle_home,
    ingest_event,
    iter_events,
    order_events,
    project_dir,
    rebuild_index,
    registered_project,
    upsert_registry_record,
    verify_chain,
)


def record_decision(
    project: Path, value: dict[str, Any], *, observed_at: str | None = None
) -> dict[str, Any]:
    required = ("decision_id", "question", "choice", "owner", "rationale")
    missing = [field for field in required if not str(value.get(field, "")).strip()]
    if missing:
        raise ValueError("Decision is missing: " + ", ".join(missing))
    event = {
        "kind": "DECISION_RECORDED",
        "importance": "notable",
        "access": str(value.get("access", "local")),
        "occurred_at": value.get("occurred_at") or observed_at,
        "headline": f"Decision recorded: {value['question']}",
        "entity_refs": [str(value["decision_id"])],
        "evidence_ids": list(value.get("evidence_ids", [])),
        "method_context": value.get("method_context", {"method": "general"}),
        "details": {
            "decision_id": value["decision_id"],
            "question": value["question"],
            "choice": value["choice"],
            "owner": value["owner"],
            "rationale": value["rationale"],
            "consequences": list(value.get("consequences", [])),
            "supersedes": value.get("supersedes"),
        },
    }
    return ingest_event(project, event, source_system="human", observed_at=observed_at)


def lessons(project: Path) -> list[dict[str, Any]]:
    return build_snapshot(project)["lessons"]


def review_lesson(
    project: Path,
    lesson_id: str,
    *,
    choice: str,
    reason: str,
    owner: str = "human",
    observed_at: str | None = None,
) -> dict[str, Any]:
    if choice not in {"approved", "rejected"}:
        raise ValueError("Lesson choice must be approved or rejected")
    known = {item["lesson_id"]: item for item in lessons(project)}
    if lesson_id not in known:
        raise ValueError(f"Unknown lesson proposal: {lesson_id}")
    return record_decision(
        project,
        {
            "decision_id": f"lesson-review:{lesson_id}",
            "question": f"Promote lesson {lesson_id}?",
            "choice": choice,
            "owner": owner,
            "rationale": reason,
            "evidence_ids": known[lesson_id].get("evidence_ids", []),
        },
        observed_at=observed_at,
    )


def export_approved_lesson(
    project: Path, lesson_id: str, output: Path, *, force: bool = False
) -> dict[str, Any]:
    known = {item["lesson_id"]: item for item in lessons(project)}
    lesson = known.get(lesson_id)
    if lesson is None:
        raise ValueError(f"Unknown lesson proposal: {lesson_id}")
    if lesson.get("review_state") != "approved":
        raise ValueError("Lesson must have a human approval receipt before export")
    registration = registered_project(project)
    envelope = {
        "schema_version": "nexo-source-envelope/brief-spec-chronicle-1.0",
        "kind": "SourceEnvelope",
        "source": {
            "provider": "brief-spec-chronicle",
            "project_id": registration["project_id"],
            "project_name": registration["name"],
            "access": "private",
        },
        "proposal": {
            "lesson_id": lesson_id,
            "observation": lesson["observation"],
            "applicability": lesson["applicability"],
            "confidence": lesson["confidence"],
            "evidence_ids": lesson["evidence_ids"],
            "review_state": "approved-for-proposal",
            "canonical_knowledge": False,
        },
        "source_event_ids": lesson["source_event_ids"],
    }
    envelope["sha256"] = sha256_bytes(canonical_json_bytes(envelope))
    atomic_external_write(output, pretty_json_bytes(envelope), force=force)
    return envelope


def archive_project(project: Path, output: Path, *, force: bool = False) -> dict[str, Any]:
    registration = registered_project(project)
    root = project_dir(registration["project_id"])
    events = list(iter_events(registration["project_id"]))
    errors = verify_chain(events)
    if errors:
        raise ValueError("; ".join(errors))
    snapshot = build_snapshot(project)
    files: dict[str, bytes] = {
        "project.json": pretty_json_bytes(
            {key: value for key, value in registration.items() if key != "private_root"}
        ),
        "chronicle.json": pretty_json_bytes(snapshot),
    }
    for path in sorted((root / "events").glob("*.ndjson")):
        files[f"events/{path.name}"] = path.read_bytes()
    for path in sorted((root / "receipts").glob("*.json")):
        files[f"receipts/{path.name}"] = path.read_bytes()
    manifest = {
        "schema_version": "brief-spec-chronicle-archive/1.0",
        "project_id": registration["project_id"],
        "created_at": snapshot["window"]["created_at"],
        "ledger_head_hash": snapshot["ledger_head_hash"],
        "files": [
            {"path": name, "size_bytes": len(content), "sha256": sha256_bytes(content)}
            for name, content in sorted(files.items())
        ],
    }
    files["manifest.json"] = pretty_json_bytes(manifest)
    content = deterministic_zip(files, snapshot["window"]["created_at"])
    atomic_external_write(output, content, force=force)
    return {
        "status": "ARCHIVED",
        "project_id": registration["project_id"],
        "path": str(output),
        "sha256": sha256_bytes(content),
        "ledger_head_hash": snapshot["ledger_head_hash"],
    }


def restore_project(archive_path: Path, project: Path, *, force: bool = False) -> dict[str, Any]:
    """Restore an authenticated Chronicle archive without modifying the repository."""
    archive_path = archive_path.expanduser().resolve(strict=True)
    root = project.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Project is not a directory: {root}")
    if archive_path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Chronicle archive exceeds 64 MiB")
    try:
        archive = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid Chronicle archive: {exc}") from exc
    with archive:
        members = archive.infolist()
        if len(members) > 256:
            raise ValueError("Chronicle archive exceeds 256 members")
        names = [member.filename for member in members]
        if len(names) != len(set(names)):
            raise ValueError("Chronicle archive contains duplicate members")
        total = 0
        for member in members:
            path = Path(member.filename)
            mode = member.external_attr >> 16
            allowed_parent = len(path.parts) == 2 and path.parts[0] in {"events", "receipts"}
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in member.filename
                or stat.S_ISLNK(mode)
                or not (len(path.parts) == 1 or allowed_parent)
            ):
                raise ValueError(f"Unsafe Chronicle archive member: {member.filename}")
            total += member.file_size
            if member.file_size > 64 * 1024 * 1024 or total > 256 * 1024 * 1024:
                raise ValueError("Chronicle archive exceeds expanded-size limits")
        required = {"project.json", "chronicle.json", "manifest.json"}
        if not required.issubset(names):
            raise ValueError("Chronicle archive is missing required metadata")
        manifest = json.loads(archive.read("manifest.json"))
        expected_names = sorted(str(item["path"]) for item in manifest.get("files", []))
        actual_names = sorted(name for name in names if name != "manifest.json")
        if expected_names != actual_names:
            raise ValueError("Chronicle archive members do not match its manifest")
        contents: dict[str, bytes] = {}
        for item in manifest["files"]:
            name = str(item["path"])
            content = archive.read(name)
            if item.get("size_bytes") != len(content) or item.get("sha256") != sha256_bytes(
                content
            ):
                raise ValueError(f"Chronicle archive integrity mismatch: {name}")
            contents[name] = content
    archived_project = json.loads(contents["project.json"])
    project_id = str(archived_project.get("project_id", ""))
    destination = project_dir(project_id)
    event_values: list[dict[str, Any]] = []
    for name in sorted(value for value in contents if value.startswith("events/")):
        for line_number, line in enumerate(contents[name].splitlines(), start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid archived event {name}:{line_number}") from exc
            errors = validate_event(event)
            if errors or event.get("project_id") != project_id:
                detail = "; ".join(errors) if errors else "project ID mismatch"
                raise ValueError(f"Invalid archived event {name}:{line_number}: {detail}")
            event_values.append(event)
    event_values = order_events(event_values)
    chain_errors = verify_chain(event_values)
    if chain_errors:
        raise ValueError("Invalid archived event chain: " + "; ".join(chain_errors))
    if event_values and manifest.get("ledger_head_hash") != event_values[-1]["event_hash"]:
        raise ValueError("Archive ledger head does not match its events")
    archived_snapshot = json.loads(contents["chronicle.json"])
    snapshot_errors = validate_snapshot(archived_snapshot)
    if snapshot_errors:
        raise ValueError("Invalid archived Chronicle snapshot: " + "; ".join(snapshot_errors))
    if archived_snapshot.get("project", {}).get("project_id") != project_id:
        raise ValueError("Archived Chronicle snapshot project ID does not match the archive")
    if archived_snapshot.get("ledger_head_hash") != manifest.get("ledger_head_hash"):
        raise ValueError("Archived Chronicle snapshot ledger head does not match the manifest")
    if destination.exists() and not force:
        raise FileExistsError(f"Chronicle project state already exists: {project_id}")
    state_root = chronicle_home()
    state_root.mkdir(parents=True, exist_ok=True)
    state_root.chmod(0o700)
    registry_path = state_root / "registry.json"
    registry_snapshot = registry_path.read_bytes() if registry_path.exists() else None
    with tempfile.TemporaryDirectory(prefix="brief-spec-chronicle-restore-") as temporary:
        backup = Path(temporary) / "project"
        if destination.exists():
            shutil.copytree(destination, backup, symlinks=True)
        try:
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(mode=0o700)
            record = {
                **archived_project,
                "private_root": str(root),
                "root_sha256": sha256_bytes(str(root).encode()),
                "capture": "explicit-archive-restore",
            }
            atomic_write(
                destination / "project.json",
                json.dumps(record, indent=2, sort_keys=True).encode() + b"\n",
            )
            for name, content in contents.items():
                if not name.startswith(("events/", "receipts/")):
                    continue
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.parent.chmod(0o700)
                atomic_write(target, content)
            rebuilt = rebuild_index(project_id)
            restored_events = list(iter_events(project_id))
            if verify_chain(restored_events):
                raise ValueError("Restored event chain failed verification")
            upsert_registry_record(record)
        except Exception:
            if destination.exists():
                shutil.rmtree(destination)
            if backup.exists():
                shutil.copytree(backup, destination, symlinks=True)
            if registry_snapshot is None:
                registry_path.unlink(missing_ok=True)
            else:
                atomic_write(registry_path, registry_snapshot)
            raise
    return {
        "status": "RESTORED",
        "project_id": project_id,
        "project": str(root),
        "ledger_head_hash": event_values[-1]["event_hash"] if event_values else "0" * 64,
        **rebuilt,
    }


def doctor(project: Path, *, fix: bool = False, dry_run: bool = False) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    registration = registered_project(project)
    root = project_dir(registration["project_id"])
    owned_paths = list(root.rglob("*"))
    symlinks = [path for path in owned_paths if path.is_symlink()]
    checks.append(
        {
            "status": "FAIL" if symlinks else "PASS",
            "name": "state-symlinks",
            "detail": (
                ", ".join(str(path.relative_to(root)) for path in symlinks) if symlinks else "none"
            ),
        }
    )
    private_dirs = [
        root,
        *[path for path in owned_paths if not path.is_symlink() and path.is_dir()],
    ]
    permission_bits_supported = os.name != "nt"
    bad_dirs = (
        [path for path in private_dirs if path.stat().st_mode & 0o777 != 0o700]
        if permission_bits_supported
        else []
    )
    checks.append(
        {
            "status": "PASS" if not bad_dirs else "WARN",
            "name": "private-state-directories",
            "detail": (
                (
                    f"{len(private_dirs)} directories at 0700"
                    if permission_bits_supported
                    else "POSIX permission bits are not enforceable on Windows"
                )
                if not bad_dirs
                else f"{len(bad_dirs)} directories are not 0700"
            ),
        }
    )
    private_files = [path for path in owned_paths if not path.is_symlink() and path.is_file()]
    bad_files = (
        [path for path in private_files if path.stat().st_mode & 0o777 != 0o600]
        if permission_bits_supported
        else []
    )
    checks.append(
        {
            "status": "PASS" if not bad_files else "WARN",
            "name": "private-state-files",
            "detail": (
                (
                    f"{len(private_files)} file(s) at 0600"
                    if permission_bits_supported
                    else "POSIX permission bits are not enforceable on Windows"
                )
                if not bad_files
                else f"{len(bad_files)} file(s) are not 0600"
            ),
        }
    )
    events = list(iter_events(registration["project_id"]))
    errors = verify_chain(events)
    checks.append(
        {
            "status": "PASS" if not errors else "FAIL",
            "name": "event-chain",
            "detail": f"{len(events)} event(s)" if not errors else "; ".join(errors),
        }
    )
    index = root / "index.sqlite3"
    index_detail = "missing; rebuildable from events"
    index_status = "WARN"
    if index.is_file():
        try:
            connection = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
            try:
                count = int(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
                integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            finally:
                connection.close()
            if count == len(events) and integrity == "ok":
                index_status = "PASS"
                index_detail = f"healthy; {count} event(s) indexed"
            else:
                index_detail = (
                    f"index mismatch: {count}/{len(events)} event(s); integrity={integrity}"
                )
        except (OSError, sqlite3.DatabaseError) as exc:
            index_status = "WARN"
            index_detail = f"unreadable; rebuildable from events: {exc}"
    checks.append(
        {
            "status": index_status,
            "name": "derived-index",
            "detail": index_detail,
        }
    )
    repaired: dict[str, Any] | None = None
    if fix and not errors and not symlinks:
        if dry_run:
            operations = ["rebuild-index"]
            if permission_bits_supported:
                operations.insert(0, "chmod-private-state")
            repaired = {
                "status": "DRY-RUN",
                "operations": operations,
            }
        else:
            if permission_bits_supported:
                for path in private_dirs:
                    with suppress(OSError):
                        path.chmod(0o700)
                for path in private_files:
                    with suppress(OSError):
                        path.chmod(0o600)
            repaired = {
                "status": "PASS",
                "permissions": {
                    "enforced": permission_bits_supported,
                    "directories": len(private_dirs),
                    "files": len(private_files),
                },
                **rebuild_index(registration["project_id"]),
            }
            for check in checks:
                if check["name"] == "private-state-directories":
                    check.update(
                        status="PASS",
                        detail=(
                            f"{len(private_dirs)} directories at 0700"
                            if permission_bits_supported
                            else "POSIX permission bits are not enforceable on Windows"
                        ),
                    )
                elif check["name"] == "private-state-files":
                    check.update(
                        status="PASS",
                        detail=(
                            f"{len(private_files)} files at 0600"
                            if permission_bits_supported
                            else "POSIX permission bits are not enforceable on Windows"
                        ),
                    )
                elif check["name"] == "derived-index":
                    check.update(
                        status="PASS",
                        detail=f"healthy; {repaired['events']} event(s) indexed",
                    )
    status = (
        "FAIL"
        if any(item["status"] == "FAIL" for item in checks)
        else ("WARN" if any(item["status"] == "WARN" for item in checks) else "PASS")
    )
    return {
        "status": status,
        "project_id": registration["project_id"],
        "checks": checks,
        "fix": repaired,
    }
