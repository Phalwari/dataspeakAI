"""Bounded table sampling that returns aggregate statistics and never raw records."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import MetaData, Table as SATable, select
from sqlalchemy.engine import Connection

from services.insights.catalog import Catalog
from services.insights.budget import sqlite_deadline


DEFAULT_SAMPLE_SIZE = 10_000
MAX_COLUMNS_PER_TABLE = 256
PROFILE_VERSION = "1"
_LIFECYCLE_VALUES = {
    "paid", "unpaid", "pending", "processing", "shipped", "delivered", "completed",
    "complete", "cancelled", "canceled", "returned", "refunded", "failed", "open", "closed",
}


@dataclass(frozen=True)
class ColumnProfile:
    sample_count: int
    null_count: int
    null_ratio: float
    distinct_count: int
    distinct_ratio: float
    numeric_parse_rate: float
    date_parse_rate: float
    numeric_min: float | None = None
    numeric_max: float | None = None
    date_min: str | None = None
    date_max: str | None = None
    contains_email_like: bool = False
    contains_phone_like: bool = False
    max_text_length: int = 0
    lifecycle_value_ratio: float = 0.0
    profile_error: bool = False


@dataclass(frozen=True)
class TableProfile:
    sampled_rows: int
    sample_truncated: bool
    columns: dict[str, ColumnProfile]
    profile_error: bool = False
    budget_exceeded: bool = False


@dataclass(frozen=True)
class ProfileSet:
    catalog_version: str
    sample_size: int
    tables: dict[str, TableProfile]
    warnings: tuple[str, ...]


def _numeric(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value).strip())
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def _date(value: Any) -> dt.date | dt.datetime | None:
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return value
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return dt.datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        try:
            return dt.date.fromisoformat(candidate)
        except ValueError:
            return None


def _value_fingerprint(value: Any) -> str:
    """Hash a sample value for cardinality only; never return or log the value."""
    try:
        serialized = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except (TypeError, ValueError):
        serialized = type(value).__name__
    return hashlib.sha256(serialized.encode("utf-8", errors="replace")).hexdigest()


def _profile_values(values: list[Any]) -> ColumnProfile:
    non_null = [value for value in values if value is not None]
    sample_count = len(values)
    distinct = {_value_fingerprint(value) for value in non_null}
    numeric_values = [number for value in non_null if (number := _numeric(value)) is not None]
    dates = [parsed for value in non_null if (parsed := _date(value)) is not None]
    denom = len(non_null)
    numeric_min = numeric_max = None
    if numeric_values:
        numeric_min = float(min(numeric_values))
        numeric_max = float(max(numeric_values))
        if not math.isfinite(numeric_min) or not math.isfinite(numeric_max):
            numeric_min = numeric_max = None
    normalized_dates = [item.isoformat() for item in dates]
    has_email = any(
        isinstance(value, str) and re.search(r"(?i)\b[^\s@]+@[^\s@]+\.[^\s@]+\b", value)
        for value in non_null
    )
    has_phone = any(
        isinstance(value, str)
        and _date(value) is None
        and bool(re.fullmatch(r"\+?[-0-9() .]{7,20}", value.strip()))
        for value in non_null
    )
    lifecycle_matches = sum(
        1 for value in non_null
        if isinstance(value, str) and value.strip().casefold() in _LIFECYCLE_VALUES
    )
    return ColumnProfile(
        sample_count=sample_count,
        null_count=sample_count - denom,
        null_ratio=(sample_count - denom) / sample_count if sample_count else 0.0,
        distinct_count=len(distinct),
        distinct_ratio=len(distinct) / denom if denom else 0.0,
        numeric_parse_rate=len(numeric_values) / denom if denom else 0.0,
        date_parse_rate=len(dates) / denom if denom else 0.0,
        numeric_min=numeric_min,
        numeric_max=numeric_max,
        date_min=min(normalized_dates) if normalized_dates else None,
        date_max=max(normalized_dates) if normalized_dates else None,
        contains_email_like=has_email,
        contains_phone_like=has_phone,
        max_text_length=max((len(value) for value in non_null if isinstance(value, str)), default=0),
        lifecycle_value_ratio=lifecycle_matches / denom if denom else 0.0,
    )


def profile_catalog(
    connection: Connection,
    catalog: Catalog,
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    max_columns_per_table: int = MAX_COLUMNS_PER_TABLE,
    deadline: float | None = None,
) -> ProfileSet:
    """Read at most sample_size + 1 rows per table and emit only aggregate statistics."""
    if sample_size < 1 or max_columns_per_table < 1:
        raise ValueError("sample_size and max_columns_per_table must be positive")
    metadata = MetaData()
    table_profiles: dict[str, TableProfile] = {}
    warnings: list[str] = []
    for table_info in catalog.tables:
        if deadline is not None and time.monotonic() >= deadline:
            table_profiles[table_info.name] = TableProfile(0, False, {}, profile_error=True, budget_exceeded=True)
            warnings.append("Insights profiling time budget reached")
            continue
        selected_columns = table_info.columns[:max_columns_per_table]
        if len(table_info.columns) > max_columns_per_table:
            warnings.append("Column profile limit reached")
        if not selected_columns:
            table_profiles[table_info.name] = TableProfile(0, False, {})
            continue
        try:
            with sqlite_deadline(connection, deadline) as timed_out:
                reflected = SATable(
                    table_info.name, metadata, schema=catalog.schema,
                    autoload_with=connection,
                )
                columns = [reflected.c[column.name] for column in selected_columns]
                statement = select(*columns).limit(sample_size + 1)
                fetched = connection.execute(statement).fetchmany(sample_size + 1)
                truncated = len(fetched) > sample_size
                sampled = fetched[:sample_size]
                by_column = {
                    column.name: _profile_values([row[index] for row in sampled])
                    for index, column in enumerate(selected_columns)
                }
                table_profiles[table_info.name] = TableProfile(
                    sampled_rows=len(sampled), sample_truncated=truncated, columns=by_column,
                )
                if truncated:
                    warnings.append("Row sample limit reached")
                if timed_out():
                    table_profiles[table_info.name] = TableProfile(
                        0, False, {}, profile_error=True, budget_exceeded=True,
                    )
                    warnings.append("Insights profiling time budget reached")
        except Exception:
            # Driver exceptions may contain SQL, sampled data, or host details; omit them from logs.
            table_profiles[table_info.name] = TableProfile(
                0, False, {}, profile_error=True,
                budget_exceeded=deadline is not None and time.monotonic() >= deadline,
            )
            warnings.append(
                "Insights profiling time budget reached"
                if deadline is not None and time.monotonic() >= deadline
                else "A table profile could not be completed"
            )
    return ProfileSet(catalog.version, sample_size, table_profiles, tuple(dict.fromkeys(warnings)))
