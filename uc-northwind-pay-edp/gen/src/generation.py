"""Registry-style DataGen dispatch across independently typed file layouts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from artifacts import write_bundle
from contract_loader import (
    load_type_01_contract,
    load_type_02_contract,
    load_type_03_contract,
    load_type_04_contract,
    load_type_05_contract,
    load_type_06_contract,
)
from generators import (
    type_01_card_settlement,
    type_02_instant_payment_events,
    type_03_payment_slip_settlement,
    type_04_ted_transfer_settlement,
    type_05_merchant_fee_assessment,
    type_06_merchant_chargeback,
)
from models import GeneratedArtifact, GenerationError, WrittenBundle


GenerateSource = Callable[[str, Path | None], GeneratedArtifact]


@dataclass(frozen=True, slots=True)
class GeneratorAdapter:
    """One file type's scenario catalog and typed rendering entrypoint."""

    type_number: str
    supported_scenarios: tuple[str, ...]
    render: GenerateSource


def _render_type_01(
    scenario: str,
    contracts_root: Path | None,
) -> GeneratedArtifact:
    contract = load_type_01_contract(contracts_root)
    return type_01_card_settlement.render_scenario(
        scenario,
        contract=contract,
    )


def _render_type_02(
    scenario: str,
    contracts_root: Path | None,
) -> GeneratedArtifact:
    contract = load_type_02_contract(contracts_root)
    return type_02_instant_payment_events.render_scenario(
        scenario,
        contract=contract,
    )


def _render_type_03(
    scenario: str,
    contracts_root: Path | None,
) -> GeneratedArtifact:
    contract = load_type_03_contract(contracts_root)
    return type_03_payment_slip_settlement.render_scenario(
        scenario,
        contract=contract,
    )


def _render_type_04(
    scenario: str,
    contracts_root: Path | None,
) -> GeneratedArtifact:
    contract = load_type_04_contract(contracts_root)
    return type_04_ted_transfer_settlement.render_scenario(
        scenario,
        contract=contract,
    )


def _render_type_05(
    scenario: str,
    contracts_root: Path | None,
) -> GeneratedArtifact:
    contract = load_type_05_contract(contracts_root)
    return type_05_merchant_fee_assessment.render_scenario(
        scenario,
        contract=contract,
    )


def _render_type_06(
    scenario: str,
    contracts_root: Path | None,
) -> GeneratedArtifact:
    contract = load_type_06_contract(contracts_root)
    return type_06_merchant_chargeback.render_scenario(
        scenario,
        contract=contract,
    )


GENERATOR_ADAPTERS = {
    "01": GeneratorAdapter(
        type_number="01",
        supported_scenarios=type_01_card_settlement.SUPPORTED_SCENARIOS,
        render=_render_type_01,
    ),
    "02": GeneratorAdapter(
        type_number="02",
        supported_scenarios=type_02_instant_payment_events.SUPPORTED_SCENARIOS,
        render=_render_type_02,
    ),
    "03": GeneratorAdapter(
        type_number="03",
        supported_scenarios=(
            type_03_payment_slip_settlement.SUPPORTED_SCENARIOS
        ),
        render=_render_type_03,
    ),
    "04": GeneratorAdapter(
        type_number="04",
        supported_scenarios=(
            type_04_ted_transfer_settlement.SUPPORTED_SCENARIOS
        ),
        render=_render_type_04,
    ),
    "05": GeneratorAdapter(
        type_number="05",
        supported_scenarios=(
            type_05_merchant_fee_assessment.SUPPORTED_SCENARIOS
        ),
        render=_render_type_05,
    ),
    "06": GeneratorAdapter(
        type_number="06",
        supported_scenarios=(
            type_06_merchant_chargeback.SUPPORTED_SCENARIOS
        ),
        render=_render_type_06,
    ),
}


def generate(
    *,
    type_number: str,
    scenario: str,
    output_root: Path,
    contracts_root: Path | None = None,
) -> WrittenBundle:
    """Generate and atomically publish one approved deterministic bundle."""

    adapter = GENERATOR_ADAPTERS.get(type_number)
    if adapter is None:
        raise GenerationError(f"Unsupported type: {type_number}")
    if scenario not in adapter.supported_scenarios:
        raise GenerationError(
            f"Unsupported Type {adapter.type_number} scenario: {scenario}"
        )

    generated = adapter.render(scenario, contracts_root)
    return write_bundle(generated, output_root=output_root)
