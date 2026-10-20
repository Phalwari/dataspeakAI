"""Offline planner V2 tests. All SQL fixtures use temporary in-memory SQLite only."""

from dataclasses import asdict, replace
from pathlib import Path

from sqlalchemy import create_engine
import pytest

from services.insights.catalog import discover_sql_catalog
from services.insights.catalog import _row_estimate
from services.insights.planner import MetricSpec, build_metric_plan
from services.insights.profiling import profile_catalog
from services.insights.runner import (
    PreparedMongoPlan,
    execute_prepared_mongo_plan,
    execute_prepared_sql_plan,
    prepare_sql_plan,
    run_sql_plan,
)
from services.insights.relationships import (
    AmbiguousRelationshipError,
    Relationship,
    find_relationship_path,
    infer_relationships,
)
from services.insights.sql_compiler import (
    CompiledMetric,
    MetricPlanValidationError,
    compile_metric,
    execute_metric,
)
from services.insights.mongo import (
    MongoMetricSpec,
    build_mongo_plan,
    compile_mongo_metric,
    discover_mongo_catalog,
    execute_mongo_metric,
)
from services.sql_dialect import UnsupportedDialectError
import models
from services import db_pool, db_utils
from services import db_pipeline_service as pipeline


def _catalog_and_profile(engine, sample_size=10_000):
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        profiles = profile_catalog(connection, catalog, sample_size=sample_size)
    return catalog, profiles


def test_catalog_discovers_composite_primary_and_foreign_keys_without_rows():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE parent (a INTEGER, b INTEGER, label TEXT, PRIMARY KEY (a, b))")
        connection.exec_driver_sql(
            "CREATE TABLE child (x INTEGER, y INTEGER, amount NUMERIC, "
            "FOREIGN KEY (x, y) REFERENCES parent (a, b))"
        )
        connection.exec_driver_sql("CREATE VIEW parent_view AS SELECT label FROM parent")
        connection.exec_driver_sql("INSERT INTO parent VALUES (1, 2, 'synthetic')")

    catalog, profiles = _catalog_and_profile(engine)
    parent = catalog.table("parent")
    child = catalog.table("child")
    view = catalog.table("parent_view")
    assert parent is not None and parent.primary_key == ("a", "b")
    assert child is not None and child.foreign_keys[0].columns == ("x", "y")
    assert child.foreign_keys[0].referred_columns == ("a", "b")
    assert view is not None and view.kind == "view"
    assert parent.row_estimate is None  # SQLite has no low-cost catalog estimate.
    assert "synthetic" not in repr(asdict(profiles))
    engine.dispose()


def test_unknown_postgresql_row_estimate_is_not_reported_as_zero():
    """Offline unit test: PostgreSQL's -1 reltuples sentinel means unknown."""

    class _ScalarResult:
        def scalar_one_or_none(self):
            return -1

    class _OfflineBind:
        def execute(self, statement, params):
            assert "pg_class" in str(statement)
            assert params["table_name"] == "facts"
            return _ScalarResult()

    assert _row_estimate(_OfflineBind(), "postgresql", "public", "facts") is None


def test_profile_is_bounded_and_contains_only_aggregate_statistics():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE facts (amount NUMERIC, state TEXT, event_date TEXT, contact_email TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO facts VALUES "
            "(4.5, 'paid', '2026-01-01', 'person.one@example.invalid'), "
            "(7.0, 'unpaid', '2026-01-02', 'person.two@example.invalid'), "
            "(NULL, 'paid', NULL, 'person.three@example.invalid'), "
            "(11.5, 'paid', '2026-01-04', 'person.four@example.invalid')"
        )

    catalog, profiles = _catalog_and_profile(engine, sample_size=3)
    profile = profiles.tables["facts"]
    amount = profile.columns["amount"]
    state = profile.columns["state"]
    email = profile.columns["contact_email"]
    assert profile.sampled_rows == 3 and profile.sample_truncated
    assert amount.sample_count == 3 and amount.null_count == 1
    assert amount.numeric_min == 4.5 and amount.numeric_max == 7.0
    assert state.lifecycle_value_ratio == 1.0
    assert email.contains_email_like
    serialized = repr(asdict(profiles))
    assert "person.one" not in serialized and "example.invalid" not in serialized
    engine.dispose()


def test_role_classifier_uses_schema_and_profile_evidence_for_misleading_names():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE measurements (id INTEGER PRIMARY KEY, total_orders INTEGER, "
            "discount_rate REAL, network_id INTEGER, void TEXT, salary NUMERIC, "
            "amount NUMERIC, created_on TEXT, state TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO measurements VALUES "
            "(1, 3, 0.2, 80, 'active', 50, 12.5, '2026-01-01', 'paid'), "
            "(2, 4, 0.1, 81, 'active', 60, 15.0, '2026-01-02', 'unpaid'), "
            "(3, 1, 0.0, 82, 'voided', 40, 7.5, '2026-01-03', 'returned')"
        )

    catalog, profiles = _catalog_and_profile(engine)
    plan = build_metric_plan(catalog, profiles)
    roles = plan.roles["measurements"]
    assert roles["id"].role == "identifier"
    assert roles["total_orders"].role == "additive_measure"
    assert roles["total_orders"].measure_kind == "count"
    assert not roles["total_orders"].revenue_candidate
    assert roles["discount_rate"].role == "rate"
    assert roles["network_id"].role == "identifier"
    assert roles["void"].role in {"status", "categorical"}
    assert roles["salary"].role == "additive_measure"
    assert not roles["salary"].revenue_candidate
    assert roles["amount"].role == "additive_measure" and roles["amount"].revenue_candidate
    assert roles["created_on"].role == "date"
    assert all(role.evidence for role in roles.values() if role.role not in {"unknown", "excluded"})
    engine.dispose()


def test_planner_marks_missing_revenue_role_unavailable_and_hash_is_stable():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE workforce (id INTEGER PRIMARY KEY, salary NUMERIC, hired_on TEXT)"
        )
        connection.exec_driver_sql("INSERT INTO workforce VALUES (1, 50, '2026-01-01')")
    catalog, profiles = _catalog_and_profile(engine)
    first = build_metric_plan(catalog, profiles)
    second = build_metric_plan(catalog, profiles)
    revenue = next(metric for metric in first.metrics if metric.id == "revenue_total")
    salary_sum = next(metric for metric in first.metrics if metric.measure == "salary" and metric.kind == "sum")
    assert revenue.status == "unavailable" and revenue.reason == "missing_role"
    assert salary_sum.semantic == "money" and "revenue" not in salary_sum.id
    assert first.plan_hash == second.plan_hash
    planner_source = Path(__import__("services.insights.planner", fromlist=["__file"]).__file__).read_text(encoding="utf-8")
    assert "SELECT " not in planner_source.upper()
    engine.dispose()


def test_sqlite_compiler_binds_date_filters_and_executes_hand_computed_sum():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE facts (amount NUMERIC, created_on TEXT)")
        connection.exec_driver_sql(
            "INSERT INTO facts VALUES (4.5, '2026-01-01'), (7.0, '2026-01-02'), (100, '2026-01-03')"
        )
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        metric = MetricSpec(
            "sum_facts_amount", "sum", "facts", measure="amount", date_column="created_on",
        )
        compiled = compile_metric(
            metric, catalog, date_from="2026-01-01", date_to_excl="2026-01-03",
        )
        assert ":date_from" in compiled.sql and ":date_to_excl" in compiled.sql
        assert "2026-01-01" not in compiled.sql and "2026-01-03" not in compiled.sql
        result = execute_metric(connection, compiled)
    assert result.status == "available" and float(result.value) == 11.5
    engine.dispose()


def test_count_zero_and_null_sum_have_distinct_states():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE empty_facts (amount NUMERIC)")
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        zero_count = execute_metric(
            connection, compile_metric(MetricSpec("count_empty", "count", "empty_facts"), catalog),
        )
        null_sum = execute_metric(
            connection,
            compile_metric(MetricSpec("sum_empty", "sum", "empty_facts", measure="amount"), catalog),
        )
    assert zero_count.status == "zero" and zero_count.value == 0
    assert null_sum.status == "unavailable" and null_sum.reason == "no_rows"
    engine.dispose()


def test_empty_catalog_and_ambiguous_dates_fail_closed():
    empty_engine = create_engine("sqlite:///:memory:")
    with empty_engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        profiles = profile_catalog(connection, catalog)
        plan = build_metric_plan(catalog, profiles)
        result = execute_prepared_sql_plan(connection, prepare_sql_plan(connection))
    revenue = next(metric for metric in plan.metrics if metric.id == "revenue_total")
    assert revenue.status == "unavailable" and revenue.reason == "missing_table"
    assert result["available_tables"] == []
    assert all(metric["status"] == "unavailable" for metric in result["key_metrics"])
    empty_engine.dispose()

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE dated (event_id INTEGER PRIMARY KEY, amount NUMERIC, "
            "created_on TEXT, updated_on TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO dated VALUES (1, 10, '2026-01-01', '2026-01-02')"
        )
    with engine.connect() as connection:
        prepared = prepare_sql_plan(connection)
        amount_sum = next(
            metric for metric in prepared.plan.metrics
            if metric.kind == "sum" and metric.measure == "amount"
        )
        assert amount_sum.date_column is None
        filtered = execute_prepared_sql_plan(
            connection, prepared, date_from="2026-01-01", date_to_excl="2026-01-02",
        )
    assert next(
        metric for metric in filtered["key_metrics"] if metric["id"] == amount_sum.id
    )["reason"] == "missing_role"
    engine.dispose()


def test_net_revenue_uses_exact_delivered_status_values():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE events (event_id INTEGER PRIMARY KEY, amount NUMERIC, "
            "created_on TEXT, state TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO events VALUES "
            "(1, 25, '2026-01-01', 'completed'), "
            "(2, 50, '2026-01-02', 'unpaid'), "
            "(3, 10, '2026-01-03', 'cancelled')"
        )
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        profiles = profile_catalog(connection, catalog)
        plan = build_metric_plan(catalog, profiles)
        gross = next(metric for metric in plan.metrics if metric.id == "revenue_total")
        net = next(metric for metric in plan.metrics if metric.id == "net_revenue")
        gross_result = execute_metric(connection, compile_metric(gross, catalog))
        net_compiled = compile_metric(net, catalog)
        assert "unpaid" not in net_compiled.sql
        assert net_compiled.params["delivered_statuses"]
        net_result = execute_metric(connection, net_compiled)
    assert float(gross_result.value) == 85.0
    assert float(net_result.value) == 25.0
    engine.dispose()


@pytest.mark.parametrize(
    ("dialect", "expected_fragment"),
    [
        ("postgresql", "to_char"),
        ("mysql", "DATE_FORMAT"),
        ("mariadb", "DATE_FORMAT"),
    ],
)
def test_dialect_sql_strings_and_bound_params(dialect, expected_fragment):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE facts (amount NUMERIC, created_on TEXT)")
        catalog = replace(discover_sql_catalog(connection), dialect=dialect)
    compiled = compile_metric(
        MetricSpec("trend_amount", "trend", "facts", measure="amount", date_column="created_on"),
        catalog,
        date_from="2026-01-01",
        date_to_excl="2026-02-01",
    )
    assert expected_fragment in compiled.sql
    assert compiled.params == {"date_from": "2026-01-01", "date_to_excl": "2026-02-01"}
    engine.dispose()


def test_compiler_rejects_non_catalog_identifiers_and_query_errors_are_typed():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE facts (amount NUMERIC)")
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        with pytest.raises(MetricPlanValidationError):
            compile_metric(MetricSpec("bad", "sum", "facts", measure="missing"), catalog)
        failed = execute_metric(
            connection,
            # Simulate a compiled plan whose referenced table vanished after discovery.
            CompiledMetric("missing_table", "count", 'SELECT COUNT(*) AS value FROM "ghost"', {}),
        )
    assert failed.status == "error" and failed.reason == "query_failed"
    assert failed.value is None
    engine.dispose()


def test_declared_fk_path_resolves_with_depth_limit_and_ambiguous_paths_reject():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE products (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql(
            "CREATE TABLE line_items (id INTEGER PRIMARY KEY, product_ref INTEGER, "
            "FOREIGN KEY(product_ref) REFERENCES products(id))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, line_ref INTEGER, "
            "FOREIGN KEY(line_ref) REFERENCES line_items(id))"
        )
        connection.exec_driver_sql("CREATE TABLE regions (id INTEGER PRIMARY KEY)")
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
    path = find_relationship_path(catalog, "orders", "products", max_depth=2)
    assert path is not None and path.tables == ("orders", "line_items", "products")
    assert find_relationship_path(catalog, "orders", "products", max_depth=1) is None
    ambiguous = (
        Relationship("orders", ("a",), "line_items", ("id",)),
        Relationship("line_items", ("b",), "products", ("id",)),
        Relationship("orders", ("c",), "regions", ("id",)),
        Relationship("regions", ("d",), "products", ("id",)),
    )
    with pytest.raises(AmbiguousRelationshipError):
        find_relationship_path(catalog, "orders", "products", relationships=ambiguous, max_depth=2)
    engine.dispose()


def test_inferred_relationship_requires_identifier_role_and_containment():
    from services.insights.roles import ColumnRole

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE parent (pk INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE child (row_key INTEGER PRIMARY KEY, network_id INTEGER)")
        connection.exec_driver_sql("INSERT INTO parent VALUES (100), (101)")
        connection.exec_driver_sql("INSERT INTO child VALUES (1, 100), (2, 101)")
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        edges = infer_relationships(
            connection,
            catalog,
            {"child": {"network_id": ColumnRole("identifier", 0.9, ("high distinct ratio",))}},
            min_containment=0.95,
        )
    inferred = [edge for edge in edges if edge.source == "inferred"]
    assert len(inferred) == 1
    assert inferred[0].left_columns == ("network_id",)
    assert inferred[0].right_columns == ("pk",)
    engine.dispose()


def test_inferred_relationship_below_containment_threshold_is_rejected():
    from services.insights.roles import ColumnRole

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE parent (pk INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("CREATE TABLE child (row_key INTEGER PRIMARY KEY, network_id INTEGER)")
        connection.exec_driver_sql("INSERT INTO parent VALUES (100), (101)")
        connection.exec_driver_sql("INSERT INTO child VALUES (1, 100), (2, 999), (3, 998)")
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        edges = infer_relationships(
            connection, catalog,
            {"child": {"network_id": ColumnRole("identifier", 0.9, ("sample evidence",))}},
            min_containment=0.95,
        )
    assert not any(edge.source == "inferred" for edge in edges)
    engine.dispose()


def test_no_fk_inferred_join_requires_containment_and_has_hand_computed_breakdown():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE product_dim (product_key INTEGER PRIMARY KEY, family TEXT)")
        connection.exec_driver_sql(
            "CREATE TABLE activity (event_key INTEGER PRIMARY KEY, product_ref INTEGER, "
            "amount NUMERIC, event_date TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO product_dim VALUES "
            + ",".join(f"({10 + index}, '{'hardware' if index < 20 else 'software'}')" for index in range(40))
        )
        connection.exec_driver_sql(
            "INSERT INTO activity VALUES "
            + ",".join(
                f"({index + 1}, {10 + index}, 1, '2026-01-01')" for index in range(40)
            )
            + ",(41, 999, 100, '2026-01-02')"
        )
    with engine.connect() as connection:
        prepared = prepare_sql_plan(connection)
        inferred_chart = next(
            metric for metric in prepared.plan.metrics
            if metric.kind == "breakdown" and metric.dimension_table == "product_dim"
        )
        assert inferred_chart.joins and inferred_chart.joins[0].source == "inferred"
        result = execute_prepared_sql_plan(connection, prepared)
    actual = next(chart for chart in result["charts"] if chart["id"] == inferred_chart.id)
    assert {point["name"]: point["value"] for point in actual["data"]} == {
        "hardware": 20.0, "software": 20.0,
    }
    gross = next(metric for metric in result["key_metrics"] if metric["id"] == "revenue_total")
    assert gross["raw_value"] == 140.0  # Base-table total retains the orphan fact.
    assert any("inferred relationships" in warning for warning in result["data_quality"]["warnings"])
    engine.dispose()


def test_fk_multi_table_breakdown_compiles_and_matches_expected_aggregate():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE products (product_key INTEGER PRIMARY KEY, category TEXT)")
        connection.exec_driver_sql(
            "CREATE TABLE order_rows (row_key INTEGER PRIMARY KEY, product_ref INTEGER, "
            "amount NUMERIC, created_on TEXT, state TEXT, "
            "FOREIGN KEY(product_ref) REFERENCES products(product_key))"
        )
        connection.exec_driver_sql("INSERT INTO products VALUES (10, 'hardware'), (11, 'software')")
        connection.exec_driver_sql(
            "INSERT INTO order_rows VALUES "
            "(1, 10, 12.5, '2026-01-01', 'paid'), "
            "(2, 10, 7.5, '2026-01-02', 'paid'), "
            "(3, 11, 30, '2026-01-03', 'unpaid')"
        )
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        profiles = profile_catalog(connection, catalog)
        plan = build_metric_plan(catalog, profiles)
        metric = next(
            metric for metric in plan.metrics
            if metric.kind == "breakdown" and metric.dimension_table == "products"
        )
        compiled = compile_metric(metric, catalog)
        result = execute_metric(connection, compiled)
    assert result.status == "available"
    assert {row["category"]: float(row["value"]) for row in result.value} == {
        "hardware": 20.0, "software": 30.0,
    }
    engine.dispose()


class _FakeCursor(list):
    def limit(self, size):
        return _FakeCursor(self[:size])

    def max_time_ms(self, _milliseconds):
        return self


class _FakeMongoCollection:
    def __init__(self, documents, *, fail_count=False, aggregate_rows=None):
        self.documents = documents
        self.fail_count = fail_count
        self.aggregate_rows = aggregate_rows or []
        self.count_queries = []
        self.count_options = []
        self.pipelines = []
        self.aggregate_options = []

    def find(self, query, projection):
        return _FakeCursor(self.documents)

    def count_documents(self, query, **options):
        self.count_queries.append(query)
        self.count_options.append(options)
        if self.fail_count:
            raise RuntimeError("offline fake count failure")
        return len(self.documents)

    def aggregate(self, pipeline, **options):
        self.pipelines.append(pipeline)
        self.aggregate_options.append(options)
        return list(self.aggregate_rows)


class _FakeMongoDatabase:
    name = "offline_fixture"

    def __init__(self, collections):
        self.collections = collections

    def list_collection_names(self):
        return list(self.collections)

    def __getitem__(self, name):
        return self.collections[name]


class _FakeMongoClient:
    def __init__(self, database):
        self.database = database
        self.closed = False

    def get_default_database(self):
        return self.database

    def close(self):
        self.closed = True


def test_mongo_nested_paths_pii_exclusion_and_array_plan_are_bounded():
    database = _FakeMongoDatabase({
        "events": _FakeMongoCollection([
            {
                "_id": 1,
                "customer": {"address": {"city": "Lahore"}, "email": "person@example.invalid"},
                "items": [{"price": 10}, {"price": 5}],
                "created_on": "2026-01-01T12:00:00Z",
                "state": "paid",
            },
            {
                "_id": 2,
                "customer": {"address": {"city": "Karachi"}, "email": "another@example.invalid"},
                "items": [{"price": 8}],
                "created_on": "2026-01-02T12:00:00Z",
                "state": "unpaid",
            },
        ])
    })
    catalog = discover_mongo_catalog(database, sample_size=10)
    collection = catalog.collections[0]
    assert "customer.address.city" in collection.fields
    assert "items[].price" in collection.fields
    assert collection.fields["customer.email"].pii
    assert "person@example.invalid" not in repr(catalog)
    plan = build_mongo_plan(catalog)
    metric = next(item for item in plan.metrics if item.measure == "items[].price" and item.kind == "trend")
    fake_collection = database["events"]
    fake_collection.aggregate_rows = [{"_id": "2026-01", "value": 23}]
    result = execute_mongo_metric(
        fake_collection, metric, date_from="2026-01-01", date_to_excl="2026-01-03",
    )
    assert result.status == "available"
    pipeline = fake_collection.pipelines[0]
    assert pipeline[0] == {"$unwind": "$items"}
    assert pipeline[1]["$match"] == {
        "created_on": {
            "$ne": None,
            "$gte": "2026-01-01",
            "$lt": "2026-01-03",
        }
    }
    assert "email" not in repr(plan)


def test_mongo_collection_limit_and_filtered_query_failure_are_explicit():
    collections = {
        f"bucket_{index}": _FakeMongoCollection([])
        for index in range(5)
    }
    database = _FakeMongoDatabase(collections)
    catalog = discover_mongo_catalog(database, max_collections=3)
    assert len(catalog.collections) == 3 and catalog.truncated
    assert "Mongo collection limit reached" in catalog.warnings

    failing = _FakeMongoCollection([], fail_count=True)
    metric = MongoMetricSpec("count_events", "count", "events", date_path="created_on")
    result = execute_mongo_metric(
        failing, metric, date_from="2026-01-01", date_to_excl="2026-01-02",
    )
    assert result.status == "error" and result.reason == "query_failed"
    assert failing.count_queries and "$gte" in failing.count_queries[0]["created_on"]
    assert 0 < failing.count_options[0]["maxTimeMS"] <= 5_000
    assert not hasattr(failing, "estimated_document_count")

    five = _FakeMongoDatabase({
        f"sample_{index}": _FakeMongoCollection([]) for index in range(5)
    })
    all_collections = discover_mongo_catalog(five)
    assert len(all_collections.collections) == 5 and not all_collections.truncated

    empty_database = _FakeMongoDatabase({})
    empty_catalog = discover_mongo_catalog(empty_database)
    empty_plan = build_mongo_plan(empty_catalog)
    empty_result = execute_prepared_mongo_plan(
        empty_database, PreparedMongoPlan(
            empty_catalog, empty_plan, __import__("time").monotonic() + 10,
        ),
    )
    assert all(metric["status"] == "unavailable" for metric in empty_result["key_metrics"])

    missing_selection = execute_prepared_mongo_plan(
        database, PreparedMongoPlan(catalog, build_mongo_plan(catalog), __import__("time").monotonic() + 10),
        selected_collection="not_in_catalog",
    )
    assert missing_selection["key_metrics"][0]["reason"] == "missing_table"


def test_mongo_mixed_numeric_types_are_not_planned_as_sum():
    database = _FakeMongoDatabase({
        "mixed": _FakeMongoCollection([{"score": 3}, {"score": "4"}])
    })
    catalog = discover_mongo_catalog(database)
    field = catalog.collections[0].fields["score"]
    assert field.heterogeneous and field.numeric_parse_rate == 1.0
    plan = build_mongo_plan(catalog)
    assert not any(metric.measure == "score" and metric.kind == "sum" for metric in plan.metrics)
    assert "A mixed-type Mongo field was omitted from numeric metrics" in plan.warnings


def test_orders_status_fixture_has_gross_and_delivered_only_revenue():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE activity (event_id INTEGER PRIMARY KEY, amount NUMERIC, "
            "created_on TEXT, state TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO activity VALUES "
            "(1, 25, '2026-01-01', 'paid'), "
            "(2, 50, '2026-01-02', 'unpaid'), "
            "(3, 10, '2026-01-03', 'cancelled'), "
            "(4, 15, '2026-01-04', 'returned'), "
            "(5, 40, '2026-01-05', 'delivered')"
        )
    with engine.connect() as connection:
        result = run_sql_plan(connection)
    metrics = {metric["id"]: metric for metric in result["key_metrics"]}
    assert metrics["revenue_total"]["raw_value"] == 140
    assert metrics["revenue_total"]["label"] == "Gross Revenue (all statuses)"
    assert metrics["net_revenue"]["raw_value"] == 40
    assert metrics["net_revenue"]["label"] == "Net Revenue (delivered only)"
    assert metrics["net_revenue"]["status"] == "available"
    engine.dispose()


def test_quantity_without_price_and_nullable_dates_has_no_revenue():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE activity (event_id INTEGER PRIMARY KEY, quantity INTEGER, created_on TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO activity VALUES (1, 2, '2026-01-01'), (2, 3, NULL)"
        )
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        profiles = profile_catalog(connection, catalog)
        plan = build_metric_plan(catalog, profiles)
        result = execute_prepared_sql_plan(
            connection,
            prepare_sql_plan(connection),
        )
    revenue = next(metric for metric in plan.metrics if metric.id == "revenue_total")
    assert revenue.status == "unavailable" and revenue.reason == "missing_role"
    assert profiles.tables["activity"].columns["created_on"].null_ratio == 0.5
    assert any(metric["id"].endswith("quantity") and metric["status"] == "available" for metric in result["key_metrics"])
    engine.dispose()


@pytest.mark.parametrize(
    ("table_sql", "insert_sql"),
    [
        (
            "CREATE TABLE workforce (person_key INTEGER PRIMARY KEY, salary NUMERIC, hired_on TEXT)",
            "INSERT INTO workforce VALUES (1, 150, '2026-01-01')",
        ),
        (
            "CREATE TABLE stock (stock_key INTEGER PRIMARY KEY, cost NUMERIC, quantity INTEGER, received_on TEXT)",
            "INSERT INTO stock VALUES (1, 80, 4, '2026-01-01')",
        ),
    ],
)
def test_hr_and_inventory_do_not_fabricate_revenue(table_sql, insert_sql):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(table_sql)
        connection.exec_driver_sql(insert_sql)
    with engine.connect() as connection:
        result = run_sql_plan(connection)
    revenue = next(metric for metric in result["key_metrics"] if metric["id"] == "revenue_total")
    assert revenue["status"] == "unavailable" and revenue["reason"] == "missing_role"
    engine.dispose()


def test_empty_table_returns_zero_count_and_unavailable_revenue():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE empty_activity (event_key INTEGER PRIMARY KEY, amount NUMERIC, created_on TEXT)"
        )
    with engine.connect() as connection:
        result = run_sql_plan(connection)
    metrics = {metric["id"]: metric for metric in result["key_metrics"]}
    assert metrics["row_count_empty_activity"]["status"] == "zero"
    assert metrics["row_count_empty_activity"]["raw_value"] == 0
    assert metrics["revenue_total"]["status"] == "unavailable"
    engine.dispose()


def test_profile_cache_is_catalog_and_connection_generation_scoped(monkeypatch):
    from services.insights import runner

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE activity (event_key INTEGER PRIMARY KEY, amount NUMERIC)")
        connection.exec_driver_sql("INSERT INTO activity VALUES (1, 10)")
    cache = {}
    calls = {"profiles": 0}
    original_profile = runner.profile_catalog

    def counted_profile(*args, **kwargs):
        calls["profiles"] += 1
        return original_profile(*args, **kwargs)

    monkeypatch.setattr(runner, "profile_catalog", counted_profile)
    with engine.connect() as connection:
        prepare_sql_plan(
            connection, profile_cache_namespace="tenant-a:connection-1:v0",
            profile_cache_get=cache.get, profile_cache_set=cache.__setitem__,
        )
        prepare_sql_plan(
            connection, profile_cache_namespace="tenant-a:connection-1:v0",
            profile_cache_get=cache.get, profile_cache_set=cache.__setitem__,
        )
        prepare_sql_plan(
            connection, profile_cache_namespace="tenant-a:connection-1:v1",
            profile_cache_get=cache.get, profile_cache_set=cache.__setitem__,
        )
    assert calls["profiles"] == 2
    assert len(cache) == 2
    assert all("v0" in key or "v1" in key for key in cache)
    assert all(isinstance(value, runner.ProfileSet) for value in cache.values())
    engine.dispose()


def test_mongo_planner_computes_neutral_average_and_status_aware_revenue():
    database = _FakeMongoDatabase({
        "activity": _FakeMongoCollection([
            {"_id": "a", "amount": 30, "discount_rate": 0.1, "created_on": "2026-01-01", "state": "Delivered"},
            {"_id": "b", "amount": 70, "discount_rate": 0.2, "created_on": "2026-01-02", "state": "unpaid"},
        ])
    })
    catalog = discover_mongo_catalog(database)
    plan = build_mongo_plan(catalog)
    assert not any(metric.kind == "sum" and metric.measure == "discount_rate" for metric in plan.metrics)
    revenue = next(metric for metric in plan.metrics if metric.id == "revenue_total")
    net = next(metric for metric in plan.metrics if metric.id == "net_revenue")
    assert revenue.semantic == "revenue" and net.status_path == "state"
    collection = database["activity"]
    collection.aggregate_rows = [{"_id": None, "value": 100}]
    total = execute_mongo_metric(
        collection, revenue, date_from="2026-01-01", date_to_excl="2026-01-03",
    )
    assert total.status == "available" and total.value == 100
    assert collection.pipelines[-1][0] == {
        "$match": {"created_on": {"$ne": None, "$gte": "2026-01-01", "$lt": "2026-01-03"}},
    }
    collection.aggregate_rows = [{"_id": None, "value": 30}]
    delivered = execute_mongo_metric(
        collection, net, date_from="2026-01-01", date_to_excl="2026-01-03",
    )
    assert delivered.value == 30
    assert "state" in repr(collection.pipelines[-1])


def test_mongo_date_strings_use_calendar_bounds_and_phone_values_are_pii():
    database = _FakeMongoDatabase({
        "events": _FakeMongoCollection([
            {"created_on": "2026-01-01T12:00:00Z", "amount": 10, "contact": "+1 (555) 010-1234"},
        ])
    })
    catalog = discover_mongo_catalog(database)
    field = catalog.collections[0].fields["contact"]
    assert field.pii
    metric = MongoMetricSpec(
        "sum_events_amount", "sum", "events", "amount",
        date_path="created_on", date_types=("string",),
    )
    query, pipeline, status, reason = compile_mongo_metric(
        metric, date_from="2026-01-01", date_to_excl="2026-01-02",
    )
    assert status == "available" and reason is None and pipeline is not None
    assert query == {"created_on": {"$ne": None, "$gte": "2026-01-01", "$lt": "2026-01-02"}}
    invalid = execute_mongo_metric(
        _FakeMongoCollection([]), metric, date_from="2026-13-01", date_to_excl="2026-13-02",
    )
    assert invalid.status == "error" and invalid.reason == "invalid_date"


def test_expired_planner_budget_stops_sql_and_mongo_before_database_work():
    import time

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE facts (amount NUMERIC)")
    with engine.connect() as connection:
        catalog = discover_sql_catalog(connection)
        metric = MetricSpec("sum_amount", "sum", "facts", measure="amount")
        result = execute_metric(
            connection, compile_metric(metric, catalog), deadline=time.monotonic() - 1,
        )
    assert result.status == "unavailable" and result.reason == "budget_exceeded"
    engine.dispose()

    mongo_collection = _FakeMongoCollection([])
    mongo_metric = MongoMetricSpec("count_docs", "count", "events")
    mongo_result = execute_mongo_metric(
        mongo_collection, mongo_metric, deadline=time.monotonic() - 1,
    )
    assert mongo_result.status == "unavailable" and mongo_result.reason == "budget_exceeded"
    assert not mongo_collection.count_queries and not mongo_collection.pipelines


def test_pipeline_selects_mongo_branch_when_collection_is_named_orders(isolated_db, monkeypatch):
    collection = _FakeMongoCollection([
        {"_id": "one", "amount": 12.5, "created_on": "2026-01-01", "state": "paid"},
    ], aggregate_rows=[{"_id": None, "value": 12.5}])
    mongo_database = _FakeMongoDatabase({"orders": collection})
    client = _FakeMongoClient(mongo_database)
    tenant = models.Tenant(name="Fake Mongo branch test")
    isolated_db.add(tenant)
    isolated_db.flush()
    source = models.DatabaseConnection(
        tenant_id=tenant.id, name="Fake Mongo branch test", db_type="mongodb",
        database="offline-placeholder", connection_string="offline-placeholder",
    )
    isolated_db.add(source)
    isolated_db.flush()
    monkeypatch.setenv("INSIGHTS_PLANNER", "v2")
    monkeypatch.setattr(pipeline.encryption_service, "decrypt", lambda _value: "offline-placeholder")
    monkeypatch.setattr("pymongo.MongoClient", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(
        db_utils, "get_connection_url",
        lambda _connection: (_ for _ in ()).throw(AssertionError("Mongo entered SQL branch")),
    )
    monkeypatch.setattr(pipeline, "cache_get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pipeline, "cache_set", lambda *_args, **_kwargs: True)

    result = pipeline.DatabasePipelineService().run_db_pipeline(
        db=isolated_db, connection_id=source.id, tenant_id=tenant.id, selected_table="orders",
    )
    assert result["planner_mode"] == "v2"
    assert result["db_type"] == "mongodb"
    assert result["available_tables"] == ["orders"]
    mongo_metrics = {metric["id"]: metric for metric in result["key_metrics"]}
    assert mongo_metrics["revenue_total"]["label"] == "Gross Revenue (all statuses)"
    assert mongo_metrics["revenue_total"]["format"] == "currency"
    assert client.closed


def test_unknown_sql_dialect_and_ratio_compilation_are_explicit():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE facts (numerator NUMERIC, denominator NUMERIC)")
        catalog = discover_sql_catalog(connection)
    ratio = MetricSpec(
        "share", "ratio", "facts", numerator="numerator", denominator="denominator",
    )
    mysql = replace(catalog, dialect="mysql")
    postgres = replace(catalog, dialect="postgresql")
    assert "DECIMAL(38, 10)" in compile_metric(ratio, mysql).sql
    assert "DOUBLE PRECISION" in compile_metric(ratio, postgres).sql
    invalid_date = compile_metric(
        MetricSpec("filtered", "sum", "facts", measure="numerator"),
        catalog, date_from="2026-13-01", date_to_excl="2026-13-02",
    )
    assert invalid_date.status == "error" and invalid_date.reason == "invalid_date"
    with pytest.raises(UnsupportedDialectError):
        compile_metric(ratio, replace(catalog, dialect="unknown"))
    engine.dispose()


def test_pipeline_v2_feature_flag_returns_generic_typed_insights(isolated_db, monkeypatch):
    source_engine = create_engine("sqlite:///:memory:")
    with source_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE activity (event_id INTEGER PRIMARY KEY, amount NUMERIC, "
            "created_on TEXT, state TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO activity VALUES "
            "(1, 25, '2026-01-01', 'completed'), "
            "(2, 50, '2026-01-02', 'unpaid')"
        )
    tenant = models.Tenant(name="Planner V2 temporary fixture")
    isolated_db.add(tenant)
    isolated_db.flush()
    source = models.DatabaseConnection(
        tenant_id=tenant.id, name="Planner V2 temporary fixture", db_type="sqlite",
        database="offline-placeholder", connection_string="offline-placeholder",
    )
    isolated_db.add(source)
    isolated_db.flush()
    cache = {}
    monkeypatch.setenv("INSIGHTS_PLANNER", "v2")
    monkeypatch.setattr(db_utils, "get_connection_url", lambda _connection: source_engine.url)
    monkeypatch.setattr(db_pool, "get_engine", lambda _url: source_engine)
    monkeypatch.setattr(pipeline, "cache_get", lambda key: cache.get(key))
    monkeypatch.setattr(pipeline, "cache_set", lambda key, value, **_kwargs: cache.__setitem__(key, value))

    result = pipeline.DatabasePipelineService().run_db_pipeline(
        db=isolated_db, connection_id=source.id, tenant_id=tenant.id,
    )
    metrics = {metric["id"]: metric for metric in result["key_metrics"]}
    assert result["planner_mode"] == "v2"
    assert metrics["revenue_total"]["raw_value"] == 75.0
    assert metrics["net_revenue"]["raw_value"] == 25.0
    assert metrics["row_count_activity"]["raw_value"] == 2
    assert result["executive_summary"]["source"] == "deterministic_fallback"
    assert result["catalog_version"] and result["plan_hash"]
    source_engine.dispose()
