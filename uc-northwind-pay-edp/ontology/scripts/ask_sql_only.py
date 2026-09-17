#!/usr/bin/env python3
"""Without-graph Floor entry: same question, legacy/postgres SQL only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from retrieve import CANONICAL_QUESTION  # noqa: E402
from sql_only import answer_from_sql  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Answer the Day 1 paid question from SQL grep only."
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=CANONICAL_QUESTION,
        help="Defaults to the Day 1 without/with question.",
    )
    args = parser.parse_args()
    question = (args.question or "").strip() or CANONICAL_QUESTION
    try:
        print(answer_from_sql(question), end="")
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
