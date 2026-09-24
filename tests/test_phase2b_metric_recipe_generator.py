import json
import os
import sys
from types import SimpleNamespace
from typing import get_args

# Setup backend import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pytest

from services.metric_recipes import (
    AggregationType,
    AtomicMetricRecipe,
    DifferenceMetricRecipe,
    RatioMetricRecipe,
    metric_recipe_to_dict,
    metric_recipe_to_json,
)
from services.metric_semantics import ALLOWED_AGGREGATIONS
from services.metric_recipe_generator import (
    AtomicRecipeRule,
    generate_metric_recipes,
)


# ============================================================
# TEST REGISTRY FIXTURE
# ============================================================

def registry_column(
    table_name: str,
    column_name: str,
    *,
    data_type: str,
    semantic_type: str,
    is_primary_key: bool = False,
    is_foreign_key: bool = False,
    is_measure: bool = False,
    is_dimension: bool = False,
):
    return SimpleNamespace(
        table_name=table_name,
        column_name=column_name,
        data_type=data_type,
        semantic_type=semantic_type,
        is_primary_key=is_primary_key,
        is_foreign_key=is_foreign_key,
        is_measure=is_measure,
        is_dimension=is_dimension,
    )


@pytest.fixture
def multi_table_registry():
    return [
        # Orders table
        registry_column("orders", "order_id", data_type="INTEGER", semantic_type="ID", is_primary_key=True),
        registry_column("orders", "customer_id", data_type="INTEGER", semantic_type="ID", is_foreign_key=True),
        registry_column("orders", "total_amount", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
        registry_column("orders", "total_cost", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
        registry_column("orders", "tax_amount", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
        registry_column("orders", "status", data_type="VARCHAR", semantic_type="CATEGORY", is_dimension=True),
        # Customers table
        registry_column("customers", "id", data_type="INTEGER", semantic_type="ID", is_primary_key=True),
        registry_column("customers", "region", data_type="VARCHAR", semantic_type="CATEGORY", is_dimension=True),
        # Healthcare tables
        registry_column("encounters", "appointment_id", data_type="INTEGER", semantic_type="ID", is_primary_key=True),
        registry_column("encounters", "patient_id", data_type="INTEGER", semantic_type="ID", is_foreign_key=True),
        registry_column("encounters", "billing_amount", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
        # Telemetry / Generic table
        registry_column("telemetry", "device_id", data_type="VARCHAR", semantic_type="ID", is_primary_key=True),
        registry_column("telemetry", "voltage", data_type="REAL", semantic_type="NUMERIC_MEASURE", is_measure=True),
        registry_column("telemetry", "temperature", data_type="REAL", semantic_type="NUMERIC_MEASURE", is_measure=True),
    ]


# ============================================================
# 1. ECOMMERCE ATOMIC RECIPES
# ============================================================

def test_ecommerce_generates_total_revenue(multi_table_registry):
    mapping = {"revenue": "orders.total_amount"}
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    revenue_kpis = [r for r in res.recipes if r.metric_id == "total_revenue"]
    assert len(revenue_kpis) == 1
    k = revenue_kpis[0]
    assert isinstance(k, AtomicMetricRecipe)
    assert k.operand.target_ref == "orders.total_amount"
    assert k.operand.aggregation == "SUM"
    assert k.format == "currency"


def test_ecommerce_generates_order_count(multi_table_registry):
    mapping = {"order_id": "orders.order_id"}
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    order_kpis = [r for r in res.recipes if r.metric_id == "total_orders"]
    assert len(order_kpis) == 1
    k = order_kpis[0]
    assert isinstance(k, AtomicMetricRecipe)
    assert k.operand.target_ref == "orders.order_id"
    assert k.operand.aggregation == "COUNT_DISTINCT"


def test_ecommerce_generates_unique_customers(multi_table_registry):
    mapping = {"customer_id": "orders.customer_id"}
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    cust_kpis = [r for r in res.recipes if r.metric_id == "unique_customers"]
    assert len(cust_kpis) == 1
    k = cust_kpis[0]
    assert isinstance(k, AtomicMetricRecipe)
    assert k.operand.target_ref == "orders.customer_id"
    assert k.operand.aggregation == "COUNT_DISTINCT"


# ============================================================
# 2. AOV RATIO RECIPE & MISSING DEPENDENCY
# ============================================================

def test_ecommerce_generates_aov_when_dependencies_exist(multi_table_registry):
    mapping = {
        "revenue": "orders.total_amount",
        "order_id": "orders.order_id",
    }
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    aov_kpis = [r for r in res.recipes if r.metric_id == "aov"]
    assert len(aov_kpis) == 1
    k = aov_kpis[0]
    assert isinstance(k, RatioMetricRecipe)
    assert k.numerator.target_ref == "orders.total_amount"
    assert k.numerator.aggregation == "SUM"
    assert k.denominator.target_ref == "orders.order_id"
    assert k.denominator.aggregation == "COUNT_DISTINCT"
    assert k.zero_division == "null"
    assert k.format == "currency"


def test_aov_skipped_when_order_id_missing(multi_table_registry):
    # Only revenue is confirmed, order_id is missing
    mapping = {"revenue": "orders.total_amount"}
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    generated_ids = {r.metric_id for r in res.recipes}
    assert "aov" not in generated_ids

    skipped_aov = [s for s in res.skipped if s.metric_id == "aov"]
    assert len(skipped_aov) == 1
    assert "Required confirmed mapping 'order_id' is missing." in skipped_aov[0].reason


# ============================================================
# 3. GROSS PROFIT DIFFERENCE RECIPE & MISSING COST
# ============================================================

def test_gross_profit_generated_when_revenue_and_cost_exist(multi_table_registry):
    mapping = {
        "revenue": "orders.total_amount",
        "cost": "orders.total_cost",
    }
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    profit_kpis = [r for r in res.recipes if r.metric_id == "gross_profit"]
    assert len(profit_kpis) == 1
    k = profit_kpis[0]
    assert isinstance(k, DifferenceMetricRecipe)
    assert k.left.target_ref == "orders.total_amount"
    assert k.left.aggregation == "SUM"
    assert k.right.target_ref == "orders.total_cost"
    assert k.right.aggregation == "SUM"
    assert k.format == "currency"


def test_gross_profit_skipped_when_cost_missing(multi_table_registry):
    mapping = {"revenue": "orders.total_amount"}
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    generated_ids = {r.metric_id for r in res.recipes}
    assert "gross_profit" not in generated_ids

    skipped_profit = [s for s in res.skipped if s.metric_id == "gross_profit"]
    assert len(skipped_profit) == 1
    assert "Required confirmed mapping 'cost' is missing." in skipped_profit[0].reason


# ============================================================
# 4. DOMAIN ISOLATION & NO FALLBACK
# ============================================================

def test_unknown_domain_does_not_fall_back_to_ecommerce(multi_table_registry):
    mapping = {
        "revenue": "orders.total_amount",
        "order_id": "orders.order_id",
    }
    res = generate_metric_recipes(
        domain_key="completely_unknown_domain_xyz",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    # Unknown domain must return empty recipes without falling back to ecommerce
    assert res.recipes == []
    assert res.skipped == []


def test_generic_dataset_generates_no_fake_business_kpis(multi_table_registry):
    mapping = {
        "voltage": "telemetry.voltage",
        "temperature": "telemetry.temperature",
    }
    res = generate_metric_recipes(
        domain_key="generic",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    assert res.recipes == []
    assert res.skipped == []


def test_healthcare_does_not_generate_ecommerce_kpis(multi_table_registry):
    mapping = {
        "patient_id": "encounters.patient_id",
        "encounter_id": "encounters.appointment_id",
        "billing_amount": "encounters.billing_amount",
    }
    res = generate_metric_recipes(
        domain_key="healthcare",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    recipe_ids = {r.metric_id for r in res.recipes}
    assert recipe_ids == {"total_encounters", "unique_patients", "avg_treatment_charge"}
    assert "total_revenue" not in recipe_ids
    assert "total_orders" not in recipe_ids
    assert "aov" not in recipe_ids


# ============================================================
# 5. ZERO INFERENCE & ZERO FUZZY MATCHING
# ============================================================

def test_generator_never_invents_column(multi_table_registry):
    # Mapping has no revenue, but registry has tax_amount
    mapping = {"order_id": "orders.order_id"}
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    generated_targets = {
        getattr(r, "operand", getattr(r, "numerator", None)).target_ref  # type: ignore
        for r in res.recipes
    }
    assert "orders.tax_amount" not in generated_targets
    assert {r.metric_id for r in res.recipes} == {"total_orders"}


def test_generator_never_fuzzy_matches_missing_mapping(multi_table_registry):
    # User passed typo "rev" instead of "revenue"
    mapping = {"rev": "orders.total_amount", "order_id": "orders.order_id"}
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    generated_ids = {r.metric_id for r in res.recipes}
    assert "total_revenue" not in generated_ids
    assert "total_orders" in generated_ids


def test_only_confirmed_mapping_is_consumed(multi_table_registry):
    # Mapping specifies order_id only; all other unconfirmed columns in registry are ignored
    mapping = {"order_id": "orders.order_id"}
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    assert len(res.recipes) == 1
    assert res.recipes[0].metric_id == "total_orders"


# ============================================================
# 6. SEMANTIC VALIDATION INTEGRATION
# ============================================================

def test_sum_identifier_rule_is_rejected_by_phase2a_validator(multi_table_registry):
    # Adversarial mapping: User confirmed identifier order_id as revenue
    mapping = {
        "revenue": "orders.order_id",  # ID column!
    }
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    # Must fail Phase 2A validator through Phase 1.5 semantic rule
    generated_ids = {r.metric_id for r in res.recipes}
    assert "total_revenue" not in generated_ids

    skipped_rev = [s for s in res.skipped if s.metric_id == "total_revenue"]
    assert len(skipped_rev) == 1
    assert "Cannot apply 'SUM' to identifier column" in skipped_rev[0].reason


# ============================================================
# 7. CROSS-TABLE DERIVED RECIPES REJECTED
# ============================================================

def test_cross_table_ratio_is_skipped(multi_table_registry):
    # revenue from orders, order_id from customers table
    mapping = {
        "revenue": "orders.total_amount",
        "order_id": "customers.id",  # Cross-table!
    }
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    generated_ids = {r.metric_id for r in res.recipes}
    assert "aov" not in generated_ids

    skipped_aov = [s for s in res.skipped if s.metric_id == "aov"]
    assert len(skipped_aov) == 1
    assert "Cross-table derived metrics require a validated relationship path." in skipped_aov[0].reason


def test_cross_table_difference_is_skipped(multi_table_registry):
    # revenue from orders, cost from customers
    mapping = {
        "revenue": "orders.total_amount",
        "cost": "customers.id",  # Cross-table!
    }
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    generated_ids = {r.metric_id for r in res.recipes}
    assert "gross_profit" not in generated_ids

    skipped_profit = [s for s in res.skipped if s.metric_id == "gross_profit"]
    assert len(skipped_profit) == 1
    assert "Cross-table derived metrics require a validated relationship path." in skipped_profit[0].reason


# ============================================================
# 8. DUPLICATES, DETERMINISM & STABILITY
# ============================================================

def test_duplicate_metric_id_not_generated_twice(multi_table_registry):
    from services.metric_recipe_generator import _generate_metric_recipes_from_rules
    # Inject two rules sharing the exact same metric_id
    duplicate_rules = (
        AtomicRecipeRule(
            metric_id="total_rev",
            title="Total Revenue 1",
            mapping_key="revenue",
            aggregation="SUM",
        ),
        AtomicRecipeRule(
            metric_id="total_rev",
            title="Total Revenue Duplicate",
            mapping_key="revenue",
            aggregation="SUM",
        ),
    )
    mapping = {"revenue": "orders.total_amount"}
    res = _generate_metric_recipes_from_rules(
        rules=duplicate_rules,
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    assert len(res.recipes) == 1
    assert res.recipes[0].metric_id == "total_rev"
    assert len(res.skipped) == 1
    assert "Duplicate metric_id 'total_rev'" in res.skipped[0].reason


def test_output_order_is_deterministic(multi_table_registry):
    mapping = {
        "revenue": "orders.total_amount",
        "order_id": "orders.order_id",
        "customer_id": "orders.customer_id",
        "cost": "orders.total_cost",
    }
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    recipe_ids = [r.metric_id for r in res.recipes]
    assert recipe_ids == [
        "total_revenue",
        "total_orders",
        "aov",
        "unique_customers",
        "gross_profit",
    ]


def test_generation_is_identical_across_repeated_runs(multi_table_registry):
    mapping = {
        "revenue": "orders.total_amount",
        "order_id": "orders.order_id",
        "customer_id": "orders.customer_id",
        "cost": "orders.total_cost",
    }
    first_run = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    for _ in range(5):
        subsequent = generate_metric_recipes(
            domain_key="ecommerce",
            confirmed_mapping=mapping,
            registry_entries=multi_table_registry,
        )
        assert [r.model_dump() for r in subsequent.recipes] == [r.model_dump() for r in first_run.recipes]
        assert [s.model_dump() for s in subsequent.skipped] == [s.model_dump() for s in first_run.skipped]


# ============================================================
# 9. SECURITY & REJECTION OF ARBITRARY FORMULA / SQL
# ============================================================

def test_no_sql_formula_or_expression_appears_in_serialized_recipes(multi_table_registry):
    mapping = {
        "revenue": "orders.total_amount",
        "order_id": "orders.order_id",
        "cost": "orders.total_cost",
    }
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=multi_table_registry,
    )
    forbidden_tokens = ["sql", "formula", "expression", "query", "python", "code", "eval", "raw_sql"]

    for recipe in res.recipes:
        serialized_dict = metric_recipe_to_dict(recipe)
        serialized_json = metric_recipe_to_json(recipe)

        for key in serialized_dict.keys():
            assert key.lower() not in forbidden_tokens

        # Check raw JSON string keys
        raw_keys = list(json.loads(serialized_json).keys())
        for k in raw_keys:
            assert k.lower() not in forbidden_tokens


# ============================================================
# 10. WHITELIST DRIFT REGRESSION GUARD
# ============================================================

def test_recipe_aggregation_contract_matches_runtime_policy():
    """
    Prevents silent drift between MetricRecipe AggregationType Literal
    and canonical metric_semantics ALLOWED_AGGREGATIONS policy.
    """
    assert set(get_args(AggregationType)) == set(ALLOWED_AGGREGATIONS)
