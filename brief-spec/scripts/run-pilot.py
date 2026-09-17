#!/usr/bin/env python3
"""Validate the synthetic Apex pilot corpus."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from briefspec.markdown import validate_checkpoint, validate_outcome  # noqa: E402


def main() -> int:
    failures: list[str] = []
    scenarios = ROOT / "pilots" / "apex" / "scenarios"
    files = sorted(scenarios.glob("*.md"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        result = (
            validate_outcome(text)
            if path.name.endswith(".outcome.md")
            else validate_checkpoint(text)
        )
        label = "PASS" if result.valid else "FAIL"
        print(f"{label} {path.relative_to(ROOT)}")
        if not result.valid:
            failures.extend(f"{path.name}: {error}" for error in result.errors)
    if not files:
        failures.append("No pilot scenarios found")
    for failure in failures:
        print(f"  {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
