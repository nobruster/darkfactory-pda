from __future__ import annotations

from typing import Any

from briefspec.harnesses import harness_adapter
from briefspec.models import Runtime


def runtime_capabilities(runtime: Runtime) -> dict[str, Any]:
    value = harness_adapter(runtime).capabilities()
    value["runtime"] = runtime.value  # compatibility alias through 0.x
    return value
