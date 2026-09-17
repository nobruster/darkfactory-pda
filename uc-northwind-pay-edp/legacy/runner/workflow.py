"""Shared batch-scoped orchestration for typed legacy workflows."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from config import RuntimeConfiguration, RuntimeConfigurationError
from type01_diagnostics import DiagnosticError  # type: ignore[import-untyped]
from evidence import EvidenceError, EvidenceWriter
from lifecycle import (
    LifecycleError,
    LifecycleState,
    ensure_remote_quarantine_reason,
    inspect_lifecycle,
    read_sanitized_observation,
    verify_remote_raw,
    verify_terminal_state,
)
from loader_common import (  # type: ignore[import-untyped]
    PostgresLoadError,
    finalize_committed_batch,
    quarantine_prepared_batch,
    record_rejected_batch,
)
from raw_intake import (
    RawIntakeError,
    archive_processing_batch,
    claim_batch,
    quarantine_processing_batch,
)
from raw_publisher import (
    PublishedRaw,
    RawPublicationError,
    publish_bundle,
    validate_bundle,
)
from recovery_journal import (
    BATCH_ID_PATTERN,
    FORCED_ORACLE_REASON,
    SAFE_REASONS,
    RecoveryRoute,
    TerminalRecovery,
    load_terminal_recovery,
    publish_terminal_recovery,
    remove_terminal_recovery,
)
from sftp_client import SftpBoundaryError
from workflow_registry import OracleResultLike, WorkflowAdapter


ROOT = Path(__file__).resolve().parents[2]


class PipelineError(Exception):
    """A typed vertical slice could not reach its expected terminal state."""


def build_adapter_parser(
    adapter: WorkflowAdapter,
    *,
    description: str,
) -> argparse.ArgumentParser:
    """Build a type-specific compatibility parser."""

    parser = argparse.ArgumentParser(description=description)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--scenario",
        choices=tuple(adapter.scenario_batch_ids),
    )
    source.add_argument(
        "--file",
        type=Path,
        help=(
            "Raw file whose parent contains its checksum and "
            "source-manifest.json."
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / ".runtime" / "generated",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=ROOT / "evidence",
    )
    return parser


def generated_bundle(
    adapter: WorkflowAdapter,
    scenario: str,
    *,
    output_root: Path,
    configuration: RuntimeConfiguration,
) -> Path:
    """Generate or verify one immutable canonical scenario bundle."""

    batch_id = adapter.scenario_batch_ids[scenario]
    bundle = output_root / batch_id
    if bundle.exists():
        receipt_path = bundle / "generation-receipt.json"
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PipelineError(
                "Existing immutable generated bundle is not reusable"
            ) from exc
        contract = receipt.get("contract")
        if (
            receipt.get("scenario") != scenario
            or (
                adapter.receipt_requires_type
                and (
                    not isinstance(contract, dict)
                    or contract.get("type_number") != adapter.type_number
                )
            )
        ):
            raise PipelineError(
                "Existing generated batch belongs to another scenario"
            )
        raw = validate_bundle(bundle, configuration=configuration)
        if raw.file_type != adapter.type_number:
            raise PipelineError(
                "Existing generated batch belongs to another file type"
            )
        return bundle

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "gen" / "src" / "cli.py"),
                "--type",
                adapter.type_number,
                "--scenario",
                scenario,
                "--output",
                str(output_root),
                "--contracts-root",
                str(ROOT / "contracts" / "types"),
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise PipelineError("DataGen exceeded its runtime limit") from exc
    if result.returncode != 0:
        raise PipelineError(
            "DataGen failed without producing a publishable batch"
        )
    return bundle


def bundle_from_file(
    adapter: WorkflowAdapter,
    raw_file: Path,
    *,
    configuration: RuntimeConfiguration,
) -> Path:
    """Resolve and verify an explicit bundle without scenario assumptions."""

    raw_file = raw_file.resolve()
    bundle = raw_file.parent
    published = validate_bundle(bundle, configuration=configuration)
    if published.filename != raw_file.name:
        raise PipelineError("FILE does not match the bundle source manifest")
    if published.file_type != adapter.type_number:
        raise PipelineError("FILE belongs to another workflow type")
    return bundle


def run_java(
    adapter: WorkflowAdapter,
    batch_id: str,
    configuration: RuntimeConfiguration,
) -> dict[str, object]:
    """Run the manifest-dispatched Java processor and parse its last JSON line."""

    command = [
        "docker",
        "compose",
        "run",
        "--rm",
        "--no-deps",
        "processor",
        "--batch-id",
        batch_id,
    ]
    if adapter.pass_type_to_java:
        command.extend(("--type", adapter.type_number))
    try:
        result = subprocess.run(
            command,
            cwd=configuration.root,
            capture_output=True,
            check=False,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        raise PipelineError("Java processor exceeded its runtime limit") from exc
    output_lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not output_lines:
        raise PipelineError("Java processor produced no structured result")
    try:
        java_result = json.loads(output_lines[-1])
    except json.JSONDecodeError as exc:
        raise PipelineError("Java processor result is not valid JSON") from exc
    if not isinstance(java_result, dict):
        raise PipelineError("Java processor result is not a JSON object")
    if result.returncode not in {0, 2}:
        raise PipelineError("Java processor container failed unexpectedly")
    if java_result.get("batch_id") != batch_id:
        raise PipelineError("Java processor result belongs to another batch")
    return java_result


def scenario_from_bundle(
    adapter: WorkflowAdapter,
    bundle: Path,
) -> str | None:
    """Recover a known scenario only from a matching local receipt."""

    receipt = bundle / "generation-receipt.json"
    if not receipt.is_file():
        return None
    try:
        value = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    contract = value.get("contract")
    scenario = value.get("scenario")
    if (
        (
            adapter.receipt_requires_type
            and (
                not isinstance(contract, dict)
                or contract.get("type_number") != adapter.type_number
            )
        )
        or scenario not in adapter.scenario_batch_ids
    ):
        return None
    return str(scenario)


def write_source_evidence(
    writer: EvidenceWriter,
    bundle: Path,
    raw: PublishedRaw,
) -> None:
    """Copy privacy-safe local source metadata into immutable evidence."""

    writer.write_bytes(
        "source-manifest.json",
        (bundle / "source-manifest.json").read_bytes(),
    )
    writer.write_bytes(
        "raw-file.sha256",
        (bundle / f"{raw.filename}.sha256").read_bytes(),
    )
    receipt = bundle / "generation-receipt.json"
    if receipt.is_file():
        writer.write_bytes(
            "generation-receipt.json",
            receipt.read_bytes(),
        )


def existing_terminal_evidence(
    adapter: WorkflowAdapter,
    evidence_root: Path,
    *,
    bundle: Path,
    raw: PublishedRaw,
    state: LifecycleState,
) -> Path | None:
    """Verify immutable evidence against source bytes and live terminal state."""

    evidence: Path = evidence_root.resolve() / str(raw.batch_id)
    if not evidence.exists():
        return None
    try:
        final = json.loads(
            (evidence / "final-status.json").read_text(encoding="utf-8")
        )
        source_manifest = (evidence / "source-manifest.json").read_bytes()
        checksum = (evidence / "raw-file.sha256").read_bytes()
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(
            f"Existing {adapter.display_name} evidence is incomplete "
            "and cannot be replayed"
        ) from exc
    if (
        final.get("batch_id") != raw.batch_id
        or final.get("status")
        not in {"succeeded", "quarantined", "oracle_mismatch"}
        or source_manifest != (bundle / "source-manifest.json").read_bytes()
        or checksum != (bundle / f"{raw.filename}.sha256").read_bytes()
    ):
        raise EvidenceError(
            f"Existing {adapter.display_name} evidence belongs to "
            "different source bytes"
        )
    if adapter.type_number != "01" and (
        final.get("file_type") != raw.file_type
        or final.get("source_controls") != dict(raw.source_controls)
    ):
        raise EvidenceError(
            f"Existing {adapter.display_name} evidence has different controls"
        )
    final_status = str(final["status"])
    final_code = final.get("code")
    if final_status in {"quarantined", "oracle_mismatch"}:
        if not isinstance(final_code, str) or final_code != state.failure_code:
            raise EvidenceError(
                f"Existing {adapter.display_name} evidence failure code "
                "disagrees with PostgreSQL"
            )
    elif final_code is not None or state.failure_code is not None:
        raise EvidenceError(
            f"Existing {adapter.display_name} success evidence has a "
            "failure code"
        )
    expected_final = adapter.final_status_evidence(
        raw,
        status=final_status,
        code=(
            state.failure_code
            if final_status in {"quarantined", "oracle_mismatch"}
            else None
        ),
    )
    if final != expected_final:
        raise EvidenceError(
            f"Existing {adapter.display_name} evidence has an unexpected "
            "terminal projection"
        )
    verify_terminal_state(state, final_status=final_status)
    return evidence


def write_not_run_evidence(
    writer: EvidenceWriter,
    *,
    reason: str,
) -> None:
    """Record that business procedures and reconciliation never ran."""

    writer.write_json(
        "procedure-run.json",
        {"reason": reason, "status": "not_run"},
    )
    writer.write_json(
        "reconciliation.json",
        {"reason": reason, "status": "not_run"},
    )


def _test_batch_selected(environment_name: str, batch_id: str) -> bool:
    """Return whether an explicit test hook selects this exact batch."""

    selected = os.environ.get(environment_name)
    return (
        selected is not None
        and BATCH_ID_PATTERN.fullmatch(selected) is not None
        and selected == batch_id
    )


def _interrupt_after(boundary: str, batch_id: str) -> None:
    """Raise only at one explicitly requested, exact-batch test seam."""

    if (
        os.environ.get("NWP_TEST_INTERRUPT_AFTER") == boundary
        and _test_batch_selected(
            "NWP_TEST_INTERRUPT_BATCH_ID",
            batch_id,
        )
    ):
        raise PipelineError(f"Injected interruption after {boundary}")


def _force_oracle_mismatch(batch_id: str) -> bool:
    """Expose one exact batch-scoped oracle mismatch seam for live recovery."""

    selected = os.environ.get(
        "NWP_TEST_FORCE_ORACLE_MISMATCH_BATCH_ID"
    )
    if selected is None:
        return False
    if BATCH_ID_PATTERN.fullmatch(selected) is None:
        raise PipelineError("Forced oracle test batch selector is invalid")
    return selected == batch_id


def _ensure_raw_quarantined(
    raw: PublishedRaw,
    *,
    code: str,
    configuration: RuntimeConfiguration,
) -> bool:
    """Idempotently move or verify one raw batch and its safe reason.

    Returns ``True`` only when this call performed the processing-to-quarantine
    transition. Recovery calls over an existing quarantine return ``False``.
    """

    before = inspect_lifecycle(raw, configuration=configuration)
    if before.raw_zone == "processing":
        quarantine_processing_batch(
            raw.batch_id,
            code=code,
            configuration=configuration,
        )
        moved = True
    elif before.raw_zone == "quarantine":
        moved = False
    else:
        raise LifecycleError(
            "Raw terminal quarantine has an unsafe source zone"
        )
    after = inspect_lifecycle(raw, configuration=configuration)
    if after.raw_zone != "quarantine":
        raise LifecycleError("Raw terminal quarantine was not durable")
    ensure_remote_quarantine_reason(
        raw.batch_id,
        plane="raw",
        code=code,
        configuration=configuration,
    )
    return moved


def _ensure_oracle_csv_quarantined(
    raw: PublishedRaw,
    *,
    configuration: RuntimeConfiguration,
) -> None:
    """Idempotently quarantine and verify any sanitized oracle-mismatch batch."""

    quarantine_prepared_batch(
        raw.batch_id,
        code="ORACLE_MISMATCH",
        configuration=configuration,
    )
    state = inspect_lifecycle(raw, configuration=configuration)
    if state.csv_zone is None:
        return
    if state.csv_zone != "quarantine":
        raise LifecycleError(
            "Oracle-mismatch CSV did not reach terminal quarantine"
        )
    ensure_remote_quarantine_reason(
        raw.batch_id,
        plane="csv",
        code="ORACLE_MISMATCH",
        configuration=configuration,
    )


def _write_recovery_prefix(
    adapter: WorkflowAdapter,
    writer: EvidenceWriter,
    *,
    bundle: Path,
    raw: PublishedRaw,
    java_result: Mapping[str, object],
) -> None:
    """Reconstruct only the safe evidence prefix from durable identities."""

    write_source_evidence(writer, bundle, raw)
    writer.write_json(
        "raw-publication.json",
        adapter.raw_publication_evidence(
            raw,
            status="verified_existing",
        ),
    )
    writer.write_json(
        "raw-intake.json",
        adapter.raw_intake_evidence(
            raw,
            manifest_sha256=raw.manifest_sha256,
            sha256=raw.sha256,
            status="verified_existing_claim",
        ),
    )
    writer.write_json("java-run.json", dict(java_result))


def _evidence_recovery_route(evidence: Path) -> RecoveryRoute | None:
    """Map already-validated terminal evidence to its journal route."""

    try:
        value = json.loads(
            (evidence / "final-status.json").read_text(encoding="utf-8")
        )
        status = value["status"]
    except (KeyError, OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(
            "Terminal evidence status cannot authorize journal cleanup"
        ) from exc
    if status == "quarantined":
        return "rejection"
    if status == "oracle_mismatch":
        return "oracle_mismatch"
    if status == "succeeded":
        return None
    raise EvidenceError(
        "Terminal evidence status cannot authorize journal cleanup"
    )


def _finish_rejection(
    adapter: WorkflowAdapter,
    writer: EvidenceWriter,
    *,
    raw: PublishedRaw,
    java_result: Mapping[str, object],
    oracle: OracleResultLike,
    postgres_diagnostic: Mapping[str, object],
    configuration: RuntimeConfiguration,
) -> Path:
    """Durably finish a Java rejection with replay-safe terminal ordering."""

    code = str(java_result.get("code"))
    publish_terminal_recovery(
        adapter,
        raw,
        route="rejection",
        java_result=java_result,
        code=code,
        configuration=configuration,
    )
    moved = _ensure_raw_quarantined(
        raw,
        code=code,
        configuration=configuration,
    )
    if moved:
        _interrupt_after("raw_quarantine", raw.batch_id)
    record_rejected_batch(
        raw,
        code=code,
        diagnostic_controls=adapter.diagnostic_controls(java_result),
        configuration=configuration,
    )
    terminal = inspect_lifecycle(raw, configuration=configuration)
    verify_terminal_state(terminal, final_status="quarantined")
    writer.write_json(
        "postgres-load.json",
        {
            "business_state_committed": False,
            "reason": code,
            "status": "control_recorded",
        },
    )
    writer.write_json(
        "postgres-diagnostic.json",
        dict(postgres_diagnostic),
    )
    write_not_run_evidence(writer, reason=code)
    writer.write_json("expected-diff.json", oracle.as_dict())
    writer.write_json(
        "final-status.json",
        adapter.final_status_evidence(
            raw,
            status="quarantined",
            code=code,
        ),
    )
    evidence = writer.commit()
    remove_terminal_recovery(
        adapter,
        raw,
        expected_route="rejection",
        configuration=configuration,
    )
    return evidence


def finish_oracle_mismatch(
    adapter: WorkflowAdapter,
    writer: EvidenceWriter,
    *,
    raw: PublishedRaw,
    java_result: Mapping[str, object],
    reason: str,
    configuration: RuntimeConfiguration,
) -> Path:
    """Quarantine one affected batch and publish immutable mismatch evidence.

    The original exception text is deliberately not persisted. The fixed
    reason labels prove the route without risking source-value disclosure.
    """

    safe_reason = (
        FORCED_ORACLE_REASON
        if reason == FORCED_ORACLE_REASON
        else SAFE_REASONS["oracle_mismatch"]
    )
    publish_terminal_recovery(
        adapter,
        raw,
        route="oracle_mismatch",
        java_result=java_result,
        code="ORACLE_MISMATCH",
        configuration=configuration,
        reason=safe_reason,
    )
    _ensure_oracle_csv_quarantined(
        raw,
        configuration=configuration,
    )
    moved = _ensure_raw_quarantined(
        raw,
        code="ORACLE_MISMATCH",
        configuration=configuration,
    )
    if moved:
        _interrupt_after("raw_quarantine", raw.batch_id)
    record_rejected_batch(
        raw,
        code="ORACLE_MISMATCH",
        status="oracle_mismatch",
        configuration=configuration,
    )
    terminal = inspect_lifecycle(raw, configuration=configuration)
    verify_terminal_state(terminal, final_status="oracle_mismatch")
    writer.write_json(
        "postgres-load.json",
        {
            "business_state_committed": False,
            "reason": "ORACLE_MISMATCH",
            "status": "rolled_back_or_not_started",
        },
    )
    writer.write_json(
        "postgres-diagnostic.json",
        {"reason": "ORACLE_MISMATCH", "status": "not_run"},
    )
    write_not_run_evidence(writer, reason="ORACLE_MISMATCH")
    writer.write_json(
        "expected-diff.json",
        {
            "actual": None,
            "error": safe_reason,
            "expected": adapter.oracle_expected_label,
            "matches": False,
            "oracle_status": "oracle_mismatch",
        },
    )
    writer.write_json(
        "final-status.json",
        adapter.final_status_evidence(
            raw,
            status="oracle_mismatch",
            code="ORACLE_MISMATCH",
        ),
    )
    evidence = writer.commit()
    remove_terminal_recovery(
        adapter,
        raw,
        expected_route="oracle_mismatch",
        configuration=configuration,
    )
    return evidence


def _resume_terminal_recovery(
    adapter: WorkflowAdapter,
    journal: TerminalRecovery,
    *,
    bundle: Path,
    scenario: str | None,
    evidence_root: Path,
    raw: PublishedRaw,
    state: LifecycleState,
    configuration: RuntimeConfiguration,
) -> Path:
    """Finish one journaled terminal route without invoking Java again."""

    if state.raw_zone not in {"processing", "quarantine"}:
        raise LifecycleError(
            "Journaled terminal recovery has an unsafe raw SFTP zone"
        )
    verify_remote_raw(
        raw,
        zone=state.raw_zone,
        configuration=configuration,
    )
    java_result = dict(journal.java_result)
    with EvidenceWriter(evidence_root, raw.batch_id) as writer:
        _write_recovery_prefix(
            adapter,
            writer,
            bundle=bundle,
            raw=raw,
            java_result=java_result,
        )
        if journal.route == "oracle_mismatch":
            return finish_oracle_mismatch(
                adapter,
                writer,
                raw=raw,
                java_result=java_result,
                reason=journal.reason,
                configuration=configuration,
            )
        try:
            oracle = adapter.compare_rejection(
                scenario,
                batch_id=raw.batch_id,
                java_result=java_result,
            )
            postgres_diagnostic = adapter.rejection_diagnostic(
                java_result,
                code=journal.code,
                configuration=configuration,
            )
        except adapter.oracle_error as exc:
            raise LifecycleError(
                "Journaled rejection no longer matches its approved oracle"
            ) from exc
        return _finish_rejection(
            adapter,
            writer,
            raw=raw,
            java_result=java_result,
            oracle=oracle,
            postgres_diagnostic=postgres_diagnostic,
            configuration=configuration,
        )


def run_pipeline(
    adapter: WorkflowAdapter,
    bundle: Path,
    *,
    scenario: str | None,
    evidence_root: Path,
    configuration: RuntimeConfiguration,
    recovery_only: bool = False,
) -> Path:
    """Run one batch through SFTP, Java, PostgreSQL, oracle, and evidence."""

    raw = validate_bundle(bundle, configuration=configuration)
    if raw.file_type != adapter.type_number:
        raise PipelineError("Bundle belongs to another workflow type")
    state = inspect_lifecycle(raw, configuration=configuration)
    existing = existing_terminal_evidence(
        adapter,
        evidence_root,
        bundle=bundle,
        raw=raw,
        state=state,
    )
    if existing is not None:
        remove_terminal_recovery(
            adapter,
            raw,
            expected_route=_evidence_recovery_route(existing),
            configuration=configuration,
        )
        return existing
    journal = load_terminal_recovery(
        adapter,
        raw,
        configuration=configuration,
    )
    if recovery_only and state.raw_zone is None:
        raise LifecycleError(
            "Recovery-only execution cannot republish an orphan cache"
        )
    if journal is not None:
        return _resume_terminal_recovery(
            adapter,
            journal,
            bundle=bundle,
            scenario=scenario,
            evidence_root=evidence_root,
            raw=raw,
            state=state,
            configuration=configuration,
        )

    with EvidenceWriter(evidence_root, raw.batch_id) as writer:
        write_source_evidence(writer, bundle, raw)
        if state.raw_zone is None:
            if state.csv_zone is not None or state.database_status is not None:
                raise LifecycleError(
                    "Downstream state exists without its raw SFTP batch"
                )
            published = publish_bundle(
                bundle,
                configuration=configuration,
            )
            raw_zone = "incoming"
            publication_status = "published"
        else:
            verify_remote_raw(
                raw,
                zone=state.raw_zone,
                configuration=configuration,
            )
            published = raw
            raw_zone = state.raw_zone
            publication_status = "verified_existing"
        writer.write_json(
            "raw-publication.json",
            adapter.raw_publication_evidence(
                raw,
                status=publication_status,
            ),
        )

        if raw_zone == "incoming":
            claimed = claim_batch(
                raw.batch_id,
                configuration=configuration,
            )
            if claimed.file_type != raw.file_type:
                raise LifecycleError("Claimed raw type changed during intake")
            raw_zone = "processing"
            intake_status = "claimed"
        elif raw_zone in {"processing", "archive"}:
            claimed = None
            intake_status = "verified_existing_claim"
        else:
            raise LifecycleError(
                "A quarantined raw batch has no recoverable evidence packet"
            )
        writer.write_json(
            "raw-intake.json",
            adapter.raw_intake_evidence(
                raw,
                manifest_sha256=(
                    claimed.manifest_sha256
                    if claimed is not None
                    else raw.manifest_sha256
                ),
                sha256=(
                    claimed.sha256 if claimed is not None else raw.sha256
                ),
                status=intake_status,
            ),
        )

        committed_resume = state.database_status in {
            "database_committed_pending_archive",
            "succeeded",
        }
        if committed_resume:
            if (
                raw_zone not in {"processing", "archive"}
                or state.csv_zone not in {"processing", "archive"}
            ):
                raise LifecycleError(
                    "Committed database state has inconsistent SFTP zones"
                )
            java_result = read_sanitized_observation(
                raw,
                zone=state.csv_zone,
                configuration=configuration,
            )
        elif state.database_status is not None:
            raise LifecycleError(
                "Existing PostgreSQL state is not safely resumable"
            )
        elif state.csv_zone in {"outgoing", "processing"}:
            java_result = read_sanitized_observation(
                raw,
                zone=state.csv_zone,
                configuration=configuration,
            )
        elif state.csv_zone is None:
            if raw_zone != "processing":
                raise LifecycleError(
                    "Java cannot run after the raw batch left processing"
                )
            java_result = run_java(adapter, raw.batch_id, configuration)
        else:
            raise LifecycleError(
                "Existing sanitized SFTP state is not safely resumable"
            )

        writer.write_json(
            "java-run.json",
            adapter.java_evidence(java_result),
        )
        if _force_oracle_mismatch(raw.batch_id):
            return finish_oracle_mismatch(
                adapter,
                writer,
                raw=raw,
                java_result=java_result,
                reason=FORCED_ORACLE_REASON,
                configuration=configuration,
            )
        if java_result.get("status") == "rejected":
            if committed_resume:
                raise LifecycleError(
                    "Committed database batch cannot resume as rejected"
                )
            code = str(java_result.get("code"))
            try:
                oracle = adapter.compare_rejection(
                    scenario,
                    batch_id=raw.batch_id,
                    java_result=java_result,
                )
                postgres_diagnostic = adapter.rejection_diagnostic(
                    java_result,
                    code=code,
                    configuration=configuration,
                )
            except adapter.oracle_error as exc:
                return finish_oracle_mismatch(
                    adapter,
                    writer,
                    raw=raw,
                    java_result=java_result,
                    reason=str(exc),
                    configuration=configuration,
                )

            return _finish_rejection(
                adapter,
                writer,
                raw=published,
                java_result=java_result,
                oracle=oracle,
                postgres_diagnostic=postgres_diagnostic,
                configuration=configuration,
            )

        if java_result.get("status") != "succeeded":
            raise PipelineError("Java processor returned an unknown status")
        try:
            if scenario in adapter.expected_rejection:
                raise adapter.oracle_error(
                    "A rejection scenario unexpectedly produced sanitized CSV"
                )
            sanitized_oracle = adapter.compare_sanitized(
                scenario,
                batch_id=raw.batch_id,
                observation=java_result,
            )
            reconciliation_oracle: OracleResultLike | None
            if committed_resume:
                load = adapter.recover(
                    raw.batch_id,
                    raw=published,
                    configuration=configuration,
                )
                observed_oracle = adapter.compare_sanitized(
                    scenario,
                    batch_id=raw.batch_id,
                    observation=adapter.load_observation(load),
                )
                reconciliation_oracle = adapter.compare_post_db(
                    scenario,
                    reconciliation=load.reconciliation,
                )
            else:
                prepared = adapter.prepare(
                    raw.batch_id,
                    raw=published,
                    configuration=configuration,
                )
                observed_oracle = adapter.compare_sanitized(
                    scenario,
                    batch_id=raw.batch_id,
                    observation=adapter.prepared_observation(prepared),
                )
                reconciliation_oracle = None

                def validate_reconciliation(
                    value: Mapping[str, object],
                ) -> object:
                    nonlocal reconciliation_oracle
                    reconciliation_oracle = adapter.compare_post_db(
                        scenario,
                        reconciliation=value,
                    )
                    return reconciliation_oracle

                load = adapter.commit(
                    prepared,
                    raw=published,
                    configuration=configuration,
                    reconciliation_validator=validate_reconciliation,
                )
                if reconciliation_oracle is None:
                    raise PipelineError(
                        "PostgreSQL reconciliation oracle did not execute"
                    )
                _interrupt_after("database_commit", raw.batch_id)
            if sanitized_oracle.actual != observed_oracle.actual:
                raise adapter.oracle_error(
                    "Java and loader observations of sanitized CSV disagree"
                )
        except adapter.oracle_error as exc:
            if committed_resume:
                raise LifecycleError(
                    "Committed recovery state no longer matches its oracle"
                ) from exc
            return finish_oracle_mismatch(
                adapter,
                writer,
                raw=raw,
                java_result=java_result,
                reason=str(exc),
                configuration=configuration,
            )

        assert reconciliation_oracle is not None
        writer.write_bytes(
            "sanitized-csv.sha256",
            f"{load.csv_sha256}  {load.csv_filename}\n".encode("ascii"),
        )
        writer.write_json(
            "postgres-load.json",
            adapter.postgres_load_evidence(
                load,
                raw=raw,
                status=(
                    "recovered_committed_batch"
                    if committed_resume
                    else "database_committed_pending_archive"
                ),
            ),
        )
        writer.write_json(
            "procedure-run.json",
            {
                "batch_id": load.batch_id,
                "procedures": load.procedure_runs,
                "status": "succeeded",
            },
        )
        writer.write_json("reconciliation.json", load.reconciliation)
        writer.write_json(
            "postgres-diagnostic.json",
            {
                "reason": "successful production path",
                "status": "not_applicable",
            },
        )
        writer.write_json(
            "expected-diff.json",
            {
                "actual": {
                    "reconciliation": reconciliation_oracle.actual,
                    "sanitized": sanitized_oracle.actual,
                },
                "expected": (
                    None
                    if scenario is None
                    else {
                        "reconciliation": reconciliation_oracle.expected,
                        "sanitized": sanitized_oracle.expected,
                    }
                ),
                "matches": reconciliation_oracle.matches,
                "oracle_status": reconciliation_oracle.oracle_status,
            },
        )
        if raw_zone == "processing":
            archive_processing_batch(
                raw.batch_id,
                configuration=configuration,
            )
            if not committed_resume:
                _interrupt_after("raw_archive", raw.batch_id)
        elif raw_zone != "archive":
            raise LifecycleError(
                "Successful raw batch is not ready for archive"
            )
        finalize_committed_batch(
            raw.batch_id,
            configuration=configuration,
        )
        terminal = inspect_lifecycle(raw, configuration=configuration)
        verify_terminal_state(terminal, final_status="succeeded")
        writer.write_json(
            "final-status.json",
            adapter.final_status_evidence(raw, status="succeeded"),
        )
        return writer.commit()


def execute(
    adapter: WorkflowAdapter,
    *,
    scenario: str | None,
    raw_file: Path | None,
    output_root: Path,
    evidence_root: Path,
    configuration: RuntimeConfiguration,
) -> Path:
    """Resolve one source selection and execute its typed workflow."""

    if scenario is not None:
        if scenario not in adapter.scenario_batch_ids:
            raise PipelineError(
                f"Unsupported {adapter.display_name} scenario: {scenario}"
            )
        bundle = generated_bundle(
            adapter,
            scenario,
            output_root=output_root.resolve(),
            configuration=configuration,
        )
    else:
        if raw_file is None:
            raise PipelineError("Exactly one scenario or FILE is required")
        bundle = bundle_from_file(
            adapter,
            raw_file,
            configuration=configuration,
        )
        scenario = scenario_from_bundle(adapter, bundle)
    return run_pipeline(
        adapter,
        bundle,
        scenario=scenario,
        evidence_root=evidence_root,
        configuration=configuration,
    )


def main_for_adapter(
    adapter: WorkflowAdapter,
    argv: Sequence[str] | None = None,
    *,
    description: str,
) -> int:
    """Run a type-specific compatibility CLI with stable output semantics."""

    args = build_adapter_parser(
        adapter,
        description=description,
    ).parse_args(argv)
    return run_cli_selection(
        adapter,
        scenario=args.scenario,
        raw_file=args.file,
        output_root=args.output_root,
        evidence_root=args.evidence_root,
    )


def run_cli_selection(
    adapter: WorkflowAdapter,
    *,
    scenario: str | None,
    raw_file: Path | None,
    output_root: Path,
    evidence_root: Path,
) -> int:
    """Execute one already-parsed CLI selection and print its safe result."""

    try:
        configuration = RuntimeConfiguration.load()
        evidence = execute(
            adapter,
            scenario=scenario,
            raw_file=raw_file,
            output_root=output_root,
            evidence_root=evidence_root,
            configuration=configuration,
        )
    except (
        EvidenceError,
        DiagnosticError,
        OSError,
        LifecycleError,
        PipelineError,
        PostgresLoadError,
        RawIntakeError,
        RawPublicationError,
        RuntimeConfigurationError,
        SftpBoundaryError,
        adapter.oracle_error,
    ) as exc:
        print(f"{adapter.display_name} run failed: {exc}", file=sys.stderr)
        return 2

    final = json.loads(
        (evidence / "final-status.json").read_text(encoding="utf-8")
    )
    print(
        json.dumps(
            {
                "batch_id": final["batch_id"],
                "evidence": str(evidence),
                "status": final["status"],
            },
            sort_keys=True,
        )
    )
    return 0
