"""
Phase 1.5D.1 - Removal of Last Silent KPI Fallbacks
Focused regression test suite covering Tasks 1 through 6.
"""

import os
import sys

# Setup backend import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from database import Base
from routers.analytics import run_agent_pipeline_sync, ALLOWED_AGENT_AGGREGATIONS
from services.dashboard_agents.schemas import KpiSpec


@pytest.fixture
def sync_db():
    """Sets up an isolated in-memory SQLite database with non-ecommerce schema."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    tenant = models.Tenant(id=1, name="Healthcare Clinic")
    db.add(tenant)

    db_conn = models.DatabaseConnection(
        id=10,
        tenant_id=1,
        name="Clinical Database",
        db_type="sqlite",
        host="localhost",
        username="test",
        password="secret_password",
        database=":memory:",
    )
    db.add(db_conn)

    # Seed verified SchemaRegistry for healthcare domain: patients & clinical_encounters
    # (Deliberately NO 'orders' table and NO 'total_amount' column in patients!)
    schema_rows = [
        models.SchemaRegistry(connection_id=10, table_name="patients", column_name="patient_id", data_type="INTEGER", is_primary_key=True, semantic_type="ID"),
        models.SchemaRegistry(connection_id=10, table_name="patients", column_name="admission_date", data_type="TIMESTAMP", is_time_axis=True, semantic_type="DATETIME"),
        models.SchemaRegistry(connection_id=10, table_name="patients", column_name="treatment_cost", data_type="REAL", is_measure=True, semantic_type="NUMERIC_MEASURE"),
        models.SchemaRegistry(connection_id=10, table_name="patients", column_name="discharge_status", data_type="VARCHAR", is_dimension=True, semantic_type="CATEGORY"),
        models.SchemaRegistry(connection_id=10, table_name="clinical_encounters", column_name="encounter_id", data_type="INTEGER", is_primary_key=True, semantic_type="ID"),
        models.SchemaRegistry(connection_id=10, table_name="clinical_encounters", column_name="fee", data_type="REAL", is_measure=True, semantic_type="NUMERIC_MEASURE"),
    ]
    db.add_all(schema_rows)
    db.commit()

    try:
        yield db, db_conn
    finally:
        db.close()


# ==============================================================================
# TESTS 1 & 2: VALID SUM AND AVG KPIS PERSIST UNCHANGED
# ==============================================================================

def test_1_valid_sum_agent_kpi_persists_unchanged(sync_db):
    """Proves that a valid SUM agent KPI persists with exact target and aggregation."""
    db, db_conn = sync_db

    agent_kpi = KpiSpec(
        kpi_title="Total Treatment Cost",
        formula_description="SUM(treatment_cost)",
        aggregation_function="sum",
        primary_column="patients.treatment_cost",
        priority=1,
        reasoning="Core financial metric for hospital clinic",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=[agent_kpi],
        db=db,
    )

    assert len(persisted) == 1
    k = persisted[0]
    assert k.kpi_title == "Total Treatment Cost"
    assert k.aggregation_function == "SUM"
    assert k.target_column == "patients.treatment_cost"
    assert k.default_chart_type == "Bar"


def test_2_valid_avg_agent_kpi_persists_unchanged(sync_db):
    """Proves that a valid AVG agent KPI persists with exact target and aggregation."""
    db, db_conn = sync_db

    agent_kpi = KpiSpec(
        kpi_title="Average Treatment Cost",
        formula_description="AVG(treatment_cost)",
        aggregation_function="avg",
        primary_column="patients.treatment_cost",
        priority=2,
        reasoning="Benchmark average patient expense",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=[agent_kpi],
        db=db,
    )

    assert len(persisted) == 1
    k = persisted[0]
    assert k.kpi_title == "Average Treatment Cost"
    assert k.aggregation_function == "AVG"
    assert k.target_column == "patients.treatment_cost"
    assert k.default_chart_type == "Line"


# ==============================================================================
# TESTS 3, 4, 5: MISSING AND UNSUPPORTED AGGREGATIONS ARE NOT PERSISTED
# ==============================================================================

@pytest.mark.parametrize("blank_agg", [None, "", "   "])
def test_3_missing_aggregation_is_not_persisted(sync_db, blank_agg):
    """Proves that missing or blank aggregation is dropped, never persisted, and never defaulted."""
    db, db_conn = sync_db

    raw_spec = SimpleNamespace(
        kpi_title="Incomplete Metric",
        aggregation_function=blank_agg,
        primary_column="patients.treatment_cost",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=[raw_spec],
        db=db,
    )

    assert len(persisted) == 0
    in_db = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == db_conn.id).all()
    assert len(in_db) == 0


def test_4_unsupported_growth_is_not_persisted(sync_db):
    """Proves that unsupported 'GROWTH' aggregation is dropped and NOT converted to COUNT or SUM."""
    db, db_conn = sync_db

    growth_spec = SimpleNamespace(
        kpi_title="Patient Intake Growth",
        aggregation_function="GROWTH",
        primary_column="patients.patient_id",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=[growth_spec],
        db=db,
    )

    assert len(persisted) == 0
    in_db = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == db_conn.id).all()
    assert len(in_db) == 0


def test_5_unsupported_difference_is_not_persisted(sync_db):
    """Proves that unsupported 'DIFFERENCE' aggregation is dropped and NOT converted to COUNT or SUM."""
    db, db_conn = sync_db

    diff_spec = SimpleNamespace(
        kpi_title="Fee Margin Difference",
        aggregation_function="DIFFERENCE",
        primary_column="patients.treatment_cost",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=[diff_spec],
        db=db,
    )

    assert len(persisted) == 0
    in_db = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == db_conn.id).all()
    assert len(in_db) == 0


# ==============================================================================
# TESTS 6 & 7: MISSING TABLE OR COLUMN ARE NOT PERSISTED
# ==============================================================================

def test_6_missing_table_name_is_not_persisted(sync_db):
    """Proves that missing table_name is dropped and never defaulted to 'orders'."""
    db, db_conn = sync_db

    spec_missing_table = SimpleNamespace(
        kpi_title="Orphan Column KPI",
        aggregation_function="SUM",
        table_name=None,
        column_name="treatment_cost",
        primary_column=None,
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=[spec_missing_table],
        db=db,
    )

    assert len(persisted) == 0
    in_db = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == db_conn.id).all()
    assert len(in_db) == 0


def test_7_missing_column_name_is_not_persisted(sync_db):
    """Proves that missing column_name is dropped and never defaulted to 'total_amount'."""
    db, db_conn = sync_db

    spec_missing_column = SimpleNamespace(
        kpi_title="Orphan Table KPI",
        aggregation_function="SUM",
        table_name="patients",
        column_name=None,
        primary_column=None,
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=[spec_missing_column],
        db=db,
    )

    assert len(persisted) == 0
    in_db = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == db_conn.id).all()
    assert len(in_db) == 0


# ==============================================================================
# TESTS 8 & 9: UNKNOWN TABLE OR COLUMN NOT IN SCHEMAREGISTRY
# ==============================================================================

def test_8_unknown_table_is_not_persisted(sync_db):
    """Proves that tables not in SchemaRegistry are rejected, blocking hallucinated tables."""
    db, db_conn = sync_db

    hallucinated_table = SimpleNamespace(
        kpi_title="Hallucinated Invoices",
        aggregation_function="SUM",
        primary_column="invoices.total_due",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=[hallucinated_table],
        db=db,
    )

    assert len(persisted) == 0
    in_db = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == db_conn.id).all()
    assert len(in_db) == 0


def test_9_unknown_column_is_not_persisted(sync_db):
    """Proves that columns not in SchemaRegistry are rejected, blocking hallucinated columns."""
    db, db_conn = sync_db

    hallucinated_col = SimpleNamespace(
        kpi_title="Hallucinated Margin",
        aggregation_function="SUM",
        primary_column="patients.non_existent_margin",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=[hallucinated_col],
        db=db,
    )

    assert len(persisted) == 0
    in_db = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == db_conn.id).all()
    assert len(in_db) == 0


# ==============================================================================
# TEST 10: NO CODE PATH FALLS BACK TO orders.total_amount
# ==============================================================================

def test_10_no_code_path_falls_back_to_orders_total_amount(sync_db):
    """
    Specifically tests that malformed, incomplete, or corrupted agent specs
    NEVER write 'orders.total_amount' to the database when orders does not exist.
    """
    db, db_conn = sync_db

    corrupted_specs = [
        SimpleNamespace(kpi_title="Corrupted 1", aggregation_function="SUM", table_name=None, column_name=None),
        SimpleNamespace(kpi_title="Corrupted 2", aggregation_function="SUM", primary_column=""),
        SimpleNamespace(kpi_title="Corrupted 3", aggregation_function="SUM", primary_column="orders.total_amount"),
    ]

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=corrupted_specs,
        db=db,
    )

    # orders.total_amount must NOT be persisted because 'orders' is not in SchemaRegistry!
    assert len(persisted) == 0

    all_kpis = db.query(models.KpiDefinition).all()
    for k in all_kpis:
        assert k.target_column != "orders.total_amount", (
            f"Violation: 'orders.total_amount' was fabricated in connection {k.connection_id}!"
        )


# ==============================================================================
# TEST 11: NO CODE PATH CONVERTS INVALID AGGREGATION TO COUNT
# ==============================================================================

@pytest.mark.parametrize("invalid_agg", [
    "GROWTH",
    "DIFFERENCE",
    "PERCENT_CHANGE",
    "RATIO",
    "COMPUTED",
    "MEDIAN",
    "CUSTOM_ALGO",
])
def test_11_no_code_path_converts_invalid_aggregation_to_count(sync_db, invalid_agg):
    """
    Proves that invalid or un-whitelisted aggregations are rejected cleanly
    and NEVER silently converted to COUNT or SUM.
    """
    db, db_conn = sync_db

    spec = SimpleNamespace(
        kpi_title=f"Test {invalid_agg}",
        aggregation_function=invalid_agg,
        primary_column="patients.treatment_cost",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=[spec],
        db=db,
    )

    assert len(persisted) == 0
    all_kpis = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == db_conn.id).all()
    for k in all_kpis:
        assert k.aggregation_function != "COUNT", (
            f"Silent fallback violation: invalid aggregation '{invalid_agg}' was converted to COUNT!"
        )


# ==============================================================================
# TEST 12: ALL-INVALID AGENT OUTPUT PRODUCES ZERO KPI DEFINITIONS
# ==============================================================================

def test_12_all_invalid_agent_output_produces_zero_kpi_definitions(sync_db):
    """
    Proves that when all agent outputs are invalid:
    - zero KPI definitions are persisted
    - no fallback rule engine is called
    - no demo data is created
    """
    db, db_conn = sync_db

    # Pre-seed an existing KPI to verify it is PRESERVED when regeneration has 0 valid KPIs
    old_kpi = models.KpiDefinition(
        tenant_id=1,
        connection_id=db_conn.id,
        kpi_title="Old Stale KPI",
        aggregation_function="SUM",
        target_column="patients.treatment_cost",
    )
    db.add(old_kpi)
    db.commit()

    all_invalid = [
        SimpleNamespace(kpi_title="Invalid 1", aggregation_function="", primary_column="patients.treatment_cost"),
        SimpleNamespace(kpi_title="Invalid 2", aggregation_function="GROWTH", primary_column="patients.treatment_cost"),
        SimpleNamespace(kpi_title="Invalid 3", aggregation_function="SUM", primary_column="fake_table.col"),
        SimpleNamespace(kpi_title="Invalid 4", aggregation_function="SUM", primary_column="patients.fake_col"),
    ]

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=db_conn.id,
        agent_kpis=all_invalid,
        db=db,
    )

    assert persisted == []
    # Crucial Task 1: Old working KPI remains completely intact
    remaining = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == db_conn.id).all()
    assert len(remaining) == 1
    assert remaining[0].kpi_title == "Old Stale KPI"
