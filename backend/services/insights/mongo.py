"""Bounded MongoDB catalog, profiling, planning, compilation, and safe execution."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable


logger = logging.getLogger(__name__)
DEFAULT_MAX_COLLECTIONS = 100
DEFAULT_SAMPLE_SIZE = 1_000
DEFAULT_MAX_DEPTH = 5
MONGO_PROFILE_VERSION = "1"
MAX_ARRAY_UNWIND_DEPTH = 1
_PII_PATH = re.compile(
    r"(^|\.)(email|e_mail|phone|mobile|ssn|password|passwd|token|secret|"
    r"address|name|[^.]*_name|dob|birth_date)(\.|$)",
    re.IGNORECASE,
)
_ID_PATH = re.compile(r"(^|\.)(_?id|key|uuid|guid|ref)(\[\])?$", re.IGNORECASE)
_STATUS_VALUES = {
    "paid", "unpaid", "pending", "processing", "shipped", "delivered", "completed",
    "complete", "cancelled", "canceled", "returned", "refunded", "failed", "open", "closed",
}
_REVENUE_TERMS = {"amount", "revenue", "sales", "sale", "subtotal", "gross", "net"}
_NON_REVENUE_TERMS = {"salary", "payroll", "cost", "fee", "balance", "expense", "debt"}
_NON_ADDITIVE_TERMS = {"rate", "ratio", "percent", "percentage", "pct", "quantity", "qty", "unit_price"}


@dataclass(frozen=True)
class MongoFieldProfile:
    path: str
    bson_types: tuple[str, ...]
    sample_count: int
    null_count: int
    distinct_count: int
    numeric_parse_rate: float
    date_parse_rate: float
    pii: bool
    heterogeneous: bool
    lifecycle_value_ratio: float = 0.0


@dataclass(frozen=True)
class MongoCollectionCatalog:
    name: str
    sample_count: int
    sample_truncated: bool
    fields: dict[str, MongoFieldProfile]


@dataclass(frozen=True)
class MongoCatalog:
    database_name: str | None
    collections: tuple[MongoCollectionCatalog, ...]
    version: str
    truncated: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class MongoMetricSpec:
    id: str
    kind: str
    collection: str
    measure: str | None = None
    date_path: str | None = None
    dimension: str | None = None
    status: str = "available"
    reason: str | None = None
    date_types: tuple[str, ...] = ()
    status_path: str | None = None
    status_values: tuple[str, ...] = ()
    semantic: str = "neutral"
    aggregation_kind: str = "sum"


@dataclass(frozen=True)
class MongoPlan:
    plan_hash: str
    metrics: tuple[MongoMetricSpec, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class MongoMetricResult:
    metric_id: str
    status: str
    reason: str | None
    value: Any = None


def _bson_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float, Decimal)):
        return "number"
    if isinstance(value, dt.datetime):
        return "datetime"
    if isinstance(value, dt.date):
        return "date"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "document"
    if isinstance(value, (list, tuple)):
        return "array"
    return "other"


def _walk(document: Any, prefix: str = "", depth: int = 0, max_depth: int = DEFAULT_MAX_DEPTH):
    if depth > max_depth:
        return
    if isinstance(document, dict):
        for key, value in document.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                yield from _walk(value, path, depth + 1, max_depth)
            elif isinstance(value, (list, tuple)):
                array_path = f"{path}[]"
                for item in value:
                    if isinstance(item, dict):
                        yield from _walk(item, array_path, depth + 1, max_depth)
                    elif isinstance(item, (list, tuple)):
                        continue
                    else:
                        yield array_path, item
            else:
                yield path, value


def _fingerprint(value: Any) -> str:
    try:
        encoded = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except (TypeError, ValueError):
        encoded = type(value).__name__
    return hashlib.sha256(encoded.encode("utf-8", errors="replace")).hexdigest()


def _numeric(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        parsed = Decimal(str(value))
        return parsed.is_finite()
    except (InvalidOperation, TypeError, ValueError):
        return False


def _date(value: Any) -> bool:
    if isinstance(value, (dt.date, dt.datetime)):
        return True
    if not isinstance(value, str):
        return False
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        try:
            dt.date.fromisoformat(value)
            return True
        except ValueError:
            return False


def _field_profile(path: str, values: list[Any]) -> MongoFieldProfile:
    non_null = [value for value in values if value is not None]
    types = {_bson_type(value) for value in non_null}
    numeric_ratio = sum(_numeric(value) for value in non_null) / len(non_null) if non_null else 0.0
    date_ratio = sum(_date(value) for value in non_null) / len(non_null) if non_null else 0.0
    pii = bool(_PII_PATH.search(path)) or any(
        isinstance(value, str)
        and (
            bool(re.search(r"(?i)\b[^\s@]+@[^\s@]+\.[^\s@]+\b", value))
            or (
                not _date(value)
                and bool(re.fullmatch(r"\+?[-0-9() .]{7,20}", value.strip()))
            )
        )
        for value in non_null
    )
    lifecycle_matches = sum(
        isinstance(value, str) and value.strip().casefold() in _STATUS_VALUES
        for value in non_null
    )
    return MongoFieldProfile(
        path=path,
        bson_types=tuple(sorted(types)),
        sample_count=len(values),
        null_count=len(values) - len(non_null),
        distinct_count=len({_fingerprint(value) for value in non_null}),
        numeric_parse_rate=numeric_ratio,
        date_parse_rate=date_ratio,
        pii=pii,
        heterogeneous=len(types) > 1,
        lifecycle_value_ratio=lifecycle_matches / len(non_null) if non_null else 0.0,
    )


def discover_mongo_catalog(
    database: Any,
    *,
    max_collections: int = DEFAULT_MAX_COLLECTIONS,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    max_depth: int = DEFAULT_MAX_DEPTH,
    deadline: float | None = None,
) -> MongoCatalog:
    """Inspect sorted collection names and bounded samples; return no document values."""
    if min(max_collections, sample_size) < 1 or max_depth < 1:
        raise ValueError("Mongo catalog limits must be positive")
    names = sorted((str(name) for name in database.list_collection_names()), key=lambda v: (v.casefold(), v))
    truncated = len(names) > max_collections
    warnings: list[str] = ["Mongo collection limit reached"] if truncated else []
    result: list[MongoCollectionCatalog] = []
    for name in names[:max_collections]:
        if deadline is not None and time.monotonic() >= deadline:
            warnings.append("Mongo profiling time budget reached")
            truncated = True
            break
        try:
            cursor = database[name].find({}, {})
            if deadline is not None and hasattr(cursor, "max_time_ms"):
                remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
                cursor = cursor.max_time_ms(remaining_ms)
            cursor = cursor.limit(sample_size + 1)
            sampled_docs = list(cursor)
        except Exception:
            logger.warning("Mongo collection sample failed")
            warnings.append("A Mongo collection could not be profiled")
            result.append(MongoCollectionCatalog(name, 0, False, {}))
            continue
        sample_truncated = len(sampled_docs) > sample_size
        sampled_docs = sampled_docs[:sample_size]
        paths: dict[str, list[Any]] = {}
        for document in sampled_docs:
            for path, value in _walk(document, max_depth=max_depth):
                paths.setdefault(path, []).append(value)
        fields = {path: _field_profile(path, values) for path, values in sorted(paths.items())}
        if sample_truncated:
            warnings.append("Mongo row sample limit reached")
        if any(field.heterogeneous for field in fields.values()):
            warnings.append("Mongo fields with mixed sampled types were found")
        result.append(MongoCollectionCatalog(name, len(sampled_docs), sample_truncated, fields))
    database_name = getattr(database, "name", None)
    structural = [
        (collection.name, tuple(
            (path, field.bson_types, field.heterogeneous, field.pii)
            for path, field in sorted(collection.fields.items())
        ))
        for collection in result
    ]
    version = hashlib.sha256(json.dumps(structural, sort_keys=True, default=str).encode()).hexdigest()
    return MongoCatalog(database_name, tuple(result), version, truncated, tuple(dict.fromkeys(warnings)))


def build_mongo_plan(catalog: MongoCatalog) -> MongoPlan:
    metrics: list[MongoMetricSpec] = []
    warnings = list(catalog.warnings)
    for collection in catalog.collections:
        if any(
            not field.pii and field.numeric_parse_rate >= 0.80 and field.heterogeneous
            for field in collection.fields.values()
        ):
            warnings.append("A mixed-type Mongo field was omitted from numeric metrics")
        numeric_fields = [
            field for field in collection.fields.values()
            if not field.pii and not _ID_PATH.search(field.path)
            and field.numeric_parse_rate >= 0.80 and not field.heterogeneous
            and not (
                field.sample_count >= 5 and field.distinct_count / max(1, field.sample_count) >= 0.98
            )
        ]
        date_fields = [
            field for field in collection.fields.values()
            if not field.pii and field.date_parse_rate >= 0.80
        ]
        metrics.append(MongoMetricSpec(
            f"document_count_{collection.name}", "count", collection.name,
            date_path=date_fields[0].path if len(date_fields) == 1 else None,
            date_types=date_fields[0].bson_types if len(date_fields) == 1 else (),
        ))
        status_fields = [
            field for field in collection.fields.values()
            if not field.pii and (
                field.lifecycle_value_ratio >= 0.80
                or field.path.rsplit(".", 1)[-1].casefold() == "status"
            )
        ]
        categorical_fields = [
            field for field in collection.fields.values()
            if not field.pii and field.sample_count > 0
            and set(field.bson_types).issubset({"string"})
            and not _ID_PATH.search(field.path)
            and field.distinct_count <= 50
            and (field.distinct_count <= 5 if field.sample_count < 20 else field.distinct_count / field.sample_count <= 0.05)
        ]
        for field in numeric_fields[:10]:
            date_field = date_fields[0] if len(date_fields) == 1 else None
            field_tokens = set(re.split(r"[^a-z0-9]+", field.path.rsplit(".", 1)[-1].casefold()))
            additive = not bool(field_tokens & _NON_ADDITIVE_TERMS) and "price" not in field_tokens
            if additive:
                metrics.append(MongoMetricSpec(
                    f"sum_{collection.name}_{field.path}", "sum", collection.name,
                    field.path, date_path=date_field.path if date_field else None,
                    date_types=date_field.bson_types if date_field else (),
                ))
            metrics.append(MongoMetricSpec(
                f"avg_{collection.name}_{field.path}", "avg", collection.name,
                field.path, date_path=date_field.path if date_field else None,
                date_types=date_field.bson_types if date_field else (),
            ))
            if date_field:
                metrics.append(MongoMetricSpec(
                    f"trend_{collection.name}_{field.path}", "trend", collection.name,
                    field.path, date_path=date_field.path, date_types=date_field.bson_types,
                    aggregation_kind="sum" if additive else "avg",
                ))
            for dimension in categorical_fields[:3]:
                metrics.append(MongoMetricSpec(
                    f"breakdown_{collection.name}_{dimension.path}_{field.path}", "breakdown",
                    collection.name, field.path, dimension=dimension.path,
                    date_path=date_field.path if date_field else None,
                    date_types=date_field.bson_types if date_field else (),
                    aggregation_kind="sum" if additive else "avg",
                ))
        date_field = date_fields[0] if len(date_fields) == 1 else None
        identifier_evidence = any(
            _ID_PATH.search(field.path) or (
                field.sample_count >= 5
                and field.distinct_count / max(1, field.sample_count) >= 0.98
            )
            for field in collection.fields.values() if not field.pii
        )
        transaction_like = bool(date_field and (identifier_evidence or status_fields))
        revenue_candidates = [
            field for field in numeric_fields
            if _REVENUE_TERMS.intersection(
                re.split(r"[^a-z0-9]+", field.path.rsplit(".", 1)[-1].casefold())
            ) and not _NON_REVENUE_TERMS.intersection(
                re.split(r"[^a-z0-9]+", field.path.rsplit(".", 1)[-1].casefold())
            )
        ]
        if transaction_like and revenue_candidates:
            measure = revenue_candidates[0]
            metrics.append(MongoMetricSpec(
                "revenue_total", "sum", collection.name, measure.path,
                date_path=date_field.path, date_types=date_field.bson_types, semantic="revenue",
            ))
            if status_fields:
                status_field = status_fields[0]
                metrics.append(MongoMetricSpec(
                    "net_revenue", "sum", collection.name, measure.path,
                    date_path=date_field.path, date_types=date_field.bson_types,
                    status_path=status_field.path,
                    status_values=("complete", "completed", "delivered", "shipped", "success", "closed"),
                    semantic="net_revenue",
                ))
            else:
                metrics.append(MongoMetricSpec(
                    "net_revenue", "sum", collection.name, measure.path,
                    date_path=date_field.path, date_types=date_field.bson_types,
                    status="unavailable", reason="missing_role", semantic="net_revenue",
                ))
        else:
            metrics.append(MongoMetricSpec(
                "revenue_total", "sum", collection.name, status="unavailable",
                reason="missing_role", semantic="revenue",
            ))
            metrics.append(MongoMetricSpec(
                "net_revenue", "sum", collection.name, status="unavailable",
                reason="missing_role", semantic="net_revenue",
            ))
    if not catalog.collections:
        metrics.extend((
            MongoMetricSpec(
                "document_count_all", "count", "", status="unavailable",
                reason="missing_table",
            ),
            MongoMetricSpec(
                "revenue_total", "sum", "", status="unavailable",
                reason="missing_table", semantic="revenue",
            ),
            MongoMetricSpec(
                "net_revenue", "sum", "", status="unavailable",
                reason="missing_table", semantic="net_revenue",
            ),
        ))
    payload = [
        (metric.id, metric.kind, metric.collection, metric.measure, metric.date_path,
         metric.dimension, metric.status_path, metric.status_values, metric.status,
         metric.reason, metric.semantic, metric.aggregation_kind)
        for metric in metrics
    ]
    plan_hash = hashlib.sha256(
        json.dumps((catalog.version, payload), sort_keys=True, default=str).encode()
    ).hexdigest()
    return MongoPlan(plan_hash, tuple(metrics), tuple(dict.fromkeys(warnings)))


def _date_filter(
    date_from: str | None, date_to_excl: str | None, path: str | None,
    bson_types: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    if not date_from and not date_to_excl:
        return None
    if not path:
        return None
    normalized_path = path.replace("[]", "")
    condition: dict[str, Any] = {"$ne": None}
    if bson_types and set(bson_types) == {"string"}:
        if date_from:
            condition["$gte"] = date_from
        if date_to_excl:
            condition["$lt"] = date_to_excl
        return {normalized_path: condition}
    if "string" in bson_types and any(item in {"date", "datetime"} for item in bson_types):
        converted = {
            "$convert": {
                "input": f"${normalized_path}", "to": "date",
                "onError": None, "onNull": None,
            }
        }
        comparisons: list[dict[str, Any]] = []
        if date_from:
            start = dt.datetime.combine(dt.date.fromisoformat(date_from), dt.time.min)
            comparisons.append({"$gte": [converted, start]})
        if date_to_excl:
            end = dt.datetime.combine(dt.date.fromisoformat(date_to_excl), dt.time.min)
            comparisons.append({"$lt": [converted, end]})
        return {"$expr": {"$and": comparisons}}
    if date_from:
        condition["$gte"] = dt.datetime.combine(dt.date.fromisoformat(date_from), dt.time.min)
    if date_to_excl:
        condition["$lt"] = dt.datetime.combine(dt.date.fromisoformat(date_to_excl), dt.time.min)
    return {normalized_path: condition}


def compile_mongo_metric(
    metric: MongoMetricSpec,
    *,
    date_from: str | None = None,
    date_to_excl: str | None = None,
    filter_path: str | None = None,
    filter_value: Any = None,
    sample_limit: int = 10_000,
    max_time_ms: int = 5_000,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None, str, str | None]:
    """Compile a Mongo operation; filter dates before aggregation, never fall back unfiltered."""
    if metric.status != "available":
        return None, None, metric.status, metric.reason
    if sample_limit < 1:
        raise ValueError("sample_limit must be positive")
    try:
        parsed_from = dt.date.fromisoformat(date_from) if date_from else None
        parsed_to = dt.date.fromisoformat(date_to_excl) if date_to_excl else None
        if (date_from and parsed_from.isoformat() != date_from) or (
            date_to_excl and parsed_to.isoformat() != date_to_excl
        ) or (parsed_from and parsed_to and parsed_from >= parsed_to):
            raise ValueError("Invalid date bounds")
    except (TypeError, ValueError):
        return None, None, "error", "invalid_date"
    date_filter = _date_filter(date_from, date_to_excl, metric.date_path, metric.date_types)
    if (date_from or date_to_excl) and date_filter is None:
        return None, None, "unavailable", "missing_role"
    array_paths = [
        path for path in (metric.measure, metric.date_path, metric.dimension, metric.status_path)
        if path and "[]" in path
    ]
    if any(path.count("[]") > 1 for path in array_paths):
        return None, None, "unavailable", "unsupported_array_depth"
    array_roots = {path.split("[]", 1)[0] for path in array_paths}
    if len(array_roots) > 1:
        return None, None, "unavailable", "unsupported_array_shape"
    pipeline: list[dict[str, Any]] = []
    if array_paths:
        unwind_path = array_paths[0].split("[]", 1)[0]
        pipeline.append({"$unwind": f"${unwind_path}"})
    predicates = [date_filter] if date_filter else []
    if filter_path:
        predicates.append({filter_path.replace("[]", ""): filter_value})
    if metric.status_path and metric.status_values:
        status_path = metric.status_path.replace("[]", "")
        normalized_status = {
            "$toLower": {
                "$convert": {
                    "input": f"${status_path}", "to": "string",
                    "onError": "", "onNull": "",
                }
            }
        }
        predicates.append({"$expr": {"$in": [normalized_status, [value.casefold() for value in metric.status_values]]}})
    match = (
        predicates[0] if len(predicates) == 1
        else {"$and": predicates} if predicates else {}
    )
    if metric.kind == "count":
        if array_paths:
            return None, None, "unavailable", "unsupported_array_shape"
        if metric.status_path:
            return {}, [{"$match": match}, {"$count": "value"}], "available", None
        return match, None, "available", None
    if predicates:
        pipeline.append({"$match": match})
    if not metric.measure:
        return None, None, "unavailable", "missing_role"
    measure = "$" + metric.measure.replace("[]", "")
    group: dict[str, Any] = {"_id": None}
    if metric.kind == "sum":
        group["value"] = {"$sum": {"$cond": [{"$isNumber": measure}, measure, None]}}
    elif metric.kind == "avg":
        group["value"] = {"$avg": {"$cond": [{"$isNumber": measure}, measure, None]}}
    elif metric.kind == "trend":
        date_path = metric.date_path.replace("[]", "") if metric.date_path else ""
        group["_id"] = {
            "$dateToString": {
                "format": "%Y-%m",
                "date": {"$convert": {
                    "input": "$" + date_path, "to": "date",
                    "onError": None, "onNull": None,
                }},
            }
        }
        group["value"] = {
            "$avg" if metric.aggregation_kind == "avg" else "$sum":
            {"$cond": [{"$isNumber": measure}, measure, None]}
        }
    elif metric.kind == "breakdown":
        dimension = metric.dimension.replace("[]", "") if metric.dimension else ""
        group["_id"] = "$" + dimension
        group["value"] = {
            "$avg" if metric.aggregation_kind == "avg" else "$sum":
            {"$cond": [{"$isNumber": measure}, measure, None]}
        }
    else:
        return None, None, "unavailable", "unsupported_metric"
    pipeline.append({"$group": group})
    pipeline.append({"$limit": sample_limit})
    return date_filter or {}, pipeline, "available", None


def execute_mongo_metric(
    collection: Any,
    metric: MongoMetricSpec,
    *,
    date_from: str | None = None,
    date_to_excl: str | None = None,
    filter_path: str | None = None,
    filter_value: Any = None,
    sample_limit: int = 10_000,
    deadline: float | None = None,
) -> MongoMetricResult:
    if deadline is not None and time.monotonic() >= deadline:
        return MongoMetricResult(metric.id, "unavailable", "budget_exceeded")
    remaining_ms = (
        max(1, min(5_000, int((deadline - time.monotonic()) * 1000)))
        if deadline is not None else 5_000
    )
    query, pipeline, status, reason = compile_mongo_metric(
        metric, date_from=date_from, date_to_excl=date_to_excl,
        filter_path=filter_path, filter_value=filter_value,
        sample_limit=sample_limit, max_time_ms=remaining_ms,
    )
    if status != "available":
        return MongoMetricResult(metric.id, status, reason)
    try:
        if metric.kind == "count":
            if pipeline is not None:
                rows = list(collection.aggregate(pipeline, maxTimeMS=remaining_ms))
                value = int(rows[0].get("value", 0)) if rows else 0
            else:
                value = collection.count_documents(query or {}, maxTimeMS=remaining_ms)
            return MongoMetricResult(metric.id, "zero" if value == 0 else "available", None, value)
        rows = list(collection.aggregate(pipeline or [], maxTimeMS=remaining_ms))
        if not rows or all(row.get("value") is None for row in rows):
            return MongoMetricResult(metric.id, "unavailable", "no_rows", [])
        values = [
            {"category": row.get("_id"), "value": row.get("value")}
            for row in rows
        ]
        if metric.kind in {"sum", "avg"} and len(values) == 1:
            return MongoMetricResult(metric.id, "zero" if values[0]["value"] == 0 else "available", None, values[0]["value"])
        return MongoMetricResult(metric.id, "available", None, values)
    except Exception:
        logger.warning("Mongo insights aggregation failed")
        if deadline is not None and time.monotonic() >= deadline:
            return MongoMetricResult(metric.id, "unavailable", "budget_exceeded")
        return MongoMetricResult(metric.id, "error", "query_failed")
