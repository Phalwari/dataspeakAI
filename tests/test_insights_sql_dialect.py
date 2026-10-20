"""Offline dialect SQL-generation and temporary SQLite execution checks."""

import sqlite3

import pytest

from services.sql_dialect import (
    UnsupportedDialectError, cast_text, concat, month_bucket, quote_ident,
    round_money,
)
from services.db_pipeline_service import _clean_sql_identifier


@pytest.mark.parametrize("dialect,expected", [
    ("sqlite", "strftime('%Y-%m', created_on)"),
    ("postgresql", "to_char(created_on, 'YYYY-MM')"),
    ("mysql", "DATE_FORMAT(created_on, '%Y-%m')"),
    ("mariadb", "DATE_FORMAT(created_on, '%Y-%m')"),
])
def test_month_bucket_strings(dialect, expected):
    assert month_bucket("created_on", dialect) == expected


@pytest.mark.parametrize("dialect,joiner,cast_target,round_expr,identifier", [
    ("sqlite", "first || ' ' || last", "CAST(id AS TEXT)", "ROUND(SUM(amount), 2)", '"order items"'),
    ("postgresql", "first || ' ' || last", "CAST(id AS TEXT)", "ROUND(CAST(SUM(amount) AS NUMERIC), 2)", '"order items"'),
    ("mysql", "CONCAT(first, ' ', last)", "CAST(id AS CHAR)", "ROUND(SUM(amount), 2)", "`order items`"),
    ("mariadb", "CONCAT(first, ' ', last)", "CAST(id AS CHAR)", "ROUND(SUM(amount), 2)", "`order items`"),
])
def test_other_dialect_fragments(dialect, joiner, cast_target, round_expr, identifier):
    assert concat(["first", "' '", "last"], dialect) == joiner
    assert cast_text("id", dialect) == cast_target
    assert round_money("SUM(amount)", dialect) == round_expr
    assert quote_ident("order items", dialect) == identifier


@pytest.mark.parametrize("helper,args", [
    (month_bucket, ("created_on",)),
    (concat, (["first", "last"],)),
    (cast_text, ("id",)),
    (round_money, ("SUM(amount)",)),
    (quote_ident, ("orders",)),
])
def test_unknown_dialect_fails_closed(helper, args):
    with pytest.raises(UnsupportedDialectError):
        helper(*args, "unknown")


def test_pipeline_identifier_quoting_has_no_mysql_fallback():
    assert _clean_sql_identifier("order items", "sqlite") == '"order items"'
    assert _clean_sql_identifier("order items", "mysql") == "`order items`"
    with pytest.raises(UnsupportedDialectError):
        _clean_sql_identifier("order items", "unknown")


def test_sqlite_fragments_execute_on_temporary_database(tmp_path):
    database_path = tmp_path / "dialect.sqlite"
    with sqlite3.connect(database_path) as conn:
        conn.execute('CREATE TABLE "order items" (id INTEGER, first TEXT, last TEXT, amount REAL, created_on TEXT)')
        conn.execute('INSERT INTO "order items" VALUES (1, ?, ?, 12.345, ?)', ("Sample", "Buyer", "2026-01-02"))
        name_expr = concat(["first", "' '", "last"], "sqlite")
        query = (
            f"SELECT {month_bucket('created_on', 'sqlite')}, "
            f"{name_expr}, "
            f"{cast_text('id', 'sqlite')}, "
            f"{round_money('SUM(amount)', 'sqlite')} "
            f"FROM {quote_ident('order items', 'sqlite')}"
        )
        result = conn.execute(query).fetchone()
    assert result == ("2026-01", "Sample Buyer", "1", 12.35)
