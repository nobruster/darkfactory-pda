"""Public CLI for complete typed legacy batch workflows."""

from __future__ import annotations

import argparse
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

from workflow import run_cli_selection  # noqa: E402
from workflow_registry import WORKFLOWS, workflow_for_type  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the one public command surface shared by every file type."""

    parser = argparse.ArgumentParser(
        description="Run one complete typed legacy vertical slice.",
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=tuple(WORKFLOWS),
        dest="type_number",
        help="Two-digit contract file type.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--scenario",
        help="Canonical scenario implemented by the selected type.",
    )
    source.add_argument(
        "--file",
        type=Path,
        help=(
            "Raw file whose parent contains its checksum and "
            "source-manifest.json."
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / ".runtime" / "generated",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=ROOT / "evidence",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Resolve the type before entering the shared lifecycle engine."""

    args = build_parser().parse_args(argv)
    adapter = workflow_for_type(args.type_number)
    return run_cli_selection(
        adapter,
        scenario=args.scenario,
        raw_file=args.file,
        output_root=args.output_root,
        evidence_root=args.evidence_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
