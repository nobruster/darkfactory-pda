from __future__ import annotations

import os
from pathlib import Path

from models import GenerationError


def _is_repository_root(path: Path) -> bool:
    return (
        (path / "contracts" / "types" / "registry.yaml").is_file()
        and (path / "gen" / "pyproject.toml").is_file()
    )


def find_repository_root() -> Path:
    configured = os.environ.get("NWP_EDP_ROOT")
    if configured:
        candidate = Path(configured).expanduser().resolve()
        if _is_repository_root(candidate):
            return candidate
        raise GenerationError("NWP_EDP_ROOT does not identify this repository")

    working_directory = Path.cwd().resolve()
    for candidate in (working_directory, *working_directory.parents):
        if _is_repository_root(candidate):
            return candidate

    source_candidate = Path(__file__).resolve().parents[2]
    if _is_repository_root(source_candidate):
        return source_candidate

    raise GenerationError(
        "Cannot locate the repository; provide --contracts-root and --output"
    )
