from __future__ import annotations

from pathlib import Path


def resource_root() -> Path:
    """Return canonical assets in source checkouts and wheel installations."""
    package_resources = Path(__file__).resolve().parent / "resources"
    if package_resources.is_dir():
        return package_resources
    repository = Path(__file__).resolve().parents[2]
    if (repository / "skills").is_dir():
        return repository
    raise FileNotFoundError("Brief-Spec installable resources are unavailable")


def repository_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "pyproject.toml").is_file() and (candidate / "skills").is_dir():
        return candidate
    return None
