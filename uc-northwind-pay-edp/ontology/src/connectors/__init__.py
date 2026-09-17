"""Postgres-only connector registry."""

from .registry import ConnectorResult, get_connector, register_connector
from . import postgres as _postgres  # noqa: F401

__all__ = [
    "ConnectorResult",
    "get_connector",
    "register_connector",
]
