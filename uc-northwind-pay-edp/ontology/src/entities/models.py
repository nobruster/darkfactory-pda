"""Canonical metadata entities for the NorthWind Pay catalog crawl.

Slimmed from OntoLayer. Enrichment fields stay empty until a later pass.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TableEntity(BaseModel):
    id: str
    source_connector: str = "postgres"
    name: str
    schema_name: str = ""
    qualified_name: str = ""
    column_ids: list[str] = Field(default_factory=list)
    column_count: int = 0
    columns_preview: str = ""
    description: str = ""


class ColumnEntity(BaseModel):
    id: str
    source_connector: str = "postgres"
    name: str
    table_id: str = ""
    table_name: str = ""
    qualified_name: str = ""
    data_type: str = "unknown"
    description: str = ""


class RelationshipEntity(BaseModel):
    id: str
    source_connector: str = "postgres"
    name: str = ""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relation_type: str = "FK"
    description: str = ""


class ViewEntity(BaseModel):
    id: str
    source_connector: str = "postgres"
    name: str
    schema_name: str = ""
    qualified_name: str = ""
    column_ids: list[str] = Field(default_factory=list)
    column_names: list[str] = Field(default_factory=list)
    definition_sql: str = ""
    referenced_tables: list[str] = Field(default_factory=list)
    description: str = ""


class ProcedureEntity(BaseModel):
    """A PostgreSQL function or procedure (pg_proc)."""

    id: str
    source_connector: str = "postgres"
    schema_name: str
    name: str
    qualified_name: str
    kind: str = "function"
    language: str = ""
    arguments: str = ""
    definition_sql: str = ""
    referenced_relations: list[str] = Field(default_factory=list)
    description: str = ""
