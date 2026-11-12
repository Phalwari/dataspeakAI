"""Deterministic column roles with confidence and explainable, value-free evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from services.insights.catalog import Column
from services.insights.profiling import ColumnProfile


ROLE_RULES_VERSION = "1"
_PII_NAME = re.compile(
    r"(^|_)(email|e_mail|phone|mobile|ssn|password|passwd|token|secret|"
    r"address|first_name|last_name|full_name|customer_name|person_name|dob|birth_date)(_|$)",
    re.IGNORECASE,
)
_RATE_NAME = re.compile(r"(^|_)(rate|ratio|percent|percentage|pct)(_|$)", re.IGNORECASE)
_DATE_NAME = re.compile(r"(^|_)(date|time|timestamp|created|updated|period)(_|$)", re.IGNORECASE)
_ID_NAME = re.compile(r"(^|_)(id|key|uuid|guid|ref)(_|$)", re.IGNORECASE)
_PRICE_NAME = re.compile(r"(^|_)(unit_price|price_per|price)(_|$)", re.IGNORECASE)
_QUANTITY_NAME = re.compile(r"(^|_)(qty|quantity|units)(_|$)", re.IGNORECASE)
_NON_REVENUE_MONEY = {"salary", "payroll", "cost", "fee", "balance", "expense", "debt"}
_MONEY_TERMS = {
    "amount", "revenue", "sales", "sale", "price", "subtotal", "gross", "net",
    "salary", "payroll", "cost", "fee", "balance", "expense", "debt", "total",
}
_REVENUE_TERMS = {"revenue", "sales", "sale", "amount", "subtotal", "gross", "net"}
@dataclass(frozen=True)
class ColumnRole:
    role: str
    confidence: float
    evidence: tuple[str, ...]
    measure_kind: str | None = None
    revenue_candidate: bool = False


def _tokens(name: str) -> set[str]:
    return {part for part in re.split(r"[^a-z0-9]+", name.casefold()) if part}


def _numeric_type(declared_type: str) -> bool:
    normalized = declared_type.casefold()
    return any(token in normalized for token in ("int", "numeric", "decimal", "number", "real", "float", "double"))


def _integer_type(declared_type: str) -> bool:
    return bool(re.search(
        r"\b(smallint|integer|int|bigint|tinyint|serial|bigserial)\b",
        declared_type.casefold(),
    ))


def _text_type(declared_type: str) -> bool:
    normalized = declared_type.casefold()
    return any(token in normalized for token in ("char", "text", "string", "clob", "enum"))


def classify_column(
    column: Column,
    profile: ColumnProfile,
    *,
    is_foreign_key: bool = False,
) -> ColumnRole:
    name = column.name.casefold()
    tokens = _tokens(name)
    declared = column.declared_type.casefold()
    if _PII_NAME.search(name) or profile.contains_email_like or profile.contains_phone_like:
        return ColumnRole("pii", 0.99, ("sensitive name or sampled value shape",))
    if any(token in declared for token in ("blob", "binary", "bytea", "large object")):
        return ColumnRole("excluded", 0.99, ("non-analytical binary type",))

    if column.primary_key_position or is_foreign_key:
        key_kind = "primary-key metadata" if column.primary_key_position else "foreign-key metadata"
        return ColumnRole("identifier", 0.99, (key_kind,))

    if _RATE_NAME.search(name):
        return ColumnRole("rate", 0.93, ("rate token", "non-additive role"), measure_kind="rate")

    if _DATE_NAME.search(name) and ("date" in declared or "time" in declared or profile.date_parse_rate >= 0.8):
        return ColumnRole("date", 0.90, ("date/time token", "date values parse successfully"))
    if "date" in declared or "time" in declared:
        return ColumnRole("date", 0.95, ("declared date/time type",))
    if profile.date_parse_rate >= 0.8 and profile.sample_count > 0:
        return ColumnRole("date", 0.82, ("sampled values are consistently date-parseable",))

    if _PRICE_NAME.search(name) and profile.numeric_parse_rate >= 0.8:
        return ColumnRole("unit_price", 0.91, ("numeric values", "unit-price token"), measure_kind="money")
    if _QUANTITY_NAME.search(name) and profile.numeric_parse_rate >= 0.8:
        return ColumnRole("quantity", 0.91, ("numeric values", "quantity token"), measure_kind="count")

    if _numeric_type(column.declared_type) and profile.numeric_parse_rate >= 0.8:
        money_terms = tokens & _MONEY_TERMS
        if money_terms:
            count_like = bool(tokens & {"order", "orders", "count", "quantity", "units"}) and not bool(
                tokens & (_REVENUE_TERMS | {"amount", "price", "subtotal", "gross", "net"})
            )
            revenue_signal = bool(tokens & _REVENUE_TERMS) and not bool(tokens & _NON_REVENUE_MONEY)
            return ColumnRole(
                "additive_measure", 0.84,
                ("numeric declared type", "additive name evidence"),
                measure_kind="count" if count_like else "money",
                revenue_candidate=revenue_signal,
            )

    if (
        _ID_NAME.search(name) and _integer_type(column.declared_type)
        and profile.distinct_count > 0
    ):
        confidence = 0.85 if profile.distinct_ratio >= 0.20 else 0.75
        return ColumnRole(
            "identifier", confidence,
            ("key/reference-like token", "integer type", "sample cardinality evidence"),
        )
    if (
        _integer_type(column.declared_type)
        and profile.numeric_parse_rate >= 0.8
        and profile.distinct_ratio >= 0.98
        and profile.sample_count >= 5
    ):
        return ColumnRole("identifier", 0.82, ("high distinct ratio", "numeric type"))

    if _text_type(column.declared_type) and profile.sample_count:
        if profile.max_text_length > 256:
            return ColumnRole("free_text", 0.85, ("long text value",))

    if (
        _text_type(column.declared_type)
        and profile.distinct_count > 0 and profile.distinct_count <= 50
        and profile.lifecycle_value_ratio >= 0.80
    ):
        return ColumnRole("status", 0.88, ("sample matches configured lifecycle values", "low sampled cardinality"))
    if "status" in tokens and _text_type(column.declared_type):
        return ColumnRole("status", 0.80, ("configured status column name",))

    if _text_type(column.declared_type) and profile.sample_count:
        small_sample_category = profile.sample_count < 20 and profile.distinct_count <= 5
        sampled_category = profile.distinct_count <= 50 and profile.distinct_ratio <= 0.05
        if small_sample_category or sampled_category:
            return ColumnRole("categorical", 0.86, ("low sampled cardinality", "text type"))

    if _text_type(column.declared_type) and profile.sample_count:
        return ColumnRole("free_text", 0.72, ("text type without confident dimension evidence",))
    if profile.sample_count == 0 and column.nullable:
        return ColumnRole("unknown", 0.0, ("no non-null sample evidence",))
    return ColumnRole("unknown", 0.0, ("insufficient role evidence",))


def classify_table_roles(
    columns: tuple[Column, ...], profiles: dict[str, ColumnProfile], foreign_key_columns: set[str] | None = None,
) -> dict[str, ColumnRole]:
    foreign_key_columns = foreign_key_columns or set()
    return {
        column.name: classify_column(
            column, profiles.get(column.name, ColumnProfile(0, 0, 0, 0, 0, 0, 0)),
            is_foreign_key=column.name in foreign_key_columns,
        )
        for column in columns
    }
