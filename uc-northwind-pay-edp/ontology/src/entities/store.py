"""In-memory entity store for the catalog crawl."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel

from .models import (
    ColumnEntity,
    ProcedureEntity,
    RelationshipEntity,
    TableEntity,
    ViewEntity,
)


class EntityStore:
    def __init__(self) -> None:
        self._entities: dict[str, BaseModel] = {}
        self._by_type: dict[type, list[str]] = defaultdict(list)
        self._by_name: dict[str, list[str]] = defaultdict(list)

    def add(self, entity: BaseModel) -> None:
        entity_id: str = entity.id  # type: ignore[attr-defined]
        self._entities[entity_id] = entity
        entity_type = type(entity)
        if entity_id not in self._by_type[entity_type]:
            self._by_type[entity_type].append(entity_id)
        name: str | None = getattr(entity, "name", None)
        if name and entity_id not in self._by_name[name]:
            self._by_name[name].append(entity_id)

    def get(self, entity_id: str) -> BaseModel | None:
        return self._entities.get(entity_id)

    def all(self, entity_type: type) -> list:
        ids = self._by_type.get(entity_type, [])
        return [self._entities[eid] for eid in ids if eid in self._entities]

    @property
    def tables(self) -> list[TableEntity]:
        return self.all(TableEntity)

    @property
    def columns(self) -> list[ColumnEntity]:
        return self.all(ColumnEntity)

    @property
    def relationships(self) -> list[RelationshipEntity]:
        return self.all(RelationshipEntity)

    @property
    def views(self) -> list[ViewEntity]:
        return self.all(ViewEntity)

    @property
    def procedures(self) -> list[ProcedureEntity]:
        return self.all(ProcedureEntity)
