"""Normalized relational metadata discovery; catalog objects contain no row data."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError


@dataclass(frozen=True)
class ForeignKey:
    columns: tuple[str, ...]
    referred_table: str
    referred_columns: tuple[str, ...]
    referred_schema: str | None = None


@dataclass(frozen=True)
class Column:
    name: str
    declared_type: str
    nullable: bool
    primary_key_position: int = 0


@dataclass(frozen=True)
class Table:
    name: str
    kind: str
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]
    foreign_keys: tuple[ForeignKey, ...]
    row_estimate: int | None = None


@dataclass(frozen=True)
class Catalog:
    dialect: str
    schema: str | None
    tables: tuple[Table, ...]
    version: str
    truncated: bool = False

    def table(self, name: str) -> Table | None:
        return next((table for table in self.tables if table.name == name), None)


def _catalog_digest(dialect: str, schema: str | None, tables: tuple[Table, ...]) -> str:
    payload = {
        "dialect": dialect,
        "schema": schema,
        "tables": [
            {
                "name": table.name,
                "kind": table.kind,
                "columns": [
                    (column.name, column.declared_type, column.nullable, column.primary_key_position)
                    for column in table.columns
                ],
                "primary_key": table.primary_key,
                "foreign_keys": [
                    (fk.columns, fk.referred_schema, fk.referred_table, fk.referred_columns)
                    for fk in table.foreign_keys
                ],
            }
            for table in tables
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _row_estimate(bind: Any, dialect: str, schema: str | None, table_name: str) -> int | None:
    """Read an engine-maintained estimate when available; never count an entire table."""
    if dialect == "postgresql":
        statement = text(
            "SELECT c.reltuples::bigint "
            "FROM pg_class AS c JOIN pg_namespace AS n ON n.oid = c.relnamespace "
            "WHERE n.nspname = COALESCE(:schema_name, current_schema()) "
            "AND c.relname = :table_name AND c.relkind IN ('r', 'p', 'm')"
        )
        params = {"schema_name": schema, "table_name": table_name}
    elif dialect in {"mysql", "mariadb"}:
        statement = text(
            "SELECT table_rows FROM information_schema.tables "
            "WHERE table_schema = COALESCE(:schema_name, DATABASE()) "
            "AND table_name = :table_name AND table_type = 'BASE TABLE'"
        )
        params = {"schema_name": schema, "table_name": table_name}
    else:
        # SQLite exposes no safe low-cost row estimate through its catalog.
        return None
    try:
        value = bind.execute(statement, params).scalar_one_or_none()
        if value is None:
            return None
        estimate = int(value)
        return estimate if estimate >= 0 else None
    except (SQLAlchemyError, TypeError, ValueError, OverflowError):
        return None


def discover_sql_catalog(
    bind: Any,
    *,
    schema: str | None = None,
    max_tables: int = 100,
) -> Catalog:
    """Discover tables, views, declared types, PKs and FKs without selecting row values."""
    if max_tables < 1:
        raise ValueError("max_tables must be positive")
    inspector = inspect(bind)
    dialect = str(inspector.bind.dialect.name).lower()
    table_names = set(inspector.get_table_names(schema=schema))
    try:
        view_names = set(inspector.get_view_names(schema=schema))
    except (NotImplementedError, AttributeError):
        view_names = set()
    all_names = sorted(table_names | view_names, key=lambda value: (value.casefold(), value))
    truncated = len(all_names) > max_tables
    tables: list[Table] = []

    for name in all_names[:max_tables]:
        raw_columns = inspector.get_columns(name, schema=schema)
        pk_info = inspector.get_pk_constraint(name, schema=schema) or {}
        pk_names = tuple(pk_info.get("constrained_columns") or ())
        pk_positions = {column_name: index + 1 for index, column_name in enumerate(pk_names)}
        columns = tuple(
            Column(
                name=str(item["name"]),
                declared_type=str(item.get("type") or "UNKNOWN"),
                nullable=bool(item.get("nullable", True)),
                primary_key_position=pk_positions.get(str(item["name"]), 0),
            )
            for item in raw_columns
        )
        foreign_keys: list[ForeignKey] = []
        for item in inspector.get_foreign_keys(name, schema=schema) or ():
            local = tuple(str(value) for value in (item.get("constrained_columns") or ()))
            remote = tuple(str(value) for value in (item.get("referred_columns") or ()))
            remote_table = item.get("referred_table")
            if local and remote and remote_table and len(local) == len(remote):
                foreign_keys.append(ForeignKey(
                    columns=local,
                    referred_table=str(remote_table),
                    referred_columns=remote,
                    referred_schema=item.get("referred_schema"),
                ))
        tables.append(Table(
            name=str(name),
            kind="view" if name in view_names else "table",
            columns=columns,
            primary_key=pk_names,
            foreign_keys=tuple(foreign_keys),
            row_estimate=_row_estimate(bind, dialect, schema, str(name)),
        ))

    normalized_tables = tuple(tables)
    return Catalog(
        dialect=dialect,
        schema=schema,
        tables=normalized_tables,
        version=_catalog_digest(dialect, schema, normalized_tables),
        truncated=truncated,
    )
