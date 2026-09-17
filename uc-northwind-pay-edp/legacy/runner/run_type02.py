"""Convenience Type 02 entrypoint backed by the public typed runner."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for module_directory in (
    ROOT / "legacy" / "runner",
    ROOT / "legacy" / "publisher",
    ROOT / "legacy" / "intake",
    ROOT / "legacy" / "postgres",
    ROOT / "validation" / "oracle",
):
    sys.path.insert(0, str(module_directory))

from workflow import main_for_adapter  # noqa: E402
from workflow_registry import TYPE02_WORKFLOW  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    """Run Type 02 without requiring an explicit ``--type`` argument."""

    return main_for_adapter(
        TYPE02_WORKFLOW,
        argv,
        description="Run the complete Type 02 legacy vertical slice.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
