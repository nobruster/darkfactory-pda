"""Golden-match: compare modern observations with contract truth and legacy.

Every comparison asks two separate questions, exactly as ``plans/modern.md``
requires:

1. **Legacy parity** — did modern reach the same observable outcome as legacy?
2. **Business correctness** — did modern satisfy the approved contract?

A source defect makes those answers differ, which is why they are answered
separately and every difference is classified rather than netted out. There is
no tolerance member anywhere in this module: the release gate permits no
unexplained financial difference, and a configurable tolerance is how one gets
introduced quietly.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

CONFIRMED_SOURCE_DEFECT = "CONFIRMED_SOURCE_DEFECT"
CONFIRMED_LEGACY_DEFECT = "CONFIRMED_LEGACY_DEFECT"
MODERN_DEFECT = "MODERN_DEFECT"
APPROVED_BEHAVIOR_CHANGE = "APPROVED_BEHAVIOR_CHANGE"
CONTRACT_AMBIGUITY = "CONTRACT_AMBIGUITY"
UNRESOLVED = "UNRESOLVED"

CLASSIFICATIONS = (
    CONFIRMED_SOURCE_DEFECT,
    CONFIRMED_LEGACY_DEFECT,
    MODERN_DEFECT,
    APPROVED_BEHAVIOR_CHANGE,
    CONTRACT_AMBIGUITY,
    UNRESOLVED,
)

# A difference is "explained" only if its classification is a settled one. The
# release gate blocks on anything else.
EXPLAINED = (
    CONFIRMED_SOURCE_DEFECT,
    CONFIRMED_LEGACY_DEFECT,
    APPROVED_BEHAVIOR_CHANGE,
)


class GoldenMatchError(RuntimeError):
    """A comparison could not be performed against the required references."""


@dataclass(frozen=True, slots=True)
class Difference:
    """One classified difference between two observations."""

    scope: str
    key: str
    field_name: str
    modern: str
    reference: str
    reference_name: str
    classification: str

    def as_dict(self) -> dict[str, str]:
        return {
            "classification": self.classification,
            "field": self.field_name,
            "key": self.key,
            "modern": self.modern,
            "reference": self.reference,
            "reference_name": self.reference_name,
            "scope": self.scope,
        }


@dataclass
class Comparison:
    """The complete golden-match verdict for one batch."""

    batch_id: str
    type_number: str
    outcome_class: str
    differences: list[Difference] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)

    @property
    def unexplained(self) -> list[Difference]:
        return [
            difference
            for difference in self.differences
            if difference.classification not in EXPLAINED
        ]

    @property
    def resolved(self) -> bool:
        return not self.unexplained and all(self.checks.values())

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "checks": dict(sorted(self.checks.items())),
            "differences": [item.as_dict() for item in self.differences],
            "outcome_class": self.outcome_class,
            "resolved": self.resolved,
            "type_number": self.type_number,
            "unexplained_count": len(self.unexplained),
        }


def _money(value: object) -> str:
    """Render an exact two-place money lexeme, refusing to repair one.

    The previous implementation was `f"{Decimal(str(value)):.2f}"`, which pads
    and rounds — and rounds ROUND_HALF_EVEN, not the contract's HALF_UP, so
    `173.445` became `173.44` where the contract says `173.45`.

    Both behaviours are wrong here for the same reason: a value that is not
    already exact at two places is a *difference*, and quietly normalizing it is
    the tolerance this module's docstring says does not exist.
    `validation/oracle/canonical.py` states the same rule for the legacy
    oracles: referees compare observations, they never repair them.
    """

    number = Decimal(str(value))
    exact = number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if exact != number:
        raise GoldenMatchError(
            "money value is not exact at two decimal places and golden-match "
            "will not round it"
        )
    return f"{exact:.2f}"


def _at_scale(value: Decimal, reference: str) -> str:
    """Render a Decimal at the fractional scale the reference text uses."""

    places = len(reference.split(".")[1]) if "." in reference else 0
    return f"{value:.{places}f}"


def _read_expected_csv(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def compare_records(
    modern_records: Sequence[Mapping[str, Any]],
    expected_csv: Path,
    *,
    batch_id: str,
    reference_name: str,
) -> list[Difference]:
    """Record level, keyed by ``(batch_id, source_record_number)``."""

    rows = _read_expected_csv(expected_csv)
    # Types key their sanitized rows differently: most by one source record
    # number, Type 03 by the A segment of its A/B pair. The key is taken from
    # the approved artifact rather than assumed.
    key_column = (
        "source_record_number"
        if rows and "source_record_number" in rows[0]
        else "source_record_number_a"
    )
    expected = {int(row[key_column]): row for row in rows}
    observed = {int(row[key_column]): row for row in modern_records}
    differences: list[Difference] = []

    for number in sorted(set(expected) | set(observed)):
        key = f"{batch_id}:{number}"
        if number not in observed:
            differences.append(
                Difference(
                    "record", key, "<row>", "<absent>", "<present>",
                    reference_name, MODERN_DEFECT,
                )
            )
            continue
        if number not in expected:
            differences.append(
                Difference(
                    "record", key, "<row>", "<present>", "<absent>",
                    reference_name, MODERN_DEFECT,
                )
            )
            continue
        want, got = expected[number], observed[number]
        for column in want:
            got_value = got.get(column)
            # Render a Decimal at the scale the approved artifact uses, so a
            # money column and a rate column are each compared at their own
            # contract scale instead of one hard-coded scale for both.
            rendered = (
                _at_scale(got_value, want[column])
                if isinstance(got_value, Decimal)
                else str(got_value)
            )
            if rendered != want[column]:
                differences.append(
                    Difference(
                        "record", key, column, rendered, want[column],
                        reference_name, MODERN_DEFECT,
                    )
                )
    return differences


def compare_reconciliation(
    modern_gold: Mapping[str, Any] | None,
    reference: Mapping[str, Any] | None,
    *,
    batch_id: str,
    reference_name: str,
) -> list[Difference]:
    """Aggregate level, keyed by ``(batch_id, currency)``."""

    if modern_gold is None and reference is None:
        return []
    if modern_gold is None:
        return [
            Difference(
                "reconciliation", batch_id, "<row>", "<absent>", "<present>",
                reference_name, MODERN_DEFECT,
            )
        ]
    if reference is None:
        return [
            Difference(
                "reconciliation", batch_id, "<row>", "<present>", "<absent>",
                reference_name, MODERN_DEFECT,
            )
        ]

    money_fields = {
        "source_net_amount",
        "staged_net_amount",
        "applied_net_amount",
        "amount_delta",
    }
    differences: list[Difference] = []
    for name in sorted(reference):
        if name not in modern_gold:
            continue
        want = reference[name]
        got = modern_gold[name]
        if name in money_fields:
            want, got = _money(want), _money(got)
        else:
            want, got = str(want), str(got)
        if want != got:
            differences.append(
                Difference(
                    "reconciliation", batch_id, name, got, want,
                    reference_name, MODERN_DEFECT,
                )
            )
    return differences


def compare_rejection(
    modern_outcome: Mapping[str, Any],
    legacy_final_status: Mapping[str, Any] | None,
    contract_expectation: Mapping[str, Any],
    *,
    batch_id: str,
) -> tuple[list[Difference], dict[str, bool]]:
    """Rejected batches compare terminal behavior, never rows.

    Inventing empty rows so that a rejected batch can be "compared like a
    successful one" would hide the difference that actually matters.

    ``legacy_final_status`` must be a **live legacy observation** — the row this
    batch left behind in ``control.batches`` — or ``None`` when the caller has
    explicitly opted out of contacting legacy. It must never be synthesized from
    ``contract_expectation``: doing so makes ``legacy_matches_contract_*`` compare
    the contract with itself, so the checks pass by construction and the emitted
    differences claim a legacy reference that was never read.
    """

    differences: list[Difference] = []
    modern_status = str(modern_outcome.get("status", ""))
    modern_code = str(modern_outcome.get("code", ""))
    expected_status = str(contract_expectation.get("expected_status", ""))
    expected_code = str(contract_expectation.get("expected_code", ""))

    checks = {
        "modern_matches_contract_status": modern_status == expected_status,
        "modern_produced_no_parquet": modern_outcome.get("parquet_sha256") is None,
        "modern_produced_no_rows": int(modern_outcome.get("record_count", 0)) == 0,
    }

    if legacy_final_status is None:
        # Degrade loudly, not silently. The business-correctness half above still
        # holds; the legacy-parity half is recorded as not asked.
        checks["legacy_terminal_comparison_skipped_by_request"] = True
        return differences, checks

    legacy_status = str(legacy_final_status.get("status", ""))
    legacy_code = str(legacy_final_status.get("code", ""))

    if modern_status != legacy_status:
        differences.append(
            Difference(
                "terminal", batch_id, "status", modern_status, legacy_status,
                "legacy-observation", MODERN_DEFECT,
            )
        )
    if modern_code != legacy_code:
        # Both systems detect the same source defect. They are independent
        # implementations, so their stable code vocabularies are their own; a
        # differing code with an identical terminal decision is a naming
        # difference, not a financial one.
        differences.append(
            Difference(
                "terminal", batch_id, "code", modern_code, legacy_code,
                "legacy-observation", APPROVED_BEHAVIOR_CHANGE,
            )
        )

    checks["legacy_terminal_observed"] = True
    checks["legacy_matches_contract_status"] = legacy_status == expected_status
    checks["legacy_matches_contract_code"] = legacy_code == expected_code

    # The declared-versus-computed disagreement itself is the source defect, and
    # both systems preserving it is the correct outcome rather than a difference.
    # Pairs are discovered rather than named, so every type's control vocabulary
    # is covered without a per-type list that can silently miss one.
    controls = modern_outcome.get("controls", {})
    preserved = False
    for key in sorted(controls):
        if not key.startswith("declared_"):
            continue
        name = key[len("declared_") :]
        computed_key = f"computed_{name}"
        if computed_key not in controls:
            continue
        declared = str(controls[key])
        computed = str(controls[computed_key])
        if declared != computed:
            differences.append(
                Difference(
                    "controls", batch_id, name, computed, declared,
                    "source-declaration", CONFIRMED_SOURCE_DEFECT,
                )
            )
            preserved = True
    if preserved:
        checks["source_declaration_preserved"] = True
    return differences, checks
