#!/usr/bin/env python3
"""Grant command: crawl live Postgres into ontology/output/graph.json."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pipeline import crawl_sync  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        graph = crawl_sync(ROOT / "output")
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    summary = graph["summary"]
    print(f"schemas: {', '.join(graph['schemas']) or '(none)'}")
    print(f"tables:  {summary['table_count']}")
    print(f"routines: {summary['routine_count']}")
    for name in summary["routine_names"]:
        print(f"  - {name}")
    recon = [
        t["qualified_name"]
        for t in graph["tables"]
        if t["qualified_name"].startswith("reporting.")
        and t["qualified_name"].endswith("_reconciliation")
    ]
    apply_fn = [
        r["qualified_name"]
        for r in graph["routines"]
        if r["qualified_name"].startswith("legacy.apply_")
    ]
    if recon and apply_fn:
        print(f"paid lives on {recon[0]}, written by {apply_fn[0]}")
    print(f"wrote {ROOT / 'output' / 'graph.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
