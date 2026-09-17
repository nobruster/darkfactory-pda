from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from entities import EntityStore

_CONNECTOR_REGISTRY: dict[str, type] = {}


@dataclass
class ConnectorResult:
    entity_store: EntityStore | None = None
    table_count: int = 0
    routine_count: int = 0
    raw_metadata: Any = None
    schemas: tuple[str, ...] = field(default_factory=tuple)


def register_connector(name: str):
    def decorator(cls: type) -> type:
        _CONNECTOR_REGISTRY[name] = cls
        return cls

    return decorator


def get_connector(connector_type: str, **kwargs: Any):
    cls = _CONNECTOR_REGISTRY.get(connector_type)
    if not cls:
        available = sorted(_CONNECTOR_REGISTRY.keys())
        raise ValueError(
            f"Unknown connector: {connector_type!r}. Available: {available}"
        )
    return cls(**kwargs)
