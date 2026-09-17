from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from briefspec.config import DEFAULT_CONFIG
from briefspec.models import EventType, Runtime, RuntimeEvent, SessionState
from briefspec.triggers import (
    elapsed_minutes,
    eligibility_reasons,
    looks_like_action_request,
    update_counters,
)

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)


def state_at(started: datetime = NOW) -> SessionState:
    return SessionState.new(Runtime.CODEX, "session", started)


def runtime_event(event_type: EventType, **changes: object) -> RuntimeEvent:
    values = {
        "runtime": Runtime.CODEX,
        "type": event_type,
        "session_id": "session",
        "occurred_at": NOW,
        "payload_hash": f"hash-{event_type.value}",
    }
    values.update(changes)
    return RuntimeEvent(**values)


@pytest.mark.parametrize(
    "prompt",
    [
        "Implement the whole feature",
        "Please fix the adapter",
        "Go ahead with the installation",
        "Take care of the tests",
        "Ship this",
    ],
)
def test_action_request_detection(prompt: str) -> None:
    assert looks_like_action_request(prompt)


@pytest.mark.parametrize("prompt", ["", "What is this?", "Explain the design"])
def test_non_action_prompt_detection(prompt: str) -> None:
    assert not looks_like_action_request(prompt)


def test_elapsed_minutes_clamps_clock_rollback() -> None:
    state = state_at(NOW + timedelta(hours=1))
    assert elapsed_minutes(state, NOW) == 0
    assert "elapsed" not in eligibility_reasons(state, deepcopy(DEFAULT_CONFIG), NOW)


def test_invalid_start_time_is_not_eligible() -> None:
    state = state_at()
    state.started_at = "invalid"
    assert elapsed_minutes(state, NOW) == 0


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (
            lambda state: setattr(
                state,
                "started_at",
                (NOW - timedelta(minutes=12)).isoformat(),
            ),
            "elapsed",
        ),
        (lambda state: setattr(state, "turn_count", 8), "turns"),
        (lambda state: setattr(state, "assistant_chars", 16_000), "assistant-volume"),
        (lambda state: setattr(state, "tool_count", 12), "tool-volume"),
    ],
)
def test_each_threshold_can_make_checkpoint_eligible(mutation: object, expected: str) -> None:
    state = state_at()
    mutation(state)  # type: ignore[operator]
    assert expected in eligibility_reasons(state, deepcopy(DEFAULT_CONFIG), NOW)


def test_minimum_turns_after_checkpoint_suppresses_all_reasons() -> None:
    state = state_at(NOW - timedelta(minutes=30))
    state.turn_count = 9
    state.last_checkpoint_turn = 8
    assert eligibility_reasons(state, deepcopy(DEFAULT_CONFIG), NOW) == []


def test_checkpoint_cooldown_suppresses_all_reasons() -> None:
    state = state_at(NOW - timedelta(minutes=30))
    state.turn_count = 20
    state.last_checkpoint_at = (NOW - timedelta(minutes=5)).isoformat()
    assert eligibility_reasons(state, deepcopy(DEFAULT_CONFIG), NOW) == []


def test_user_prompt_updates_counts_and_resets_repair_guard() -> None:
    state = state_at()
    state.repair_attempted = True
    event = runtime_event(EventType.USER_PROMPT, prompt_chars=17)
    update_counters(state, event, "Please build the feature")
    assert state.turn_count == 1
    assert state.prompt_chars == 17
    assert state.outcome_expected
    assert not state.repair_attempted


def test_tool_and_stop_events_update_volume() -> None:
    state = state_at()
    update_counters(state, runtime_event(EventType.POST_TOOL, tool_calls=3))
    update_counters(state, runtime_event(EventType.AGENT_STOP, assistant_chars=200))
    assert state.tool_count == 3
    assert state.assistant_chars == 200


def test_precompact_creates_one_pending_reason() -> None:
    state = state_at()
    event = runtime_event(EventType.PRE_COMPACT)
    update_counters(state, event)
    update_counters(state, event)
    assert state.pending_checkpoint
    assert state.pending_reasons == ["pre-compact"]
