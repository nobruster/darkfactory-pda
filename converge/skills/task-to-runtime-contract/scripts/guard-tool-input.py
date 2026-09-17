#!/usr/bin/env python3
"""Vendor-hook bridge: read tool JSON from stdin and guard every candidate path."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


PATH_KEYS = {
    "file_path",
    "notebook_path",
    "path",
    "target_path",
    "destination",
}


def collect(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in PATH_KEYS and isinstance(item, str):
                found.append(item)
            else:
                found.extend(collect(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(collect(item))
    return found


def main() -> int:
    profile = os.environ.get("CVG_EXECUTION_PROFILE", "")
    if not profile:
        print("CVG_EXECUTION_PROFILE is required", file=sys.stderr)
        return 2
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"invalid tool-input JSON: {exc}", file=sys.stderr)
        return 2
    paths = sorted(set(collect(payload)))
    if not paths:
        return 0
    guard = Path(__file__).with_name("check-path-policy.py")
    command = [sys.executable, str(guard), "--profile", profile]
    for path in paths:
        command.extend(["--candidate", path])
    checked = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if checked.returncode == 0:
        # Exit 0 with no output means "no hook decision"; normal permission
        # handling continues.
        return 0

    reason = (checked.stdout + "\n" + checked.stderr).strip()
    if not reason:
        reason = "Converge path policy refused this tool call."
    # Claude Code PreToolUse consumes this exact structured decision. Returning
    # the child guard's rc=1 with plain stdout does NOT block a tool; either exit
    # 2 or permissionDecision=deny is required. JSON keeps the diagnostic
    # machine-readable and lets Claude explain the refusal.
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason[:4000],
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
