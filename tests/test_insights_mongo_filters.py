"""Offline Mongo Insights tests with a fake client and no network calls."""

import datetime
import json
import sys
from types import ModuleType

import models
from services import db_pipeline_service as pipeline
from services import db_utils


class FakeCollection:
    def __init__(self, *, fail_count=False):
        self.fail_count = fail_count
        self.count_queries = []
        self.aggregate_pipelines = []
        self.distinct_queries = []
        self.estimated_calls = 0
        self.client_closes = 0

    def count_documents(self, query):
        self.count_queries.append(query)
        if self.fail_count:
            raise RuntimeError("synthetic count failure")
        return 2

    def estimated_document_count(self):
        self.estimated_calls += 1
        return 99

    def aggregate(self, stages):
        self.aggregate_pipelines.append(stages)
        return []

    def distinct(self, field, query=None):
        self.distinct_queries.append((field, query))
        return []

    def find_one(self, *_args, **_kwargs):
        return None


def run_mongo_case(
    isolated_db, monkeypatch, collection, *, with_date=True,
    date_from="2026-01-01", date_to="2026-01-02", fail_lookup=False,
):
    columns = {"amount": "number", "state": "string"}
    if with_date:
        columns["created_on"] = "date"
    tenant = models.Tenant(name="Offline Mongo fixture")
    isolated_db.add(tenant)
    isolated_db.flush()
    connection = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Offline Mongo fixture",
        db_type="mongodb",
        database="offline-fixture",
        connection_string="offline-placeholder",
        tables_metadata={"orders": {"columns": columns, "row_count": 2}},
    )
    isolated_db.add(connection)
    isolated_db.flush()

    class FakeDatabase:
        def __getitem__(self, _collection_name):
            if fail_lookup:
                raise RuntimeError("synthetic collection lookup failure")
            return collection

    class FakeClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def get_default_database(self):
            return FakeDatabase()

        def close(self):
            collection.client_closes += 1

    pymongo_module = ModuleType("pymongo")
    pymongo_module.MongoClient = FakeClient
    monkeypatch.setitem(sys.modules, "pymongo", pymongo_module)
    monkeypatch.setattr(pipeline, "cache_get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pipeline, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pipeline.encryption_service, "decrypt", lambda _value: "offline-placeholder")
    monkeypatch.setattr(
        db_utils, "get_connection_url",
        lambda _connection: (_ for _ in ()).throw(AssertionError("SQL path must not run")),
    )
    monkeypatch.setattr(
        "services.llm_generation_service.generate",
        lambda *_args, **_kwargs: json.dumps({
            "business_domain": "Test data", "executive_summary": "Synthetic summary",
            "strategic_insights": [], "tactical_recommendations": [],
        }),
    )
    return pipeline.DatabasePipelineService().run_db_pipeline(
        db=isolated_db, connection_id=connection.id, tenant_id=tenant.id,
        date_from=date_from, date_to=date_to,
    )


def test_orders_collection_uses_mongo_branch_and_exclusive_calendar_bounds(isolated_db, monkeypatch):
    collection = FakeCollection()
    result = run_mongo_case(isolated_db, monkeypatch, collection)
    expected = {
        "$ne": None,
        "$gte": datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        "$lt": datetime.datetime(2026, 1, 3, tzinfo=datetime.timezone.utc),
    }
    assert result["success"] is True
    assert collection.count_queries == [{"created_on": expected}]
    assert collection.estimated_calls == 0
    assert collection.aggregate_pipelines
    assert all(
        stage["$match"].get("created_on") == expected
        for stages in collection.aggregate_pipelines for stage in stages if "$match" in stage
    )


def test_filtered_count_failure_has_no_unfiltered_fallback(isolated_db, monkeypatch):
    collection = FakeCollection(fail_count=True)
    result = run_mongo_case(isolated_db, monkeypatch, collection)
    metrics = {item["id"]: item for item in result["key_metrics"]}
    assert metrics["orders_total_rows"]["status"] == "error"
    assert metrics["orders_total_rows"]["reason"] == "query_failed"
    assert metrics["orders_total_rows"]["value"] is None
    assert collection.estimated_calls == 0


def test_missing_date_role_does_not_run_unfiltered_aggregates(isolated_db, monkeypatch):
    collection = FakeCollection()
    result = run_mongo_case(isolated_db, monkeypatch, collection, with_date=False)
    metrics = {item["id"]: item for item in result["key_metrics"]}
    assert metrics["orders_total_rows"]["status"] == "unavailable"
    assert metrics["orders_total_rows"]["reason"] == "missing_role"
    assert not collection.count_queries
    assert not collection.aggregate_pipelines
    assert not collection.distinct_queries


def test_mongo_client_closes_after_unexpected_collection_error(isolated_db, monkeypatch):
    collection = FakeCollection()
    run_mongo_case(isolated_db, monkeypatch, collection, fail_lookup=True)
    assert collection.client_closes == 1
