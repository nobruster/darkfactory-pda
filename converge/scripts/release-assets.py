#!/usr/bin/env python3
"""Assemble deterministic Converge GitHub release assets and provenance."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import tarfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_evidence(source: Path, destination: Path) -> None:
    files = sorted(
        path for path in source.rglob("*") if path.is_file() and not path.is_symlink()
    )
    if not files:
        raise SystemExit(f"stable release evidence is empty: {source}")
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in files:
                    relative = Path("evidence") / path.relative_to(source)
                    info = archive.gettarinfo(str(path), arcname=relative.as_posix())
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    with path.open("rb") as handle:
                        archive.addfile(info, handle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, default=None)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--ci-run-url", required=True)
    parser.add_argument("--product-commit", default="")
    parser.add_argument("--evidence-commit", default="")
    parser.add_argument(
        "--taskspec-commit", default="0e6180cfc3009bd4ef9cf7ab050b463e10d4af91"
    )
    parser.add_argument(
        "--seamwise-commit", default="5a398169c3fefcb65eb1a47c0cb4f967dfdc0515"
    )
    args = parser.parse_args()

    if not args.package.is_file():
        raise SystemExit(f"release input is missing: {args.package}")
    if args.pdf is not None and not args.pdf.is_file():
        raise SystemExit(f"release input is missing: {args.pdf}")
    if not args.evidence.is_dir():
        raise SystemExit(f"stable release evidence is missing: {args.evidence}")

    args.out.mkdir(parents=True, exist_ok=True)
    package = args.out / args.package.name
    evidence = args.out / "converge-v0.2.0-evidence.tar.gz"
    shutil.copyfile(args.package, package)
    archive_evidence(args.evidence, evidence)
    shipped = [package, evidence]
    if args.pdf is not None:
        guide = args.out / "converge-v0.2.0.pdf"
        shutil.copyfile(args.pdf, guide)
        shipped.append(guide)

    artifacts = []
    checksum_lines = []
    for path in shipped:
        digest = sha256(path)
        artifacts.append(
            {"name": path.name, "sha256": digest, "bytes": path.stat().st_size}
        )
        checksum_lines.append(f"{digest}  {path.name}")

    manifest = {
        "contract": "ConvergeReleaseManifest/v1",
        "product": "converge",
        "version": "0.2.0",
        "source": {
            "commit": args.source_commit,
            "ref": args.source_ref,
            "product_commit": args.product_commit or args.source_commit,
            "evidence_commit": args.evidence_commit or args.source_commit,
        },
        "dependencies": [
            {
                "product": "task-spec",
                "version": "3.8.0",
                "commit": args.taskspec_commit,
            },
            {
                "product": "seamwise",
                "version": "0.2.0",
                "commit": args.seamwise_commit,
            },
        ],
        "artifacts": artifacts,
        "ci": {"run_url": args.ci_run_url},
    }
    (args.out / "release-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
