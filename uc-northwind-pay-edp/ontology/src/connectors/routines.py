"""Map pg_proc rows into ProcedureEntity. Pure — no live database."""

from __future__ import annotations

from entities.models import ProcedureEntity
from ids import entity_id

KIND_MAP = {
    "f": "function",
    "p": "procedure",
    "a": "aggregate",
    "w": "window",
}


def truncate_sql(sql: str, max_chars: int) -> str:
    text = sql or ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 15] + "\n-- [truncated]"


def procedure_entities_from_rows(
    rows: list[tuple],
    edges: dict[tuple[str, str], list[str]],
    *,
    max_definition_chars: int = 8000,
) -> list[ProcedureEntity]:
    """Turn (schema, name, arguments, language, kind, definition) tuples into entities."""
    entities: list[ProcedureEntity] = []
    seen: set[str] = set()
    for schema, name, arguments, language, kind, definition in rows:
        schema_name = str(schema)
        proc_name = str(name)
        identity_args = str(arguments or "")
        kind_key = str(kind or "f")
        kind_name = KIND_MAP.get(kind_key, kind_key)
        qualified = f"{schema_name}.{proc_name}"
        entity_key = entity_id("PROCEDURE", schema_name, proc_name, identity_args)
        if entity_key in seen:
            continue
        seen.add(entity_key)
        entities.append(
            ProcedureEntity(
                id=entity_key,
                schema_name=schema_name,
                name=proc_name,
                qualified_name=qualified,
                kind=kind_name,
                language=str(language or ""),
                arguments=identity_args,
                definition_sql=truncate_sql(str(definition or ""), max_definition_chars),
                referenced_relations=list(edges.get((schema_name, proc_name), [])),
            )
        )
    return entities
