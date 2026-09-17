from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from generation import generate
from models import GenerationError
from paths import find_repository_root


def build_parser() -> argparse.ArgumentParser:
    """Build the stable command-line interface for deterministic generation."""

    parser = argparse.ArgumentParser(
        prog="datagen",
        description="Generate deterministic NorthWind Pay raw source artifacts.",
    )
    parser.add_argument("--type", required=True, dest="type_number")
    parser.add_argument("--scenario", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Artifact output root (default: <repository>/gen/output).",
    )
    parser.add_argument(
        "--contracts-root",
        type=Path,
        default=None,
        help="Override contracts/types for contract tests.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run DataGen and translate safe domain failures into exit code 2."""

    args = build_parser().parse_args(argv)
    try:
        repository_root: Path | None = None
        if args.output is None or args.contracts_root is None:
            repository_root = find_repository_root()
        output_root = args.output
        if output_root is None:
            assert repository_root is not None
            output_root = repository_root / "gen" / "output"
        contracts_root = args.contracts_root
        if contracts_root is None:
            assert repository_root is not None
            contracts_root = repository_root / "contracts" / "types"
        bundle = generate(
            type_number=args.type_number,
            scenario=args.scenario,
            output_root=output_root,
            contracts_root=contracts_root,
        )
    except GenerationError as exc:
        print(f"generation failed: {exc}", file=sys.stderr)
        return 2

    print(f"generated batch: {bundle.batch_id}")
    print(f"artifact directory: {bundle.directory}")
    print(f"raw sha256: {bundle.raw_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
