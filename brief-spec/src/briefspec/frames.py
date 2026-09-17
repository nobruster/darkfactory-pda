"""Render bounded Human Frames for lifecycle coordinators such as Workhelm."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from briefspec.models import WorkType
from briefspec.state import atomic_write_public
from briefspec.work_types import classify_task

REQUEST_CONTRACT = "BriefSpecFrameRequest/v1"
RECEIPT_CONTRACT = "BriefSpecFrameReceipt/v1"
RENDERER_VERSION = "1.0"
MAX_BODY_BYTES = 2_000_000
PRODUCER = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_frame_request(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Human Frame request must be a JSON object")
    allowed = {"contract", "work_type", "subject", "producer", "body"}
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise ValueError(f"Human Frame request has unsupported fields: {', '.join(unexpected)}")
    if value.get("contract") != REQUEST_CONTRACT:
        raise ValueError(f"Human Frame request contract must be {REQUEST_CONTRACT}")
    work_type = value.get("work_type")
    if work_type not in {item.value for item in WorkType}:
        raise ValueError("Human Frame work_type is unsupported")
    subject = value.get("subject")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Human Frame subject is required")
    producer = value.get("producer")
    if not isinstance(producer, str) or PRODUCER.fullmatch(producer) is None:
        raise ValueError("Human Frame producer must be a stable lowercase token")
    body = value.get("body")
    if not isinstance(body, str) or not body.strip():
        raise ValueError("Human Frame body is required")
    if len(body.encode("utf-8")) > MAX_BODY_BYTES:
        raise ValueError("Human Frame body exceeds the 2 MB boundary")
    return value


def render_frame(
    request: object,
    *,
    output: Path,
    force: bool = False,
) -> dict[str, Any]:
    """Classify and atomically render one presentation-only Markdown frame."""

    value = validate_frame_request(request)
    destination = output.expanduser().resolve()
    if destination.exists() and not force:
        raise ValueError(f"Refusing to overwrite existing Human Frame: {destination}")
    body = str(value["body"]).rstrip()
    classification = classify_task(
        body,
        explicit_type=str(value["work_type"]),
        subject=str(value["subject"]),
    ).to_dict()
    marker = (
        "<!-- brief-spec:frame:v1 "
        f"type={classification['work_type']} "
        f"subject={classification['subject']} "
        f"confidence={classification['confidence']} "
        f"origin={classification['origin']} "
        f"classified_at={classification['classified_at']} "
        f"profile={classification['profile_version']} "
        f"decision_id={classification['decision_id']} "
        f"producer={value['producer']} -->"
    )
    rendered = f"{marker}\n{body}\n<!-- /brief-spec -->\n"
    rendered_bytes = rendered.encode("utf-8")
    atomic_write_public(destination, rendered_bytes)
    return {
        "contract": RECEIPT_CONTRACT,
        "renderer_version": RENDERER_VERSION,
        "request_sha256": _sha256(_canonical(value)),
        "body_sha256": _sha256(str(value["body"]).encode("utf-8")),
        "output": str(destination),
        "output_sha256": _sha256(rendered_bytes),
        "classification": classification,
        "approval_authority": False,
        "dispatch_authority": False,
    }
