"""Canonical Brief-Spec package.

The implementation remains import-compatible with the historical ``briefspec``
package throughout the 0.x line.  Sharing the legacy package search path makes
``brief_spec.<module>`` imports resolve to the same dependency-free sources
without maintaining two divergent implementations.
"""

from __future__ import annotations

from briefspec import __path__ as _legacy_path
from briefspec import __version__

__all__ = ["__version__"]
__path__ = _legacy_path
