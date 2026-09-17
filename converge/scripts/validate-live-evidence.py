#!/usr/bin/env python3
"""Validate the retained authenticated composed-demo evidence."""

from __future__ import annotations

import json
import pathlib
import re

import jsonschema

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/releases/v0.2.0/live-codex"
EXPECTED_COMMITS = {
    "task_spec": "0e6180cfc3009bd4ef9cf7ab050b463e10d4af91",
    "seamwise": "5a398169c3fefcb65eb1a47c0cb4f967dfdc0515",
}
SECRET_ASSIGNMENT = re.compile(
    r"(?:OPENAI|GITHUB|TASKSPEC|ANTHROPIC)_[A-Z_]*?(?:KEY|TOKEN)\s*[=:]",
    re.IGNORECASE,
)


def read_json(name: str) -> dict[str, object]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def main() -> int:
    if not EVIDENCE.is_dir():
        raise SystemExit("LIVE_EVIDENCE=BLOCKED reason=canonical_evidence_missing")

    environment = read_json("environment.json")
    assert environment["release_candidate_commits"] == EXPECTED_COMMITS
    assert environment["release_candidate_provenance_verified"] is True
    versions = environment["versions"]
    assert isinstance(versions, dict)
    assert versions["task_spec"] == "3.8.0"
    assert versions["seamwise"] == "seamwise, version 0.2.0"
    assert environment["credentials_recorded"] is False

    composition = read_json("composition-receipt.json")
    schema = json.loads(
        (ROOT / "contracts/converge-composition-receipt-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.validate(composition, schema)
    assert composition["dispatch_authorized"] is False

    snapshot = read_json("final-snapshot.json")
    assert snapshot["accepted"] is True
    assert snapshot["working_tree_clean"] is True
    acceptance = read_json("acceptance-record.json")
    outcome = acceptance["outcome"]
    assert isinstance(outcome, dict) and outcome["status"] == "accepted"

    settlement = (EVIDENCE / "10-settlement.txt").read_text(encoding="utf-8")
    assert "TASK_LOOP=LOCAL_SETTLED" in settlement or "TASK_LOOP=SETTLED" in settlement
    assert "ACCEPTED=1" in settlement
    status = read_json("11-final-status.json")
    data = status["data"]
    assert isinstance(data, dict)
    assert data["next_action"] == "all composed tasks are independently accepted"

    files = [path for path in EVIDENCE.iterdir() if path.is_file()]
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "/Users/luanmorenomaciel" not in text
        # TaskHandoff/v3 binds the exact ephemeral workspace. Redacting those
        # paths would invalidate its digest, so only this typed artifact may
        # retain a non-secret /var/folders path.
        if path.name != "task-handoff.json":
            assert "/var/folders/" not in text
        assert SECRET_ASSIGNMENT.search(text) is None

    print(f"LIVE_EVIDENCE=READY files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
