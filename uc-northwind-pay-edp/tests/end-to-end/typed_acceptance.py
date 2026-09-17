"""Reusable end-to-end acceptance harness for legacy Types 03 through 05.

The harness deliberately drives the public ``run_type.py --type`` command.
Canonical YAML artifacts provide expected batches, outcomes, rejection codes,
and reconciliations; the type specifications below contain only topology and
privacy mappings that cannot be inferred from those artifacts.

This module is executable infrastructure, not a unit-test substitute. It
expects the deployed local SFTP and PostgreSQL topology and refuses to reuse
an existing local acceptance workspace.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType

import psycopg
import yaml
from psycopg import sql


ROOT = Path(__file__).resolve().parents[2]
for module_directory in (
    ROOT / "legacy" / "runner",
    ROOT / "legacy" / "publisher",
):
    sys.path.insert(0, str(module_directory))

from config import RuntimeConfiguration  # noqa: E402
from evidence import EvidenceWriter  # noqa: E402
from raw_publisher import (  # noqa: E402
    RawPublicationError,
    publish_bundle,
)
from sftp_client import connect_sftp, exists  # noqa: E402


BATCH_ID = re.compile(r"B[0-9]{15}")
BASE_EVIDENCE_FILES = frozenset(
    {
        "expected-diff.json",
        "final-status.json",
        "generation-receipt.json",
        "java-run.json",
        "postgres-diagnostic.json",
        "postgres-load.json",
        "procedure-run.json",
        "raw-file.sha256",
        "raw-intake.json",
        "raw-publication.json",
        "reconciliation.json",
        "source-manifest.json",
    }
)
SUCCESS_EVIDENCE_FILES = BASE_EVIDENCE_FILES | {
    "sanitized-csv.sha256",
}


class AcceptanceFailure(AssertionError):
    """A typed acceptance invariant did not hold."""


class AcceptanceConfigurationError(AcceptanceFailure):
    """The harness or its canonical contract mapping is incomplete."""


@dataclass(frozen=True, slots=True)
class ScenarioContract:
    """One canonical scenario and the YAML artifact that defines its result."""

    name: str
    artifact: str
    expected_status: str


@dataclass(frozen=True, slots=True)
class EvidenceValues:
    """Raw values that must never appear in aggregate-only evidence."""

    restricted: frozenset[bytes]
    row_scoped: frozenset[bytes]


@dataclass(frozen=True, slots=True)
class TypeAcceptanceSpec:
    """Immutable topology and privacy mapping for one accepted file type."""

    type_number: str
    contract_slug: str
    scenarios: tuple[ScenarioContract, ...]
    business_table: tuple[str, str]
    reporting_table: tuple[str, str]
    zero_delta_columns: tuple[str, ...]
    privacy_columns: tuple[tuple[str, re.Pattern[str]], ...]
    privacy_consistency: Callable[[Mapping[str, str]], bool]
    success_java_fields: frozenset[str]
    rejection_java_fields: frozenset[str]
    forbidden_evidence_keys: frozenset[str]
    extract_evidence_values: Callable[[bytes], EvidenceValues]

    @property
    def contract_main(self) -> Path:
        """Return the canonical fixture/oracle directory for this type."""

        return ROOT / "contracts" / "types" / self.contract_slug / "main"

    @property
    def output_root(self) -> Path:
        """Return the isolated generated-bundle root for this suite."""

        return ROOT / ".runtime" / f"e2e-type{self.type_number}-generated"

    @property
    def evidence_root(self) -> Path:
        """Return the isolated immutable-evidence root for this suite."""

        return ROOT / ".runtime" / f"e2e-type{self.type_number}-evidence"


@dataclass(frozen=True, slots=True)
class ScenarioExpectation:
    """Validated outcome loaded directly from one canonical YAML artifact."""

    scenario: str
    batch_id: str
    status: str
    code: str | None
    oracle: Mapping[str, object]


def _nonempty(value: bytes) -> bytes | None:
    stripped = value.rstrip(b" ~")
    return stripped if stripped else None


def _type03_evidence_values(raw: bytes) -> EvidenceValues:
    """Extract Type 03 restricted and long row-level values by contract offsets."""

    restricted: set[bytes] = set()
    row_scoped: set[bytes] = set()
    for record in raw.split(b"\r\n"):
        if len(record) != 240:
            continue
        if record.startswith(b"A"):
            restricted.add(record[29:77])
            row_scoped.update(
                {
                    record[13:29],
                    record[134:154],
                }
            )
        elif record.startswith(b"B"):
            tax_id = record[30:44]
            restricted.add(tax_id)
            if tax_id.startswith(b"000"):
                restricted.add(tax_id[3:])
            for candidate in (
                record[44:84],
                record[84:105],
                record[87:105],
                record[92:104],
            ):
                value = _nonempty(candidate)
                if value is not None:
                    restricted.add(value)
            row_scoped.update(
                {
                    record[13:29],
                    record[105:125],
                }
            )
    return EvidenceValues(
        restricted=frozenset(restricted),
        row_scoped=frozenset(value for value in row_scoped if value),
    )


def _type04_evidence_values(raw: bytes) -> EvidenceValues:
    """Extract Type 04 restricted and long row-level values by variant offsets."""

    restricted: set[bytes] = set()
    row_scoped: set[bytes] = set()
    for record in raw.split(b"\r\n"):
        if record.startswith(b"D") and len(record) == 162:
            payer_tax_id = record[73:87]
            beneficiary_tax_id = record[112:126]
            restricted.update(
                {
                    record[61:73],
                    payer_tax_id,
                    record[100:112],
                    beneficiary_tax_id,
                }
            )
            if payer_tax_id.startswith(b"000"):
                restricted.add(payer_tax_id[3:])
            if beneficiary_tax_id.startswith(b"000"):
                restricted.add(beneficiary_tax_id[3:])
            beneficiary_name = _nonempty(record[139:162])
            if beneficiary_name is not None:
                restricted.add(beneficiary_name)
            row_scoped.add(record[1:17])
        elif record.startswith(b"R") and len(record) == 91:
            reason_text = _nonempty(record[67:91])
            if reason_text is not None:
                restricted.add(reason_text)
            row_scoped.update({record[1:17], record[17:33]})
    return EvidenceValues(
        restricted=frozenset(value for value in restricted if value),
        row_scoped=frozenset(value for value in row_scoped if value),
    )


def _type05_evidence_values(raw: bytes) -> EvidenceValues:
    """Extract Type 05 CNPJs and long row identifiers without repairing CSV."""

    restricted = {
        match.group(1)
        for match in re.finditer(rb";([0-9]{14});", raw)
    }
    row_scoped: set[bytes] = set()
    for match in re.finditer(
        rb"(?:^|\n)(FEE[0-9]{13});B[0-9]{15};(MER[0-9]{13});",
        raw,
    ):
        row_scoped.update(match.groups())
    return EvidenceValues(
        restricted=frozenset(restricted),
        row_scoped=frozenset(row_scoped),
    )


def _type03_privacy_consistency(row: Mapping[str, str]) -> bool:
    """Require the Type 03 tax mask length to agree with its tax-id type."""

    tax_type = row["beneficiary_tax_id_type"]
    mask = row["beneficiary_tax_id_masked"]
    return (
        tax_type == "CPF"
        and re.fullmatch(r"\*{7}[0-9]{4}", mask) is not None
    ) or (
        tax_type == "CNPJ"
        and re.fullmatch(r"\*{10}[0-9]{4}", mask) is not None
    )


def _always_consistent(row: Mapping[str, str]) -> bool:
    """Return true when regex validation is the complete privacy rule."""

    del row
    return True


TYPE03_REJECTION_CONTROLS = frozenset(
    {
        "computed_discount_amount",
        "computed_face_amount",
        "computed_fee_amount",
        "computed_logical_count",
        "computed_lot_count",
        "computed_net_amount",
        "computed_orphan_segment_count",
        "computed_physical_record_count",
        "declared_discount_amount",
        "declared_face_amount",
        "declared_fee_amount",
        "declared_logical_count",
        "declared_lot_count",
        "declared_net_amount",
        "declared_physical_record_count",
    }
)
TYPE04_REJECTION_CONTROLS = frozenset(
    {
        "computed_gross_amount",
        "computed_net_amount",
        "computed_return_amount",
        "computed_return_count",
        "computed_transfer_count",
        "declared_gross_amount",
        "declared_net_amount",
        "declared_return_amount",
        "declared_return_count",
        "declared_transfer_count",
    }
)
TYPE05_REJECTION_CONTROLS = frozenset(
    {
        "computed_assessed_fee",
        "computed_calculated_fee",
        "computed_gross_amount",
        "computed_row_count",
        "declared_assessed_fee",
        "declared_calculated_fee",
        "declared_gross_amount",
        "declared_row_count",
    }
)


TYPE_SPECS: Mapping[str, TypeAcceptanceSpec] = MappingProxyType(
    {
        "03": TypeAcceptanceSpec(
            type_number="03",
            contract_slug="03-payment-slip-settlement",
            scenarios=(
                ScenarioContract(
                    "malformed",
                    "expected-malformed-rejection.yaml",
                    "quarantined",
                ),
                ScenarioContract(
                    "valid-minimal",
                    "expected-reconciliation.yaml",
                    "succeeded",
                ),
                ScenarioContract(
                    "DF-SOURCE-003",
                    "expected-df-source-003-finding.yaml",
                    "quarantined",
                ),
                ScenarioContract(
                    "valid-boundary",
                    "expected-valid-boundary-reconciliation.yaml",
                    "succeeded",
                ),
                ScenarioContract(
                    "multi-lot",
                    "expected-multi-lot-reconciliation.yaml",
                    "succeeded",
                ),
            ),
            business_table=("legacy", "payment_slip_settlement"),
            reporting_table=(
                "reporting",
                "payment_slip_settlement_reconciliation",
            ),
            zero_delta_columns=(
                "count_delta",
                "face_amount_delta",
                "discount_amount_delta",
                "fee_amount_delta",
                "net_amount_delta",
                "orphan_segment_count_delta",
                "reject_count",
            ),
            privacy_columns=(
                (
                    "payment_reference_token",
                    re.compile(r"payref_[0-9a-f]{24}"),
                ),
                ("payment_reference_last4", re.compile(r"[0-9]{4}")),
                (
                    "beneficiary_token",
                    re.compile(r"party_[0-9a-f]{24}"),
                ),
                ("beneficiary_tax_id_type", re.compile(r"(?:CPF|CNPJ)")),
                (
                    "beneficiary_tax_id_masked",
                    re.compile(r"(?:\*{7}|\*{10})[0-9]{4}"),
                ),
                (
                    "bank_account_token",
                    re.compile(r"acct_[0-9a-f]{24}"),
                ),
                ("bank_account_last4", re.compile(r"[0-9]{4}")),
            ),
            privacy_consistency=_type03_privacy_consistency,
            success_java_fields=frozenset(
                {
                    "batch_id",
                    "code",
                    "csv_file",
                    "csv_sha256",
                    "discount_amount",
                    "face_amount",
                    "fee_amount",
                    "file_type",
                    "net_amount",
                    "orphan_segment_count",
                    "row_count",
                    "status",
                }
            ),
            rejection_java_fields=(
                frozenset(
                    {
                        "batch_id",
                        "code",
                        "file_type",
                        "record_number",
                        "status",
                    }
                )
                | TYPE03_REJECTION_CONTROLS
            ),
            forbidden_evidence_keys=frozenset(
                {
                    "account_number",
                    "bank_account",
                    "beneficiary_name",
                    "beneficiary_tax_id",
                    "payment_reference",
                    "raw_record",
                    "raw_value",
                }
            ),
            extract_evidence_values=_type03_evidence_values,
        ),
        "04": TypeAcceptanceSpec(
            type_number="04",
            contract_slug="04-ted-transfer-settlement",
            scenarios=(
                ScenarioContract(
                    "malformed",
                    "expected-malformed-rejection.yaml",
                    "quarantined",
                ),
                ScenarioContract(
                    "valid-minimal",
                    "expected-reconciliation.yaml",
                    "succeeded",
                ),
                ScenarioContract(
                    "DF-SOURCE-004",
                    "expected-df-source-004-finding.yaml",
                    "quarantined",
                ),
                ScenarioContract(
                    "valid-boundary",
                    "expected-valid-boundary-reconciliation.yaml",
                    "succeeded",
                ),
                ScenarioContract(
                    "all-returned-zero-net",
                    "expected-all-returned-zero-net-reconciliation.yaml",
                    "succeeded",
                ),
            ),
            business_table=("legacy", "ted_transfer_movement"),
            reporting_table=("reporting", "ted_transfer_reconciliation"),
            zero_delta_columns=(
                "transfer_count_delta",
                "return_count_delta",
                "gross_amount_delta",
                "return_amount_delta",
                "net_amount_delta",
                "reject_count",
            ),
            privacy_columns=(
                (
                    "payer_account_token",
                    re.compile(r"tedacct_[0-9a-f]{24}"),
                ),
                (
                    "payer_tax_id_masked",
                    re.compile(r"(?:\*{7}|\*{10})[0-9]{4}"),
                ),
                (
                    "beneficiary_account_token",
                    re.compile(r"tedacct_[0-9a-f]{24}"),
                ),
                (
                    "beneficiary_tax_id_masked",
                    re.compile(r"(?:\*{7}|\*{10})[0-9]{4}"),
                ),
            ),
            privacy_consistency=_always_consistent,
            success_java_fields=frozenset(
                {
                    "batch_id",
                    "code",
                    "csv_file",
                    "csv_sha256",
                    "file_type",
                    "gross_amount",
                    "net_amount",
                    "return_amount",
                    "return_count",
                    "row_count",
                    "status",
                    "transfer_count",
                }
            ),
            rejection_java_fields=(
                frozenset(
                    {
                        "batch_id",
                        "code",
                        "file_type",
                        "record_number",
                        "status",
                    }
                )
                | TYPE04_REJECTION_CONTROLS
            ),
            forbidden_evidence_keys=frozenset(
                {
                    "beneficiary_account",
                    "beneficiary_name",
                    "beneficiary_tax_id",
                    "payer_account",
                    "payer_tax_id",
                    "raw_record",
                    "raw_value",
                    "return_reason_text",
                }
            ),
            extract_evidence_values=_type04_evidence_values,
        ),
        "05": TypeAcceptanceSpec(
            type_number="05",
            contract_slug="05-merchant-fee-assessment",
            scenarios=(
                ScenarioContract(
                    "malformed",
                    "expected-malformed-rejection.yaml",
                    "quarantined",
                ),
                ScenarioContract(
                    "valid-minimal",
                    "expected-reconciliation.yaml",
                    "succeeded",
                ),
                ScenarioContract(
                    "DF-SOURCE-005",
                    "expected-df-source-005-finding.yaml",
                    "quarantined",
                ),
                ScenarioContract(
                    "valid-boundary",
                    "expected-valid-boundary-reconciliation.yaml",
                    "succeeded",
                ),
                ScenarioContract(
                    "rounding-half-up",
                    "expected-rounding-half-up-reconciliation.yaml",
                    "succeeded",
                ),
            ),
            business_table=("legacy", "merchant_fee_assessment"),
            reporting_table=("reporting", "merchant_fee_reconciliation"),
            zero_delta_columns=(
                "count_delta",
                "gross_amount_delta",
                "assessed_fee_delta",
                "calculated_fee_delta",
                "assessment_calculation_delta",
                "reject_count",
            ),
            privacy_columns=(
                (
                    "merchant_tax_id_masked",
                    re.compile(r"\*{10}[0-9]{4}"),
                ),
            ),
            privacy_consistency=_always_consistent,
            success_java_fields=frozenset(
                {
                    "assessed_fee",
                    "batch_id",
                    "calculated_fee",
                    "code",
                    "csv_file",
                    "csv_sha256",
                    "file_type",
                    "gross_amount",
                    "row_count",
                    "status",
                }
            ),
            rejection_java_fields=(
                frozenset(
                    {
                        "batch_id",
                        "code",
                        "file_type",
                        "physical_record_number",
                        "record_number",
                        "status",
                    }
                )
                | TYPE05_REJECTION_CONTROLS
            ),
            forbidden_evidence_keys=frozenset(
                {
                    "assessment_id",
                    "description",
                    "fee_code",
                    "merchant_id",
                    "merchant_tax_id",
                    "raw_row",
                    "raw_value",
                }
            ),
            extract_evidence_values=_type05_evidence_values,
        ),
    }
)


def suite_for_type(type_number: str) -> TypeAcceptanceSpec:
    """Resolve one supported acceptance suite and fail closed otherwise."""

    try:
        return TYPE_SPECS[type_number]
    except KeyError as exc:
        raise AcceptanceConfigurationError(
            "Acceptance harness supports only Types 03, 04, and 05"
        ) from exc


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise AcceptanceConfigurationError(
            f"Cannot load canonical acceptance artifact: {path.name}"
        ) from exc
    if not isinstance(value, dict):
        raise AcceptanceConfigurationError(
            f"Canonical acceptance artifact is not a mapping: {path.name}"
        )
    return value


def _is_zero(value: object) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return Decimal(str(value)) == Decimal("0")
    except (InvalidOperation, ValueError):
        return False


def load_expectations(
    spec: TypeAcceptanceSpec,
) -> Mapping[str, ScenarioExpectation]:
    """Load and validate all five expected outcomes from canonical YAML."""

    expectations: dict[str, ScenarioExpectation] = {}
    for scenario_contract in spec.scenarios:
        oracle = _read_yaml_mapping(
            spec.contract_main / scenario_contract.artifact
        )
        batch_id = oracle.get("batch_id")
        if (
            not isinstance(batch_id, str)
            or BATCH_ID.fullmatch(batch_id) is None
        ):
            raise AcceptanceConfigurationError(
                f"Canonical batch ID is invalid: {scenario_contract.name}"
            )

        code: str | None = None
        if scenario_contract.expected_status == "succeeded":
            if oracle.get("status") != "MATCHED":
                raise AcceptanceConfigurationError(
                    f"Success oracle is not MATCHED: {scenario_contract.name}"
                )
            if any(
                column not in oracle or not _is_zero(oracle[column])
                for column in spec.zero_delta_columns
            ):
                raise AcceptanceConfigurationError(
                    f"Success oracle has missing/nonzero deltas: "
                    f"{scenario_contract.name}"
                )
        elif scenario_contract.expected_status == "quarantined":
            code_value = oracle.get("expected_code")
            if (
                oracle.get("scenario") != scenario_contract.name
                or oracle.get("expected_status") != "quarantined"
                or oracle.get("quarantine_scope") != "batch"
                or oracle.get("csv_produced") is not False
                or oracle.get("postgres_business_mutation") is not False
                or not isinstance(code_value, str)
            ):
                raise AcceptanceConfigurationError(
                    f"Rejection oracle is incomplete: {scenario_contract.name}"
                )
            code = code_value
        else:
            raise AcceptanceConfigurationError(
                f"Unsupported expected status: "
                f"{scenario_contract.expected_status}"
            )

        if scenario_contract.name.startswith("DF-SOURCE-") and (
            oracle.get("source_system_role") != "system_of_record"
            or oracle.get("unrelated_batches_continue") is not True
        ):
            raise AcceptanceConfigurationError(
                f"Dark Factory oracle is incomplete: "
                f"{scenario_contract.name}"
            )
        expectations[scenario_contract.name] = ScenarioExpectation(
            scenario=scenario_contract.name,
            batch_id=batch_id,
            status=scenario_contract.expected_status,
            code=code,
            oracle=MappingProxyType(dict(oracle)),
        )

    statuses = [item.status for item in expectations.values()]
    if (
        len(expectations) != 5
        or statuses.count("succeeded") != 3
        or statuses.count("quarantined") != 2
        or len({item.batch_id for item in expectations.values()}) != 5
    ):
        raise AcceptanceConfigurationError(
            f"Type {spec.type_number} must map exactly "
            "three successes and two batch quarantines"
        )
    return MappingProxyType(expectations)


def runner_command(
    spec: TypeAcceptanceSpec,
    scenario: str,
    *,
    output_root: Path,
    evidence_root: Path,
) -> list[str]:
    """Build the public typed command used by every acceptance scenario."""

    if scenario not in {item.name for item in spec.scenarios}:
        raise AcceptanceConfigurationError(
            f"Unsupported Type {spec.type_number} scenario: {scenario}"
        )
    return [
        sys.executable,
        str(ROOT / "legacy" / "runner" / "run_type.py"),
        "--type",
        spec.type_number,
        "--scenario",
        scenario,
        "--output-root",
        str(output_root),
        "--evidence-root",
        str(evidence_root),
    ]


def run_scenario(
    spec: TypeAcceptanceSpec,
    expectation: ScenarioExpectation,
    *,
    output_root: Path,
    evidence_root: Path,
) -> dict[str, object]:
    """Run one canonical case and validate its public terminal envelope."""

    try:
        result = subprocess.run(
            runner_command(
                spec,
                expectation.scenario,
                output_root=output_root,
                evidence_root=evidence_root,
            ),
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        raise AcceptanceFailure(
            f"Type {spec.type_number} scenario exceeded 180 seconds: "
            f"{expectation.scenario}"
        ) from exc
    if result.returncode != 0:
        raise AcceptanceFailure(
            f"Type {spec.type_number} scenario failed without exposing "
            f"captured output: {expectation.scenario}"
        )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    try:
        output = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise AcceptanceFailure(
            f"Type {spec.type_number} returned no valid terminal envelope: "
            f"{expectation.scenario}"
        ) from exc
    expected_evidence = (evidence_root / expectation.batch_id).resolve()
    if (
        not isinstance(output, dict)
        or set(output) != {"batch_id", "evidence", "status"}
        or output.get("batch_id") != expectation.batch_id
        or output.get("status") != expectation.status
        or Path(str(output.get("evidence"))).resolve() != expected_evidence
    ):
        raise AcceptanceFailure(
            f"Type {spec.type_number} terminal state is incorrect: "
            f"{expectation.scenario}"
        )
    return output


def interrupt_scenario(
    spec: TypeAcceptanceSpec,
    expectation: ScenarioExpectation,
    *,
    boundary: str,
    output_root: Path,
    evidence_root: Path,
) -> None:
    """Inject one post-durability crash and require an evidence-free stop."""

    if expectation.status != "succeeded":
        raise AcceptanceConfigurationError(
            "Interruption recovery applies only to canonical successes"
        )
    environment = os.environ.copy()
    environment["NWP_TEST_INTERRUPT_AFTER"] = boundary
    environment["NWP_TEST_INTERRUPT_BATCH_ID"] = expectation.batch_id
    try:
        result = subprocess.run(
            runner_command(
                spec,
                expectation.scenario,
                output_root=output_root,
                evidence_root=evidence_root,
            ),
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            env=environment,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        raise AcceptanceFailure(
            f"Type {spec.type_number} interruption timed out: "
            f"{expectation.scenario}/{boundary}"
        ) from exc
    if (
        result.returncode != 2
        or (evidence_root / expectation.batch_id).exists()
    ):
        raise AcceptanceFailure(
            f"Type {spec.type_number} interruption was not isolated: "
            f"{expectation.scenario}/{boundary}"
        )


def _directory_snapshot(directory: Path) -> Mapping[str, str]:
    """Hash every immutable evidence artifact for exact replay checks."""

    if not directory.is_dir():
        raise AcceptanceFailure("Replay evidence packet does not exist")
    return MappingProxyType(
        {
            str(path.relative_to(directory)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(directory.rglob("*"))
            if path.is_file()
        }
    )


def verify_exact_replay(
    spec: TypeAcceptanceSpec,
    expectation: ScenarioExpectation,
    *,
    output_root: Path,
    evidence_root: Path,
) -> None:
    """Replay a completed batch and require byte-identical evidence."""

    packet = evidence_root / expectation.batch_id
    before = _directory_snapshot(packet)
    run_scenario(
        spec,
        expectation,
        output_root=output_root,
        evidence_root=evidence_root,
    )
    after = _directory_snapshot(packet)
    if before != after:
        raise AcceptanceFailure(
            f"Type {spec.type_number} replay changed immutable evidence"
        )


def _assert_no_partial_files(sftp: object, remote_directory: str) -> None:
    """Reject stale manifest-last temporary files in a terminal batch."""

    names = getattr(sftp, "listdir")(remote_directory)
    if any(name.endswith(".part") for name in names):
        raise AcceptanceFailure(
            f"Partial SFTP artifact remains in {remote_directory}"
        )


def verify_sftp(
    spec: TypeAcceptanceSpec,
    expectations: Mapping[str, ScenarioExpectation],
    configuration: RuntimeConfiguration,
) -> None:
    """Verify exact raw/CSV terminal zones and absence of partial CSV."""

    raw_zones = ("incoming", "processing", "archive", "quarantine")
    csv_zones = ("outgoing", "processing", "archive", "quarantine")
    with connect_sftp(configuration, configuration.operator) as sftp:
        for expectation in expectations.values():
            expected_raw_zone = (
                "archive"
                if expectation.status == "succeeded"
                else "quarantine"
            )
            expected_csv_zone = (
                "archive" if expectation.status == "succeeded" else None
            )
            for zone in raw_zones:
                path = f"/raw/{zone}/{expectation.batch_id}"
                observed = exists(sftp, path)
                if observed != (zone == expected_raw_zone):
                    raise AcceptanceFailure(
                        f"Type {spec.type_number} raw SFTP state is "
                        f"inconsistent: {expectation.scenario}"
                    )
                if observed:
                    _assert_no_partial_files(sftp, path)
            for zone in csv_zones:
                path = f"/csv/{zone}/{expectation.batch_id}"
                observed = exists(sftp, path)
                if observed != (zone == expected_csv_zone):
                    raise AcceptanceFailure(
                        f"Type {spec.type_number} CSV SFTP state is "
                        f"inconsistent: {expectation.scenario}"
                    )
                if observed:
                    _assert_no_partial_files(sftp, path)


def verify_duplicate_refusal(
    spec: TypeAcceptanceSpec,
    expectations: Mapping[str, ScenarioExpectation],
    configuration: RuntimeConfiguration,
    *,
    output_root: Path,
) -> None:
    """Prove immutable publication rejects a terminal canonical bundle."""

    batch_id = expectations["valid-minimal"].batch_id
    try:
        publish_bundle(
            output_root / batch_id,
            configuration=configuration,
        )
    except RawPublicationError:
        return
    raise AcceptanceFailure(
        f"Type {spec.type_number} duplicate publication was accepted"
    )


def _qualified_table(table: tuple[str, str]) -> sql.Composed:
    return sql.SQL("{}.{}").format(
        sql.Identifier(table[0]),
        sql.Identifier(table[1]),
    )


def _verify_loader_write_boundary(
    spec: TypeAcceptanceSpec,
    configuration: RuntimeConfiguration,
) -> None:
    """Require both declared and exercised denial of direct governed writes."""

    business_name = ".".join(spec.business_table)
    reporting_name = ".".join(spec.reporting_table)
    with psycopg.connect(configuration.postgres_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_user,
                    has_table_privilege(
                        current_user, %s, 'INSERT,UPDATE,DELETE'
                    ),
                    has_table_privilege(
                        current_user, %s, 'INSERT,UPDATE,DELETE'
                    )
                """,
                (business_name, reporting_name),
            )
            current_user, business_write, reporting_write = cursor.fetchone()
            if (
                current_user != configuration.postgres_app_user
                or business_write
                or reporting_write
            ):
                raise AcceptanceFailure(
                    f"Type {spec.type_number} loader has direct governed "
                    "table mutation privileges"
                )

    statements = (
        sql.SQL("UPDATE {} SET batch_id = batch_id WHERE false").format(
            _qualified_table(spec.business_table)
        ),
        sql.SQL("UPDATE {} SET status = status WHERE false").format(
            _qualified_table(spec.reporting_table)
        ),
    )
    for statement in statements:
        with psycopg.connect(configuration.postgres_dsn) as connection:
            try:
                connection.execute(statement)
            except psycopg.errors.InsufficientPrivilege:
                connection.rollback()
            else:
                connection.rollback()
                raise AcceptanceFailure(
                    f"Type {spec.type_number} loader performed a forbidden "
                    "direct mutation"
                )


def verify_postgres(
    spec: TypeAcceptanceSpec,
    expectations: Mapping[str, ScenarioExpectation],
    configuration: RuntimeConfiguration,
) -> None:
    """Verify typed control rows, reconciliation, isolation, and privacy."""

    successes = {
        expectation.batch_id
        for expectation in expectations.values()
        if expectation.status == "succeeded"
    }
    quarantines = {
        expectation.batch_id
        for expectation in expectations.values()
        if expectation.status == "quarantined"
    }
    expected_rejections = {
        (expectation.batch_id, expectation.code)
        for expectation in expectations.values()
        if expectation.status == "quarantined"
    }
    expected_controls = {
        (expectation.batch_id, expectation.status)
        for expectation in expectations.values()
    }

    with psycopg.connect(configuration.postgres_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT batch_id, status
                  FROM control.batches
                 WHERE file_type = %s
                """,
                (spec.type_number,),
            )
            if set(cursor.fetchall()) != expected_controls:
                raise AcceptanceFailure(
                    f"Type {spec.type_number} filtered control states "
                    "are incomplete"
                )

            cursor.execute(
                """
                SELECT reject.batch_id, reject.code
                  FROM control.rejects AS reject
                  JOIN control.batches AS batch
                    ON batch.batch_id = reject.batch_id
                 WHERE batch.file_type = %s
                """,
                (spec.type_number,),
            )
            if set(cursor.fetchall()) != expected_rejections:
                raise AcceptanceFailure(
                    f"Type {spec.type_number} filtered reject history "
                    "is incomplete"
                )

            report_columns = (
                "batch_id",
                "status",
                *spec.zero_delta_columns,
            )
            cursor.execute(
                sql.SQL("SELECT {} FROM {}").format(
                    sql.SQL(", ").join(
                        sql.Identifier(column)
                        for column in report_columns
                    ),
                    _qualified_table(spec.reporting_table),
                )
            )
            report_rows = cursor.fetchall()
            if (
                {row[0] for row in report_rows} != successes
                or any(row[1] != "MATCHED" for row in report_rows)
                or any(
                    not _is_zero(value)
                    for row in report_rows
                    for value in row[2:]
                )
            ):
                raise AcceptanceFailure(
                    f"Type {spec.type_number} reconciliation is not "
                    "complete and zero-delta"
                )

            cursor.execute(
                sql.SQL("SELECT DISTINCT batch_id FROM {}").format(
                    _qualified_table(spec.business_table)
                )
            )
            if {row[0] for row in cursor.fetchall()} != successes:
                raise AcceptanceFailure(
                    f"Type {spec.type_number} operational batches are "
                    "not exactly the successful set"
                )

            cursor.execute(
                sql.SQL(
                    "SELECT count(*) FROM {} WHERE batch_id = ANY(%s)"
                ).format(_qualified_table(spec.business_table)),
                (list(quarantines),),
            )
            if cursor.fetchone()[0] != 0:
                raise AcceptanceFailure(
                    f"Type {spec.type_number} rejected batch mutated "
                    "operational state"
                )

            privacy_names = tuple(
                name for name, _ in spec.privacy_columns
            )
            cursor.execute(
                sql.SQL("SELECT {} FROM {}").format(
                    sql.SQL(", ").join(
                        sql.Identifier(name) for name in privacy_names
                    ),
                    _qualified_table(spec.business_table),
                )
            )
            for values in cursor.fetchall():
                row = {
                    name: value
                    for name, value in zip(
                        privacy_names,
                        values,
                        strict=True,
                    )
                }
                if any(
                    not isinstance(row[name], str)
                    or pattern.fullmatch(row[name]) is None
                    for name, pattern in spec.privacy_columns
                ) or not spec.privacy_consistency(row):
                    raise AcceptanceFailure(
                        f"Type {spec.type_number} operational privacy "
                        "format is invalid"
                    )

    _verify_loader_write_boundary(spec, configuration)


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcceptanceFailure(
            f"Evidence JSON is unreadable: {path.name}"
        ) from exc
    if not isinstance(value, dict):
        raise AcceptanceFailure(
            f"Evidence JSON is not an object: {path.name}"
        )
    return value


def _walk_mapping_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(_walk_mapping_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(_walk_mapping_keys(nested))
    return keys


def _collect_evidence_values(
    spec: TypeAcceptanceSpec,
    expectations: Mapping[str, ScenarioExpectation],
    *,
    output_root: Path,
) -> EvidenceValues:
    restricted: set[bytes] = set()
    row_scoped: set[bytes] = set()
    for expectation in expectations.values():
        bundle = output_root / expectation.batch_id
        manifest = _read_json_object(bundle / "source-manifest.json")
        source_file = manifest.get("source_file")
        if not isinstance(source_file, dict):
            raise AcceptanceFailure("Generated source manifest is incomplete")
        filename = source_file.get("name")
        if not isinstance(filename, str):
            raise AcceptanceFailure("Generated source filename is missing")
        values = spec.extract_evidence_values(
            (bundle / filename).read_bytes()
        )
        restricted.update(values.restricted)
        row_scoped.update(values.row_scoped)
    if not restricted or not row_scoped:
        raise AcceptanceFailure(
            f"Type {spec.type_number} privacy extractor found no "
            "restricted or row-level values"
        )
    return EvidenceValues(
        restricted=frozenset(restricted),
        row_scoped=frozenset(row_scoped),
    )


def _verify_common_packet(
    spec: TypeAcceptanceSpec,
    expectation: ScenarioExpectation,
    packet: Path,
) -> dict[str, dict[str, object]]:
    expected_files = (
        SUCCESS_EVIDENCE_FILES
        if expectation.status == "succeeded"
        else BASE_EVIDENCE_FILES
    )
    observed_files = {
        path.name for path in packet.iterdir() if path.is_file()
    }
    if observed_files != expected_files:
        raise AcceptanceFailure(
            f"Type {spec.type_number} evidence packet is incomplete: "
            f"{expectation.scenario}"
        )
    json_objects = {
        path.name: _read_json_object(path)
        for path in packet.glob("*.json")
    }
    source = json_objects["source-manifest.json"]
    publication = json_objects["raw-publication.json"]
    intake = json_objects["raw-intake.json"]
    final = json_objects["final-status.json"]
    source_type = source.get("file_type")
    source_controls = source.get("source_controls")
    if (
        not isinstance(source_type, dict)
        or source_type.get("number") != spec.type_number
        or source.get("batch_id") != expectation.batch_id
        or not isinstance(source_controls, dict)
        or publication.get("batch_id") != expectation.batch_id
        or publication.get("file_type") != spec.type_number
        or publication.get("source_controls") != source_controls
        or intake.get("batch_id") != expectation.batch_id
        or intake.get("file_type") != spec.type_number
        or intake.get("source_controls") != source_controls
        or final.get("batch_id") != expectation.batch_id
        or final.get("file_type") != spec.type_number
        or final.get("source_controls") != source_controls
        or final.get("scope") != "batch"
        or final.get("status") != expectation.status
    ):
        raise AcceptanceFailure(
            f"Type {spec.type_number} evidence lost lineage or scope: "
            f"{expectation.scenario}"
        )
    expected_diff = json_objects["expected-diff.json"]
    if (
        expected_diff.get("matches") is not True
        or expected_diff.get("oracle_status") != "oracle_matched"
    ):
        raise AcceptanceFailure(
            f"Type {spec.type_number} canonical oracle did not match: "
            f"{expectation.scenario}"
        )
    for value in json_objects.values():
        if spec.forbidden_evidence_keys & _walk_mapping_keys(value):
            raise AcceptanceFailure(
                f"Type {spec.type_number} evidence contains row-level keys: "
                f"{expectation.scenario}"
            )
    return json_objects


def _verify_success_packet(
    spec: TypeAcceptanceSpec,
    expectation: ScenarioExpectation,
    objects: Mapping[str, Mapping[str, object]],
) -> None:
    java = objects["java-run.json"]
    postgres_load = objects["postgres-load.json"]
    procedure = objects["procedure-run.json"]
    reconciliation = objects["reconciliation.json"]
    diagnostic = objects["postgres-diagnostic.json"]
    if (
        set(java) != spec.success_java_fields
        or java.get("status") != "succeeded"
        or java.get("file_type") != spec.type_number
        or java.get("batch_id") != expectation.batch_id
        or reconciliation != expectation.oracle
        or procedure.get("status") != "succeeded"
        or diagnostic
        != {
            "reason": "successful production path",
            "status": "not_applicable",
        }
    ):
        raise AcceptanceFailure(
            f"Type {spec.type_number} success evidence is incomplete: "
            f"{expectation.scenario}"
        )
    expected_load_status = (
        "recovered_committed_batch"
        if expectation.scenario in {"valid-minimal", "valid-boundary"}
        else "database_committed_pending_archive"
    )
    if (
        postgres_load.get("status") != expected_load_status
        or postgres_load.get("file_type") != spec.type_number
        or postgres_load.get("batch_id") != expectation.batch_id
        or not isinstance(postgres_load.get("stage_controls"), dict)
    ):
        raise AcceptanceFailure(
            f"Type {spec.type_number} durable recovery evidence is "
            f"incomplete: {expectation.scenario}"
        )


def _verify_rejection_packet(
    spec: TypeAcceptanceSpec,
    expectation: ScenarioExpectation,
    objects: Mapping[str, Mapping[str, object]],
) -> None:
    java = objects["java-run.json"]
    final = objects["final-status.json"]
    postgres_load = objects["postgres-load.json"]
    procedure = objects["procedure-run.json"]
    reconciliation = objects["reconciliation.json"]
    if (
        set(java) != spec.rejection_java_fields
        or java.get("status") != "rejected"
        or java.get("code") != expectation.code
        or java.get("batch_id") != expectation.batch_id
        or final.get("code") != expectation.code
        or postgres_load
        != {
            "business_state_committed": False,
            "reason": expectation.code,
            "status": "control_recorded",
        }
        or procedure
        != {"reason": expectation.code, "status": "not_run"}
        or reconciliation
        != {"reason": expectation.code, "status": "not_run"}
    ):
        raise AcceptanceFailure(
            f"Type {spec.type_number} quarantine evidence is incomplete: "
            f"{expectation.scenario}"
        )

    diagnostic = objects["postgres-diagnostic.json"]
    if expectation.scenario.startswith("DF-SOURCE-"):
        aggregate = {
            key: value
            for key, value in expectation.oracle.items()
            if key.startswith(("declared_", "computed_"))
        }
        expected_diagnostic = {
            "business_state_committed": False,
            "file_type": spec.type_number,
            "input": "privacy-safe-java-aggregate-controls",
            "mode": "source-parser-observation",
            **aggregate,
            "status": "completed",
        }
        if (
            diagnostic != expected_diagnostic
            or any(java.get(key) != value for key, value in aggregate.items())
        ):
            raise AcceptanceFailure(
                f"Type {spec.type_number} Dark Factory aggregate "
                "diagnostic is incomplete"
            )
    elif diagnostic != {
        "file_type": spec.type_number,
        "reason": expectation.code,
        "status": "not_run",
    }:
        raise AcceptanceFailure(
            f"Type {spec.type_number} malformed diagnostic is not "
            "aggregate-only"
        )


def verify_evidence(
    spec: TypeAcceptanceSpec,
    expectations: Mapping[str, ScenarioExpectation],
    *,
    output_root: Path,
    evidence_root: Path,
) -> None:
    """Verify immutable, complete, aggregate-only, privacy-safe evidence."""

    values = _collect_evidence_values(
        spec,
        expectations,
        output_root=output_root,
    )
    prohibited = values.restricted | values.row_scoped
    for expectation in expectations.values():
        packet = evidence_root / expectation.batch_id
        objects = _verify_common_packet(spec, expectation, packet)
        if expectation.status == "succeeded":
            _verify_success_packet(spec, expectation, objects)
        else:
            _verify_rejection_packet(spec, expectation, objects)
        for path in packet.iterdir():
            content = path.read_bytes()
            if any(value in content for value in prohibited):
                raise AcceptanceFailure(
                    f"Type {spec.type_number} raw restricted/row value "
                    f"leaked into evidence: {expectation.scenario}"
                )

    suite_path = (
        evidence_root
        / f"type{spec.type_number}-suite"
        / "source-isolation.json"
    )
    suite = _read_json_object(suite_path)
    dark_factory = next(
        expectation
        for expectation in expectations.values()
        if expectation.scenario.startswith("DF-SOURCE-")
    )
    peers = [
        expectations["valid-boundary"].batch_id,
        next(
            expectation.batch_id
            for expectation in expectations.values()
            if expectation.status == "succeeded"
            and expectation.scenario
            not in {"valid-minimal", "valid-boundary"}
        ),
    ]
    source_system_role = suite.get("source_system_role")
    continuation = suite.get("unrelated_batches_continue")
    if not isinstance(source_system_role, dict) or not isinstance(
        continuation,
        dict,
    ):
        raise AcceptanceFailure(
            f"Type {spec.type_number} suite-level source isolation "
            "proof has an invalid shape"
        )
    if (
        suite.get("df_batch_id") != dark_factory.batch_id
        or suite.get("file_type") != spec.type_number
        or suite.get("execution_order")
        != [scenario.name for scenario in spec.scenarios]
        or source_system_role.get("actual") != "system_of_record"
        or source_system_role.get("status") != "verified"
        or continuation.get("status") != "verified"
        or continuation.get("executed_after_batch_id")
        != dark_factory.batch_id
        or set(
            continuation.get(
                "succeeded_batch_ids",
                [],
            )
        )
        != set(peers)
    ):
        raise AcceptanceFailure(
            f"Type {spec.type_number} suite-level source isolation "
            "proof is incomplete"
        )
    suite_content = suite_path.read_bytes()
    if any(value in suite_content for value in prohibited):
        raise AcceptanceFailure(
            f"Type {spec.type_number} suite evidence leaked a raw value"
        )


def write_suite_evidence(
    spec: TypeAcceptanceSpec,
    expectations: Mapping[str, ScenarioExpectation],
    *,
    output_root: Path,
    evidence_root: Path,
) -> None:
    """Record source ownership and successful continuation after DF failure."""

    dark_factory = next(
        expectation
        for expectation in expectations.values()
        if expectation.scenario.startswith("DF-SOURCE-")
    )
    peer_scenarios = (
        "valid-boundary",
        next(
            expectation.scenario
            for expectation in expectations.values()
            if expectation.status == "succeeded"
            and expectation.scenario
            not in {"valid-minimal", "valid-boundary"}
        ),
    )
    peers = [expectations[name].batch_id for name in peer_scenarios]
    for batch_id in peers:
        final = _read_json_object(
            evidence_root / batch_id / "final-status.json"
        )
        if final.get("status") != "succeeded":
            raise AcceptanceFailure(
                f"Type {spec.type_number} peer did not continue after "
                "the source defect"
            )

    receipt = _read_json_object(
        output_root
        / dark_factory.batch_id
        / "generation-receipt.json"
    )
    publication = _read_json_object(
        evidence_root
        / dark_factory.batch_id
        / "raw-publication.json"
    )
    generator = receipt.get("generator")
    contract = receipt.get("contract")
    fault = receipt.get("fault")
    artifacts = receipt.get("artifacts")
    if (
        not isinstance(generator, dict)
        or generator.get("name") != "northwind-pay-datagen"
        or not isinstance(contract, dict)
        or contract.get("type_number") != spec.type_number
        or not isinstance(fault, dict)
        or fault.get("injected") is not True
        or fault.get("code") != dark_factory.code
        or not isinstance(artifacts, dict)
        or artifacts.get("data_sha256") != publication.get("sha256")
    ):
        raise AcceptanceFailure(
            f"Type {spec.type_number} source-of-record proof is "
            "inconsistent"
        )

    with EvidenceWriter(
        evidence_root,
        f"type{spec.type_number}-suite",
    ) as writer:
        writer.write_json(
            "source-isolation.json",
            {
                "df_batch_id": dark_factory.batch_id,
                "execution_order": [
                    scenario.name for scenario in spec.scenarios
                ],
                "file_type": spec.type_number,
                "source_system_role": {
                    "actual": "system_of_record",
                    "basis": (
                        "DataGen injected the canonical defect before "
                        "SFTP and its generated hash equals the published "
                        "raw hash"
                    ),
                    "status": "verified",
                },
                "unrelated_batches_continue": {
                    "basis": (
                        "two canonical peer scenarios completed after "
                        "the source-owned batch quarantine"
                    ),
                    "executed_after_batch_id": dark_factory.batch_id,
                    "status": "verified",
                    "succeeded_batch_ids": peers,
                },
            },
        )
        writer.commit()


def run_acceptance(type_number: str) -> None:
    """Run one complete five-scenario typed acceptance suite."""

    spec = suite_for_type(type_number)
    expectations = load_expectations(spec)
    configuration = RuntimeConfiguration.load()
    output_root = spec.output_root
    evidence_root = spec.evidence_root
    if output_root.exists() or evidence_root.exists():
        raise AcceptanceFailure(
            f"Type {type_number} acceptance workspace already exists; "
            "use the guarded runtime cleanup before a live rerun"
        )

    for scenario in spec.scenarios:
        expectation = expectations[scenario.name]
        if scenario.name == "valid-minimal":
            interrupt_scenario(
                spec,
                expectation,
                boundary="database_commit",
                output_root=output_root,
                evidence_root=evidence_root,
            )
        elif scenario.name == "valid-boundary":
            interrupt_scenario(
                spec,
                expectation,
                boundary="raw_archive",
                output_root=output_root,
                evidence_root=evidence_root,
            )
        run_scenario(
            spec,
            expectation,
            output_root=output_root,
            evidence_root=evidence_root,
        )

    verify_exact_replay(
        spec,
        expectations["valid-minimal"],
        output_root=output_root,
        evidence_root=evidence_root,
    )
    write_suite_evidence(
        spec,
        expectations,
        output_root=output_root,
        evidence_root=evidence_root,
    )
    verify_sftp(spec, expectations, configuration)
    verify_duplicate_refusal(
        spec,
        expectations,
        configuration,
        output_root=output_root,
    )
    verify_postgres(spec, expectations, configuration)
    verify_evidence(
        spec,
        expectations,
        output_root=output_root,
        evidence_root=evidence_root,
    )


def main_for_type(type_number: str) -> int:
    """Run a supported suite with a concise, privacy-safe terminal result."""

    try:
        run_acceptance(type_number)
    except AcceptanceFailure as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        f"Type {type_number} end-to-end suite passed: "
        "3 succeeded, 2 batch-quarantined"
    )
    return 0
