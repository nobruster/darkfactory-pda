from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from models import (
    ContractError,
    Type01Contract,
    Type02Contract,
    Type03Contract,
    Type04Contract,
    Type05Contract,
    Type06Contract,
)
from paths import find_repository_root


def default_contracts_root() -> Path:
    return find_repository_root() / "contracts" / "types"


def _load_mapping(path: Path) -> Mapping[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise ContractError(f"Cannot safely load contract file: {path.name}") from exc

    if not isinstance(value, Mapping):
        raise ContractError(f"Contract file is not a mapping: {path.name}")
    return value


def _require_mapping(value: object, *, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"Contract field is not a mapping: {field_name}")
    return value


def _require_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"Contract field is not a non-empty string: {field_name}")
    return value


def _require_int(value: object, *, field_name: str) -> int:
    if type(value) is not int:
        raise ContractError(f"Contract field is not an integer: {field_name}")
    return value


def _load_approved_entry(
    *,
    type_number: str,
    contracts_root: Path | None,
) -> tuple[Path, Path, Mapping[str, Any]]:
    root = (contracts_root or default_contracts_root()).resolve()
    registry_path = root / "registry.yaml"
    registry = _load_mapping(registry_path)
    entries = registry.get("types")
    if not isinstance(entries, list):
        raise ContractError("Registry types must be a list")

    entry: Mapping[str, Any] | None = None
    for candidate in entries:
        if (
            isinstance(candidate, Mapping)
            and candidate.get("number") == type_number
        ):
            entry = candidate
            break
    if entry is None:
        raise ContractError(f"Type {type_number} is not registered")
    if entry.get("status") != "approved-for-implementation":
        raise ContractError(
            f"Type {type_number} contract is not approved for implementation"
        )
    return root, registry_path, entry


def load_type_01_contract(contracts_root: Path | None = None) -> Type01Contract:
    """Load the approved Type 01 contract from the live contract registry."""

    root, registry_path, entry = _load_approved_entry(
        type_number="01",
        contracts_root=contracts_root,
    )
    folder = _require_string(
        entry.get("folder"),
        field_name="registry.types[01].folder",
    )
    layout_path = root / folder / "layout.yaml"
    layout = _load_mapping(layout_path)
    file_type = _require_mapping(layout.get("file_type"), field_name="file_type")
    records = _require_mapping(layout.get("records"), field_name="records")
    header = _require_mapping(records.get("header"), field_name="records.header")
    detail = _require_mapping(records.get("detail"), field_name="records.detail")
    trailer = _require_mapping(records.get("trailer"), field_name="records.trailer")
    overpunch = _require_mapping(layout.get("overpunch"), field_name="overpunch")

    positive = _require_string(
        overpunch.get("positive_characters"),
        field_name="overpunch.positive_characters",
    )
    negative = _require_string(
        overpunch.get("negative_characters"),
        field_name="overpunch.negative_characters",
    )
    if len(positive) != 10 or len(negative) != 10:
        raise ContractError("Overpunch maps must each contain exactly ten characters")

    return Type01Contract(
        contract_version=_require_int(layout.get("version"), field_name="version"),
        type_number=_require_string(entry.get("number"), field_name="number"),
        code=_require_string(file_type.get("code"), field_name="file_type.code"),
        layout_version=_require_string(
            file_type.get("layout_version"),
            field_name="file_type.layout_version",
        ),
        filename_pattern=_require_string(
            file_type.get("filename_regex"),
            field_name="file_type.filename_regex",
        ),
        encoding=_require_string(
            file_type.get("encoding"),
            field_name="file_type.encoding",
        ),
        line_ending=_require_string(
            file_type.get("line_ending"),
            field_name="file_type.line_ending",
        ),
        final_newline=_require_string(
            file_type.get("final_newline"),
            field_name="file_type.final_newline",
        ),
        header_length=_require_int(
            header.get("length_bytes"),
            field_name="records.header.length_bytes",
        ),
        detail_length=_require_int(
            detail.get("length_bytes"),
            field_name="records.detail.length_bytes",
        ),
        trailer_length=_require_int(
            trailer.get("length_bytes"),
            field_name="records.trailer.length_bytes",
        ),
        positive_overpunch=positive,
        negative_overpunch=negative,
        registry_path=registry_path,
        layout_path=layout_path,
    )


def load_type_02_contract(contracts_root: Path | None = None) -> Type02Contract:
    """Load and structurally validate the approved Type 02 contract."""

    root, registry_path, entry = _load_approved_entry(
        type_number="02",
        contracts_root=contracts_root,
    )
    folder = _require_string(
        entry.get("folder"),
        field_name="registry.types[02].folder",
    )
    layout_path = root / folder / "layout.yaml"
    layout = _load_mapping(layout_path)
    file_type = _require_mapping(layout.get("file_type"), field_name="file_type")
    grammar = _require_mapping(layout.get("grammar"), field_name="grammar")
    records = _require_mapping(layout.get("records"), field_name="records")
    header = _require_mapping(records.get("header"), field_name="records.header")
    event = _require_mapping(records.get("event"), field_name="records.event")
    trailer = _require_mapping(records.get("trailer"), field_name="records.trailer")

    type_number = _require_string(entry.get("number"), field_name="number")
    layout_type_number = _require_string(
        file_type.get("number"),
        field_name="file_type.number",
    )
    code = _require_string(file_type.get("code"), field_name="file_type.code")
    registry_code = _require_string(
        entry.get("file_type_code"),
        field_name="registry.types[02].file_type_code",
    )
    if layout_type_number != type_number or code != registry_code:
        raise ContractError("Type 02 registry and layout identities disagree")

    delimiter = _require_string(
        grammar.get("delimiter"),
        field_name="grammar.delimiter",
    )
    escape_character = _require_string(
        grammar.get("escape_character"),
        field_name="grammar.escape_character",
    )
    if len(delimiter) != 1 or len(escape_character) != 1:
        raise ContractError("Type 02 delimiter and escape must be one character")
    if delimiter == escape_character:
        raise ContractError("Type 02 delimiter and escape must be distinct")

    return Type02Contract(
        contract_version=_require_int(layout.get("version"), field_name="version"),
        type_number=type_number,
        code=code,
        layout_version=_require_string(
            file_type.get("layout_version"),
            field_name="file_type.layout_version",
        ),
        filename_pattern=_require_string(
            file_type.get("filename_regex"),
            field_name="file_type.filename_regex",
        ),
        encoding=_require_string(
            file_type.get("encoding"),
            field_name="file_type.encoding",
        ),
        line_ending=_require_string(
            file_type.get("line_ending"),
            field_name="file_type.line_ending",
        ),
        final_newline=_require_string(
            file_type.get("final_newline"),
            field_name="file_type.final_newline",
        ),
        delimiter=delimiter,
        escape_character=escape_character,
        header_field_count=_require_int(
            header.get("field_count"),
            field_name="records.header.field_count",
        ),
        event_field_count=_require_int(
            event.get("field_count"),
            field_name="records.event.field_count",
        ),
        trailer_field_count=_require_int(
            trailer.get("field_count"),
            field_name="records.trailer.field_count",
        ),
        max_record_bytes=_require_int(
            file_type.get("max_record_bytes"),
            field_name="file_type.max_record_bytes",
        ),
        max_source_file_bytes=_require_int(
            file_type.get("max_source_file_bytes"),
            field_name="file_type.max_source_file_bytes",
        ),
        registry_path=registry_path,
        layout_path=layout_path,
    )


def load_type_03_contract(
    contracts_root: Path | None = None,
) -> Type03Contract:
    """Load and structurally validate the approved Type 03 contract."""

    root, registry_path, entry = _load_approved_entry(
        type_number="03",
        contracts_root=contracts_root,
    )
    folder = _require_string(
        entry.get("folder"),
        field_name="registry.types[03].folder",
    )
    layout_path = root / folder / "layout.yaml"
    layout = _load_mapping(layout_path)
    file_type = _require_mapping(
        layout.get("file_type"),
        field_name="file_type",
    )
    record_sequence = _require_mapping(
        layout.get("record_sequence"),
        field_name="record_sequence",
    )
    records = _require_mapping(
        layout.get("records"),
        field_name="records",
    )

    type_number = _require_string(entry.get("number"), field_name="number")
    layout_type_number = _require_string(
        file_type.get("number"),
        field_name="file_type.number",
    )
    code = _require_string(file_type.get("code"), field_name="file_type.code")
    registry_code = _require_string(
        entry.get("file_type_code"),
        field_name="registry.types[03].file_type_code",
    )
    if layout_type_number != type_number or code != registry_code:
        raise ContractError("Type 03 registry and layout identities disagree")
    if record_sequence.get("grammar") != "H (L (A B)+ T)+ Z":
        raise ContractError("Type 03 record grammar is unsupported")

    expected_discriminators = {
        "file_header": "H",
        "lot_header": "L",
        "financial_segment": "A",
        "beneficiary_segment": "B",
        "lot_trailer": "T",
        "file_trailer": "Z",
    }
    for record_name, discriminator in expected_discriminators.items():
        record = _require_mapping(
            records.get(record_name),
            field_name=f"records.{record_name}",
        )
        if record.get("discriminator") != discriminator:
            raise ContractError(
                f"Type 03 discriminator is invalid: {record_name}"
            )

    record_length = _require_int(
        file_type.get("record_length_bytes"),
        field_name="file_type.record_length_bytes",
    )
    transport_length = _require_int(
        file_type.get("transport_record_length_bytes"),
        field_name="file_type.transport_record_length_bytes",
    )
    if transport_length != record_length + 2:
        raise ContractError(
            "Type 03 transport record length must include one CRLF"
        )
    reserved = _require_string(
        file_type.get("reserved_character"),
        field_name="file_type.reserved_character",
    )
    if len(reserved) != 1:
        raise ContractError(
            "Type 03 reserved character must be exactly one character"
        )

    return Type03Contract(
        contract_version=_require_int(
            layout.get("version"),
            field_name="version",
        ),
        type_number=type_number,
        code=code,
        layout_version=_require_string(
            file_type.get("layout_version"),
            field_name="file_type.layout_version",
        ),
        filename_pattern=_require_string(
            file_type.get("filename_regex"),
            field_name="file_type.filename_regex",
        ),
        encoding=_require_string(
            file_type.get("encoding"),
            field_name="file_type.encoding",
        ),
        line_ending=_require_string(
            file_type.get("line_ending"),
            field_name="file_type.line_ending",
        ),
        final_newline=_require_string(
            file_type.get("final_line_ending"),
            field_name="file_type.final_line_ending",
        ),
        record_length_bytes=record_length,
        transport_record_length_bytes=transport_length,
        max_lots=_require_int(
            file_type.get("max_lots"),
            field_name="file_type.max_lots",
        ),
        max_logical_rows=_require_int(
            file_type.get("max_logical_rows"),
            field_name="file_type.max_logical_rows",
        ),
        max_physical_records=_require_int(
            file_type.get("max_physical_records"),
            field_name="file_type.max_physical_records",
        ),
        max_source_file_bytes=_require_int(
            file_type.get("max_source_file_bytes"),
            field_name="file_type.max_source_file_bytes",
        ),
        reserved_character=reserved,
        registry_path=registry_path,
        layout_path=layout_path,
    )


def load_type_04_contract(
    contracts_root: Path | None = None,
) -> Type04Contract:
    """Load and structurally validate the approved Type 04 contract."""

    root, registry_path, entry = _load_approved_entry(
        type_number="04",
        contracts_root=contracts_root,
    )
    folder = _require_string(
        entry.get("folder"),
        field_name="registry.types[04].folder",
    )
    layout_path = root / folder / "layout.yaml"
    layout = _load_mapping(layout_path)
    file_type = _require_mapping(
        layout.get("file_type"),
        field_name="file_type",
    )
    record_sequence = _require_mapping(
        layout.get("record_sequence"),
        field_name="record_sequence",
    )
    records = _require_mapping(
        layout.get("records"),
        field_name="records",
    )
    padding = _require_mapping(
        layout.get("padding"),
        field_name="padding",
    )
    timestamps = _require_mapping(
        layout.get("timestamp_semantics"),
        field_name="timestamp_semantics",
    )

    type_number = _require_string(entry.get("number"), field_name="number")
    layout_type_number = _require_string(
        file_type.get("number"),
        field_name="file_type.number",
    )
    code = _require_string(file_type.get("code"), field_name="file_type.code")
    registry_code = _require_string(
        entry.get("file_type_code"),
        field_name="registry.types[04].file_type_code",
    )
    if layout_type_number != type_number or code != registry_code:
        raise ContractError("Type 04 registry and layout identities disagree")
    if (
        record_sequence.get("grammar") != "H (D | D R)+ T"
        or record_sequence.get("branch_rule")
        != "D.status_code=OK selects D; D.status_code=RT selects D R"
    ):
        raise ContractError("Type 04 conditional record grammar is unsupported")

    expected_records = {
        "header": ("H", 56),
        "transfer": ("D", 162),
        "return": ("R", 91),
        "trailer": ("T", 82),
    }
    lengths: dict[str, int] = {}
    for record_name, (discriminator, expected_length) in (
        expected_records.items()
    ):
        record = _require_mapping(
            records.get(record_name),
            field_name=f"records.{record_name}",
        )
        if record.get("discriminator") != discriminator:
            raise ContractError(
                f"Type 04 discriminator is invalid: {record_name}"
            )
        length = _require_int(
            record.get("length_bytes"),
            field_name=f"records.{record_name}.length_bytes",
        )
        if length != expected_length:
            raise ContractError(
                f"Type 04 record length is unsupported: {record_name}"
            )
        lengths[record_name] = length

    visible_padding = _require_string(
        padding.get("visible_character"),
        field_name="padding.visible_character",
    )
    if len(visible_padding) != 1:
        raise ContractError(
            "Type 04 visible padding must be exactly one character"
        )
    source_zone = _require_string(
        timestamps.get("source_zone"),
        field_name="timestamp_semantics.source_zone",
    )
    if (
        timestamps.get("output")
        != "ISO-8601_seconds_with_explicit_numeric_offset"
    ):
        raise ContractError("Type 04 timestamp output is unsupported")

    return Type04Contract(
        contract_version=_require_int(
            layout.get("version"),
            field_name="version",
        ),
        type_number=type_number,
        code=code,
        layout_version=_require_string(
            file_type.get("layout_version"),
            field_name="file_type.layout_version",
        ),
        filename_pattern=_require_string(
            file_type.get("filename_regex"),
            field_name="file_type.filename_regex",
        ),
        encoding=_require_string(
            file_type.get("encoding"),
            field_name="file_type.encoding",
        ),
        line_ending=_require_string(
            file_type.get("line_ending"),
            field_name="file_type.line_ending",
        ),
        final_newline=_require_string(
            file_type.get("final_line_ending"),
            field_name="file_type.final_line_ending",
        ),
        header_length=lengths["header"],
        transfer_length=lengths["transfer"],
        return_length=lengths["return"],
        trailer_length=lengths["trailer"],
        max_transfers=_require_int(
            file_type.get("max_transfers"),
            field_name="file_type.max_transfers",
        ),
        max_returns=_require_int(
            file_type.get("max_returns"),
            field_name="file_type.max_returns",
        ),
        max_movements=_require_int(
            file_type.get("max_movements"),
            field_name="file_type.max_movements",
        ),
        max_physical_records=_require_int(
            file_type.get("max_physical_records"),
            field_name="file_type.max_physical_records",
        ),
        max_source_file_bytes=_require_int(
            file_type.get("max_source_file_bytes"),
            field_name="file_type.max_source_file_bytes",
        ),
        visible_padding_character=visible_padding,
        source_zone=source_zone,
        registry_path=registry_path,
        layout_path=layout_path,
    )


def load_type_05_contract(
    contracts_root: Path | None = None,
) -> Type05Contract:
    """Load and structurally validate the approved Type 05 contract."""

    root, registry_path, entry = _load_approved_entry(
        type_number="05",
        contracts_root=contracts_root,
    )
    folder = _require_string(
        entry.get("folder"),
        field_name="registry.types[05].folder",
    )
    layout_path = root / folder / "layout.yaml"
    layout = _load_mapping(layout_path)
    file_type = _require_mapping(
        layout.get("file_type"),
        field_name="file_type",
    )
    grammar = _require_mapping(
        layout.get("grammar"),
        field_name="grammar",
    )
    calculation = _require_mapping(
        layout.get("calculation"),
        field_name="calculation",
    )

    type_number = _require_string(entry.get("number"), field_name="number")
    layout_type_number = _require_string(
        file_type.get("number"),
        field_name="file_type.number",
    )
    code = _require_string(file_type.get("code"), field_name="file_type.code")
    registry_code = _require_string(
        entry.get("file_type_code"),
        field_name="registry.types[05].file_type_code",
    )
    if layout_type_number != type_number or code != registry_code:
        raise ContractError("Type 05 registry and layout identities disagree")

    expected_grammar = {
        "style": "semicolon_delimited",
        "parser": "single_pass_quote_aware_lexer",
        "delimiter": "semicolon",
        "quote_character": "double_quote",
        "escaped_quote": "doubled_quote",
        "multiline_fields": "forbidden",
        "whitespace_outside_quotes": "forbidden",
        "field_count": 10,
        "description_must_be_quoted": True,
        "non_description_fields_must_be_unquoted": True,
        "empty_fields": "forbidden",
    }
    if any(grammar.get(name) != value for name, value in expected_grammar.items()):
        raise ContractError("Type 05 source grammar is unsupported")

    expected_columns = (
        "assessment_id",
        "batch_id",
        "merchant_id",
        "merchant_tax_id",
        "fee_code",
        "description",
        "gross_amount_brl",
        "rate_percent",
        "assessed_fee_brl",
        "assessment_date",
    )
    columns = layout.get("columns")
    if not isinstance(columns, list) or len(columns) != len(expected_columns):
        raise ContractError("Type 05 source columns are unsupported")
    for position, (column, expected_name) in enumerate(
        zip(columns, expected_columns, strict=True),
        start=1,
    ):
        value = _require_mapping(
            column,
            field_name=f"columns[{position}]",
        )
        if value.get("position") != position or value.get("name") != expected_name:
            raise ContractError("Type 05 source column order is unsupported")

    if (
        file_type.get("unicode_normalization") != "NFC_required_on_input"
        or calculation.get("expression")
        != "gross_amount_brl * rate_percent / 100"
        or calculation.get("intermediate") != "arbitrary_precision_decimal"
        or calculation.get("final_scale") != 2
        or calculation.get("rounding_mode") != "HALF_UP"
        or calculation.get("assessed_fee_must_equal_calculated_fee") is not True
        or calculation.get("binary_floating_point") != "forbidden"
    ):
        raise ContractError(
            "Type 05 normalization or calculation semantics are unsupported"
        )

    type05_contract = Type05Contract(  # returned below after field assembly
        contract_version=_require_int(
            layout.get("version"),
            field_name="version",
        ),
        type_number=type_number,
        code=code,
        layout_version=_require_string(
            file_type.get("layout_version"),
            field_name="file_type.layout_version",
        ),
        filename_pattern=_require_string(
            file_type.get("filename_regex"),
            field_name="file_type.filename_regex",
        ),
        encoding=_require_string(
            file_type.get("encoding"),
            field_name="file_type.encoding",
        ),
        unicode_normalization="NFC",
        line_ending=_require_string(
            file_type.get("line_ending"),
            field_name="file_type.line_ending",
        ),
        final_newline=_require_string(
            file_type.get("final_line_ending"),
            field_name="file_type.final_line_ending",
        ),
        delimiter=";",
        quote_character='"',
        field_count=_require_int(
            grammar.get("field_count"),
            field_name="grammar.field_count",
        ),
        exact_header=_require_string(
            _require_mapping(
                layout.get("header"),
                field_name="header",
            ).get("exact"),
            field_name="header.exact",
        ),
        max_detail_rows=_require_int(
            file_type.get("max_detail_rows"),
            field_name="file_type.max_detail_rows",
        ),
        max_physical_record_bytes=_require_int(
            file_type.get("max_physical_record_bytes"),
            field_name="file_type.max_physical_record_bytes",
        ),
        max_source_file_bytes=_require_int(
            file_type.get("max_source_file_bytes"),
            field_name="file_type.max_source_file_bytes",
        ),
        registry_path=registry_path,
        layout_path=layout_path,
    )
    return type05_contract


def load_type_06_contract(
    contracts_root: Path | None = None,
) -> Type06Contract:
    """Load and structurally validate the approved Type 06 contract."""

    root, registry_path, entry = _load_approved_entry(
        type_number="06",
        contracts_root=contracts_root,
    )
    folder = _require_string(
        entry.get("folder"),
        field_name="registry.types[06].folder",
    )
    layout_path = root / folder / "layout.yaml"
    layout = _load_mapping(layout_path)
    file_type = _require_mapping(layout.get("file_type"), field_name="file_type")
    grammar = _require_mapping(layout.get("grammar"), field_name="grammar")
    calculation = _require_mapping(
        layout.get("calculation"),
        field_name="calculation",
    )
    type_number = _require_string(entry.get("number"), field_name="number")
    code = _require_string(file_type.get("code"), field_name="file_type.code")
    if calculation.get("rounding_mode") != "HALF_UP":
        raise ContractError("Type 06 calculation semantics are unsupported")
    return Type06Contract(
        contract_version=_require_int(layout.get("version"), field_name="version"),
        type_number=type_number,
        code=code,
        layout_version=_require_string(
            file_type.get("layout_version"),
            field_name="file_type.layout_version",
        ),
        filename_pattern=_require_string(
            file_type.get("filename_regex"),
            field_name="file_type.filename_regex",
        ),
        encoding=_require_string(
            file_type.get("encoding"),
            field_name="file_type.encoding",
        ),
        unicode_normalization="NFC",
        line_ending=_require_string(
            file_type.get("line_ending"),
            field_name="file_type.line_ending",
        ),
        final_newline=_require_string(
            file_type.get("final_line_ending"),
            field_name="file_type.final_line_ending",
        ),
        delimiter=";",
        quote_character='"',
        field_count=_require_int(
            grammar.get("field_count"),
            field_name="grammar.field_count",
        ),
        exact_header=_require_string(
            _require_mapping(layout.get("header"), field_name="header").get("exact"),
            field_name="header.exact",
        ),
        max_detail_rows=_require_int(
            file_type.get("max_detail_rows"),
            field_name="file_type.max_detail_rows",
        ),
        max_physical_record_bytes=_require_int(
            file_type.get("max_physical_record_bytes"),
            field_name="file_type.max_physical_record_bytes",
        ),
        max_source_file_bytes=_require_int(
            file_type.get("max_source_file_bytes"),
            field_name="file_type.max_source_file_bytes",
        ),
        registry_path=registry_path,
        layout_path=layout_path,
    )
