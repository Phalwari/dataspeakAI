"""SQL fragments for the dialects supported by the Insights query planner."""

from __future__ import annotations

from typing import Sequence


class UnsupportedDialectError(ValueError):
    """Raised before producing SQL for an unsupported relational dialect."""


def _dialect(dialect: str) -> str:
    normalized = str(dialect).lower()
    if normalized == "mariadb":
        return "mysql"
    if normalized not in {"sqlite", "postgresql", "mysql"}:
        raise UnsupportedDialectError("Unsupported SQL dialect for insights")
    return normalized


def month_bucket(column: str, dialect: str) -> str:
    kind = _dialect(dialect)
    if kind == "sqlite":
        return f"strftime('%Y-%m', {column})"
    if kind == "postgresql":
        return f"to_char({column}, 'YYYY-MM')"
    return f"DATE_FORMAT({column}, '%Y-%m')"


def concat(parts: Sequence[str], dialect: str) -> str:
    kind = _dialect(dialect)
    if not parts:
        raise ValueError("At least one SQL expression is required")
    if kind == "mysql":
        return f"CONCAT({', '.join(parts)})"
    return " || ".join(parts)


def cast_text(expression: str, dialect: str) -> str:
    kind = _dialect(dialect)
    target = "CHAR" if kind == "mysql" else "TEXT"
    return f"CAST({expression} AS {target})"


def cast_numeric(expression: str, dialect: str) -> str:
    """Cast an aggregate to a portable fractional numeric type for safe division."""
    kind = _dialect(dialect)
    target = "DECIMAL(38, 10)" if kind == "mysql" else "DOUBLE PRECISION" if kind == "postgresql" else "REAL"
    return f"CAST({expression} AS {target})"


def round_money(expression: str, dialect: str) -> str:
    kind = _dialect(dialect)
    if kind == "postgresql":
        return f"ROUND(CAST({expression} AS NUMERIC), 2)"
    return f"ROUND({expression}, 2)"


def quote_ident(name: str, dialect: str) -> str:
    kind = _dialect(dialect)
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ValueError("Invalid SQL identifier")
    quote = "`" if kind == "mysql" else '"'
    return quote + name.replace(quote, quote * 2) + quote
