#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "brief-spec-chronicle" / "src"))

from brief_spec_chronicle.derive import build_snapshot  # noqa: E402
from brief_spec_chronicle.operations import archive_project, restore_project  # noqa: E402
from brief_spec_chronicle.rendering import export_snapshot, verify_export  # noqa: E402
from brief_spec_chronicle.sources import normalize_source_event  # noqa: E402
from brief_spec_chronicle.storage import (  # noqa: E402
    delete_project,
    ingest_event,
    init_project,
    iter_events,
)

from briefspec.artifacts import sha256_bytes  # noqa: E402

TIMES = [f"2026-08-14T13:{minute:02}:00+00:00" for minute in range(20)]


def _ingest(project: Path, source: str, value: dict[str, Any], index: int) -> dict[str, Any]:
    return ingest_event(
        project,
        normalize_source_event(value, source_system=source),
        source_system=source,
        observed_at=TIMES[index],
    )


def run() -> dict[str, Any]:
    previous_home = os.environ.get("BRIEF_SPEC_HOME")
    try:
        with tempfile.TemporaryDirectory(prefix="brief-spec-chronicle-e2e-") as temporary:
            root = Path(temporary)
            os.environ["BRIEF_SPEC_HOME"] = str(root / "state")
            project = root / "journey"
            project.mkdir()
            proof = project / "proof.txt"
            proof.write_text("journey verified\n", encoding="utf-8")
            registration = init_project(project, name="Seamwise Task-Spec Converge Journey")
            _ingest(
                project,
                "seamwise",
                {
                    "schema": "seamwise/1.0",
                    "intent_id": "intent-continuity",
                    "intent": "Deliver evidence-bound human continuity",
                    "phase": "intent",
                },
                0,
            )
            _ingest(
                project,
                "task-spec",
                {
                    "kind": "task-handoff",
                    "task_id": "task-chronicle",
                    "intent_ref": "intent-continuity",
                    "goal": "Implement and verify Chronicle",
                    "phase": "declared",
                    "constraints": ["No raw transcripts", "Explicit activation only"],
                },
                1,
            )
            _ingest(
                project,
                "converge",
                {
                    "event_kind": "TASK_STARTED",
                    "task_ref": "task-chronicle",
                    "intent_ref": "intent-continuity",
                    "headline": "Authorized Chronicle implementation began",
                    "authorization_ref": "authorization-chronicle",
                    "phase": "execution",
                },
                2,
            )
            ingest_event(
                project,
                {
                    "kind": "HUMAN_NOTE",
                    "importance": "notable",
                    "access": "local",
                    "occurred_at": TIMES[3],
                    "headline": "The renderer work became an explained detour",
                    "method_context": {
                        "method": "converge",
                        "phase": "execution",
                        "intent_ref": "intent-continuity",
                        "task_ref": "task-chronicle",
                    },
                    "entity_refs": ["task-chronicle"],
                    "evidence_ids": [],
                    "details": {
                        "signal": "detour",
                        "reason": "Reusable renderer helpers reduce duplicated delivery logic",
                    },
                },
                source_system="human",
                observed_at=TIMES[3],
            )
            proof_id = f"file:proof.txt#sha256={sha256_bytes(proof.read_bytes())}"
            for index, (kind, headline) in enumerate(
                (
                    ("TASK_COMPLETED", "Chronicle implementation completed with proof"),
                    ("TASK_ACCEPTED", "Chronicle implementation independently accepted"),
                ),
                start=4,
            ):
                ingest_event(
                    project,
                    {
                        "kind": kind,
                        "importance": "notable",
                        "access": "local",
                        "occurred_at": TIMES[index],
                        "headline": headline,
                        "method_context": {
                            "method": "converge",
                            "phase": "settlement",
                            "intent_ref": "intent-continuity",
                            "task_ref": "task-chronicle",
                        },
                        "entity_refs": ["task-chronicle"],
                        "evidence_ids": [proof_id],
                        "details": {
                            "next": ["Review the Human Review Pack"]
                            if kind == "TASK_ACCEPTED"
                            else []
                        },
                    },
                    source_system="converge",
                    observed_at=TIMES[index],
                )
            snapshot = build_snapshot(project, created_at=TIMES[6])
            output = root / "review-pack"
            export_snapshot(snapshot, output, formats={"markdown", "json", "html", "zip"})
            rendered = verify_export(
                output,
                level="rendered",
                workspace=project,
                offline=True,
            )
            if rendered["status"] != "PASS":
                raise RuntimeError(f"Chronicle E2E verification failed: {rendered}")
            bundle_verified = verify_export(
                output / "chronicle.zip", level="rendered", workspace=project
            )
            if bundle_verified["status"] != "PASS":
                raise RuntimeError(f"Chronicle ZIP verification failed: {bundle_verified}")
            archive = root / "archive.zip"
            archive_project(project, archive)
            delete_project(registration["project_id"], registration["project_id"])
            restored_root = root / "restored"
            restored_root.mkdir()
            restored = restore_project(archive, restored_root)
            restored_events = list(iter_events(registration["project_id"]))
            return {
                "status": "PASS",
                "project_id": registration["project_id"],
                "events": len(restored_events),
                "snapshot_sha256": snapshot["canonical_sha256"],
                "ledger_head_hash": snapshot["ledger_head_hash"],
                "bundle_sha256": sha256_bytes((output / "chronicle.zip").read_bytes()),
                "archive_sha256": sha256_bytes(archive.read_bytes()),
                "restored": restored["status"],
            }
    finally:
        if previous_home is None:
            os.environ.pop("BRIEF_SPEC_HOME", None)
        else:
            os.environ["BRIEF_SPEC_HOME"] = previous_home


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
