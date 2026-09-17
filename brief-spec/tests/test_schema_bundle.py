from __future__ import annotations

import importlib.util
from pathlib import Path

from jsonschema.validators import validator_for
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


def _builder() -> object:
    script = ROOT / "scripts" / "build-schema-bundle.py"
    spec = importlib.util.spec_from_file_location("brief_spec_schema_bundle", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_compound_schema_validates_without_network_or_rewriting() -> None:
    module = _builder()
    bundle = module.build_bundle(ROOT / "schemas")
    validator_class = validator_for(bundle)
    validator_class.check_schema(bundle)
    validator = validator_class(
        bundle,
        registry=Registry().with_resource(bundle["$id"], Resource.from_contents(bundle)),
    )
    payload = {
        "schema_version": "2.0",
        "kind": "brief-spec-delivery",
        "source": {
            "harness": "test",
            "brief_spec_version": "0.5.0",
            "created_at": "2026-08-13T12:00:00Z",
        },
        "classification": {
            "work_type": "general",
            "subject": "general",
            "confidence": "low",
            "origin": "fallback",
            "classified_at": "2026-08-13T12:00:00Z",
            "profile_version": "1.0",
            "rule_ids": ["fallback.general"],
        },
        "explanation": {
            "profile_version": "1.0",
            "sections": [
                {"id": "answer", "label": "Answer", "content": "Complete."},
                {"id": "rationale", "label": "Rationale", "content": "Validated."},
                {"id": "next_action", "label": "Next action", "content": "None."},
            ],
        },
        "brief": {
            "schema_version": "1.0",
            "kind": "outcome-brief",
            "status": "DONE",
            "outcome": "The bundle validates offline.",
            "human_action": None,
            "proof": [
                {
                    "kind": "test",
                    "label": "Schema test",
                    "locator": "tests/test_schema_bundle.py",
                    "basis": "direct",
                    "result": "pass",
                }
            ],
            "gaps": [],
            "next": [],
            "open": [],
        },
        "provenance": [],
        "artifacts": [],
        "work_items": [],
    }
    validator.validate(payload)
