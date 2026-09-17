from __future__ import annotations

import json

from checksum import sha256_hex
from models import GeneratedArtifact, Type03Contract, Type05Contract, Type06Contract


def minor_units_to_string(amount_minor: int) -> str:
    sign = "-" if amount_minor < 0 else ""
    absolute = abs(amount_minor)
    return f"{sign}{absolute // 100}.{absolute % 100:02d}"


def optional_minor_units_to_string(amount_minor: int | None) -> str | None:
    if amount_minor is None:
        return None
    return minor_units_to_string(amount_minor)


def stable_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def build_source_manifest(
    generated: GeneratedArtifact,
    *,
    raw_sha256: str,
) -> bytes:
    """Build a deterministic transport manifest from a generated artifact."""

    batch = generated.batch
    contract = generated.contract
    source_file: dict[str, object] = {
        "encoding": contract.encoding,
        "final_newline": contract.final_newline,
        "line_ending": contract.line_ending,
        "name": batch.filename,
        "sha256": raw_sha256,
        "size_bytes": len(generated.raw_bytes),
    }
    if isinstance(contract, Type03Contract):
        source_file["record_length_bytes"] = (
            contract.record_length_bytes
        )
    if isinstance(contract, (Type05Contract, Type06Contract)):
        source_file["unicode_normalization"] = (
            contract.unicode_normalization
        )
    return stable_json(
        {
            "batch_id": batch.batch_id,
            "file_type": {
                "code": contract.code,
                "contract_version": contract.contract_version,
                "layout_version": contract.layout_version,
                "number": contract.type_number,
            },
            "schema_version": 1,
            "source_controls": dict(generated.source_control_values()),
            "source_file": source_file,
        }
    )


def build_generation_receipt(
    generated: GeneratedArtifact,
    *,
    raw_sha256: str,
    manifest_bytes: bytes,
    checksum_filename: str,
) -> bytes:
    """Build deterministic local evidence for one generation decision."""

    contract = generated.contract
    fault = (
        None
        if generated.expected_violation is None
        else {
            "code": generated.expected_violation,
            "expected_stage": "java-validation",
            "injected": True,
        }
    )
    return stable_json(
        {
            "artifacts": {
                "checksum_file": checksum_filename,
                "data_file": generated.batch.filename,
                "data_sha256": raw_sha256,
                "source_manifest": "source-manifest.json",
                "source_manifest_sha256": sha256_hex(manifest_bytes),
            },
            "batch_id": generated.batch.batch_id,
            "contract": {
                "layout_sha256": sha256_hex(contract.layout_path.read_bytes()),
                "layout_version": contract.layout_version,
                "registry_sha256": sha256_hex(
                    contract.registry_path.read_bytes()
                ),
                "type_number": contract.type_number,
                "version": contract.contract_version,
            },
            "controls": dict(generated.receipt_control_values()),
            "expected_contract_result": {
                "status": generated.expected_contract_status,
                "violation": generated.expected_violation,
            },
            "fault": fault,
            "generator": {
                "name": "northwind-pay-datagen",
                "version": "0.1.0",
            },
            "scenario": generated.scenario,
            "schema_version": 1,
            "status": "generated",
        }
    )
