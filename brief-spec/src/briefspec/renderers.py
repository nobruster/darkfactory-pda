from __future__ import annotations

from importlib import metadata
from pathlib import Path
from typing import Any, Protocol

from briefspec import __version__

_OFFICIAL_RENDERERS = {
    "pdf": "brief-spec-renderer-pdf",
    "audio": "brief-spec-renderer-audio",
}
_REGISTRATION_METADATA: dict[str, dict[str, str]] = {}


class Renderer(Protocol):
    name: str
    media_type: str
    filename: str

    def capabilities(self) -> dict[str, Any]: ...

    def render(
        self,
        delivery: dict[str, Any],
        output: Path,
        options: dict[str, Any],
    ) -> dict[str, Any]: ...

    def verify(self, artifact: Path) -> dict[str, Any]: ...


def _major_minor(version: str) -> tuple[int, int]:
    numbers = version.split(".", 2)
    try:
        return int(numbers[0]), int(numbers[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"invalid renderer version: {version}") from exc


def available_renderers(
    names: set[str] | None = None,
    *,
    official_only: bool = False,
) -> dict[str, Renderer]:
    """Load only explicitly requested renderer entry points when a name set is supplied."""
    discovered: dict[str, Renderer] = {}
    entry_points = metadata.entry_points()
    for group in ("briefspec.renderers", "brief_spec.renderers"):
        candidates = (
            entry_points.select(group=group)
            if hasattr(entry_points, "select")
            else entry_points.get(group, ())
        )
        for entry_point in candidates:
            entry_name = str(getattr(entry_point, "name", ""))
            if names is not None and entry_name not in names:
                continue
            if official_only:
                expected_distribution = _OFFICIAL_RENDERERS.get(entry_name)
                distribution = getattr(entry_point, "dist", None)
                distribution_name = str(getattr(distribution, "name", ""))
                distribution_version = str(getattr(distribution, "version", ""))
                if distribution_name.lower().replace("_", "-") != expected_distribution:
                    continue
                if _major_minor(distribution_version) != _major_minor(__version__):
                    continue
            factory = entry_point.load()
            renderer = factory() if isinstance(factory, type) else factory
            renderer_name = str(renderer.name)
            if names is not None and renderer_name not in names:
                continue
            discovered[renderer_name] = renderer
            distribution = getattr(entry_point, "dist", None)
            _REGISTRATION_METADATA[renderer_name] = {
                "renderer_distribution": str(getattr(distribution, "name", "unknown")),
                "renderer_distribution_version": str(getattr(distribution, "version", "unknown")),
                "renderer_entry_point_group": group,
            }
    return discovered


def render_with_plugin(
    name: str,
    delivery: dict[str, Any],
    output_dir: Path,
    *,
    force: bool = False,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    renderer = available_renderers().get(name)
    if renderer is None:
        raise ValueError(
            f"Renderer {name!r} is not installed. Install the matching Brief-Spec renderer package."
        )
    output = output_dir / renderer.filename
    if output.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite existing output: {output}")
    output_dir.mkdir(parents=True, exist_ok=True)
    record = renderer.render(delivery, output, options or {})
    metadata_value = record.get("metadata")
    plugin_metadata = _REGISTRATION_METADATA.get(name, {})
    record["metadata"] = {
        **(metadata_value if isinstance(metadata_value, dict) else {}),
        **plugin_metadata,
    }
    return record


def renderer_capabilities() -> list[dict[str, Any]]:
    return [
        {"name": name, **renderer.capabilities()}
        for name, renderer in sorted(available_renderers().items())
    ]


def setup_renderers(*, dry_run: bool = False) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name, renderer in sorted(available_renderers().items()):
        setup = getattr(renderer, "setup", None)
        if setup is None:
            results.append({"renderer": name, "status": "PASS", "detail": "no setup required"})
            continue
        result = setup(dry_run=dry_run)
        results.append({"renderer": name, **result})
    return results
