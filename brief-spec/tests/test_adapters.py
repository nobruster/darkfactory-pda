from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import pytest

from briefspec.adapters import normalize_event
from briefspec.adapters.base import (
    MAX_TRANSCRIPT_BYTES,
    canonical_hash,
    event_type,
    read_last_assistant_message,
)
from briefspec.models import EventType, Runtime


@pytest.mark.parametrize("runtime", list(Runtime))
@pytest.mark.parametrize(
    ("event_name", "expected"),
    [
        ("SessionStart", EventType.SESSION_START),
        ("sessionStart", EventType.SESSION_START),
        ("UserPromptSubmit", EventType.USER_PROMPT),
        ("userPromptSubmitted", EventType.USER_PROMPT),
        ("PostToolUse", EventType.POST_TOOL),
        ("postToolUse", EventType.POST_TOOL),
        ("PreCompact", EventType.PRE_COMPACT),
        ("preCompact", EventType.PRE_COMPACT),
        ("Stop", EventType.AGENT_STOP),
        ("agentStop", EventType.AGENT_STOP),
        ("SubagentStart", EventType.SUBAGENT_START),
        ("SubagentStop", EventType.SUBAGENT_STOP),
        ("ErrorOccurred", EventType.ERROR),
    ],
)
def test_provider_event_aliases_normalize(
    runtime: Runtime, event_name: str, expected: EventType
) -> None:
    event = normalize_event(
        runtime,
        {
            "sessionId": "session-1",
            "timestamp": "2026-07-31T12:00:00Z",
            "cwd": "/tmp/project",
        },
        event_name,
    )
    assert event.runtime is runtime
    assert event.type is expected
    assert event.session_id == "session-1"
    assert event.occurred_at.tzinfo is not None


def test_unknown_event_is_preserved_as_unknown() -> None:
    assert event_type({"eventName": "FutureEvent"}) is EventType.UNKNOWN


def test_explicit_event_takes_precedence_over_payload() -> None:
    event = normalize_event(
        Runtime.COPILOT,
        {"eventName": "sessionStart", "sessionId": "s"},
        "agentStop",
    )
    assert event.type is EventType.AGENT_STOP


def test_common_payload_fields_and_content_blocks_are_normalized() -> None:
    payload = {
        "conversationId": "conversation-7",
        "turnId": "turn-3",
        "timestamp": 1_753_968_000_000,
        "prompt": [{"text": "Build it"}, {"text": "and test it"}],
        "response": {"content": [{"type": "text", "text": "Completed"}]},
        "cwd": "~/work",
        "stopHookActive": True,
    }
    event = normalize_event(Runtime.CLAUDE, payload, "Stop")
    assert event.session_id == "conversation-7"
    assert event.turn_id == "turn-3"
    assert event.occurred_at.tzinfo is UTC
    assert event.prompt_chars == len("Build it\nand test it")
    assert event.assistant_text == "Completed"
    assert event.assistant_chars == len("Completed")
    assert event.stop_hook_active
    assert event.cwd == Path("~/work").expanduser()


def test_payload_hash_is_canonical_across_key_order() -> None:
    assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})


def test_copilot_reads_last_assistant_message_from_jsonl_transcript(
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps({"role": "user", "content": "request"}),
                "{malformed",
                json.dumps(
                    {
                        "type": "assistant_message",
                        "message": {
                            "role": "assistant",
                            "content": [
                                {"type": "text", "text": "First"},
                                {"type": "text", "text": "Second"},
                            ],
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    event = normalize_event(
        Runtime.COPILOT,
        {"session_id": "copilot-1", "transcript_path": str(transcript)},
        "agentStop",
    )
    assert event.assistant_text == "First\nSecond"


def test_transcript_tail_is_bounded_and_finds_last_complete_record(
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "large.jsonl"
    record = json.dumps({"role": "assistant", "content": "tail result"})
    transcript.write_bytes(b"x" * (MAX_TRANSCRIPT_BYTES + 100) + b"\n" + record.encode() + b"\n")
    assert read_last_assistant_message(transcript) == "tail result"


def test_malformed_transcript_returns_none(tmp_path: Path) -> None:
    transcript = tmp_path / "bad.jsonl"
    transcript.write_text("not json\n[]\n{}\n", encoding="utf-8")
    assert read_last_assistant_message(transcript) is None


def test_transcript_reader_refuses_symlinks(tmp_path: Path) -> None:
    target = tmp_path / "target.jsonl"
    target.write_text(
        json.dumps({"role": "assistant", "content": "must not be read"}),
        encoding="utf-8",
    )
    link = tmp_path / "link.jsonl"
    link.symlink_to(target)
    assert read_last_assistant_message(link) is None


def test_explicit_assistant_text_wins_over_transcript(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"role": "assistant", "content": "from transcript"}),
        encoding="utf-8",
    )
    event = normalize_event(
        Runtime.COPILOT,
        {
            "session_id": "copilot-2",
            "response": "from payload",
            "transcriptPath": str(transcript),
        },
        "agentStop",
    )
    assert event.assistant_text == "from payload"
