#!/usr/bin/env python3
"""MCP stdio entry: catalog tools over ontology/output/graph.json."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp_stdio import serve_stdio  # noqa: E402


def main() -> int:
    try:
        serve_stdio()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
