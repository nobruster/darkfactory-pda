#!/usr/bin/env python3
"""Build the self-contained canonical Brief-Spec 0.5.0 schema bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_NAMES = (
    "brief-spec-evidence.schema.json",
    "brief-spec-outcome-brief.schema.json",
    "brief-spec-session-checkpoint.schema.json",
    "brief-spec-delivery.schema.json",
    "brief-spec-bundle-manifest.schema.json",
    "brief-spec-delivery-receipt.schema.json",
    "brief-spec-event.schema.json",
)
BUNDLE_ID = (
    "https://github.com/luanmorenommaciel/brief-spec/releases/download/v0.5.0/"
    "brief-spec-schemas.bundle.json"
)


def build_bundle(schema_dir: Path) -> dict[str, object]:
    resources = {
        name.removesuffix(".schema.json").replace("-", "_"): json.loads(
            (schema_dir / name).read_text(encoding="utf-8")
        )
        for name in SCHEMA_NAMES
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": BUNDLE_ID,
        "title": "Brief-Spec 0.5.0 offline compound schema",
        "$ref": resources["brief_spec_delivery"]["$id"],  # type: ignore[index]
        "$defs": resources,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle = build_bundle(ROOT / "schemas")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
