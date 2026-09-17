"""Type 01 emit entry: same contract raw bytes the live line already reads."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_MAIN = REPO_ROOT / "contracts" / "types" / "01-card-settlement" / "main"
SCENARIOS = {
    "valid-minimal": CONTRACT_MAIN / "valid-minimal.dat",
    "valid-boundary": CONTRACT_MAIN / "valid-boundary.dat",
    "negative-overpunch": CONTRACT_MAIN / "negative-overpunch.dat",
    "df-source-001": CONTRACT_MAIN / "df-source-001.dat",
    "malformed": CONTRACT_MAIN / "malformed.dat",
}


def _load_handler():  # type: ignore[no-untyped-def]
    path = (
        Path(__file__).resolve().parent
        / "types"
        / "01-card-settlement"
        / "handler.py"
    )
    spec = importlib.util.spec_from_file_location("nwp_t01_handler", path)
    if spec is None or spec.loader is None:
        raise ImportError("handler.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["nwp_t01_handler"] = module
    spec.loader.exec_module(module)
    return module


def emit_scenario(
    scenario: str,
    *,
    landing_root: Path,
    tokenization_key: str | None = None,
) -> dict[str, Any]:
    raw = SCENARIOS[scenario]
    if tokenization_key:
        os.environ["NWP_TOKENIZATION_KEY"] = tokenization_key
    os.environ.setdefault(
        "NWP_TOKENIZATION_KEY", "northwind-pay-edp-fixture-key-v1"
    )
    handler = _load_handler()
    outcome = handler.process(raw, landing_root=landing_root)
    return outcome.as_dict()


def emit_all(landing_root: Path) -> dict[str, dict[str, Any]]:
    return {
        name: emit_scenario(name, landing_root=landing_root)
        for name in ("valid-minimal", "df-source-001", "malformed")
    }


if __name__ == "__main__":
    import json

    landing = REPO_ROOT / "modern" / "landing"
    print(json.dumps(emit_all(landing), indent=2, sort_keys=True))
