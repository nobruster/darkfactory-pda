"""PostgreSQL catalog connector.

Adapted from OntoLayer's PostgresConnector:
- read-only session
- tables, columns, FKs, views, COMMENT ON
- plus pg_proc routines (the one real addition)

Schema filter is a comma list. Empty or `public` becomes the four plant schemas.
"""

from __future__ import annotations

import logging
from typing import Any

from connectors.registry import ConnectorResult, register_connector
from connectors.routines import procedure_entities_from_rows
from entities import (
    ColumnEntity,
    EntityStore,
    RelationshipEntity,
    TableEntity,
    ViewEntity,
)
from ids import entity_id
from settings import PLANT_SCHEMAS

try:
    import psycopg2
except ImportError:
    psycopg2 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_SYSTEM_SCHEMAS = frozenset({"information_schema", "pg_catalog", "pg_toast"})


def _ensure_psycopg2() -> None:
    if psycopg2 is None:
        raise ImportError(
            "psycopg2 is required. Install ontology extras or psycopg2-binary."
        )


@register_connector("postgres")
class PostgresConnector:
    connector_name = "postgres"

    def __init__(
        self,
        connection_string: str,
        schema_filter: str = "",
        definition_sql_max_chars: int = 8000,
    ) -> None:
        _ensure_psycopg2()
        self._connection_string = connection_string
        self._schemas = _parse_schemas(schema_filter)
        self._definition_sql_max_chars = definition_sql_max_chars
        self._conn: Any = None
        self._metadata: dict[str, Any] = {}
        self._fk_dicts: list[dict[str, str]] = []
        self._views: list[dict[str, Any]] = []
        self._routines: list[Any] = []

    def _in_schemas(self, column: str) -> tuple[str, tuple[str, ...]]:
        placeholders = ",".join(["%s"] * len(self._schemas))
        return f"{column} IN ({placeholders})", self._schemas

    def connect(self) -> None:
        try:
            self._conn = psycopg2.connect(self._connection_string)
            self._conn.set_session(readonly=True, autocommit=True)
        except Exception as exc:
            raise RuntimeError(
                f"Cannot open Postgres catalog (read-only). "
                f"Run `make deploy` first. Detail: {exc}"
            ) from exc

    async def fetch(self) -> bool:
        if self._conn is None:
            try:
                self.connect()
            except RuntimeError as exc:
                logger.error("PostgresConnector: %s", exc)
                return False
        try:
            table_comments, column_comments = self._extract_comments()
            self._metadata = self._extract_metadata(table_comments, column_comments)
            self._fk_dicts = self._extract_foreign_keys()
            self._views = self._extract_views(table_comments, column_comments)
            self._routines = self._extract_routines()
            logger.info(
                "PostgresConnector: Fetched %s tables, %s FKs, %s views, %s routines",
                len(self._metadata.get("tables", [])),
                len(self._fk_dicts),
                len(self._views),
                len(self._routines),
            )
            return True
        except Exception as exc:
            logger.error("PostgresConnector: Failed to extract metadata: %s", exc)
            return False

    def _extract_comments(
        self,
    ) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str, str], str]]:
        assert self._conn is not None
        cursor = self._conn.cursor()
        table_comments: dict[tuple[str, str], str] = {}
        column_comments: dict[tuple[str, str, str], str] = {}
        schema_sql, schema_params = self._in_schemas("n.nspname")
        try:
            cursor.execute(
                f"""
                SELECT n.nspname, c.relname, d.description
                FROM pg_catalog.pg_description d
                JOIN pg_catalog.pg_class c ON c.oid = d.objoid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE d.objsubid = 0
                  AND c.relkind IN ('r', 'v', 'm', 'p')
                  AND {schema_sql}
                """,
                schema_params,
            )
            for schema, relname, description in cursor.fetchall():
                if description:
                    table_comments[(schema, relname)] = description.strip()
            cursor.execute(
                f"""
                SELECT n.nspname, c.relname, a.attname, d.description
                FROM pg_catalog.pg_description d
                JOIN pg_catalog.pg_class c ON c.oid = d.objoid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_catalog.pg_attribute a
                    ON a.attrelid = c.oid AND a.attnum = d.objsubid
                WHERE d.objsubid > 0
                  AND c.relkind IN ('r', 'v', 'm', 'p')
                  AND a.attisdropped = false
                  AND {schema_sql}
                """,
                schema_params,
            )
            for schema, relname, colname, description in cursor.fetchall():
                if description:
                    column_comments[(schema, relname, colname)] = description.strip()
        except Exception as exc:
            logger.warning("PostgresConnector: Comment extraction failed: %s", exc)
        finally:
            cursor.close()
        return table_comments, column_comments

    def _extract_metadata(
        self,
        table_comments: dict[tuple[str, str], str] | None = None,
        column_comments: dict[tuple[str, str, str], str] | None = None,
    ) -> dict[str, Any]:
        assert self._conn is not None
        cursor = self._conn.cursor()
        table_comments = table_comments or {}
        column_comments = column_comments or {}
        schema_sql, schema_params = self._in_schemas("table_schema")
        cursor.execute(
            f"SELECT table_schema, table_name FROM information_schema.tables "
            f"WHERE table_type = 'BASE TABLE' AND {schema_sql} "
            f"ORDER BY table_schema, table_name",
            schema_params,
        )
        table_rows = cursor.fetchall()
        if not table_rows:
            cursor.close()
            return {"tables": []}
        cursor.execute(
            f"SELECT table_schema, table_name, column_name, data_type "
            f"FROM information_schema.columns "
            f"WHERE {schema_sql} "
            f"ORDER BY table_schema, table_name, ordinal_position",
            schema_params,
        )
        col_rows = cursor.fetchall()
        cursor.close()

        col_lookup: dict[tuple[str, str], list[dict]] = {}
        for schema, table, col_name, data_type in col_rows:
            col_entry: dict[str, Any] = {"name": col_name, "data_type": data_type}
            col_comment = column_comments.get((schema, table, col_name))
            if col_comment:
                col_entry["description"] = col_comment
            col_lookup.setdefault((schema, table), []).append(col_entry)

        tables: list[dict[str, Any]] = []
        for schema, table in table_rows:
            columns = col_lookup.get((schema, table), [])
            table_entry: dict[str, Any] = {
                "table": table,
                "schema": schema,
                "columns": columns,
            }
            table_comment = table_comments.get((schema, table))
            if table_comment:
                table_entry["description"] = table_comment
            tables.append(table_entry)
        return {"tables": tables}

    def _extract_foreign_keys(self) -> list[dict[str, str]]:
        assert self._conn is not None
        cursor = self._conn.cursor()
        schema_sql, schema_params = self._in_schemas("kcu.table_schema")
        to_sql, to_params = self._in_schemas("ccu.table_schema")
        try:
            cursor.execute(
                f"""
                SELECT
                    kcu.table_schema AS from_schema,
                    kcu.table_name AS from_table,
                    kcu.column_name AS from_column,
                    ccu.table_schema AS to_schema,
                    ccu.table_name AS to_table,
                    ccu.column_name AS to_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.constraint_schema = kcu.constraint_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                    AND tc.constraint_schema = ccu.constraint_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND {schema_sql}
                  AND {to_sql}
                """,
                schema_params + to_params,
            )
            fk_rows = cursor.fetchall()
            cursor.close()
            fks = []
            for from_schema, from_table, from_col, to_schema, to_table, to_col in fk_rows:
                fks.append(
                    {
                        "from_table": f"{from_schema}.{from_table}",
                        "from_column": from_col,
                        "to_table": f"{to_schema}.{to_table}",
                        "to_column": to_col,
                    }
                )
            return fks
        except Exception as exc:
            cursor.close()
            logger.debug("PostgresConnector: FK extraction failed: %s", exc)
            return []

    def _extract_views(
        self,
        table_comments: dict[tuple[str, str], str] | None = None,
        column_comments: dict[tuple[str, str, str], str] | None = None,
    ) -> list[dict[str, Any]]:
        assert self._conn is not None
        cursor = self._conn.cursor()
        table_comments = table_comments or {}
        column_comments = column_comments or {}
        schema_sql, schema_params = self._in_schemas("table_schema")
        try:
            cursor.execute(
                f"SELECT table_schema, table_name, view_definition "
                f"FROM information_schema.views "
                f"WHERE {schema_sql} "
                f"ORDER BY table_schema, table_name",
                schema_params,
            )
            view_rows = cursor.fetchall()
        except Exception as exc:
            cursor.close()
            logger.warning("PostgresConnector: View extraction failed: %s", exc)
            return []
        if not view_rows:
            cursor.close()
            return []

        view_keys = {(schema, name) for schema, name, _ in view_rows}
        col_lookup: dict[tuple[str, str], list[dict]] = {}
        try:
            cursor.execute(
                f"SELECT table_schema, table_name, column_name, data_type "
                f"FROM information_schema.columns "
                f"WHERE {schema_sql} "
                f"ORDER BY table_schema, table_name, ordinal_position",
                schema_params,
            )
            for schema, table, col, dtype in cursor.fetchall():
                if (schema, table) in view_keys:
                    entry: dict[str, Any] = {"name": col, "data_type": dtype}
                    col_comment = column_comments.get((schema, table, col))
                    if col_comment:
                        entry["description"] = col_comment
                    col_lookup.setdefault((schema, table), []).append(entry)
        except Exception as exc:
            logger.warning("PostgresConnector: View columns query failed: %s", exc)

        ref_lookup: dict[tuple[str, str], list[str]] = {}
        view_schema_sql, view_schema_params = self._in_schemas("view_schema")
        try:
            cursor.execute(
                f"SELECT view_schema, view_name, table_schema, table_name "
                f"FROM information_schema.view_table_usage "
                f"WHERE {view_schema_sql}",
                view_schema_params,
            )
            for v_schema, v_name, t_schema, t_name in cursor.fetchall():
                if (v_schema, v_name) in view_keys:
                    qualified = f"{t_schema}.{t_name}" if t_schema else t_name
                    ref_lookup.setdefault((v_schema, v_name), []).append(qualified)
        except Exception as exc:
            logger.debug("PostgresConnector: view_table_usage unavailable: %s", exc)
        cursor.close()

        views: list[dict[str, Any]] = []
        for schema, name, definition in view_rows:
            view_entry: dict[str, Any] = {
                "schema": schema,
                "view": name,
                "definition_sql": definition or "",
                "columns": col_lookup.get((schema, name), []),
                "referenced_tables": list(dict.fromkeys(ref_lookup.get((schema, name), []))),
            }
            view_comment = table_comments.get((schema, name))
            if view_comment:
                view_entry["description"] = view_comment
            views.append(view_entry)
        return views

    def _extract_routines(self) -> list[Any]:
        """Scan pg_proc for plant-schema functions and procedures."""
        assert self._conn is not None
        cursor = self._conn.cursor()
        schema_sql, schema_params = self._in_schemas("n.nspname")
        rows: list[tuple] = []
        try:
            cursor.execute(
                f"""
                SELECT
                    n.nspname,
                    p.proname,
                    pg_get_function_identity_arguments(p.oid),
                    l.lanname,
                    p.prokind::text,
                    CASE
                        WHEN p.prokind IN ('f', 'p') THEN pg_get_functiondef(p.oid)
                        ELSE ''
                    END
                FROM pg_catalog.pg_proc p
                JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                JOIN pg_catalog.pg_language l ON l.oid = p.prolang
                WHERE {schema_sql}
                ORDER BY n.nspname, p.proname, pg_get_function_identity_arguments(p.oid)
                """,
                schema_params,
            )
            rows = list(cursor.fetchall())
        except Exception as exc:
            logger.warning("PostgresConnector: Routine extraction failed: %s", exc)
            cursor.close()
            return []

        edges: dict[tuple[str, str], list[str]] = {}
        rel_sql, rel_params = self._in_schemas("rn.nspname")
        try:
            cursor.execute(
                f"""
                SELECT DISTINCT
                    n.nspname,
                    p.proname,
                    rn.nspname,
                    c.relname
                FROM pg_catalog.pg_depend d
                JOIN pg_catalog.pg_proc p ON p.oid = d.objid
                JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                JOIN pg_catalog.pg_class c ON c.oid = d.refobjid
                JOIN pg_catalog.pg_namespace rn ON rn.oid = c.relnamespace
                WHERE d.classid = 'pg_proc'::regclass
                  AND d.refclassid = 'pg_class'::regclass
                  AND {schema_sql}
                  AND {rel_sql}
                  AND c.relkind IN ('r', 'v', 'm', 'p')
                """,
                schema_params + rel_params,
            )
            for r_schema, r_name, rel_schema, rel_name in cursor.fetchall():
                key = (r_schema, r_name)
                qualified = f"{rel_schema}.{rel_name}"
                bucket = edges.setdefault(key, [])
                if qualified not in bucket:
                    bucket.append(qualified)
        except Exception as exc:
            logger.debug("PostgresConnector: pg_depend scan failed: %s", exc)
        finally:
            cursor.close()

        return procedure_entities_from_rows(
            rows,
            edges,
            max_definition_chars=self._definition_sql_max_chars,
        )

    def _build_entity_store(self) -> EntityStore:
        store = EntityStore()
        tables = self._metadata.get("tables", [])
        for table in tables:
            table_name = table.get("table", "unknown")
            schema = table.get("schema", "")
            columns = table.get("columns", [])
            qualified = f"{schema}.{table_name}" if schema else table_name
            table_id = entity_id("TABLE", schema, table_name)
            col_ids: list[str] = []
            for col in columns:
                col_name = col.get("name", "unknown")
                col_id = entity_id("COLUMN", schema, table_name, col_name)
                col_ids.append(col_id)
                store.add(
                    ColumnEntity(
                        id=col_id,
                        name=col_name,
                        table_id=table_id,
                        table_name=qualified,
                        qualified_name=f"{qualified}.{col_name}",
                        data_type=col.get("data_type", "unknown"),
                        description=col.get("description", ""),
                    )
                )
            store.add(
                TableEntity(
                    id=table_id,
                    name=table_name,
                    schema_name=schema,
                    qualified_name=qualified,
                    column_ids=col_ids,
                    column_count=len(columns),
                    columns_preview=", ".join(c.get("name", "") for c in columns[:5]),
                    description=table.get("description", ""),
                )
            )

        for fk in self._fk_dicts:
            from_table = fk.get("from_table", "")
            to_table = fk.get("to_table", "")
            from_column = fk.get("from_column", "")
            to_column = fk.get("to_column", from_column)
            store.add(
                RelationshipEntity(
                    id=entity_id("RELATIONSHIP", from_table, to_table, from_column),
                    name=f"{from_table} -> {to_table} via {from_column}",
                    from_table=from_table,
                    from_column=from_column,
                    to_table=to_table,
                    to_column=to_column,
                    relation_type="FK",
                )
            )

        for view in self._views:
            view_name = view.get("view", "unknown")
            schema = view.get("schema") or ""
            columns = view.get("columns", [])
            qualified = f"{schema}.{view_name}" if schema else view_name
            view_id = entity_id("VIEW", schema, view_name)
            col_ids = []
            col_names = []
            for col in columns:
                col_name = col.get("name", "unknown")
                col_id = entity_id("COLUMN", schema, view_name, col_name)
                col_ids.append(col_id)
                col_names.append(col_name)
            store.add(
                ViewEntity(
                    id=view_id,
                    name=view_name,
                    schema_name=schema,
                    qualified_name=qualified,
                    column_ids=col_ids,
                    column_names=col_names,
                    definition_sql=view.get("definition_sql") or "",
                    referenced_tables=list(view.get("referenced_tables") or []),
                    description=view.get("description", ""),
                )
            )

        known_relations = [
            f"{t.get('schema')}.{t.get('table')}"
            for t in tables
            if t.get("schema") and t.get("table")
        ]
        for routine in self._routines:
            if not routine.referenced_relations:
                routine.referenced_relations = _relations_mentioned(
                    routine.definition_sql, known_relations
                )
            store.add(routine)

        logger.info(
            "PostgresConnector: Entity store tables=%s columns=%s fks=%s views=%s routines=%s",
            len(store.tables),
            len(store.columns),
            len(store.relationships),
            len(store.views),
            len(store.procedures),
        )
        return store

    def process(self) -> ConnectorResult:
        if not self._metadata and not self._routines:
            raise RuntimeError("Must call fetch() before process()")
        store = self._build_entity_store()
        return ConnectorResult(
            entity_store=store,
            table_count=len(store.tables),
            routine_count=len(store.procedures),
            raw_metadata=self._metadata,
            schemas=self._schemas,
        )

    def close(self) -> None:
        conn = getattr(self, "_conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._conn = None

    def __del__(self) -> None:
        self.close()


def _relations_mentioned(sql: str, known_relations: list[str]) -> list[str]:
    """Fallback when pg_depend is empty: find schema.table tokens in the body."""
    if not sql:
        return []
    found: list[str] = []
    for qualified in known_relations:
        if qualified in sql and qualified not in found:
            found.append(qualified)
    return found


def _parse_schemas(schema_filter: str) -> tuple[str, ...]:
    parts = tuple(p.strip() for p in (schema_filter or "").split(",") if p.strip())
    if not parts or parts == ("public",):
        return PLANT_SCHEMAS
    cleaned = tuple(p for p in parts if p not in _SYSTEM_SCHEMAS)
    return cleaned or PLANT_SCHEMAS
