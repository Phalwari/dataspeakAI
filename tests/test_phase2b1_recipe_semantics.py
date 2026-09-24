import inspect
import os
import sys
from types import SimpleNamespace
from typing import get_args

# Setup backend import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pytest
from pydantic import ValidationError

from services.domain_templates import _DOMAIN_REGISTRY, ECOMMERCE_TEMPLATE, SAAS_TEMPLATE, KpiRecipe
from services.metric_recipes import (
    AtomicMetricRecipe,
    MetricRecipeValidationError,
    RatioMetricRecipe,
)
from services.metric_recipe_generator import (
    AtomicRecipeRule,
    MissingMappingError,
    build_domain_recipe_rules,
    generate_metric_recipes,
    _generate_metric_recipes_from_rules,
)


# ============================================================
# TEST REGISTRY FIXTURE
# ============================================================

def make_col(
    table_name: str,
    column_name: str,
    *,
    data_type: str = "REAL",
    semantic_type: str = "NUMERIC_MEASURE",
    is_primary_key: bool = False,
    is_foreign_key: bool = False,
    is_measure: bool = True,
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
def mock_registry():
    return [
        # Orders / Subscriptions table
        make_col("orders", "order_id", data_type="INTEGER", semantic_type="ID", is_primary_key=True, is_measure=False),
        make_col("orders", "customer_id", data_type="INTEGER", semantic_type="ID", is_foreign_key=True, is_measure=False),
        make_col("orders", "total_amount", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
        make_col("orders", "total_cost", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
        make_col("subscriptions", "subscription_id", data_type="INTEGER", semantic_type="ID", is_primary_key=True, is_measure=False),
        make_col("subscriptions", "mrr", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
        # Healthcare table
        make_col("encounters", "encounter_id", data_type="INTEGER", semantic_type="ID", is_primary_key=True, is_measure=False),
        make_col("encounters", "appointment_id", data_type="INTEGER", semantic_type="ID", is_foreign_key=True, is_measure=False),
        make_col("encounters", "patient_id", data_type="INTEGER", semantic_type="ID", is_foreign_key=True, is_measure=False),
        make_col("encounters", "billing_amount", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
    ]


# ============================================================
# 1. MRR NEVER SILENTLY SATISFIES REVENUE
# ============================================================

def test_mrr_never_silently_satisfies_revenue(mock_registry):
    """
    P0 Issue 1: If mapping has 'mrr' but 'revenue' is missing,
    total_revenue must NOT be generated via silent concept substitution (SUM(mrr)).
    Instead, total_revenue must be skipped with a structured MissingMappingError reason.
    """
    mapping = {
        "mrr": "subscriptions.mrr",
        "order_id": "orders.order_id",
    }
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=mock_registry,
    )

    generated_ids = {r.metric_id for r in res.recipes}
    assert "total_revenue" not in generated_ids

    skipped_rev = [s for s in res.skipped if s.metric_id == "total_revenue"]
    assert len(skipped_rev) == 1
    assert "Required confirmed mapping 'revenue' is missing." in skipped_rev[0].reason


# ============================================================
# 2. ENCOUNTER_ID NEVER SILENTLY SATISFIES APPOINTMENT_ID
# ============================================================

def test_encounter_id_never_silently_satisfies_appointment_id(mock_registry):
    """
    Semantic concept substitution must never occur across appointment_id and encounter_id.
    If a domain requires appointment_id, encounter_id cannot satisfy it.
    If healthcare requires encounter_id, appointment_id cannot satisfy it.
    """
    # Healthcare template canonical required_variables is 'encounter_id'.
    # If the user only confirmed 'appointment_id', total_encounters must NOT be generated.
    mapping = {
        "appointment_id": "encounters.appointment_id",
        "patient_id": "encounters.patient_id",
    }
    res = generate_metric_recipes(
        domain_key="healthcare",
        confirmed_mapping=mapping,
        registry_entries=mock_registry,
    )

    generated_ids = {r.metric_id for r in res.recipes}
    assert "total_encounters" not in generated_ids

    skipped_enc = [s for s in res.skipped if s.metric_id == "total_encounters"]
    assert len(skipped_enc) == 1
    assert "Required confirmed mapping 'encounter_id' is missing." in skipped_enc[0].reason


# ============================================================
# 3. TRANSACTION_AMOUNT NEVER SILENTLY SATISFIES AMOUNT
# ============================================================

def test_transaction_amount_never_silently_satisfies_amount(mock_registry):
    """
    Concept substitution between 'transaction_amount' and 'amount' must never happen.
    """
    test_rule = AtomicRecipeRule(
        metric_id="total_amount",
        title="Total Amount",
        mapping_key="amount",
        aggregation="SUM",
    )
    # Mapping contains transaction_amount, NOT amount
    mapping = {"transaction_amount": "orders.total_amount"}

    res = _generate_metric_recipes_from_rules(
        rules=(test_rule,),
        confirmed_mapping=mapping,
        registry_entries=mock_registry,
    )

    assert len(res.recipes) == 0
    assert len(res.skipped) == 1
    assert res.skipped[0].metric_id == "total_amount"
    assert "Required confirmed mapping 'amount' is missing." in res.skipped[0].reason


# ============================================================
# 4. ACTIVE SUBSCRIPTION NOT GENERATED WITHOUT FILTER CONDITION
# ============================================================

def test_active_subscription_not_generated_without_filter_condition(mock_registry):
    """
    P0 Issue 2: COUNT_DISTINCT(subscription_id) without a status filter
    calculates total subscriptions, NOT active subscriptions.
    Must be explicitly skipped with a structured reason until filter-aware recipes exist.
    """
    mapping = {
        "subscription_id": "subscriptions.subscription_id",
        "mrr": "subscriptions.mrr",
    }
    res = generate_metric_recipes(
        domain_key="saas",
        confirmed_mapping=mapping,
        registry_entries=mock_registry,
    )

    generated_ids = {r.metric_id for r in res.recipes}
    assert "active_subscriptions" not in generated_ids

    skipped_active = [s for s in res.skipped if s.metric_id == "active_subscriptions"]
    assert len(skipped_active) == 1
    assert "Metric requires a status/filter condition not supported by the Phase 2A recipe contract." in skipped_active[0].reason

    # Verify that valid filter-free metrics in saas (total_mrr, arpu) are generated properly
    assert "total_mrr" in generated_ids
    assert "arpu" in generated_ids


# ============================================================
# 5. AOV PRESERVES CANONICAL TEMPLATE METRIC ID
# ============================================================

def test_aov_preserves_canonical_template_metric_id(mock_registry):
    """
    Issue 3: Average Order Value must keep the canonical template ID 'aov'
    from domain_templates.py, NOT a fabricated 'average_order_value'.
    """
    mapping = {
        "revenue": "orders.total_amount",
        "order_id": "orders.order_id",
    }
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=mock_registry,
    )

    recipe_map = {r.metric_id: r for r in res.recipes}
    assert "aov" in recipe_map
    assert "average_order_value" not in recipe_map

    aov_recipe = recipe_map["aov"]
    assert isinstance(aov_recipe, RatioMetricRecipe)
    assert aov_recipe.title == "Average Order Value"
    assert aov_recipe.format == "currency"


# ============================================================
# 6. ATOMIC METADATA IS SOURCED FROM DOMAIN_TEMPLATES
# ============================================================

def test_atomic_metadata_is_sourced_from_domain_templates(mock_registry):
    """
    Issue 3: Atomic rules must dynamically read metadata (title, format, description,
    aggregation, variable) directly from domain_templates.py.
    """
    rules = build_domain_recipe_rules("ecommerce")
    rule_map = {r.metric_id: r for r in rules if isinstance(r, AtomicRecipeRule)}

    # Check total_revenue against ECOMMERCE_TEMPLATE
    template_kpi = next(k for k in ECOMMERCE_TEMPLATE.kpis if k.id == "total_revenue")
    rev_rule = rule_map["total_revenue"]
    assert rev_rule.title == template_kpi.title
    assert rev_rule.aggregation == template_kpi.aggregation
    assert rev_rule.mapping_key == template_kpi.required_variables[0]
    assert rev_rule.format == template_kpi.format
    assert rev_rule.description == template_kpi.description

    # Check total_orders against ECOMMERCE_TEMPLATE
    template_orders = next(k for k in ECOMMERCE_TEMPLATE.kpis if k.id == "total_orders")
    orders_rule = rule_map["total_orders"]
    assert orders_rule.title == template_orders.title
    assert orders_rule.aggregation == template_orders.aggregation
    assert orders_rule.mapping_key == template_orders.required_variables[0]


# ============================================================
# 7. CHANGING TEMPLATE METADATA IS REFLECTED WITHOUT DUPLICATE RULE EDIT
# ============================================================

def test_template_metadata_change_is_reflected_by_generator(mock_registry):
    """
    Proves single-source-of-truth: modifying a template KPI in domain_templates
    is immediately reflected by build_domain_recipe_rules() and generated recipes
    without maintaining or editing a separate parallel dictionary.
    """
    target_kpi = next(k for k in ECOMMERCE_TEMPLATE.kpis if k.id == "total_revenue")
    original_title = target_kpi.title
    try:
        target_kpi.title = "Dynamically Modified Gross Sales"
        rules = build_domain_recipe_rules("ecommerce")
        rev_rule = next(r for r in rules if r.metric_id == "total_revenue")
        assert rev_rule.title == "Dynamically Modified Gross Sales"

        mapping = {"revenue": "orders.total_amount"}
        res = generate_metric_recipes(
            domain_key="ecommerce",
            confirmed_mapping=mapping,
            registry_entries=mock_registry,
        )
        gen_rev = next(r for r in res.recipes if r.metric_id == "total_revenue")
        assert gen_rev.title == "Dynamically Modified Gross Sales"
    finally:
        target_kpi.title = original_title


# ============================================================
# 8. MISSING MAPPING CREATES STRUCTURED SKIP
# ============================================================

def test_missing_mapping_creates_structured_skip(mock_registry):
    """
    Missing required confirmed mappings must be cleanly skipped with structured reason.
    """
    mapping = {}  # completely empty mapping
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=mock_registry,
    )
    assert len(res.recipes) == 0
    assert len(res.skipped) > 0

    skipped_ids = {s.metric_id for s in res.skipped}
    assert "total_revenue" in skipped_ids
    assert "total_orders" in skipped_ids
    assert "aov" in skipped_ids


# ============================================================
# 9. UNEXPECTED PROGRAMMER VALUEERROR PROPAGATES
# ============================================================

def test_unexpected_programmer_value_error_propagates(mock_registry, monkeypatch):
    """
    Issue 4: Broad ValueError was removed. An unexpected ValueError caused by
    a bug or syntax issue inside rule building must NOT be swallowed into SkippedMetric.
    It must propagate up and fail loudly.
    """
    def broken_build_recipe(rule, confirmed_mapping):
        raise ValueError("Simulated programmer bug / unexpected exception!")

    import services.metric_recipe_generator as gen_module
    monkeypatch.setattr(gen_module, "_build_recipe_from_rule", broken_build_recipe)

    with pytest.raises(ValueError, match="Simulated programmer bug / unexpected exception!"):
        generate_metric_recipes(
            domain_key="ecommerce",
            confirmed_mapping={"revenue": "orders.total_amount"},
            registry_entries=mock_registry,
        )


# ============================================================
# 10. EXPECTED SEMANTIC VALIDATION ERRORS CREATE STRUCTURED SKIP
# ============================================================

def test_semantic_validation_errors_create_structured_skip(mock_registry):
    """
    Legitimate domain contract errors (MetricRecipeValidationError, ValidationError, MissingMappingError)
    must still be caught and transformed into a SkippedMetric.
    """
    # Identifier passed for SUM aggregation triggers MetricRecipeValidationError
    bad_mapping = {"revenue": "orders.order_id"}  # order_id is ID column, cannot SUM
    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=bad_mapping,
        registry_entries=mock_registry,
    )
    skipped_rev = [s for s in res.skipped if s.metric_id == "total_revenue"]
    assert len(skipped_rev) == 1
    assert "Cannot apply 'SUM' to identifier column" in skipped_rev[0].reason


# ============================================================
# 11. NO PUBLIC ARBITRARY-RULE OVERRIDE EXISTS
# ============================================================

def test_no_public_arbitrary_rule_override_exists():
    """
    Issue 6: The public generate_metric_recipes() function signature must NOT allow
    callers to inject arbitrary rules. Rules must resolve internally from domain templates.
    """
    sig = inspect.signature(generate_metric_recipes)
    assert "rules" not in sig.parameters
    assert set(sig.parameters.keys()) == {"domain_key", "confirmed_mapping", "registry_entries"}


# ============================================================
# 12. OUTPUT REMAINS DETERMINISTIC
# ============================================================

def test_output_remains_deterministic(mock_registry):
    """
    Deterministic order and contents must be strictly maintained across multiple runs.
    """
    mapping = {
        "revenue": "orders.total_amount",
        "order_id": "orders.order_id",
        "customer_id": "orders.customer_id",
        "cost": "orders.total_cost",
    }
    first = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping=mapping,
        registry_entries=mock_registry,
    )
    for _ in range(5):
        current = generate_metric_recipes(
            domain_key="ecommerce",
            confirmed_mapping=mapping,
            registry_entries=mock_registry,
        )
        assert [r.metric_id for r in current.recipes] == [r.metric_id for r in first.recipes]
        assert [r.model_dump() for r in current.recipes] == [r.model_dump() for r in first.recipes]
        assert [s.model_dump() for s in current.skipped] == [s.model_dump() for s in first.skipped]
