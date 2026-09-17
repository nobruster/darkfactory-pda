from __future__ import annotations

import shutil
import sys
from pathlib import Path

from config import repository_root


def main() -> int:
    root = repository_root().resolve()
    targets = (
        root / ".runtime",
        root / "evidence",
    )
    for target in targets:
        resolved_parent = target.parent.resolve()
        if (
            resolved_parent != root
            or target == root
            or target.is_symlink()
        ):
            print("refusing unsafe runtime cleanup target", file=sys.stderr)
            return 2
    for target in targets:
        if target.exists():
            shutil.rmtree(target)
    print("disposable runtime and evidence removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

