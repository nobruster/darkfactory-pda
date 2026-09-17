from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from briefspec.events import load_event_bytes

from brief_spec_chronicle import __version__
from brief_spec_chronicle.derive import build_snapshot
from brief_spec_chronicle.operations import (
    archive_project,
    doctor,
    export_approved_lesson,
    lessons,
    record_decision,
    restore_project,
    review_lesson,
)
from brief_spec_chronicle.rendering import export_snapshot, pretty_json_bytes, verify_export
from brief_spec_chronicle.sources import normalize_source_event
from brief_spec_chronicle.storage import (
    atomic_external_write,
    delete_project,
    ingest_event,
    init_project,
    iter_events,
    registered_project,
)


def _read(path: str, *, event: bool = False) -> dict[str, Any]:
    content = sys.stdin.buffer.read() if path == "-" else Path(path).read_bytes()
    if event:
        return load_event_bytes(content)
    value = json.loads(content)
    if not isinstance(value, dict):
        raise ValueError("Input must be a JSON object")
    return value


def _print(value: Any, as_json: bool) -> None:
    if as_json or isinstance(value, (dict, list)):
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="brief-spec-chronicle",
        description="Explicit, evidence-bound project continuity for Brief-Spec.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("--project", required=True, type=Path)
    init.add_argument("--name")
    init.add_argument("--json", action="store_true")

    ingest = commands.add_parser("ingest")
    ingest.add_argument("input")
    ingest.add_argument("--project", required=True, type=Path)
    ingest.add_argument("--source", required=True)
    ingest.add_argument("--observed-at")
    ingest.add_argument("--dry-run", action="store_true")
    ingest.add_argument("--json", action="store_true")

    status = commands.add_parser("status")
    status.add_argument("--project", required=True, type=Path)
    status.add_argument("--as-of")
    status.add_argument("--json", action="store_true")

    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--project", required=True, type=Path)
    snapshot.add_argument("--since")
    snapshot.add_argument("--until")
    snapshot.add_argument("--created-at")
    snapshot.add_argument("--ledger-cutoff", help="Replay through this ingest-order event ID")
    snapshot.add_argument("--output", required=True, type=Path)
    snapshot.add_argument("--force", action="store_true")
    snapshot.add_argument("--json", action="store_true")

    export = commands.add_parser("export")
    export.add_argument("snapshot", type=Path)
    export.add_argument(
        "--formats",
        default="markdown,json,html",
        help="markdown,json,html,zip,spoken-text,pdf,audio,video",
    )
    export.add_argument("--output-dir", required=True, type=Path)
    export.add_argument("--force", action="store_true")
    export.add_argument("--pdf-page-format", choices=["A4", "Letter"], default="A4")
    export.add_argument("--audio-provider", choices=["macos", "openai"], default="macos")
    export.add_argument("--voice")
    export.add_argument("--rate", type=int, default=190)
    export.add_argument("--consent-network", action="store_true")
    export.add_argument("--json", action="store_true")

    verify = commands.add_parser("verify")
    verify.add_argument("target", type=Path)
    verify.add_argument(
        "--level", choices=["structural", "resolved", "rendered"], default="structural"
    )
    verify.add_argument("--workspace", type=Path)
    verify.add_argument("--offline", action="store_true")
    verify.add_argument("--json", action="store_true")

    decision = commands.add_parser("decision")
    decision_commands = decision.add_subparsers(dest="decision_command", required=True)
    decision_record = decision_commands.add_parser("record")
    decision_record.add_argument("input")
    decision_record.add_argument("--project", required=True, type=Path)
    decision_record.add_argument("--observed-at")
    decision_record.add_argument("--json", action="store_true")

    lesson = commands.add_parser("lessons")
    lesson_commands = lesson.add_subparsers(dest="lesson_command", required=True)
    lesson_list = lesson_commands.add_parser("list")
    lesson_list.add_argument("--project", required=True, type=Path)
    lesson_list.add_argument("--json", action="store_true")
    approve = lesson_commands.add_parser("approve")
    approve.add_argument("lesson_id")
    approve.add_argument("--project", required=True, type=Path)
    approve.add_argument("--output", required=True, type=Path)
    approve.add_argument("--reason", default="Approved for proposal export")
    approve.add_argument("--owner", default="human")
    approve.add_argument("--force", action="store_true")
    approve.add_argument("--json", action="store_true")
    reject = lesson_commands.add_parser("reject")
    reject.add_argument("lesson_id")
    reject.add_argument("--project", required=True, type=Path)
    reject.add_argument("--reason", required=True)
    reject.add_argument("--owner", default="human")
    reject.add_argument("--json", action="store_true")

    archive = commands.add_parser("archive")
    archive.add_argument("--project", required=True, type=Path)
    archive.add_argument("--output", required=True, type=Path)
    archive.add_argument("--force", action="store_true")
    archive.add_argument("--json", action="store_true")

    restore = commands.add_parser("restore")
    restore.add_argument("archive", type=Path)
    restore.add_argument("--project", required=True, type=Path)
    restore.add_argument("--force", action="store_true")
    restore.add_argument("--json", action="store_true")

    delete = commands.add_parser("delete")
    delete.add_argument("--project-id", required=True)
    delete.add_argument("--confirm", required=True)
    delete.add_argument("--json", action="store_true")

    diagnose = commands.add_parser("doctor")
    diagnose.add_argument("--project", required=True, type=Path)
    diagnose.add_argument("--fix", action="store_true")
    diagnose.add_argument("--dry-run", action="store_true")
    diagnose.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            value = init_project(args.project, name=args.name)
        elif args.command == "ingest":
            source_value = _read(args.input, event=True)
            value = ingest_event(
                args.project,
                normalize_source_event(source_value, source_system=args.source),
                source_system=args.source,
                observed_at=args.observed_at,
                dry_run=args.dry_run,
            )
        elif args.command == "status":
            registration = registered_project(args.project)
            events = list(iter_events(registration["project_id"]))
            if args.as_of:
                events = [event for event in events if event["occurred_at"] <= args.as_of]
            value = {
                "status": "ACTIVE",
                "project_id": registration["project_id"],
                "project": registration["name"],
                "events": len(events),
                "ledger_head_hash": events[-1]["event_hash"] if events else None,
                "latest": events[-1] if events else None,
            }
        elif args.command == "snapshot":
            snapshot = build_snapshot(
                args.project,
                since=args.since,
                until=args.until,
                created_at=args.created_at,
                ledger_cutoff=args.ledger_cutoff,
            )
            atomic_external_write(args.output, pretty_json_bytes(snapshot), force=args.force)
            value = {
                "status": "CREATED",
                "path": str(args.output),
                "canonical_sha256": snapshot["canonical_sha256"],
            }
        elif args.command == "export":
            snapshot = _read(str(args.snapshot))
            value = export_snapshot(
                snapshot,
                args.output_dir,
                formats={item.strip() for item in args.formats.split(",") if item.strip()},
                force=args.force,
                options={
                    "page_format": args.pdf_page_format,
                    "provider": args.audio_provider,
                    "voice": args.voice,
                    "rate": args.rate,
                    "consent_network": args.consent_network,
                },
            )
        elif args.command == "verify":
            value = verify_export(
                args.target,
                level=args.level,
                workspace=args.workspace,
                offline=args.offline,
            )
        elif args.command == "decision":
            value = record_decision(args.project, _read(args.input), observed_at=args.observed_at)
        elif args.command == "lessons":
            if args.lesson_command == "list":
                value = lessons(args.project)
            elif args.lesson_command == "approve":
                review_lesson(
                    args.project,
                    args.lesson_id,
                    choice="approved",
                    reason=args.reason,
                    owner=args.owner,
                )
                value = export_approved_lesson(
                    args.project, args.lesson_id, args.output, force=args.force
                )
            else:
                value = review_lesson(
                    args.project,
                    args.lesson_id,
                    choice="rejected",
                    reason=args.reason,
                    owner=args.owner,
                )
        elif args.command == "archive":
            value = archive_project(args.project, args.output, force=args.force)
        elif args.command == "restore":
            value = restore_project(args.archive, args.project, force=args.force)
        elif args.command == "delete":
            value = delete_project(args.project_id, args.confirm)
        else:
            value = doctor(args.project, fix=args.fix, dry_run=args.dry_run)
        _print(value, getattr(args, "json", False))
        if isinstance(value, dict) and value.get("status") == "FAIL":
            return 1
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"brief-spec-chronicle: {exc}", file=sys.stderr)
        return 2
