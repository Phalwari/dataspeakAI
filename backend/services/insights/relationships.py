"""Declared-FK graph and conservative, bounded single-column relationship inference."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import time
from typing import Any

from sqlalchemy import MetaData, Table as SATable, func, select
from sqlalchemy.engine import Connection

from services.insights.catalog import Catalog, ForeignKey
from services.insights.roles import ColumnRole


@dataclass(frozen=True)
class Relationship:
    left_table: str
    left_columns: tuple[str, ...]
    right_table: str
    right_columns: tuple[str, ...]
    source: str = "declared"
    confidence: float = 1.0


@dataclass(frozen=True)
class RelationshipPath:
    tables: tuple[str, ...]
    relationships: tuple[Relationship, ...]


class AmbiguousRelationshipError(ValueError):
    """Raised when more than one equally short path can connect two tables."""


def declared_relationships(catalog: Catalog) -> tuple[Relationship, ...]:
    result = []
    for table in catalog.tables:
        for foreign_key in table.foreign_keys:
            result.append(Relationship(
                left_table=table.name,
                left_columns=foreign_key.columns,
                right_table=foreign_key.referred_table,
                right_columns=foreign_key.referred_columns,
                source="declared",
                confidence=1.0,
            ))
    return tuple(sorted(result, key=lambda edge: (
        edge.left_table.casefold(), edge.right_table.casefold(), edge.left_columns,
    )))


def find_relationship_path(
    catalog: Catalog,
    source_table: str,
    target_table: str,
    *,
    relationships: tuple[Relationship, ...] | None = None,
    max_depth: int = 2,
) -> RelationshipPath | None:
    """Find a unique shortest path; ambiguous or over-depth joins are not guessed."""
    if max_depth < 0 or catalog.table(source_table) is None or catalog.table(target_table) is None:
        return None
    if source_table == target_table:
        return RelationshipPath((source_table,), ())
    edges = relationships if relationships is not None else declared_relationships(catalog)
    adjacency: dict[str, list[tuple[str, Relationship]]] = {}
    for edge in edges:
        adjacency.setdefault(edge.left_table, []).append((edge.right_table, edge))
        adjacency.setdefault(edge.right_table, []).append((edge.left_table, edge))
    queue = deque([(source_table, (source_table,), ())])
    shortest: list[RelationshipPath] = []
    shortest_length: int | None = None
    while queue:
        table, visited, path_edges = queue.popleft()
        depth = len(path_edges)
        if shortest_length is not None and depth >= shortest_length:
            continue
        if depth >= max_depth:
            continue
        for neighbor, edge in sorted(adjacency.get(table, ()), key=lambda item: item[0].casefold()):
            if neighbor in visited:
                continue
            next_edges = path_edges + (edge,)
            next_tables = visited + (neighbor,)
            if neighbor == target_table:
                shortest_length = len(next_edges) if shortest_length is None else shortest_length
                if len(next_edges) == shortest_length:
                    shortest.append(RelationshipPath(next_tables, next_edges))
            else:
                queue.append((neighbor, next_tables, next_edges))
    if len(shortest) > 1:
        raise AmbiguousRelationshipError("Multiple equally short relationship paths exist")
    return shortest[0] if shortest else None


def _type_family(value: Any) -> str:
    normalized = str(value).casefold()
    if any(token in normalized for token in ("int", "numeric", "decimal", "real", "float", "double")):
        return "numeric"
    if any(token in normalized for token in ("char", "text", "string", "uuid", "guid")):
        return "text"
    return "other"


def infer_relationships(
    connection: Connection,
    catalog: Catalog,
    roles: dict[str, dict[str, ColumnRole]],
    *,
    sample_size: int = 1_000,
    min_containment: float = 0.95,
    deadline: float | None = None,
    max_checks: int = 500,
) -> tuple[Relationship, ...]:
    """Infer only identifier-to-primary-key links with compatible types and bounded containment."""
    if sample_size < 1 or max_checks < 1 or not 0 < min_containment <= 1:
        raise ValueError("Invalid relationship inference bounds")
    metadata = MetaData()
    reflected: dict[str, SATable] = {}
    for table in catalog.tables:
        if table.primary_key:
            try:
                reflected[table.name] = SATable(
                    table.name, metadata, schema=catalog.schema, autoload_with=connection,
                )
            except Exception:
                continue
    declared = declared_relationships(catalog)
    declared_columns = {(edge.left_table, column) for edge in declared for column in edge.left_columns}
    found: list[Relationship] = []
    checks = 0
    for child in catalog.tables:
        child_sa = reflected.get(child.name)
        child_roles = roles.get(child.name, {})
        if child_sa is None:
            continue
        for parent in catalog.tables:
            parent_sa = reflected.get(parent.name)
            if parent_sa is None or parent.name == child.name or len(parent.primary_key) != 1:
                continue
            parent_pk = parent.primary_key[0]
            parent_type = next(column.declared_type for column in parent.columns if column.name == parent_pk)
            if _type_family(parent_type) == "other":
                continue
            for candidate in child.columns:
                if checks >= max_checks or (deadline is not None and time.monotonic() >= deadline):
                    return tuple(sorted((*declared, *found), key=lambda edge: (
                        edge.left_table.casefold(), edge.right_table.casefold(), edge.left_columns,
                    )))
                if candidate.primary_key_position or (child.name, candidate.name) in declared_columns:
                    continue
                role = child_roles.get(candidate.name)
                if role is None or role.role != "identifier" or role.confidence < 0.80:
                    continue
                if _type_family(candidate.declared_type) != _type_family(parent_type):
                    continue
                child_column = child_sa.c[candidate.name]
                parent_column = parent_sa.c[parent_pk]
                sampled_child = (
                    select(child_column.label("child_key"))
                    .where(child_column.is_not(None))
                    .distinct()
                    .limit(sample_size)
                    .subquery()
                )
                try:
                    checks += 1
                    counts = connection.execute(
                        select(
                            func.count().label("sampled"),
                            func.count(parent_column).label("matched"),
                        ).select_from(
                            sampled_child.outerjoin(
                                parent_sa, sampled_child.c.child_key == parent_column,
                            )
                        )
                    ).one()
                except Exception:
                    continue
                sampled_count = int(counts.sampled or 0)
                matched_count = int(counts.matched or 0)
                containment = matched_count / sampled_count if sampled_count else 0.0
                if sampled_count and containment >= min_containment:
                    found.append(Relationship(
                        left_table=child.name,
                        left_columns=(candidate.name,),
                        right_table=parent.name,
                        right_columns=(parent_pk,),
                        source="inferred",
                        confidence=containment,
                    ))
    unique = {
        (edge.left_table, edge.left_columns, edge.right_table, edge.right_columns): edge
        for edge in (*declared, *found)
    }
    return tuple(sorted(unique.values(), key=lambda edge: (
        edge.left_table.casefold(), edge.right_table.casefold(), edge.left_columns,
    )))
