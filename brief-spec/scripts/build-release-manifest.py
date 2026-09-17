#!/usr/bin/env python3
"""Create a deterministic manifest for all release distributions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    files = []
    for path in sorted((*args.dist.glob("*.whl"), *args.dist.glob("*.tar.gz"))):
        content = path.read_bytes()
        files.append(
            {
                "filename": path.name,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    if not files:
        raise SystemExit("No wheel or source distribution found")
    repository = os.environ.get(
        "GITHUB_REPOSITORY",
        "luanmorenommaciel/brief-spec",
    )
    run_id = os.environ.get("GITHUB_RUN_ID")
    provenance_urls = []
    if run_id:
        provenance_urls.append(f"https://github.com/{repository}/actions/runs/{run_id}")
    manifest = {
        "schema_version": "1.0",
        "kind": "brief-spec-release-manifest",
        "distribution": "brief-spec",
        "version": project["version"],
        "python_requires": project["requires-python"],
        "supported_harnesses": {
            "live-verified": ["codex", "claude", "omp", "grok", "kimi"],
            "hold": [],
            "experimental": ["copilot", "cursor", "goose"],
        },
        "schema_versions": {
            "outcome_brief": "1.0",
            "session_checkpoint": "1.0",
            "delivery": "2.0",
            "bundle_manifest": "2.0",
            "delivery_receipt": "2.0",
        },
        "source_revision": os.environ.get("GITHUB_SHA"),
        "provenance_urls": provenance_urls,
        "files": files,
    }
    destination = args.dist / "release-manifest.json"
    destination.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    checksums = args.dist / "SHA256SUMS"
    checksums.write_text(
        "".join(f"{record['sha256']}  {record['filename']}\n" for record in files),
        encoding="utf-8",
    )
    print(destination)
    print(checksums)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
