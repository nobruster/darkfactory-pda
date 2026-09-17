#!/usr/bin/env python3
"""Render the agent context from the canonical CLI command matrix."""

from __future__ import annotations

import argparse
import json
import pathlib


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True, type=pathlib.Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    commands = matrix.get("commands")
    if matrix.get("contract") != "ConvergeCLICommandMatrix/v1" or not isinstance(commands, list):
        raise SystemExit("invalid Converge CLI command matrix")
    if matrix.get("command_count") != len(commands):
        raise SystemExit("Converge CLI command matrix count drift")
    manifest = {
        "schema_version": "1.0",
        "contract": "ConvergeAgentContext/v1",
        "tool": "cvg",
        "version": args.version,
        "role": "composition coordinator and assurance referee",
        "description": (
            "Converge sequences independently versioned Seamwise and Task-Spec engines, "
            "binds execution, and verifies settlement without taking over either engine's authority."
        ),
        "contracts": {
            "stdout": "human output by default; one ConvergeCLIResult/v1 document under --json",
            "stderr": "diagnostics and progress only outside --json",
            "token": "every verdict surface ends in one stable greppable token",
            "color": "TTY-only; NO_COLOR or CVG_COLOR=0 disables ANSI",
            "determinism": "read-only and dry-run calls preserve project state",
            "resolution": (
                "CVG_HOME selects Converge, CVG_PROJECT_ROOT selects the project, "
                "CVG_TASKSPEC_BIN and CVG_SEAMWISE_BIN select external engines"
            ),
            "command_matrix": "contracts/cli-command-matrix.json",
        },
        "global_flags": [
            {
                "flag": "--json",
                "position": "any",
                "effect": "emit exactly one ConvergeCLIResult/v1 document and preserve the underlying exit code",
            },
            {
                "flag": "--dry-run",
                "position": "any",
                "effect": "prevent mutating command forms; read-only forms still execute",
            },
        ],
        "exit_codes": [
            {"code": 0, "name": "OK", "retryable": False, "side_effects": "declared by command"},
            {"code": 1, "name": "CONTRACT_FAIL", "retryable": False, "side_effects": "none after failure"},
            {"code": 2, "name": "USAGE_ERROR", "retryable": False, "side_effects": "none"},
            {"code": 3, "name": "ENGINE_UNAVAILABLE", "retryable": True, "side_effects": "none"},
            {"code": 20, "name": "SKIP", "retryable": True, "side_effects": "none"},
            {"code": 21, "name": "TIMEOUT", "retryable": True, "side_effects": "none"},
            {"code": 22, "name": "ENGINE_ERROR", "retryable": True, "side_effects": "none"},
        ],
        "commands": commands,
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
