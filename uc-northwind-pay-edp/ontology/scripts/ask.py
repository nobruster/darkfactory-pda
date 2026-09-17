#!/usr/bin/env python3
"""Floor CLI: ask the catalog without wiring an MCP client."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from retrieve import CANONICAL_QUESTION, catalog_ask, format_ask, load_graph  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask the NorthWind Pay catalog graph.")
    parser.add_argument(
        "question",
        nargs="?",
        default=CANONICAL_QUESTION,
        help="Defaults to the Day 1 without/with question.",
    )
    parser.add_argument("--json", action="store_true", help="Print structured JSON.")
    args = parser.parse_args()
    question = (args.question or "").strip() or CANONICAL_QUESTION
    try:
        graph = load_graph()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    result = catalog_ask(graph, question)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_ask(result))
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
