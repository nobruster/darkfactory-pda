"""Backward-compatible Type 01 entrypoint for the shared typed runner."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for module_directory in (
    ROOT / "legacy" / "runner",
    ROOT / "legacy" / "publisher",
    ROOT / "legacy" / "intake",
    ROOT / "legacy" / "postgres",
    ROOT / "validation" / "oracle",
):
    sys.path.insert(0, str(module_directory))

from config import RuntimeConfiguration  # noqa: E402
from workflow import (  # noqa: E402
    PipelineError,
    build_adapter_parser,
    bundle_from_file,
    generated_bundle,
    main_for_adapter,
    run_java,
    run_pipeline as run_typed_pipeline,
    scenario_from_bundle,
)
from workflow_registry import TYPE01_WORKFLOW  # noqa: E402


SCENARIO_BATCH_IDS: Mapping[str, str] = TYPE01_WORKFLOW.scenario_batch_ids


def build_parser() -> argparse.ArgumentParser:
    """Return the original Type 01 CLI surface."""

    return build_adapter_parser(
        TYPE01_WORKFLOW,
        description="Run the complete Type 01 legacy vertical slice.",
    )


def _generated_bundle(
    scenario: str,
    *,
    output_root: Path,
    configuration: RuntimeConfiguration,
) -> Path:
    """Compatibility wrapper around typed generation."""

    return generated_bundle(
        TYPE01_WORKFLOW,
        scenario,
        output_root=output_root,
        configuration=configuration,
    )


def _bundle_from_file(
    raw_file: Path,
    *,
    configuration: RuntimeConfiguration,
) -> Path:
    """Compatibility wrapper around typed bundle validation."""

    return bundle_from_file(
        TYPE01_WORKFLOW,
        raw_file,
        configuration=configuration,
    )


def _run_java(
    batch_id: str,
    configuration: RuntimeConfiguration,
) -> dict[str, object]:
    """Compatibility wrapper around typed Java dispatch."""

    return run_java(TYPE01_WORKFLOW, batch_id, configuration)


def _scenario_from_bundle(bundle: Path) -> str | None:
    """Compatibility wrapper around typed receipt discovery."""

    return scenario_from_bundle(TYPE01_WORKFLOW, bundle)


def run_pipeline(
    bundle: Path,
    *,
    scenario: str | None,
    evidence_root: Path,
    configuration: RuntimeConfiguration,
) -> Path:
    """Run Type 01 through the single shared lifecycle implementation."""

    return run_typed_pipeline(
        TYPE01_WORKFLOW,
        bundle,
        scenario=scenario,
        evidence_root=evidence_root,
        configuration=configuration,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the original CLI through the public shared implementation."""

    return main_for_adapter(
        TYPE01_WORKFLOW,
        argv,
        description="Run the complete Type 01 legacy vertical slice.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
