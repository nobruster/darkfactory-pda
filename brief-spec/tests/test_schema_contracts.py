from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema.protocols import Validator
from jsonschema.validators import validator_for
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
CANONICAL_SCHEMA_BASE = "https://github.com/luanmorenommaciel/brief-spec/releases/download/v0.5.0/"


def _schema_documents() -> dict[str, dict[str, Any]]:
    documents = [
        json.loads(path.read_text(encoding="utf-8")) for path in sorted(SCHEMAS.glob("*.json"))
    ]
    return {document["$id"]: document for document in documents}


def _validator(name: str) -> Validator:
    return _validator_id(f"https://briefspec.dev/schemas/{name}.schema.json")


def _validator_id(identifier: str) -> Validator:
    documents = _schema_documents()
    schema = documents[identifier]
    registry = Registry().with_resources(
        [
            (identifier, Resource.from_contents(document))
            for identifier, document in documents.items()
        ]
    )
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    return validator_class(schema, registry=registry)


def _proof() -> list[dict[str, str]]:
    return [
        {
            "kind": "test",
            "label": "Contract suite",
            "locator": "tests/test_schema_contracts.py",
            "basis": "direct",
            "result": "pass",
        }
    ]


CHECKPOINTS = {
    "orient": {
        "current_state": "The implementation is ready for release verification.",
        "completed": ["Aligned the portable and human contracts."],
        "decisions": ["Keep one bounded presentation model."],
        "open": [],
    },
    "teach": {
        "mental_model": "One contract is rendered differently for each reading need.",
        "why_it_matters": "The schema cannot drift from the visible handoff.",
        "what_changed": ["Mode-specific fields are represented explicitly."],
        "example": "Teach carries a mental model while Orient carries current state.",
        "watch_outs": ["Structural validity is not truth verification."],
    },
    "spoken": {
        "script": "Here is the short spoken rendering of the current session state.",
    },
}


@pytest.mark.parametrize(("mode", "mode_fields"), CHECKPOINTS.items())
def test_checkpoint_schema_represents_every_human_mode(
    mode: str,
    mode_fields: dict[str, Any],
) -> None:
    payload = {
        "schema_version": "1.0",
        "kind": "session-checkpoint",
        "mode": mode,
        "headline": f"{mode.title()} checkpoint",
        "proof": _proof(),
        "next": ["Continue with the release gate."],
        **mode_fields,
    }
    _validator("session-checkpoint").validate(payload)


@pytest.mark.parametrize(
    ("mode", "missing_field"),
    [
        ("orient", "current_state"),
        ("teach", "mental_model"),
        ("spoken", "script"),
    ],
)
def test_checkpoint_schema_requires_mode_specific_fields(
    mode: str,
    missing_field: str,
) -> None:
    payload = {
        "schema_version": "1.0",
        "kind": "session-checkpoint",
        "mode": mode,
        "headline": f"{mode.title()} checkpoint",
        "proof": _proof(),
        "next": ["Continue with the release gate."],
        **CHECKPOINTS[mode],
    }
    del payload[missing_field]
    errors = list(_validator("session-checkpoint").iter_errors(payload))
    assert any(missing_field in error.message for error in errors)


def test_delivery_manifest_and_receipt_schemas_compose_existing_contracts() -> None:
    delivery = {
        "schema_version": "1.0",
        "kind": "briefspec-delivery",
        "source": {
            "runtime": "codex",
            "briefspec_version": "0.4.0",
            "created_at": "2026-08-11T12:00:00Z",
        },
        "brief": {
            "schema_version": "1.0",
            "kind": "outcome-brief",
            "status": "DONE",
            "outcome": "Delivery is complete.",
            "human_action": None,
            "proof": _proof(),
            "gaps": [],
            "next": [],
            "open": [],
        },
        "provenance": [
            {
                "provider": "firecrawl",
                "locator": "https://example.com/source",
                "retrieved_at": "2026-08-11T12:00:00Z",
                "basis": "direct",
                "access": "public",
            }
        ],
        "artifacts": [],
        "work_items": [
            {
                "work_id": "task-1",
                "activity": "COMPLETED",
                "headline": "Implement delivery",
                "last_updated": "2026-08-11T12:00:00Z",
            }
        ],
    }
    _validator("briefspec-delivery").validate(delivery)

    manifest = {
        "schema_version": "1.0",
        "kind": "briefspec-bundle-manifest",
        "briefspec_version": "0.4.0",
        "delivery_schema_version": "1.0",
        "canonical_sha256": "a" * 64,
        "created_at": "2026-08-11T12:00:00Z",
        "files": [
            {
                "format": "json",
                "path": "brief.json",
                "media_type": "application/json",
                "size_bytes": 10,
                "sha256": "b" * 64,
                "renderer_version": "1.0",
            }
        ],
    }
    _validator("bundle-manifest").validate(manifest)

    receipt = {
        "schema_version": "1.0",
        "kind": "briefspec-delivery-receipt",
        "status": "delivered",
        "delivery_id": "receipt-1",
        "format": "application/zip",
        "destination": {"kind": "local", "locator": "/tmp/brief.zip"},
        "content_sha256": "c" * 64,
        "briefspec_version": "0.4.0",
        "delivery_schema_version": "1.0",
        "renderer_versions": ["1.0"],
        "verification_level": "delivered",
        "delivered_at": "2026-08-11T12:00:00Z",
    }
    _validator("delivery-receipt").validate(receipt)


def test_canonical_v2_delivery_manifest_and_receipt_schemas() -> None:
    delivery = {
        "schema_version": "2.0",
        "kind": "brief-spec-delivery",
        "source": {
            "harness": "omp",
            "brief_spec_version": "0.5.0",
            "host_version": "17.2.15",
            "adapter_version": "0.5.0",
            "model_provider": "xai",
            "model": "grok-code",
            "session_ref": "opaque-task",
            "source_revision": "deadbeef",
            "created_at": "2026-08-12T12:00:00Z",
        },
        "classification": {
            "work_type": "review",
            "subject": "pull-request",
            "confidence": "high",
            "origin": "host",
            "classified_at": "2026-08-12T12:00:00Z",
            "profile_version": "1.0",
            "rule_ids": ["host.pull-request"],
        },
        "explanation": {
            "profile_version": "1.0",
            "sections": [
                {"id": "scope", "label": "Scope", "content": "Review PR 42."},
                {"id": "verdict", "label": "Verdict", "content": "Ready."},
                {"id": "findings", "label": "Findings", "content": "No blockers."},
                {"id": "risk", "label": "Risk", "content": "Low."},
                {"id": "validation", "label": "Validation", "content": "Tests pass."},
                {
                    "id": "recommendation",
                    "label": "Recommendation",
                    "content": "Merge after CI.",
                },
            ],
        },
        "brief": {
            "schema_version": "1.0",
            "kind": "outcome-brief",
            "status": "DONE",
            "outcome": "The pull request is ready.",
            "human_action": None,
            "proof": _proof(),
            "gaps": [],
            "next": [],
            "open": [],
        },
        "provenance": [],
        "artifacts": [],
        "work_items": [],
    }
    _validator_id(f"{CANONICAL_SCHEMA_BASE}brief-spec-delivery.schema.json").validate(delivery)

    manifest = {
        "schema_version": "2.0",
        "kind": "brief-spec-bundle-manifest",
        "brief_spec_version": "0.5.0",
        "delivery_schema_version": "2.0",
        "canonical_sha256": "a" * 64,
        "created_at": "2026-08-12T12:00:00Z",
        "files": [
            {
                "format": "json",
                "path": "brief.json",
                "media_type": "application/json",
                "size_bytes": 10,
                "sha256": "b" * 64,
                "renderer_version": "2.0",
            }
        ],
    }
    _validator_id(f"{CANONICAL_SCHEMA_BASE}brief-spec-bundle-manifest.schema.json").validate(
        manifest
    )

    receipt = {
        "schema_version": "2.0",
        "kind": "brief-spec-delivery-receipt",
        "status": "delivered",
        "delivery_id": "receipt-1",
        "format": "application/zip",
        "destination": {"kind": "local", "locator": "/tmp/brief.zip"},
        "content_sha256": "c" * 64,
        "brief_spec_version": "0.5.0",
        "delivery_schema_version": "2.0",
        "renderer_versions": ["2.0"],
        "verification_level": "delivered",
        "delivered_at": "2026-08-12T12:00:00Z",
    }
    _validator_id(f"{CANONICAL_SCHEMA_BASE}brief-spec-delivery-receipt.schema.json").validate(
        receipt
    )
