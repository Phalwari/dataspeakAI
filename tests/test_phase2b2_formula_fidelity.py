import inspect
import os
import sys
from types import SimpleNamespace

# Setup backend import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pytest

from services.domain_templates import (
    DomainTemplate,
    KpiRecipe,
    get_domain_template,
)
from services.metric_recipes import (
    AtomicMetricRecipe,
    RatioMetricRecipe,
)
from services.metric_recipe_generator import (
    AtomicRecipeRule,
    DeferredRecipeRule,
    _atomic_rule_from_template,
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
        make_col("orders", "order_id", data_type="INTEGER", semantic_type="ID", is_primary_key=True, is_measure=False),
        make_col("orders", "total_amount", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
        make_col("orders", "total_cost", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
        make_col("subscriptions", "subscription_id", data_type="INTEGER", semantic_type="ID", is_primary_key=True, is_measure=False),
        make_col("subscriptions", "mrr", data_type="REAL", semantic_type="CURRENCY", is_measure=True),
    ]


# ============================================================
# 1. SUM({revenue}) BECOMES ATOMIC RECIPE RULE
# ============================================================

def test_sum_revenue_becomes_atomic_recipe_rule():
    kpi = KpiRecipe(
        id="total_revenue",
        title="Total Revenue",
        formula_template="SUM({revenue})",
        required_variables=["revenue"],
        aggregation="SUM",
        format="currency",
    )
    rule = _atomic_rule_from_template(kpi)
    assert isinstance(rule, AtomicRecipeRule)
    assert rule.metric_id == "total_revenue"
    assert rule.mapping_key == "revenue"
    assert rule.aggregation == "SUM"
    assert rule.format == "currency"


# ============================================================
# 2. WHITESPACE AROUND SIMPLE FORMULA STILL WORKS
# ============================================================

def test_whitespace_around_simple_formula_still_works():
    kpi = KpiRecipe(
        id="spaced_metric",
        title="Spaced Metric",
        formula_template="   SUM(   {revenue}   )   ",
        required_variables=["revenue"],
        aggregation="SUM",
        format="currency",
    )
    rule = _atomic_rule_from_template(kpi)
    assert isinstance(rule, AtomicRecipeRule)
    assert rule.metric_id == "spaced_metric"
    assert rule.mapping_key == "revenue"
    assert rule.aggregation == "SUM"


# ============================================================
# 3. AGGREGATION MISMATCH IS DEFERRED
# ============================================================

def test_aggregation_mismatch_is_deferred():
    kpi = KpiRecipe(
        id="mismatched_agg",
        title="Mismatched Aggregation",
        formula_template="AVG({revenue})",
        required_variables=["revenue"],
        aggregation="SUM",  # Declared SUM, but formula is AVG
        format="currency",
    )
    rule = _atomic_rule_from_template(kpi)
    assert isinstance(rule, DeferredRecipeRule)
    assert rule.metric_id == "mismatched_agg"
    assert "Template formula aggregation does not match the declared aggregation." in rule.reason


# ============================================================
# 4. PLACEHOLDER / REQUIRED-VARIABLE MISMATCH IS DEFERRED
# ============================================================

def test_placeholder_variable_mismatch_is_deferred():
    kpi = KpiRecipe(
        id="mismatched_var",
        title="Mismatched Variable",
        formula_template="SUM({sales})",  # Formula specifies sales
        required_variables=["revenue"],   # Declared required variable is revenue
        aggregation="SUM",
        format="currency",
    )
    rule = _atomic_rule_from_template(kpi)
    assert isinstance(rule, DeferredRecipeRule)
    assert rule.metric_id == "mismatched_var"
    assert "Template formula variable does not match required_variables." in rule.reason


# ============================================================
# 5. MULTIPLE REQUIRED VARIABLES ARE DEFERRED WITHOUT TYPED OVERRIDE
# ============================================================

def test_multiple_required_variables_are_deferred():
    kpi = KpiRecipe(
        id="multi_var",
        title="Multi Variable Metric",
        formula_template="SUM({revenue}) - SUM({cost})",
        required_variables=["revenue", "cost"],
        aggregation="SUM",
        format="currency",
    )
    rule = _atomic_rule_from_template(kpi)
    assert isinstance(rule, DeferredRecipeRule)
    assert rule.metric_id == "multi_var"
    assert "Template requires multiple semantic variables and needs a typed derived recipe." in rule.reason


# ============================================================
# 6. FORMULA CONTAINING DIVISION IS NOT ATOMIC
# ============================================================

def test_formula_containing_division_is_not_atomic():
    kpi = KpiRecipe(
        id="raw_ratio",
        title="Raw Ratio",
        formula_template="SUM({revenue}) / COUNT({order_id})",
        required_variables=["revenue"],
        aggregation="SUM",
        format="ratio",
    )
    rule = _atomic_rule_from_template(kpi)
    assert isinstance(rule, DeferredRecipeRule)
    assert rule.metric_id == "raw_ratio"
    assert "Template formula contains semantics not supported by a simple atomic MetricRecipe." in rule.reason


# ============================================================
# 7. FORMULA CONTAINING SUBTRACTION IS NOT ATOMIC
# ============================================================

def test_formula_containing_subtraction_is_not_atomic():
    kpi = KpiRecipe(
        id="raw_diff",
        title="Raw Difference",
        formula_template="SUM({revenue}) - SUM({cost})",
        required_variables=["revenue"],
        aggregation="SUM",
        format="currency",
    )
    rule = _atomic_rule_from_template(kpi)
    assert isinstance(rule, DeferredRecipeRule)
    assert rule.metric_id == "raw_diff"
    assert "Template formula contains semantics not supported by a simple atomic MetricRecipe." in rule.reason


# ============================================================
# 8. FORMULA CONTAINING WHERE IS NOT ATOMIC
# ============================================================

def test_formula_containing_where_is_not_atomic():
    kpi = KpiRecipe(
        id="filtered_metric",
        title="Filtered Metric",
        formula_template="COUNT({order_id}) WHERE {status} = 'active'",
        required_variables=["order_id"],
        aggregation="COUNT",
        format="number",
    )
    rule = _atomic_rule_from_template(kpi)
    assert isinstance(rule, DeferredRecipeRule)
    assert rule.metric_id == "filtered_metric"
    assert "Template formula contains semantics not supported by a simple atomic MetricRecipe." in rule.reason


# ============================================================
# 9. FORMULA CONTAINING CASE IS NOT ATOMIC
# ============================================================

def test_formula_containing_case_is_not_atomic():
    kpi = KpiRecipe(
        id="case_metric",
        title="Conditional Case Metric",
        formula_template="SUM(CASE WHEN {status} = 'paid' THEN {amount} ELSE 0 END)",
        required_variables=["amount"],
        aggregation="SUM",
        format="currency",
    )
    rule = _atomic_rule_from_template(kpi)
    assert isinstance(rule, DeferredRecipeRule)
    assert rule.metric_id == "case_metric"
    assert "Template formula contains semantics not supported by a simple atomic MetricRecipe." in rule.reason


# ============================================================
# 10. ACTIVE_SUBSCRIPTIONS REMAINS DEFERRED
# ============================================================

def test_active_subscriptions_remains_deferred(mock_registry):
    rules = build_domain_recipe_rules("saas")
    rule_map = {r.metric_id: r for r in rules}
    assert "active_subscriptions" in rule_map
    assert isinstance(rule_map["active_subscriptions"], DeferredRecipeRule)
    assert "Metric requires a status/filter condition not supported by the Phase 2A recipe contract." in rule_map["active_subscriptions"].reason

    res = generate_metric_recipes(
        domain_key="saas",
        confirmed_mapping={"subscription_id": "subscriptions.subscription_id", "mrr": "subscriptions.mrr"},
        registry_entries=mock_registry,
    )
    assert "active_subscriptions" not in {r.metric_id for r in res.recipes}
    skipped = [s for s in res.skipped if s.metric_id == "active_subscriptions"]
    assert len(skipped) == 1
    assert "Metric requires a status/filter condition not supported by the Phase 2A recipe contract." in skipped[0].reason


# ============================================================
# 11. AOV TYPED RATIO OVERRIDE STILL WINS
# ============================================================

def test_aov_typed_ratio_override_still_wins(mock_registry):
    rules = build_domain_recipe_rules("ecommerce")
    aov_rule = next(r for r in rules if r.metric_id == "aov")
    assert not isinstance(aov_rule, DeferredRecipeRule)
    assert not isinstance(aov_rule, AtomicRecipeRule)
    # Must be the RatioRecipeRule from DERIVED_RECIPE_OVERRIDES
    assert aov_rule.metric_id == "aov"

    res = generate_metric_recipes(
        domain_key="ecommerce",
        confirmed_mapping={"revenue": "orders.total_amount", "order_id": "orders.order_id"},
        registry_entries=mock_registry,
    )
    aov_recipe = next(r for r in res.recipes if r.metric_id == "aov")
    assert isinstance(aov_recipe, RatioMetricRecipe)
    assert aov_recipe.metric_id == "aov"
    assert aov_recipe.numerator.aggregation == "SUM"
    assert aov_recipe.denominator.aggregation == "COUNT_DISTINCT"


# ============================================================
# 12. DEFERRED RULES CREATE STRUCTURED SKIPPEDMETRIC
# ============================================================

def test_deferred_rules_create_structured_skipped_metric(mock_registry):
    custom_rules = (
        DeferredRecipeRule(
            metric_id="unsupported_kpi",
            title="Unsupported KPI",
            reason="Custom deferred reason: formula contains unsupported window function.",
        ),
    )
    res = _generate_metric_recipes_from_rules(
        rules=custom_rules,
        confirmed_mapping={"dummy": "orders.total_amount"},
        registry_entries=mock_registry,
    )
    assert len(res.recipes) == 0
    assert len(res.skipped) == 1
    assert res.skipped[0].metric_id == "unsupported_kpi"
    assert res.skipped[0].reason == "Custom deferred reason: formula contains unsupported window function."


# ============================================================
# 13. UNKNOWN DOMAIN REMAINS EMPTY
# ============================================================

def test_unknown_domain_remains_empty(mock_registry):
    res = generate_metric_recipes(
        domain_key="non_existent_fake_domain",
        confirmed_mapping={"revenue": "orders.total_amount"},
        registry_entries=mock_registry,
    )
    assert res.recipes == []
    assert res.skipped == []


# ============================================================
# 14. PUBLIC GET_DOMAIN_TEMPLATE PATH IS USED
# ============================================================

def test_public_get_domain_template_path_is_used():
    import services.metric_recipe_generator as gen_mod
    # Verify _DOMAIN_REGISTRY is not imported or used in metric_recipe_generator
    assert not hasattr(gen_mod, "_DOMAIN_REGISTRY")
    # Verify get_domain_template is imported
    assert hasattr(gen_mod, "get_domain_template")
    assert gen_mod.get_domain_template is get_domain_template


# ============================================================
# 15. ALL EXISTING DOMAIN ATOMIC KPIS REMAIN VALID AND GREEN
# ============================================================

def test_canonical_domain_templates_pass_formula_fidelity():
    """
    Checks that every atomic KPI in canonical templates (ecommerce, saas, healthcare)
    that is not an override or filter-deferred parses cleanly into an AtomicRecipeRule.
    """
    for domain_id in ("ecommerce", "saas", "healthcare"):
        dt = get_domain_template(domain_id)
        for kpi in dt.kpis:
            if kpi.id in ("aov", "active_subscriptions"):
                continue  # Handled by override or filter-deferred
            rule = _atomic_rule_from_template(kpi)
            assert isinstance(
                rule, AtomicRecipeRule
            ), f"KPI '{kpi.id}' in domain '{domain_id}' failed formula fidelity: {getattr(rule, 'reason', None)}"
