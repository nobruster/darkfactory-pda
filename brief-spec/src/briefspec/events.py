from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from briefspec.artifacts import canonical_json_bytes, sha256_bytes
from briefspec.models import EventType, RuntimeEvent

EVENT_SCHEMA_VERSION = "brief-spec-event/1.0"
MAX_EVENT_BYTES = 64 * 1024

EVENT_KINDS = frozenset(
    {
        "INTENT_DECLARED",
        "INTENT_REVISED",
        "PLAN_CREATED",
        "TASK_CREATED",
        "TASK_STARTED",
        "TASK_COMPLETED",
        "TASK_FAILED",
        "TASK_ACCEPTED",
        "TASK_REJECTED",
        "DECISION_REQUESTED",
        "DECISION_RECORDED",
        "BLOCKER_RAISED",
        "BLOCKER_CLEARED",
        "EVIDENCE_ADDED",
        "ARTIFACT_CREATED",
        "DRIFT_DETECTED",
        "DRIFT_RESOLVED",
        "LESSON_PROPOSED",
        "HUMAN_NOTE",
    }
)
IMPORTANCE_LEVELS = frozenset({"informational", "notable", "needs-attention", "blocking"})
ACCESS_LEVELS = frozenset({"local", "private", "public"})
METHOD_CONTEXTS = frozenset({"general", "seamwise", "task-spec", "converge"})
EVENT_FIELDS = frozenset(
    {
        "schema_version",
        "event_id",
        "project_id",
        "kind",
        "importance",
        "access",
        "occurred_at",
        "observed_at",
        "source",
        "method_context",
        "headline",
        "entity_refs",
        "evidence_ids",
        "details",
        "previous_event_hash",
        "event_hash",
    }
)
SOURCE_FIELDS = frozenset(
    {
        "system",
        "harness",
        "adapter_version",
        "opaque_ref",
        "source_revision",
        "provider_event_kind",
    }
)
METHOD_FIELDS = frozenset({"method", "phase", "intent_ref", "task_ref", "parent_ref"})
FORBIDDEN_KEY = re.compile(
    r"(?i)(?:^|_)(?:authorization|api_?key|access_?token|refresh_?token|password|secret|"
    r"credential|resume_?token|raw_?prompt|transcript|tool_?output)(?:$|_)"
)
CREDENTIAL_VALUE = re.compile(
    r"(?i)(?:\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"
    r"|\b(?:sk|ghp|gho|github_pat|xox[abprs])[-_][A-Za-z0-9_-]{16,}"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
    r"|https?://[^\s/:@]+:[^\s/@]+@"
    r"|[?&](?:access_token|api_?key|signature|token)=[^&#\s]{8,}"
)


def _is_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _forbidden_paths(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            normalized = str(key).lower()
            if FORBIDDEN_KEY.search(str(key)) and not normalized.endswith(
                ("_ref", "_id", "_sha256")
            ):
                found.append(path)
            found.extend(_forbidden_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_paths(child, f"{prefix}[{index}]"))
    return found


def _credential_paths(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.extend(_credential_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_credential_paths(child, f"{prefix}[{index}]"))
    elif isinstance(value, str) and CREDENTIAL_VALUE.search(value):
        found.append(prefix or "<root>")
    return found


def validate_event(value: Any, *, chained: bool = True) -> list[str]:
    if not isinstance(value, dict):
        return ["Event must be an object"]
    errors: list[str] = []
    unexpected = sorted(set(value) - EVENT_FIELDS)
    if unexpected:
        errors.append("Event contains unknown field(s): " + ", ".join(unexpected))
    if value.get("schema_version") != EVENT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {EVENT_SCHEMA_VERSION}")
    if value.get("kind") not in EVENT_KINDS:
        errors.append("kind is invalid")
    if value.get("importance") not in IMPORTANCE_LEVELS:
        errors.append("importance is invalid")
    if value.get("access") not in ACCESS_LEVELS:
        errors.append("access is invalid")
    for field in ("project_id", "headline"):
        if not isinstance(value.get(field), str) or not str(value[field]).strip():
            errors.append(f"{field} is required")
    if len(str(value.get("headline", ""))) > 500:
        errors.append("headline exceeds 500 characters")
    for field in ("occurred_at", "observed_at"):
        if not _is_timestamp(value.get(field)):
            errors.append(f"{field} must be an ISO 8601 timestamp with timezone")
    source = value.get("source")
    if not isinstance(source, dict) or not str(source.get("system", "")).strip():
        errors.append("source.system is required")
    elif set(source) - SOURCE_FIELDS:
        errors.append(
            "source contains unknown field(s): " + ", ".join(sorted(set(source) - SOURCE_FIELDS))
        )
    method = value.get("method_context")
    if not isinstance(method, dict) or method.get("method") not in METHOD_CONTEXTS:
        errors.append("method_context.method is invalid")
    elif set(method) - METHOD_FIELDS:
        errors.append(
            "method_context contains unknown field(s): "
            + ", ".join(sorted(set(method) - METHOD_FIELDS))
        )
    elif method.get("phase") is not None and not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", str(method.get("phase"))
    ):
        errors.append("method_context.phase must be a normalized slug")
    for field in ("entity_refs", "evidence_ids"):
        items = value.get(field, [])
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            errors.append(f"{field} must be an array of strings")
        elif len(items) > 64:
            errors.append(f"{field} exceeds 64 entries")
    details = value.get("details", {})
    if not isinstance(details, dict):
        errors.append("details must be an object")
    forbidden = _forbidden_paths(value)
    if forbidden:
        errors.append("Event contains forbidden field(s): " + ", ".join(sorted(forbidden)))
    credentials = _credential_paths(value)
    if credentials:
        errors.append(
            "Event contains credential-shaped value(s): " + ", ".join(sorted(credentials))
        )
    if len(canonical_json_bytes(value)) > MAX_EVENT_BYTES:
        errors.append(f"Event exceeds {MAX_EVENT_BYTES} bytes")
    if chained:
        if not re.fullmatch(r"bse-[0-9a-f]{24}", str(value.get("event_id", ""))):
            errors.append("event_id is invalid")
        for field in ("previous_event_hash", "event_hash"):
            if not re.fullmatch(r"[0-9a-f]{64}", str(value.get(field, ""))):
                errors.append(f"{field} is invalid")
    return errors


def _identity_fields(event: dict[str, Any]) -> dict[str, Any]:
    source = event.get("source", {})
    details = event.get("details", {})
    correlation_id = details.get("correlation_id") if isinstance(details, dict) else None
    if isinstance(correlation_id, str) and correlation_id.strip():
        return {
            "schema_version": event.get("schema_version"),
            "project_id": event.get("project_id"),
            "kind": event.get("kind"),
            "correlation_id": correlation_id,
            "entity_refs": event.get("entity_refs", []),
        }
    return {
        "schema_version": event.get("schema_version"),
        "project_id": event.get("project_id"),
        "kind": event.get("kind"),
        "occurred_at": event.get("occurred_at"),
        "source": {
            "system": source.get("system"),
            "opaque_ref": source.get("opaque_ref"),
            "provider_event_kind": source.get("provider_event_kind"),
            "source_revision": source.get("source_revision"),
        },
        "method_context": event.get("method_context"),
        "headline": event.get("headline"),
        "entity_refs": event.get("entity_refs", []),
        "evidence_ids": event.get("evidence_ids", []),
        "details": event.get("details", {}),
    }


def prepare_event(
    value: dict[str, Any],
    *,
    project_id: str,
    source_system: str,
    previous_event_hash: str,
    observed_at: str | None = None,
) -> dict[str, Any]:
    event = dict(value)
    event["schema_version"] = EVENT_SCHEMA_VERSION
    event["project_id"] = project_id
    event.setdefault("importance", "informational")
    event.setdefault("access", "local")
    if not event.get("occurred_at"):
        event["occurred_at"] = observed_at or datetime.now(UTC).isoformat()
    if not event.get("observed_at"):
        event["observed_at"] = observed_at or event["occurred_at"]
    source = dict(event.get("source") or {})
    source["system"] = source_system
    event["source"] = source
    method = dict(event.get("method_context") or {})
    method.setdefault("method", "general")
    event["method_context"] = method
    event.setdefault("entity_refs", [])
    event.setdefault("evidence_ids", [])
    event.setdefault("details", {})
    errors = validate_event(event, chained=False)
    if errors:
        raise ValueError("; ".join(errors))
    identity_sha = sha256_bytes(canonical_json_bytes(_identity_fields(event)))
    event["event_id"] = f"bse-{identity_sha[:24]}"
    event["previous_event_hash"] = previous_event_hash
    event["event_hash"] = sha256_bytes(canonical_json_bytes(event))
    errors = validate_event(event)
    if errors:
        raise ValueError("; ".join(errors))
    return event


def load_event_bytes(content: bytes) -> dict[str, Any]:
    if len(content) > MAX_EVENT_BYTES:
        raise ValueError(f"Event exceeds {MAX_EVENT_BYTES} bytes")
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Event is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Event must be a JSON object")
    return value


def _proof_locator(item: dict[str, Any]) -> str | None:
    locator = str(item.get("locator") or "").strip()
    if not locator:
        return None
    kind = str(item.get("kind") or "observation")
    if locator.startswith(("https://", "http://", "file:", "commit:")):
        return locator[:2048]
    if kind in {"file", "artifact"}:
        return f"file:{locator}"[:2048]
    if kind == "commit":
        return f"commit:{locator}"[:2048]
    return f"evidence:{locator}"[:2048]


def material_event_candidate(
    event: RuntimeEvent,
    *,
    method: str = "general",
    phase: str | None = None,
) -> dict[str, Any] | None:
    """Project one material host boundary without retaining raw host conversation content."""
    source = {
        "harness": event.runtime.value,
        "opaque_ref": event.turn_id or event.session_id,
        "provider_event_kind": event.type.value,
    }
    normalized_phase = (
        phase
        if isinstance(phase, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", phase)
        else None
    )
    context = {
        "method": method if method in METHOD_CONTEXTS else "general",
        **({"phase": normalized_phase} if normalized_phase else {}),
        **({"task_ref": event.turn_id} if event.turn_id else {}),
    }
    occurred_at = event.occurred_at.isoformat()
    if event.type is EventType.AGENT_STOP and event.assistant_text:
        from briefspec.delivery import load_delivery
        from briefspec.markdown import validate_checkpoint, validate_outcome

        outcome = validate_outcome(event.assistant_text)
        checkpoint = validate_checkpoint(event.assistant_text)
        if outcome.valid:
            delivery, _ = load_delivery(
                event.assistant_text,
                runtime=event.runtime.value,
                session_ref=event.session_id,
                created_at=occurred_at,
            )
            data = delivery["brief"]
            status = str(data.get("status") or "")
            kind = {
                "DONE": "TASK_COMPLETED",
                "REVIEW": "TASK_COMPLETED",
                "DECIDE": "DECISION_REQUESTED",
                "BLOCKED": "BLOCKER_RAISED",
                "FAILED": "TASK_FAILED",
            }.get(status, "HUMAN_NOTE")
            evidence = [
                locator
                for item in data.get("proof", [])
                if isinstance(item, dict) and (locator := _proof_locator(item))
            ]
            return {
                "kind": kind,
                "importance": "blocking" if status == "BLOCKED" else "notable",
                "access": "local",
                "occurred_at": occurred_at,
                "headline": str(data.get("outcome") or "Outcome boundary observed")[:500],
                "source": source,
                "method_context": context,
                "entity_refs": [event.turn_id] if event.turn_id else [],
                "evidence_ids": evidence[:64],
                "details": {
                    "status": status,
                    "human_action": data.get("human_action"),
                    "next": [str(item)[:500] for item in data.get("next", [])][:3],
                    "gaps": [str(item)[:500] for item in data.get("gaps", [])][:16],
                },
            }
        if checkpoint.valid:
            delivery, _ = load_delivery(
                event.assistant_text,
                runtime=event.runtime.value,
                session_ref=event.session_id,
                created_at=occurred_at,
            )
            data = delivery["brief"]
            return {
                "kind": "HUMAN_NOTE",
                "importance": "notable",
                "access": "local",
                "occurred_at": occurred_at,
                "headline": str(data.get("headline") or "Checkpoint boundary observed")[:500],
                "source": source,
                "method_context": context,
                "entity_refs": [event.turn_id] if event.turn_id else [],
                "evidence_ids": [],
                "details": {"checkpoint_mode": data.get("mode")},
            }
        return None
    if event.type is EventType.PRE_COMPACT:
        return {
            "kind": "HUMAN_NOTE",
            "importance": "notable",
            "access": "local",
            "occurred_at": occurred_at,
            "headline": "Pre-compaction continuity boundary observed",
            "source": source,
            "method_context": context,
            "entity_refs": [event.turn_id] if event.turn_id else [],
            "evidence_ids": [],
            "details": {"boundary": "pre-compaction"},
        }
    if event.type in {EventType.SUBAGENT_START, EventType.SUBAGENT_STOP}:
        return {
            "kind": (
                "TASK_STARTED" if event.type is EventType.SUBAGENT_START else "TASK_COMPLETED"
            ),
            "importance": "informational",
            "access": "local",
            "occurred_at": occurred_at,
            "headline": (
                "Bounded subagent work started"
                if event.type is EventType.SUBAGENT_START
                else "Bounded subagent work ended"
            ),
            "source": source,
            "method_context": context,
            "entity_refs": [event.turn_id] if event.turn_id else [],
            "evidence_ids": [],
            "details": {"work_item_only": True},
        }
    if event.type is EventType.ERROR:
        return {
            "kind": "TASK_FAILED",
            "importance": "needs-attention",
            "access": "local",
            "occurred_at": occurred_at,
            "headline": "Harness reported a material error boundary",
            "source": source,
            "method_context": context,
            "entity_refs": [event.turn_id] if event.turn_id else [],
            "evidence_ids": [],
            "details": {"raw_error_stored": False},
        }
    return None
