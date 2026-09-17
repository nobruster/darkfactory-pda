#!/usr/bin/env python3
"""Fail if an existing PyPI release contains different distribution bytes."""

from __future__ import annotations

import argparse
import email
import hashlib
import json
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path


def wheel_identity(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        metadata_name = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = email.message_from_bytes(archive.read(metadata_name))
    return str(metadata["Name"]), str(metadata["Version"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument(
        "--require-published",
        action="store_true",
        help="fail unless every local distribution is present on PyPI with the same digest",
    )
    args = parser.parse_args()
    projects: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    for wheel in sorted(args.dist.glob("*.whl")):
        name, version = wheel_identity(wheel)
        files = [wheel]
        normalized = name.lower().replace("-", "_")
        files.extend(args.dist.glob(f"{normalized}-{version}.tar.gz"))
        files.extend(args.dist.glob(f"{name.lower()}-{version}.tar.gz"))
        for path in files:
            projects[(name, version)][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for (name, version), local in sorted(projects.items()):
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                remote = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                if args.require_published:
                    raise SystemExit(f"{name} {version}: not yet on PyPI") from exc
                print(f"{name} {version}: not yet on PyPI")
                continue
            raise
        published = {item["filename"]: item["digests"]["sha256"] for item in remote.get("urls", [])}
        missing = sorted(set(local).difference(published))
        if args.require_published and missing:
            raise SystemExit(
                f"PyPI is missing {name} {version} distribution(s): {', '.join(missing)}"
            )
        for filename, digest in local.items():
            if filename in published and published[filename] != digest:
                raise SystemExit(
                    f"PyPI digest mismatch for {name} {version} {filename}: "
                    f"local {digest}, published {published[filename]}"
                )
        print(f"{name} {version}: existing PyPI files match local bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
