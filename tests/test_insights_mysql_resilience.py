"""Offline tests for externally managed MySQL catalog compatibility."""

import logging

from sqlalchemy.exc import SQLAlchemyError

from services import db_pipeline_service as pipeline
from services import sql_engine


class _CatalogWithUnavailableTable:
    def get_table_names(self):
        return ["available_table", "unavailable_table"]

    def get_columns(self, table_name):
        if table_name == "unavailable_table":
            raise SQLAlchemyError("synthetic unavailable storage engine")
        return [{"name": "id", "type": "INTEGER"}, {"name": "label", "type": "TEXT"}]


def test_schema_discovery_skips_only_inaccessible_catalog_entries(caplog):
    """A single unavailable table cannot discard the rest of a MySQL catalog."""
    with caplog.at_level(logging.WARNING, logger=pipeline.__name__):
        schema, skipped = pipeline._inspect_accessible_sql_schema(_CatalogWithUnavailableTable())

    assert list(schema) == ["available_table"]
    assert schema["available_table"]["columns"] == {"id": "INTEGER", "label": "TEXT"}
    assert skipped == ["unavailable_table"]
    assert "Skipped 1 inaccessible table(s) during schema discovery" in caplog.text
    assert "synthetic unavailable storage engine" not in caplog.text


class _TimeoutUnsupportedConnection:
    def __init__(self):
        self.info = {}
        self.attempts = 0

    def execute(self, _statement):
        self.attempts += 1
        raise SQLAlchemyError("synthetic unsupported timeout setting")


def test_mysql_timeout_capability_is_logged_once_per_pooled_connection(caplog):
    """Optional timeout failure is remembered while the watchdog remains available."""
    connection = _TimeoutUnsupportedConnection()

    with caplog.at_level(logging.DEBUG, logger="dataspeak.sql_engine"):
        sql_engine._apply_optional_mysql_statement_timeout(connection)
        sql_engine._apply_optional_mysql_statement_timeout(connection)

    assert connection.attempts == 1
    assert connection.info["dataspeak_mysql_statement_timeout_unsupported"] is True
    assert caplog.text.count("MySQL statement timeout is unavailable") == 1
