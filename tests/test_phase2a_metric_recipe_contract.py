import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

# Setup backend import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pytest
from pydantic import ValidationError

from services.metric_recipes import (
    AtomicMetricOperand,
    AtomicMetricRecipe,
    RatioMetricRecipe,
    DifferenceMetricRecipe,
    MetricRecipeValidationError,
    parse_metric_recipe,
    metric_recipe_to_dict,
    metric_recipe_to_json,
    validate_recipe_against_registry,
    validate_recipe_for_connection,
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
def registry():
    return [
        registry_column(
            "orders",
            "order_id",
            data_type="INTEGER",
            semantic_type="ID",
            is_primary_key=True,
        ),
        registry_column(
            "orders",
            "customer_id",
            data_type="INTEGER",
            semantic_type="ID",
            is_foreign_key=True,
        ),
        registry_column(
            "orders",
            "total_amount",
            data_type="REAL",
            semantic_type="CURRENCY",
            is_measure=True,
        ),
        registry_column(
            "orders",
            "total_cost",
            data_type="REAL",
            semantic_type="CURRENCY",
            is_measure=True,
        ),
        registry_column(
            "orders",
            "margin_pct",
            data_type="REAL",
            semantic_type="PERCENTAGE",
            is_measure=True,
        ),
        registry_column(
            "orders",
            "created_at",
            data_type="DATETIME",
            semantic_type="DATETIME",
            is_dimension=True,
        ),
        registry_column(
            "customers",
            "id",
            data_type="INTEGER",
            semantic_type="ID",
            is_primary_key=True,
        ),
    ]


# ============================================================
# 1. VALID ATOMIC SUM
# ============================================================

def test_valid_atomic_sum_recipe(registry):
    recipe = AtomicMetricRecipe(
        metric_id="total_revenue",
        title="Total Revenue",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    validated = validate_recipe_against_registry(
        recipe,
        registry,
    )

    assert isinstance(validated, AtomicMetricRecipe)
    assert validated.metric_id == "total_revenue"
    assert validated.operand.aggregation == "SUM"


# ============================================================
# 2. VALID COUNT DISTINCT
# ============================================================

def test_valid_atomic_count_distinct(registry):
    recipe = AtomicMetricRecipe(
        metric_id="unique_customers",
        title="Unique Customers",
        format="integer",
        operand=AtomicMetricOperand(
            target_ref="orders.customer_id",
            aggregation="COUNT_DISTINCT",
        ),
    )

    validate_recipe_against_registry(
        recipe,
        registry,
    )


# ============================================================
# 3. VALID COUNT(*)
# ============================================================

def test_valid_count_wildcard(registry):
    recipe = AtomicMetricRecipe(
        metric_id="total_orders",
        title="Total Orders",
        format="integer",
        operand=AtomicMetricOperand(
            target_ref="orders.*",
            aggregation="COUNT",
        ),
    )

    validate_recipe_against_registry(
        recipe,
        registry,
    )


# ============================================================
# 4. SUM(*) REJECTED
# ============================================================

def test_sum_wildcard_rejected():
    with pytest.raises(ValidationError):
        AtomicMetricOperand(
            target_ref="orders.*",
            aggregation="SUM",
        )


# ============================================================
# 5. UNQUALIFIED TARGET REJECTED
# ============================================================

def test_unqualified_column_rejected():
    with pytest.raises(ValidationError):
        AtomicMetricOperand(
            target_ref="total_amount",
            aggregation="SUM",
        )


# ============================================================
# 6. MEDIAN REJECTED
# ============================================================

def test_median_rejected():
    with pytest.raises(ValidationError):
        AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="MEDIAN",
        )


# ============================================================
# 7. COMPUTED REJECTED
# ============================================================

def test_computed_rejected():
    with pytest.raises(ValidationError):
        AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="COMPUTED",
        )


# ============================================================
# 8. VALID AOV RATIO
# ============================================================

def test_valid_aov_ratio(registry):
    recipe = RatioMetricRecipe(
        metric_id="average_order_value",
        title="Average Order Value",
        format="currency",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    validate_recipe_against_registry(
        recipe,
        registry,
    )


# ============================================================
# 9. ZERO-DIVISION POLICY MUST BE EXPLICIT
# ============================================================

def test_ratio_zero_division_policy_required():
    with pytest.raises(ValidationError):
        RatioMetricRecipe.model_validate({
            "metric_id": "average_order_value",
            "title": "Average Order Value",
            "numerator": AtomicMetricOperand(
                target_ref="orders.total_amount",
                aggregation="SUM",
            ),
            "denominator": AtomicMetricOperand(
                target_ref="orders.order_id",
                aggregation="COUNT_DISTINCT",
            ),
        })


# ============================================================
# 10. CROSS-TABLE RATIO REJECTED
# ============================================================

def test_cross_table_ratio_rejected():
    with pytest.raises(ValidationError):
        RatioMetricRecipe(
            metric_id="invalid_ratio",
            title="Invalid Ratio",
            numerator=AtomicMetricOperand(
                target_ref="orders.total_amount",
                aggregation="SUM",
            ),
            denominator=AtomicMetricOperand(
                target_ref="customers.id",
                aggregation="COUNT_DISTINCT",
            ),
            zero_division="null",
        )


# ============================================================
# 11. VALID DIFFERENCE
# ============================================================

def test_valid_same_table_difference(registry):
    recipe = DifferenceMetricRecipe(
        metric_id="gross_profit",
        title="Gross Profit",
        format="currency",
        left=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        right=AtomicMetricOperand(
            target_ref="orders.total_cost",
            aggregation="SUM",
        ),
    )

    validate_recipe_against_registry(
        recipe,
        registry,
    )


# ============================================================
# 12. CROSS-TABLE DIFFERENCE REJECTED
# ============================================================

def test_cross_table_difference_rejected():
    with pytest.raises(ValidationError):
        DifferenceMetricRecipe(
            metric_id="bad_difference",
            title="Bad Difference",
            left=AtomicMetricOperand(
                target_ref="orders.total_amount",
                aggregation="SUM",
            ),
            right=AtomicMetricOperand(
                target_ref="customers.id",
                aggregation="COUNT",
            ),
        )


# ============================================================
# 13. UNKNOWN TABLE
# ============================================================

def test_unknown_table_rejected(registry):
    recipe = AtomicMetricRecipe(
        metric_id="bad_metric",
        title="Bad Metric",
        operand=AtomicMetricOperand(
            target_ref="payments.amount",
            aggregation="SUM",
        ),
    )

    with pytest.raises(
        MetricRecipeValidationError,
        match="Table 'payments'",
    ):
        validate_recipe_against_registry(
            recipe,
            registry,
        )


# ============================================================
# 14. UNKNOWN COLUMN
# ============================================================

def test_unknown_column_rejected(registry):
    recipe = AtomicMetricRecipe(
        metric_id="bad_metric",
        title="Bad Metric",
        operand=AtomicMetricOperand(
            target_ref="orders.fake_amount",
            aggregation="SUM",
        ),
    )

    with pytest.raises(
        MetricRecipeValidationError,
        match="fake_amount",
    ):
        validate_recipe_against_registry(
            recipe,
            registry,
        )


# ============================================================
# 15. SUM(ID) REJECTED
# ============================================================

def test_sum_identifier_rejected(registry):
    recipe = AtomicMetricRecipe(
        metric_id="bad_identifier_sum",
        title="Bad Identifier Sum",
        operand=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="SUM",
        ),
    )

    with pytest.raises(
        MetricRecipeValidationError,
    ):
        validate_recipe_against_registry(
            recipe,
            registry,
        )


# ============================================================
# 16. SUM(PERCENTAGE) REJECTED
# ============================================================

def test_sum_percentage_rejected(registry):
    recipe = AtomicMetricRecipe(
        metric_id="bad_margin_sum",
        title="Bad Margin Sum",
        operand=AtomicMetricOperand(
            target_ref="orders.margin_pct",
            aggregation="SUM",
        ),
    )

    with pytest.raises(
        MetricRecipeValidationError,
    ):
        validate_recipe_against_registry(
            recipe,
            registry,
        )


# ============================================================
# 17. COUNT DISTINCT ID ALLOWED
# ============================================================

def test_count_distinct_identifier_allowed(registry):
    recipe = AtomicMetricRecipe(
        metric_id="unique_customers",
        title="Unique Customers",
        operand=AtomicMetricOperand(
            target_ref="orders.customer_id",
            aggregation="COUNT_DISTINCT",
        ),
    )

    validate_recipe_against_registry(
        recipe,
        registry,
    )


# ============================================================
# 18. RAW SQL FIELD REJECTED
# ============================================================

def test_raw_sql_field_rejected():
    payload = {
        "recipe_version": "1.0",
        "metric_type": "atomic",
        "metric_id": "total_revenue",
        "title": "Total Revenue",
        "operand": {
            "target_ref": "orders.total_amount",
            "aggregation": "SUM",
        },
        "sql": "DROP TABLE orders;",
    }

    with pytest.raises(ValidationError):
        parse_metric_recipe(payload)


# ============================================================
# 19. FORMULA FIELD REJECTED
# ============================================================

def test_formula_field_rejected():
    payload = {
        "recipe_version": "1.0",
        "metric_type": "ratio",
        "metric_id": "average_order_value",
        "title": "Average Order Value",
        "numerator": {
            "target_ref": "orders.total_amount",
            "aggregation": "SUM",
        },
        "denominator": {
            "target_ref": "orders.order_id",
            "aggregation": "COUNT_DISTINCT",
        },
        "zero_division": "null",
        "formula": "SUM(total_amount) / COUNT(order_id)",
    }

    with pytest.raises(ValidationError):
        parse_metric_recipe(payload)


# ============================================================
# 20. SERIALIZATION ROUND-TRIP
# ============================================================

def test_serialization_round_trip_is_stable():
    original = RatioMetricRecipe(
        metric_id="average_order_value",
        title="Average Order Value",
        description="Revenue divided by distinct orders.",
        format="currency",
        reasoning="Canonical deterministic AOV recipe.",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    payload = metric_recipe_to_dict(original)

    restored = parse_metric_recipe(payload)

    assert metric_recipe_to_dict(restored) == payload

    assert (
        metric_recipe_to_json(restored)
        == metric_recipe_to_json(original)
    )


# ============================================================
# 21. CONNECTION-AWARE VALIDATION DEFENSE
# ============================================================

def test_validate_recipe_for_connection_unauthorized():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    recipe = AtomicMetricRecipe(
        metric_id="total_rev",
        title="Total Revenue",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    with pytest.raises(MetricRecipeValidationError, match="not found or unauthorized"):
        validate_recipe_for_connection(
            recipe,
            connection_id=999,
            tenant_id=1,
            db=mock_db,
        )
