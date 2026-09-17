#!/usr/bin/env python3
"""Authorize exact CI-built bytes only after the retained live-host matrix passes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument(
        "--live-evidence",
        type=Path,
        default=ROOT / "release" / "live-e2e-evidence.json",
    )
    args = parser.parse_args()
    check = subprocess.run(
        [
            sys.executable,
            "scripts/build-live-e2e-evidence.py",
            "--check",
            "--require-authorized",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if check.returncode:
        raise SystemExit(check.stderr.strip() or check.stdout.strip())
    with (ROOT / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    dist = args.dist.resolve()
    dist.mkdir(parents=True, exist_ok=True)
    evidence_source = args.live_evidence.resolve()
    evidence_target = dist / "live-e2e-evidence.json"
    shutil.copy2(evidence_source, evidence_target)
    evidence_sha256 = hashlib.sha256(evidence_target.read_bytes()).hexdigest()
    authorization = {
        "schema_version": "1.0",
        "kind": "brief-spec-release-authorization",
        "sha": args.sha,
        "version": version,
        "workflow_run_id": args.run_id,
        "gates": [
            "python-matrix",
            "plugin-hosts",
            "project-hooks",
            "hermetic-none",
            "hermetic-fake",
            "pdf",
            "browser",
            "audio",
            "clean-wheel",
            "clean-sdist",
            "live-host-matrix",
        ],
        "live_e2e_sha256": evidence_sha256,
        "status": "authorized",
    }
    destination = dist / "release-authorization.json"
    destination.write_text(
        json.dumps(authorization, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
