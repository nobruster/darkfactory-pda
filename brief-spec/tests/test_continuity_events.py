from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from briefspec.artifacts import (
    artifact_record,
    build_manifest,
    canonical_json_bytes,
    sha256_bytes,
    verify_manifest,
)
from briefspec.continuity import detect_method_context, human_frame_delivery_tier, method_context
from briefspec.events import prepare_event, validate_event
from briefspec.harnesses import harness_adapter
from briefspec.models import EventType, Runtime, RuntimeEvent


def test_canonical_artifact_primitives_are_deterministic(tmp_path: Path) -> None:
    assert canonical_json_bytes({"b": 1, "a": "é"}) == b'{"a":"\xc3\xa9","b":1}'
    content = b"bounded"
    target = tmp_path / "brief.txt"
    target.write_bytes(content)
    record = artifact_record(
        format_name="text",
        filename=target.name,
        media_type="text/plain",
        content=content,
        renderer_version="1.0",
    )
    manifest = build_manifest(
        kind="test-manifest",
        schema_version="test/1.0",
        canonical_sha256=sha256_bytes(b"canonical"),
        created_at="2026-08-14T12:00:00+00:00",
        files=[record],
    )
    assert verify_manifest(manifest, tmp_path) == []
    target.write_bytes(b"changed")
    assert "hash mismatch" in " ".join(verify_manifest(manifest, tmp_path)).lower()


def test_event_identity_is_stable_but_chain_hash_changes() -> None:
    raw = {
        "kind": "TASK_STARTED",
        "headline": "Implement bounded Chronicle events",
        "occurred_at": "2026-08-14T12:00:00+00:00",
        "method_context": {
            "method": "converge",
            "phase": "execution",
            "task_ref": "task-1",
            "intent_ref": "intent-1",
        },
        "details": {"authorization_ref": "auth-1"},
    }
    first = prepare_event(
        raw,
        project_id="bscp-0123456789abcdef01234567",
        source_system="converge",
        previous_event_hash="0" * 64,
        observed_at="2026-08-14T12:00:01+00:00",
    )
    second = prepare_event(
        raw,
        project_id="bscp-0123456789abcdef01234567",
        source_system="converge",
        previous_event_hash="1" * 64,
        observed_at="2026-08-14T12:00:02+00:00",
    )
    assert first["event_id"] == second["event_id"]
    assert first["event_hash"] != second["event_hash"]
    assert validate_event(first) == []


@pytest.mark.parametrize("key", ["api_key", "raw_prompt", "transcript", "tool_output"])
def test_event_rejects_forbidden_content(key: str) -> None:
    with pytest.raises(ValueError, match="forbidden"):
        prepare_event(
            {
                "kind": "HUMAN_NOTE",
                "headline": "A bounded observation",
                "occurred_at": "2026-08-14T12:00:00+00:00",
                "details": {key: "must-not-persist"},
            },
            project_id="bscp-0123456789abcdef01234567",
            source_system="human",
            previous_event_hash="0" * 64,
        )


def test_event_rejects_credential_shaped_values_even_under_safe_keys() -> None:
    with pytest.raises(ValueError, match="credential-shaped"):
        prepare_event(
            {
                "kind": "HUMAN_NOTE",
                "headline": "Accidental value sk-exampleCredentialValue123456789",
                "occurred_at": "2026-08-14T12:00:00+00:00",
            },
            project_id="bscp-0123456789abcdef01234567",
            source_system="human",
            previous_event_hash="0" * 64,
        )


def test_method_context_and_harness_capabilities_are_explicit() -> None:
    assert method_context("task_spec", phase="acceptance")["method"] == "task-spec"
    with pytest.raises(ValueError, match="normalized slug"):
        method_context("converge", phase="Not A Slug")
    assert human_frame_delivery_tier(final_output=True, lifecycle_hooks=True) == "pre-final-context"
    assert human_frame_delivery_tier(final_output=False, lifecycle_hooks=True) == "terminal-only"
    capabilities = harness_adapter(Runtime.CODEX).capabilities()
    assert capabilities["human_frame_delivery"] == "pre-final-context"
    assert capabilities["method_contexts"] == ["general", "seamwise", "task-spec", "converge"]
    assert detect_method_context("Use Task-Spec for this handoff") == (
        "task-spec",
        None,
        "inferred",
    )
    assert detect_method_context("Connect Seamwise, Task-Spec, and Converge") == (
        "general",
        None,
        "fallback",
    )
    assert detect_method_context(
        "bounded task",
        host_context={"method_context": "converge", "method_phase": "settlement"},
    ) == ("converge", "settlement", "host")
    assert detect_method_context(
        "bounded task",
        host_context={"method_context": "task-spec", "method_phase": "Not / A Phase"},
    ) == ("task-spec", None, "host")


def test_harness_material_projection_keeps_only_bounded_terminal_fields() -> None:
    outcome = """<!-- briefspec:outcome:v1 -->
Status: DONE
Outcome: The bounded implementation is complete.
Human action: None
Proof:
- [direct/pass kind=file] Tests at `tests/test_continuity_events.py`
Gaps: None
Next: Run the release gate.
Open: None
<!-- /briefspec -->"""
    event = RuntimeEvent(
        runtime=Runtime.CODEX,
        type=EventType.AGENT_STOP,
        session_id="opaque-session",
        turn_id="task-42",
        occurred_at=datetime(2026, 8, 14, 12, tzinfo=UTC),
        payload_hash="a" * 64,
        assistant_text=outcome,
    )
    candidate = harness_adapter(Runtime.CODEX).material_event(
        event, method="task-spec", phase="acceptance"
    )
    assert candidate is not None
    assert candidate["kind"] == "TASK_COMPLETED"
    assert candidate["method_context"]["method"] == "task-spec"
    assert candidate["evidence_ids"] == ["file:tests/test_continuity_events.py"]
    serialized = canonical_json_bytes(candidate)
    assert b"briefspec:outcome" not in serialized
    assert b"raw" not in serialized
    prompt = RuntimeEvent(
        runtime=Runtime.CODEX,
        type=EventType.USER_PROMPT,
        session_id="opaque-session",
        occurred_at=datetime(2026, 8, 14, 12, tzinfo=UTC),
        payload_hash="b" * 64,
    )
    assert harness_adapter(Runtime.CODEX).material_event(prompt) is None
