"""Typed workflow adapters for independently implemented legacy file types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Protocol, cast

from config import RuntimeConfiguration
from type01_diagnostics import calculate_detail_controls
from loader_common import (
    DiagnosticControls,
    LoadResult,
)
from type01_loader import (
    PreparedType01Load,
    commit_type01_batch,
    prepare_type01_sanitized_batch,
    read_type01_committed_batch,
)
from raw_publisher import PublishedRaw
from type01_oracle import (
    EXPECTED_REJECTION as TYPE01_EXPECTED_REJECTION,
)
from type01_oracle import (
    Type01OracleMismatchError,
    compare_post_db_reconciliation as compare_type01_post_db,
    compare_rejection as compare_type01_rejection,
    compare_sanitized_before_posting as compare_type01_sanitized,
)
from type02_loader import (
    PreparedType02Load,
    commit_type02_batch,
    prepare_type02_sanitized_batch,
    read_type02_committed_batch,
)
from type02_oracle import (
    EXPECTED_REJECTION as TYPE02_EXPECTED_REJECTION,
)
from type02_oracle import (
    Type02OracleMismatchError,
    compare_post_db_reconciliation as compare_type02_post_db,
    compare_rejection as compare_type02_rejection,
    compare_sanitized_before_posting as compare_type02_sanitized,
)
from type03_loader import (
    PreparedType03Load,
    commit_type03_batch,
    prepare_type03_sanitized_batch,
    read_type03_committed_batch,
)
from type03_oracle import (
    EXPECTED_REJECTION as TYPE03_EXPECTED_REJECTION,
)
from type03_oracle import (
    Type03OracleMismatchError,
    compare_post_db_reconciliation as compare_type03_post_db,
    compare_rejection as compare_type03_rejection,
    compare_sanitized_before_posting as compare_type03_sanitized,
)
from type04_loader import (
    PreparedType04Load,
    commit_type04_batch,
    prepare_type04_sanitized_batch,
    read_type04_committed_batch,
)
from type04_oracle import (
    EXPECTED_REJECTION as TYPE04_EXPECTED_REJECTION,
)
from type04_oracle import (
    Type04OracleMismatchError,
    compare_post_db_reconciliation as compare_type04_post_db,
    compare_rejection as compare_type04_rejection,
    compare_sanitized_before_posting as compare_type04_sanitized,
)
from type05_loader import (
    PreparedType05Load,
    commit_type05_batch,
    prepare_type05_sanitized_batch,
    read_type05_committed_batch,
)
from type05_oracle import (
    EXPECTED_REJECTION as TYPE05_EXPECTED_REJECTION,
)
from type05_oracle import (
    Type05OracleMismatchError,
    compare_post_db_reconciliation as compare_type05_post_db,
    compare_rejection as compare_type05_rejection,
    compare_sanitized_before_posting as compare_type05_sanitized,
)
from type06_loader import (
    PreparedType06Load,
    commit_type06_batch,
    prepare_type06_sanitized_batch,
    read_type06_committed_batch,
)
from type06_oracle import (
    EXPECTED_REJECTION as TYPE06_EXPECTED_REJECTION,
)
from type06_oracle import (
    Type06OracleMismatchError,
    compare_post_db_reconciliation as compare_type06_post_db,
    compare_rejection as compare_type06_rejection,
    compare_sanitized_before_posting as compare_type06_sanitized,
)


class OracleResultLike(Protocol):
    """Structural documentation for oracle results consumed by the engine."""

    matches: bool | None
    expected: dict[str, object] | None
    actual: dict[str, object]
    oracle_status: str

    def as_dict(self) -> dict[str, object]:
        """Return privacy-safe JSON-compatible comparison evidence."""

        ...


class WorkflowAdapter(ABC):
    """Type-owned operations required by the shared orchestration engine."""

    type_number: str
    display_name: str
    scenario_batch_ids: Mapping[str, str]
    expected_rejection: Mapping[str, str]
    oracle_error: type[Exception]
    pass_type_to_java: bool = False
    receipt_requires_type: bool = False

    @abstractmethod
    def prepare(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> object:
        """Validate and claim sanitized output without database mutation."""

    @abstractmethod
    def commit(
        self,
        prepared: object,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
        reconciliation_validator: Callable[[Mapping[str, object]], object],
    ) -> LoadResult:
        """Commit one prepared batch with an in-transaction oracle callback."""

    @abstractmethod
    def recover(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> LoadResult:
        """Read and verify an already committed batch."""

    @abstractmethod
    def prepared_observation(
        self,
        prepared: object,
    ) -> Mapping[str, object]:
        """Return complete sanitized controls independently seen by loader."""

    @abstractmethod
    def load_observation(
        self,
        load: LoadResult,
    ) -> Mapping[str, object]:
        """Return complete sanitized controls from committed recovery state."""

    @abstractmethod
    def compare_sanitized(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        observation: Mapping[str, object],
    ) -> OracleResultLike:
        """Apply the pre-database sanitized oracle."""

    @abstractmethod
    def compare_post_db(
        self,
        scenario: str | None,
        *,
        reconciliation: Mapping[str, object],
    ) -> OracleResultLike:
        """Apply the complete reconciliation oracle."""

    @abstractmethod
    def compare_rejection(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        java_result: Mapping[str, object],
    ) -> OracleResultLike:
        """Apply the canonical rejection oracle."""

    @abstractmethod
    def rejection_diagnostic(
        self,
        java_result: Mapping[str, object],
        *,
        code: str,
        configuration: RuntimeConfiguration,
    ) -> dict[str, object]:
        """Produce privacy-safe rejection diagnostics."""

    @abstractmethod
    def diagnostic_controls(
        self,
        java_result: Mapping[str, object],
    ) -> DiagnosticControls:
        """Normalize common count/net controls for control-plane persistence."""

    def java_evidence(
        self,
        java_result: Mapping[str, object],
    ) -> dict[str, object]:
        """Return the Java evidence shape; Type 01 retains its exact output."""

        return dict(java_result)

    def raw_publication_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
    ) -> dict[str, object]:
        """Return Type 01-compatible publication evidence by default."""

        return {
            "batch_id": raw.batch_id,
            "manifest_last": True,
            "sha256": raw.sha256,
            "status": status,
        }

    def raw_intake_evidence(
        self,
        raw: PublishedRaw,
        *,
        manifest_sha256: str,
        sha256: str,
        status: str,
    ) -> dict[str, object]:
        """Return Type 01-compatible intake evidence by default."""

        return {
            "batch_id": raw.batch_id,
            "manifest_sha256": manifest_sha256,
            "sha256": sha256,
            "status": status,
        }

    def postgres_load_evidence(
        self,
        load: LoadResult,
        *,
        raw: PublishedRaw,
        status: str,
    ) -> dict[str, object]:
        """Return Type 01-compatible load evidence by default."""

        return {
            "batch_id": load.batch_id,
            "net_amount": load.net_amount,
            "row_count": load.row_count,
            "status": status,
        }

    def final_status_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
        code: str | None = None,
    ) -> dict[str, object]:
        """Return Type 01-compatible terminal evidence by default."""

        value: dict[str, object] = {
            "batch_id": raw.batch_id,
            "scope": "batch",
            "status": status,
        }
        if code is not None:
            value["code"] = code
        return value

    @property
    def oracle_expected_label(self) -> str:
        """Return the safe artifact label used for oracle mismatch evidence."""

        return f"approved Type {self.type_number} contract artifact"


class Type01WorkflowAdapter(WorkflowAdapter):
    """Type 01 orchestration behind the shared typed workflow boundary."""

    type_number = "01"
    display_name = "Type 01"
    scenario_batch_ids = MappingProxyType(
        {
            "valid-minimal": "B202607230000001",
            "valid-boundary": "B202402290000001",
            "negative-overpunch": "B202607230000002",
            "malformed": "B202607230000003",
            "DF-SOURCE-001": "B202607230000004",
        }
    )
    expected_rejection = TYPE01_EXPECTED_REJECTION
    oracle_error = Type01OracleMismatchError
    pass_type_to_java = True
    receipt_requires_type = True

    def prepare(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> PreparedType01Load:
        return prepare_type01_sanitized_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    def commit(
        self,
        prepared: object,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
        reconciliation_validator: Callable[[Mapping[str, object]], object],
    ) -> LoadResult:
        if not isinstance(prepared, PreparedType01Load):
            raise TypeError("Type 01 workflow received another prepared type")
        return commit_type01_batch(
            prepared,
            raw=raw,
            configuration=configuration,
            reconciliation_validator=reconciliation_validator,
        )

    def recover(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> LoadResult:
        return read_type01_committed_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    def prepared_observation(
        self,
        prepared: object,
    ) -> Mapping[str, object]:
        if not isinstance(prepared, PreparedType01Load):
            raise TypeError("Type 01 workflow received another prepared type")
        return {
            "batch_id": prepared.batch_id,
            "csv_sha256": prepared.csv_sha256,
            "net_amount": prepared.net_amount,
            "row_count": prepared.row_count,
            "status": "succeeded",
        }

    def load_observation(
        self,
        load: LoadResult,
    ) -> Mapping[str, object]:
        return {
            "batch_id": load.batch_id,
            "csv_sha256": load.csv_sha256,
            "net_amount": load.net_amount,
            "row_count": load.row_count,
            "status": "succeeded",
        }

    def compare_sanitized(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        observation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type01_sanitized(
                scenario,
                batch_id=batch_id,
                java_result=observation,
            ),
        )

    def compare_post_db(
        self,
        scenario: str | None,
        *,
        reconciliation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type01_post_db(
                scenario,
                reconciliation=reconciliation,
            ),
        )

    def compare_rejection(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        java_result: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type01_rejection(
                scenario,
                batch_id=batch_id,
                java_result=java_result,
            ),
        )

    def rejection_diagnostic(
        self,
        java_result: Mapping[str, object],
        *,
        code: str,
        configuration: RuntimeConfiguration,
    ) -> dict[str, object]:
        amounts = java_result.get("detail_amounts")
        if amounts is None:
            return {"reason": code, "status": "not_run"}
        diagnostic = calculate_detail_controls(
            amounts,
            configuration=configuration,
        )
        if (
            diagnostic["computed_detail_count"]
            != java_result.get("computed_detail_count")
            or diagnostic["computed_net_amount"]
            != java_result.get("computed_net_amount")
        ):
            raise Type01OracleMismatchError(
                "Read-only PostgreSQL diagnostic disagrees with "
                "the Java source controls"
            )
        return diagnostic

    def diagnostic_controls(
        self,
        java_result: Mapping[str, object],
    ) -> DiagnosticControls:
        return DiagnosticControls(
            computed_count=cast(
                int | None,
                java_result.get("computed_detail_count"),
            ),
            computed_net_amount=cast(
                str | None,
                java_result.get("computed_net_amount"),
            ),
            declared_count=cast(
                int | None,
                java_result.get("declared_detail_count"),
            ),
            declared_net_amount=cast(
                str | None,
                java_result.get("declared_net_amount"),
            ),
        )

    def java_evidence(
        self,
        java_result: Mapping[str, object],
    ) -> dict[str, object]:
        """Project the original Type 01 result through an explicit allowlist."""

        safe_fields = (
            "batch_id",
            "code",
            "computed_detail_count",
            "computed_net_amount",
            "csv_file",
            "csv_sha256",
            "declared_detail_count",
            "declared_net_amount",
            "detail_amounts",
            "net_amount",
            "record_number",
            "row_count",
            "status",
            "transaction_id",
        )
        return {
            name: java_result.get(name)
            for name in safe_fields
        }


class Type02WorkflowAdapter(WorkflowAdapter):
    """Type 02 orchestration using aggregate-only privacy-safe controls."""

    type_number = "02"
    display_name = "Type 02"
    scenario_batch_ids = MappingProxyType(
        {
            "valid-minimal": "B202607230000101",
            "valid-boundary": "B202402290000102",
            "escaped-content": "B202607230000104",
            "malformed": "B202607230000103",
            "DF-SOURCE-002": "B202607230000105",
        }
    )
    expected_rejection = TYPE02_EXPECTED_REJECTION
    oracle_error = Type02OracleMismatchError
    pass_type_to_java = True
    receipt_requires_type = True

    def prepare(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> PreparedType02Load:
        return prepare_type02_sanitized_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    def commit(
        self,
        prepared: object,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
        reconciliation_validator: Callable[[Mapping[str, object]], object],
    ) -> LoadResult:
        if not isinstance(prepared, PreparedType02Load):
            raise TypeError("Type 02 workflow received another prepared type")
        return commit_type02_batch(
            prepared,
            raw=raw,
            configuration=configuration,
            reconciliation_validator=reconciliation_validator,
        )

    def recover(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> LoadResult:
        return read_type02_committed_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    @staticmethod
    def _observation(
        *,
        batch_id: str,
        csv_sha256: str,
        row_count: object,
        credit_amount: object,
        debit_amount: object,
        net_amount: object,
        returned_count: object,
    ) -> Mapping[str, object]:
        return {
            "batch_id": batch_id,
            "credit_amount": credit_amount,
            "csv_sha256": csv_sha256,
            "debit_amount": debit_amount,
            "net_amount": net_amount,
            "returned_count": returned_count,
            "row_count": row_count,
            "status": "succeeded",
        }

    def prepared_observation(
        self,
        prepared: object,
    ) -> Mapping[str, object]:
        if not isinstance(prepared, PreparedType02Load):
            raise TypeError("Type 02 workflow received another prepared type")
        controls = prepared.stage_controls
        return self._observation(
            batch_id=prepared.batch_id,
            csv_sha256=prepared.csv_sha256,
            row_count=controls["row_count"],
            credit_amount=controls["credit_amount"],
            debit_amount=controls["debit_amount"],
            net_amount=controls["net_amount"],
            returned_count=controls["returned_count"],
        )

    def load_observation(
        self,
        load: LoadResult,
    ) -> Mapping[str, object]:
        reconciliation = load.reconciliation
        return self._observation(
            batch_id=load.batch_id,
            csv_sha256=load.csv_sha256,
            row_count=reconciliation.get("staged_count"),
            credit_amount=reconciliation.get("staged_credit_amount"),
            debit_amount=reconciliation.get("staged_debit_amount"),
            net_amount=reconciliation.get("staged_net_amount"),
            returned_count=reconciliation.get("staged_returned_count"),
        )

    def compare_sanitized(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        observation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type02_sanitized(
                scenario,
                batch_id=batch_id,
                java_result=observation,
            ),
        )

    def compare_post_db(
        self,
        scenario: str | None,
        *,
        reconciliation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type02_post_db(
                scenario,
                reconciliation=reconciliation,
            ),
        )

    def compare_rejection(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        java_result: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type02_rejection(
                scenario,
                batch_id=batch_id,
                java_result=java_result,
            ),
        )

    def rejection_diagnostic(
        self,
        java_result: Mapping[str, object],
        *,
        code: str,
        configuration: RuntimeConfiguration,
    ) -> dict[str, object]:
        del configuration
        if code == "INVALID_FIELD_COUNT":
            return {
                "file_type": self.type_number,
                "reason": code,
                "status": "not_run",
            }
        safe_fields = (
            "computed_credit_amount",
            "computed_debit_amount",
            "computed_event_count",
            "computed_net_amount",
            "declared_credit_amount",
            "declared_debit_amount",
            "declared_event_count",
            "declared_net_amount",
        )
        return {
            "business_state_committed": False,
            "file_type": self.type_number,
            "input": "privacy-safe-java-aggregate-controls",
            "mode": "source-parser-observation",
            **{name: java_result.get(name) for name in safe_fields},
            "status": "completed",
        }

    def diagnostic_controls(
        self,
        java_result: Mapping[str, object],
    ) -> DiagnosticControls:
        computed_count = java_result.get("computed_event_count")
        declared_count = java_result.get("declared_event_count")
        computed_net = java_result.get("computed_net_amount")
        declared_net = java_result.get("declared_net_amount")
        return DiagnosticControls(
            computed_count=(
                computed_count
                if isinstance(computed_count, int)
                and not isinstance(computed_count, bool)
                else None
            ),
            computed_net_amount=(
                computed_net if isinstance(computed_net, str) else None
            ),
            declared_count=(
                declared_count
                if isinstance(declared_count, int)
                and not isinstance(declared_count, bool)
                else None
            ),
            declared_net_amount=(
                declared_net if isinstance(declared_net, str) else None
            ),
        )

    def java_evidence(
        self,
        java_result: Mapping[str, object],
    ) -> dict[str, object]:
        safe_fields: tuple[str, ...]
        if java_result.get("status") == "succeeded":
            safe_fields = (
                "batch_id",
                "code",
                "credit_amount",
                "csv_file",
                "csv_sha256",
                "debit_amount",
                "net_amount",
                "returned_count",
                "row_count",
                "status",
            )
        else:
            safe_fields = (
                "batch_id",
                "code",
                "computed_credit_amount",
                "computed_debit_amount",
                "computed_event_count",
                "computed_net_amount",
                "declared_credit_amount",
                "declared_debit_amount",
                "declared_event_count",
                "declared_net_amount",
                "record_number",
                "status",
            )
        return {
            "file_type": self.type_number,
            **{name: java_result.get(name) for name in safe_fields},
        }

    def raw_publication_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
    ) -> dict[str, object]:
        value = super().raw_publication_evidence(raw, status=status)
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value

    def raw_intake_evidence(
        self,
        raw: PublishedRaw,
        *,
        manifest_sha256: str,
        sha256: str,
        status: str,
    ) -> dict[str, object]:
        value = super().raw_intake_evidence(
            raw,
            manifest_sha256=manifest_sha256,
            sha256=sha256,
            status=status,
        )
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value

    def postgres_load_evidence(
        self,
        load: LoadResult,
        *,
        raw: PublishedRaw,
        status: str,
    ) -> dict[str, object]:
        reconciliation = load.reconciliation
        return {
            "batch_id": load.batch_id,
            "csv_sha256": load.csv_sha256,
            "file_type": raw.file_type,
            "net_amount": load.net_amount,
            "row_count": load.row_count,
            "source_controls": dict(raw.source_controls),
            "stage_controls": {
                "credit_amount": reconciliation.get(
                    "staged_credit_amount"
                ),
                "currency": reconciliation.get("currency"),
                "debit_amount": reconciliation.get("staged_debit_amount"),
                "net_amount": reconciliation.get("staged_net_amount"),
                "returned_count": reconciliation.get(
                    "staged_returned_count"
                ),
                "row_count": reconciliation.get("staged_count"),
            },
            "status": status,
        }

    def final_status_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
        code: str | None = None,
    ) -> dict[str, object]:
        value = super().final_status_evidence(
            raw,
            status=status,
            code=code,
        )
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value


class Type03WorkflowAdapter(WorkflowAdapter):
    """Type 03 orchestration using only aggregate rejection controls."""

    type_number = "03"
    display_name = "Type 03"
    scenario_batch_ids = MappingProxyType(
        {
            "valid-minimal": "B202607230000201",
            "valid-boundary": "B202402290000202",
            "malformed": "B202607230000203",
            "multi-lot": "B202607230000204",
            "DF-SOURCE-003": "B202607230000205",
        }
    )
    expected_rejection = TYPE03_EXPECTED_REJECTION
    oracle_error = Type03OracleMismatchError
    pass_type_to_java = True
    receipt_requires_type = True

    def prepare(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> PreparedType03Load:
        return prepare_type03_sanitized_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    def commit(
        self,
        prepared: object,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
        reconciliation_validator: Callable[[Mapping[str, object]], object],
    ) -> LoadResult:
        if not isinstance(prepared, PreparedType03Load):
            raise TypeError("Type 03 workflow received another prepared type")
        return commit_type03_batch(
            prepared,
            raw=raw,
            configuration=configuration,
            reconciliation_validator=reconciliation_validator,
        )

    def recover(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> LoadResult:
        return read_type03_committed_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    @staticmethod
    def _observation(
        *,
        batch_id: str,
        csv_sha256: str,
        row_count: object,
        face_amount: object,
        discount_amount: object,
        fee_amount: object,
        net_amount: object,
        orphan_segment_count: object,
    ) -> Mapping[str, object]:
        return {
            "batch_id": batch_id,
            "csv_sha256": csv_sha256,
            "discount_amount": discount_amount,
            "face_amount": face_amount,
            "fee_amount": fee_amount,
            "net_amount": net_amount,
            "orphan_segment_count": orphan_segment_count,
            "row_count": row_count,
            "status": "succeeded",
        }

    def prepared_observation(
        self,
        prepared: object,
    ) -> Mapping[str, object]:
        if not isinstance(prepared, PreparedType03Load):
            raise TypeError("Type 03 workflow received another prepared type")
        controls = prepared.stage_controls
        return self._observation(
            batch_id=prepared.batch_id,
            csv_sha256=prepared.csv_sha256,
            row_count=controls["row_count"],
            face_amount=controls["face_amount"],
            discount_amount=controls["discount_amount"],
            fee_amount=controls["fee_amount"],
            net_amount=controls["net_amount"],
            orphan_segment_count=controls["orphan_segment_count"],
        )

    def load_observation(
        self,
        load: LoadResult,
    ) -> Mapping[str, object]:
        reconciliation = load.reconciliation
        return self._observation(
            batch_id=load.batch_id,
            csv_sha256=load.csv_sha256,
            row_count=reconciliation.get("staged_count"),
            face_amount=reconciliation.get("staged_face_amount"),
            discount_amount=reconciliation.get(
                "staged_discount_amount"
            ),
            fee_amount=reconciliation.get("staged_fee_amount"),
            net_amount=reconciliation.get("staged_net_amount"),
            orphan_segment_count=reconciliation.get(
                "staged_orphan_segment_count"
            ),
        )

    def compare_sanitized(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        observation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type03_sanitized(
                scenario,
                batch_id=batch_id,
                java_result=observation,
            ),
        )

    def compare_post_db(
        self,
        scenario: str | None,
        *,
        reconciliation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type03_post_db(
                scenario,
                reconciliation=reconciliation,
            ),
        )

    def compare_rejection(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        java_result: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type03_rejection(
                scenario,
                batch_id=batch_id,
                java_result=java_result,
            ),
        )

    @staticmethod
    def _rejection_control_fields() -> tuple[str, ...]:
        return (
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
        )

    def rejection_diagnostic(
        self,
        java_result: Mapping[str, object],
        *,
        code: str,
        configuration: RuntimeConfiguration,
    ) -> dict[str, object]:
        del configuration
        if code == "SEGMENT_PAIR_MISMATCH":
            return {
                "file_type": self.type_number,
                "reason": code,
                "status": "not_run",
            }
        return {
            "business_state_committed": False,
            "file_type": self.type_number,
            "input": "privacy-safe-java-aggregate-controls",
            "mode": "source-parser-observation",
            **{
                name: java_result.get(name)
                for name in self._rejection_control_fields()
            },
            "status": "completed",
        }

    def diagnostic_controls(
        self,
        java_result: Mapping[str, object],
    ) -> DiagnosticControls:
        computed_count = java_result.get("computed_logical_count")
        declared_count = java_result.get("declared_logical_count")
        computed_net = java_result.get("computed_net_amount")
        declared_net = java_result.get("declared_net_amount")
        return DiagnosticControls(
            computed_count=(
                computed_count
                if isinstance(computed_count, int)
                and not isinstance(computed_count, bool)
                else None
            ),
            computed_net_amount=(
                computed_net if isinstance(computed_net, str) else None
            ),
            declared_count=(
                declared_count
                if isinstance(declared_count, int)
                and not isinstance(declared_count, bool)
                else None
            ),
            declared_net_amount=(
                declared_net if isinstance(declared_net, str) else None
            ),
        )

    def java_evidence(
        self,
        java_result: Mapping[str, object],
    ) -> dict[str, object]:
        safe_fields: tuple[str, ...]
        if java_result.get("status") == "succeeded":
            safe_fields = (
                "batch_id",
                "code",
                "csv_file",
                "csv_sha256",
                "discount_amount",
                "face_amount",
                "fee_amount",
                "net_amount",
                "orphan_segment_count",
                "row_count",
                "status",
            )
        else:
            safe_fields = (
                "batch_id",
                "code",
                *self._rejection_control_fields(),
                "record_number",
                "status",
            )
        return {
            "file_type": self.type_number,
            **{name: java_result.get(name) for name in safe_fields},
        }

    def raw_publication_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
    ) -> dict[str, object]:
        value = super().raw_publication_evidence(raw, status=status)
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value

    def raw_intake_evidence(
        self,
        raw: PublishedRaw,
        *,
        manifest_sha256: str,
        sha256: str,
        status: str,
    ) -> dict[str, object]:
        value = super().raw_intake_evidence(
            raw,
            manifest_sha256=manifest_sha256,
            sha256=sha256,
            status=status,
        )
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value

    def postgres_load_evidence(
        self,
        load: LoadResult,
        *,
        raw: PublishedRaw,
        status: str,
    ) -> dict[str, object]:
        reconciliation = load.reconciliation
        return {
            "batch_id": load.batch_id,
            "csv_sha256": load.csv_sha256,
            "file_type": raw.file_type,
            "net_amount": load.net_amount,
            "row_count": load.row_count,
            "source_controls": dict(raw.source_controls),
            "stage_controls": {
                "currency": reconciliation.get("currency"),
                "discount_amount": reconciliation.get(
                    "staged_discount_amount"
                ),
                "face_amount": reconciliation.get(
                    "staged_face_amount"
                ),
                "fee_amount": reconciliation.get("staged_fee_amount"),
                "net_amount": reconciliation.get("staged_net_amount"),
                "orphan_segment_count": reconciliation.get(
                    "staged_orphan_segment_count"
                ),
                "row_count": reconciliation.get("staged_count"),
            },
            "status": status,
        }

    def final_status_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
        code: str | None = None,
    ) -> dict[str, object]:
        value = super().final_status_evidence(
            raw,
            status=status,
            code=code,
        )
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value


class Type04WorkflowAdapter(WorkflowAdapter):
    """Type 04 orchestration using only aggregate rejection controls."""

    type_number = "04"
    display_name = "Type 04"
    scenario_batch_ids = MappingProxyType(
        {
            "valid-minimal": "B202607230000301",
            "valid-boundary": "B200002290000302",
            "malformed": "B202607230000303",
            "all-returned-zero-net": "B202607230000304",
            "DF-SOURCE-004": "B202607230000305",
        }
    )
    expected_rejection = TYPE04_EXPECTED_REJECTION
    oracle_error = Type04OracleMismatchError
    pass_type_to_java = True
    receipt_requires_type = True

    def prepare(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> PreparedType04Load:
        return prepare_type04_sanitized_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    def commit(
        self,
        prepared: object,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
        reconciliation_validator: Callable[[Mapping[str, object]], object],
    ) -> LoadResult:
        if not isinstance(prepared, PreparedType04Load):
            raise TypeError("Type 04 workflow received another prepared type")
        return commit_type04_batch(
            prepared,
            raw=raw,
            configuration=configuration,
            reconciliation_validator=reconciliation_validator,
        )

    def recover(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> LoadResult:
        return read_type04_committed_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    @staticmethod
    def _observation(
        *,
        batch_id: str,
        csv_sha256: str,
        row_count: object,
        transfer_count: object,
        return_count: object,
        gross_amount: object,
        return_amount: object,
        net_amount: object,
    ) -> Mapping[str, object]:
        return {
            "batch_id": batch_id,
            "csv_sha256": csv_sha256,
            "gross_amount": gross_amount,
            "net_amount": net_amount,
            "return_amount": return_amount,
            "return_count": return_count,
            "row_count": row_count,
            "status": "succeeded",
            "transfer_count": transfer_count,
        }

    def prepared_observation(
        self,
        prepared: object,
    ) -> Mapping[str, object]:
        if not isinstance(prepared, PreparedType04Load):
            raise TypeError("Type 04 workflow received another prepared type")
        controls = prepared.stage_controls
        return self._observation(
            batch_id=prepared.batch_id,
            csv_sha256=prepared.csv_sha256,
            row_count=controls["row_count"],
            transfer_count=controls["transfer_count"],
            return_count=controls["return_count"],
            gross_amount=controls["gross_amount"],
            return_amount=controls["return_amount"],
            net_amount=controls["net_amount"],
        )

    def load_observation(
        self,
        load: LoadResult,
    ) -> Mapping[str, object]:
        reconciliation = load.reconciliation
        transfer_count = reconciliation.get("staged_transfer_count")
        return_count = reconciliation.get("staged_return_count")
        row_count = (
            transfer_count + return_count
            if isinstance(transfer_count, int)
            and not isinstance(transfer_count, bool)
            and isinstance(return_count, int)
            and not isinstance(return_count, bool)
            else None
        )
        return self._observation(
            batch_id=load.batch_id,
            csv_sha256=load.csv_sha256,
            row_count=row_count,
            transfer_count=transfer_count,
            return_count=return_count,
            gross_amount=reconciliation.get("staged_gross_amount"),
            return_amount=reconciliation.get("staged_return_amount"),
            net_amount=reconciliation.get("staged_net_amount"),
        )

    def compare_sanitized(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        observation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type04_sanitized(
                scenario,
                batch_id=batch_id,
                java_result=observation,
            ),
        )

    def compare_post_db(
        self,
        scenario: str | None,
        *,
        reconciliation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type04_post_db(
                scenario,
                reconciliation=reconciliation,
            ),
        )

    def compare_rejection(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        java_result: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type04_rejection(
                scenario,
                batch_id=batch_id,
                java_result=java_result,
            ),
        )

    @staticmethod
    def _rejection_control_fields() -> tuple[str, ...]:
        return (
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
        )

    def rejection_diagnostic(
        self,
        java_result: Mapping[str, object],
        *,
        code: str,
        configuration: RuntimeConfiguration,
    ) -> dict[str, object]:
        del configuration
        if code == "INVALID_TRANSPORT":
            return {
                "file_type": self.type_number,
                "reason": code,
                "status": "not_run",
            }
        return {
            "business_state_committed": False,
            "file_type": self.type_number,
            "input": "privacy-safe-java-aggregate-controls",
            "mode": "source-parser-observation",
            **{
                name: java_result.get(name)
                for name in self._rejection_control_fields()
            },
            "status": "completed",
        }

    def diagnostic_controls(
        self,
        java_result: Mapping[str, object],
    ) -> DiagnosticControls:
        computed_count = java_result.get("computed_transfer_count")
        declared_count = java_result.get("declared_transfer_count")
        computed_net = java_result.get("computed_net_amount")
        declared_net = java_result.get("declared_net_amount")
        return DiagnosticControls(
            computed_count=(
                computed_count
                if isinstance(computed_count, int)
                and not isinstance(computed_count, bool)
                else None
            ),
            computed_net_amount=(
                computed_net if isinstance(computed_net, str) else None
            ),
            declared_count=(
                declared_count
                if isinstance(declared_count, int)
                and not isinstance(declared_count, bool)
                else None
            ),
            declared_net_amount=(
                declared_net if isinstance(declared_net, str) else None
            ),
        )

    def java_evidence(
        self,
        java_result: Mapping[str, object],
    ) -> dict[str, object]:
        safe_fields: tuple[str, ...]
        if java_result.get("status") == "succeeded":
            safe_fields = (
                "batch_id",
                "code",
                "csv_file",
                "csv_sha256",
                "gross_amount",
                "net_amount",
                "return_amount",
                "return_count",
                "row_count",
                "status",
                "transfer_count",
            )
        else:
            safe_fields = (
                "batch_id",
                "code",
                *self._rejection_control_fields(),
                "record_number",
                "status",
            )
        return {
            "file_type": self.type_number,
            **{name: java_result.get(name) for name in safe_fields},
        }

    def raw_publication_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
    ) -> dict[str, object]:
        value = super().raw_publication_evidence(raw, status=status)
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value

    def raw_intake_evidence(
        self,
        raw: PublishedRaw,
        *,
        manifest_sha256: str,
        sha256: str,
        status: str,
    ) -> dict[str, object]:
        value = super().raw_intake_evidence(
            raw,
            manifest_sha256=manifest_sha256,
            sha256=sha256,
            status=status,
        )
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value

    def postgres_load_evidence(
        self,
        load: LoadResult,
        *,
        raw: PublishedRaw,
        status: str,
    ) -> dict[str, object]:
        reconciliation = load.reconciliation
        return {
            "batch_id": load.batch_id,
            "csv_sha256": load.csv_sha256,
            "file_type": raw.file_type,
            "net_amount": load.net_amount,
            "row_count": load.row_count,
            "source_controls": dict(raw.source_controls),
            "stage_controls": {
                "currency": reconciliation.get("currency"),
                "gross_amount": reconciliation.get(
                    "staged_gross_amount"
                ),
                "net_amount": reconciliation.get("staged_net_amount"),
                "return_amount": reconciliation.get(
                    "staged_return_amount"
                ),
                "return_count": reconciliation.get(
                    "staged_return_count"
                ),
                "row_count": load.row_count,
                "transfer_count": reconciliation.get(
                    "staged_transfer_count"
                ),
            },
            "status": status,
        }

    def final_status_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
        code: str | None = None,
    ) -> dict[str, object]:
        value = super().final_status_evidence(
            raw,
            status=status,
            code=code,
        )
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value


class Type05WorkflowAdapter(WorkflowAdapter):
    """Type 05 orchestration with aggregate-only privacy-safe evidence."""

    type_number = "05"
    display_name = "Type 05"
    scenario_batch_ids = MappingProxyType(
        {
            "valid-minimal": "B202607230000401",
            "valid-boundary": "B200002290000402",
            "malformed": "B202607230000403",
            "rounding-half-up": "B202607230000404",
            "DF-SOURCE-005": "B202607230000405",
        }
    )
    expected_rejection = TYPE05_EXPECTED_REJECTION
    oracle_error = Type05OracleMismatchError
    pass_type_to_java = True
    receipt_requires_type = True

    def prepare(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> PreparedType05Load:
        return prepare_type05_sanitized_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    def commit(
        self,
        prepared: object,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
        reconciliation_validator: Callable[[Mapping[str, object]], object],
    ) -> LoadResult:
        if not isinstance(prepared, PreparedType05Load):
            raise TypeError("Type 05 workflow received another prepared type")
        return commit_type05_batch(
            prepared,
            raw=raw,
            configuration=configuration,
            reconciliation_validator=reconciliation_validator,
        )

    def recover(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> LoadResult:
        return read_type05_committed_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    @staticmethod
    def _observation(
        *,
        batch_id: str,
        csv_sha256: str,
        row_count: object,
        gross_amount: object,
        assessed_fee: object,
        calculated_fee: object,
    ) -> Mapping[str, object]:
        return {
            "assessed_fee": assessed_fee,
            "batch_id": batch_id,
            "calculated_fee": calculated_fee,
            "csv_sha256": csv_sha256,
            "gross_amount": gross_amount,
            "row_count": row_count,
            "status": "succeeded",
        }

    def prepared_observation(
        self,
        prepared: object,
    ) -> Mapping[str, object]:
        if not isinstance(prepared, PreparedType05Load):
            raise TypeError("Type 05 workflow received another prepared type")
        controls = prepared.stage_controls
        return self._observation(
            batch_id=prepared.batch_id,
            csv_sha256=prepared.csv_sha256,
            row_count=controls["row_count"],
            gross_amount=controls["gross_amount"],
            assessed_fee=controls["assessed_fee"],
            calculated_fee=controls["calculated_fee"],
        )

    def load_observation(
        self,
        load: LoadResult,
    ) -> Mapping[str, object]:
        reconciliation = load.reconciliation
        return self._observation(
            batch_id=load.batch_id,
            csv_sha256=load.csv_sha256,
            row_count=reconciliation.get("staged_count"),
            gross_amount=reconciliation.get("staged_gross_amount"),
            assessed_fee=reconciliation.get("staged_assessed_fee"),
            calculated_fee=reconciliation.get("staged_calculated_fee"),
        )

    def compare_sanitized(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        observation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type05_sanitized(
                scenario,
                batch_id=batch_id,
                java_result=observation,
            ),
        )

    def compare_post_db(
        self,
        scenario: str | None,
        *,
        reconciliation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type05_post_db(
                scenario,
                reconciliation=reconciliation,
            ),
        )

    def compare_rejection(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        java_result: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type05_rejection(
                scenario,
                batch_id=batch_id,
                java_result=java_result,
            ),
        )

    @staticmethod
    def _rejection_control_fields() -> tuple[str, ...]:
        return (
            "computed_assessed_fee",
            "computed_calculated_fee",
            "computed_gross_amount",
            "computed_row_count",
            "declared_assessed_fee",
            "declared_calculated_fee",
            "declared_gross_amount",
            "declared_row_count",
        )

    def rejection_diagnostic(
        self,
        java_result: Mapping[str, object],
        *,
        code: str,
        configuration: RuntimeConfiguration,
    ) -> dict[str, object]:
        del configuration
        if code == "INVALID_CSV_QUOTING":
            return {
                "file_type": self.type_number,
                "reason": code,
                "status": "not_run",
            }
        return {
            "business_state_committed": False,
            "file_type": self.type_number,
            "input": "privacy-safe-java-aggregate-controls",
            "mode": "source-parser-observation",
            **{
                name: java_result.get(name)
                for name in self._rejection_control_fields()
            },
            "status": "completed",
        }

    def diagnostic_controls(
        self,
        java_result: Mapping[str, object],
    ) -> DiagnosticControls:
        computed_count = java_result.get("computed_row_count")
        declared_count = java_result.get("declared_row_count")
        computed_assessed = java_result.get("computed_assessed_fee")
        declared_assessed = java_result.get("declared_assessed_fee")
        return DiagnosticControls(
            computed_count=(
                computed_count
                if isinstance(computed_count, int)
                and not isinstance(computed_count, bool)
                else None
            ),
            computed_net_amount=(
                computed_assessed
                if isinstance(computed_assessed, str)
                else None
            ),
            declared_count=(
                declared_count
                if isinstance(declared_count, int)
                and not isinstance(declared_count, bool)
                else None
            ),
            declared_net_amount=(
                declared_assessed
                if isinstance(declared_assessed, str)
                else None
            ),
        )

    def java_evidence(
        self,
        java_result: Mapping[str, object],
    ) -> dict[str, object]:
        safe_fields: tuple[str, ...]
        if java_result.get("status") == "succeeded":
            safe_fields = (
                "assessed_fee",
                "batch_id",
                "calculated_fee",
                "code",
                "csv_file",
                "csv_sha256",
                "gross_amount",
                "row_count",
                "status",
            )
        else:
            safe_fields = (
                "batch_id",
                "code",
                *self._rejection_control_fields(),
                "physical_record_number",
                "record_number",
                "status",
            )
        return {
            "file_type": self.type_number,
            **{name: java_result.get(name) for name in safe_fields},
        }

    def raw_publication_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
    ) -> dict[str, object]:
        value = super().raw_publication_evidence(raw, status=status)
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value

    def raw_intake_evidence(
        self,
        raw: PublishedRaw,
        *,
        manifest_sha256: str,
        sha256: str,
        status: str,
    ) -> dict[str, object]:
        value = super().raw_intake_evidence(
            raw,
            manifest_sha256=manifest_sha256,
            sha256=sha256,
            status=status,
        )
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value

    def postgres_load_evidence(
        self,
        load: LoadResult,
        *,
        raw: PublishedRaw,
        status: str,
    ) -> dict[str, object]:
        reconciliation = load.reconciliation
        return {
            "batch_id": load.batch_id,
            "csv_sha256": load.csv_sha256,
            "file_type": raw.file_type,
            "net_amount": load.net_amount,
            "row_count": load.row_count,
            "source_controls": dict(raw.source_controls),
            "stage_controls": {
                "assessed_fee": reconciliation.get(
                    "staged_assessed_fee"
                ),
                "calculated_fee": reconciliation.get(
                    "staged_calculated_fee"
                ),
                "currency": reconciliation.get("currency"),
                "gross_amount": reconciliation.get(
                    "staged_gross_amount"
                ),
                "row_count": reconciliation.get("staged_count"),
            },
            "status": status,
        }

    def final_status_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
        code: str | None = None,
    ) -> dict[str, object]:
        value = super().final_status_evidence(
            raw,
            status=status,
            code=code,
        )
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value


class Type06WorkflowAdapter(WorkflowAdapter):
    """Type 06 orchestration with aggregate-only privacy-safe evidence."""

    type_number = "06"
    display_name = "Type 06"
    scenario_batch_ids = MappingProxyType(
        {
            "valid-minimal": "B202607230000501",
            "valid-boundary": "B200002290000502",
            "malformed": "B202607230000503",
            "legacy-miss": "B202607230000504",
        }
    )
    expected_rejection = TYPE06_EXPECTED_REJECTION
    oracle_error = Type06OracleMismatchError
    pass_type_to_java = True
    receipt_requires_type = True

    def prepare(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> PreparedType06Load:
        return prepare_type06_sanitized_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    def commit(
        self,
        prepared: object,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
        reconciliation_validator: Callable[[Mapping[str, object]], object],
    ) -> LoadResult:
        if not isinstance(prepared, PreparedType06Load):
            raise TypeError("Type 06 workflow received another prepared type")
        return commit_type06_batch(
            prepared,
            raw=raw,
            configuration=configuration,
            reconciliation_validator=reconciliation_validator,
        )

    def recover(
        self,
        batch_id: str,
        *,
        raw: PublishedRaw,
        configuration: RuntimeConfiguration,
    ) -> LoadResult:
        return read_type06_committed_batch(
            batch_id,
            raw=raw,
            configuration=configuration,
        )

    @staticmethod
    def _observation(
        *,
        batch_id: str,
        csv_sha256: str,
        row_count: object,
        original_amount: object,
        chargeback_amount: object,
        calculated_amount: object,
    ) -> Mapping[str, object]:
        return {
            "batch_id": batch_id,
            "calculated_amount": calculated_amount,
            "chargeback_amount": chargeback_amount,
            "csv_sha256": csv_sha256,
            "original_amount": original_amount,
            "row_count": row_count,
            "status": "succeeded",
        }

    def prepared_observation(
        self,
        prepared: object,
    ) -> Mapping[str, object]:
        if not isinstance(prepared, PreparedType06Load):
            raise TypeError("Type 06 workflow received another prepared type")
        controls = prepared.stage_controls
        return self._observation(
            batch_id=prepared.batch_id,
            csv_sha256=prepared.csv_sha256,
            row_count=controls["row_count"],
            original_amount=controls["original_amount"],
            chargeback_amount=controls["chargeback_amount"],
            calculated_amount=controls["calculated_amount"],
        )

    def load_observation(
        self,
        load: LoadResult,
    ) -> Mapping[str, object]:
        reconciliation = load.reconciliation
        return self._observation(
            batch_id=load.batch_id,
            csv_sha256=load.csv_sha256,
            row_count=reconciliation.get("staged_count"),
            original_amount=reconciliation.get("staged_original_amount"),
            chargeback_amount=reconciliation.get("staged_chargeback_amount"),
            calculated_amount=reconciliation.get("staged_calculated_amount"),
        )

    def compare_sanitized(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        observation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type06_sanitized(
                scenario,
                batch_id=batch_id,
                java_result=observation,
            ),
        )

    def compare_post_db(
        self,
        scenario: str | None,
        *,
        reconciliation: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type06_post_db(
                scenario,
                reconciliation=reconciliation,
            ),
        )

    def compare_rejection(
        self,
        scenario: str | None,
        *,
        batch_id: str,
        java_result: Mapping[str, object],
    ) -> OracleResultLike:
        return cast(
            OracleResultLike,
            compare_type06_rejection(
                scenario,
                batch_id=batch_id,
                java_result=java_result,
            ),
        )

    @staticmethod
    def _rejection_control_fields() -> tuple[str, ...]:
        return (
            "computed_calculated_amount",
            "computed_chargeback_amount",
            "computed_original_amount",
            "computed_row_count",
            "declared_calculated_amount",
            "declared_chargeback_amount",
            "declared_original_amount",
            "declared_row_count",
        )

    def rejection_diagnostic(
        self,
        java_result: Mapping[str, object],
        *,
        code: str,
        configuration: RuntimeConfiguration,
    ) -> dict[str, object]:
        del configuration
        if code == "INVALID_CSV_QUOTING":
            return {
                "file_type": self.type_number,
                "reason": code,
                "status": "not_run",
            }
        return {
            "business_state_committed": False,
            "file_type": self.type_number,
            "input": "privacy-safe-java-aggregate-controls",
            "mode": "source-parser-observation",
            **{
                name: java_result.get(name)
                for name in self._rejection_control_fields()
            },
            "status": "completed",
        }

    def diagnostic_controls(
        self,
        java_result: Mapping[str, object],
    ) -> DiagnosticControls:
        computed_count = java_result.get("computed_row_count")
        declared_count = java_result.get("declared_row_count")
        computed_chargeback = java_result.get("computed_chargeback_amount")
        declared_chargeback = java_result.get("declared_chargeback_amount")
        return DiagnosticControls(
            computed_count=(
                computed_count
                if isinstance(computed_count, int)
                and not isinstance(computed_count, bool)
                else None
            ),
            computed_net_amount=(
                computed_chargeback
                if isinstance(computed_chargeback, str)
                else None
            ),
            declared_count=(
                declared_count
                if isinstance(declared_count, int)
                and not isinstance(declared_count, bool)
                else None
            ),
            declared_net_amount=(
                declared_chargeback
                if isinstance(declared_chargeback, str)
                else None
            ),
        )

    def java_evidence(
        self,
        java_result: Mapping[str, object],
    ) -> dict[str, object]:
        safe_fields: tuple[str, ...]
        if java_result.get("status") == "succeeded":
            safe_fields = (
                "batch_id",
                "calculated_amount",
                "chargeback_amount",
                "code",
                "csv_file",
                "csv_sha256",
                "original_amount",
                "row_count",
                "status",
            )
        else:
            safe_fields = (
                "batch_id",
                "code",
                *self._rejection_control_fields(),
                "physical_record_number",
                "record_number",
                "status",
            )
        return {
            "file_type": self.type_number,
            **{name: java_result.get(name) for name in safe_fields},
        }

    def raw_publication_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
    ) -> dict[str, object]:
        value = super().raw_publication_evidence(raw, status=status)
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value

    def raw_intake_evidence(
        self,
        raw: PublishedRaw,
        *,
        manifest_sha256: str,
        sha256: str,
        status: str,
    ) -> dict[str, object]:
        value = super().raw_intake_evidence(
            raw,
            manifest_sha256=manifest_sha256,
            sha256=sha256,
            status=status,
        )
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value

    def postgres_load_evidence(
        self,
        load: LoadResult,
        *,
        raw: PublishedRaw,
        status: str,
    ) -> dict[str, object]:
        reconciliation = load.reconciliation
        return {
            "batch_id": load.batch_id,
            "csv_sha256": load.csv_sha256,
            "file_type": raw.file_type,
            "net_amount": load.net_amount,
            "row_count": load.row_count,
            "source_controls": dict(raw.source_controls),
            "stage_controls": {
                "calculated_amount": reconciliation.get(
                    "staged_calculated_amount"
                ),
                "chargeback_amount": reconciliation.get(
                    "staged_chargeback_amount"
                ),
                "currency": reconciliation.get("currency"),
                "original_amount": reconciliation.get(
                    "staged_original_amount"
                ),
                "row_count": reconciliation.get("staged_count"),
            },
            "status": status,
        }

    def final_status_evidence(
        self,
        raw: PublishedRaw,
        *,
        status: str,
        code: str | None = None,
    ) -> dict[str, object]:
        value = super().final_status_evidence(
            raw,
            status=status,
            code=code,
        )
        value.update(
            {
                "file_type": raw.file_type,
                "source_controls": dict(raw.source_controls),
            }
        )
        return value


TYPE01_WORKFLOW = Type01WorkflowAdapter()
TYPE02_WORKFLOW = Type02WorkflowAdapter()
TYPE03_WORKFLOW = Type03WorkflowAdapter()
TYPE04_WORKFLOW = Type04WorkflowAdapter()
TYPE05_WORKFLOW = Type05WorkflowAdapter()
TYPE06_WORKFLOW = Type06WorkflowAdapter()
WORKFLOWS: Mapping[str, WorkflowAdapter] = MappingProxyType(
    {
        TYPE01_WORKFLOW.type_number: TYPE01_WORKFLOW,
        TYPE02_WORKFLOW.type_number: TYPE02_WORKFLOW,
        TYPE03_WORKFLOW.type_number: TYPE03_WORKFLOW,
        TYPE04_WORKFLOW.type_number: TYPE04_WORKFLOW,
        TYPE05_WORKFLOW.type_number: TYPE05_WORKFLOW,
        TYPE06_WORKFLOW.type_number: TYPE06_WORKFLOW,
    }
)


def workflow_for_type(type_number: str) -> WorkflowAdapter:
    """Resolve one implemented workflow or fail before external mutation."""

    try:
        return WORKFLOWS[type_number]
    except KeyError as exc:
        raise ValueError(f"Unsupported workflow type: {type_number}") from exc
