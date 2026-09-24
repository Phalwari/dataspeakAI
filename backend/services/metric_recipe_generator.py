import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, ValidationError

from services.domain_templates import KpiRecipe, get_domain_template
from services.metric_recipes import (
    AtomicMetricOperand,
    AtomicMetricRecipe,
    DifferenceMetricRecipe,
    MetricRecipe,
    MetricRecipeValidationError,
    RatioMetricRecipe,
    validate_recipe_against_registry,
)
from services.metric_semantics import ALLOWED_AGGREGATIONS


# ============================================================
# RESULT TYPES
# ============================================================

class SkippedMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    reason: str


class MetricRecipeGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipes: list[MetricRecipe]
    skipped: list[SkippedMetric]


class MissingMappingError(ValueError):
    """Raised when an explicit confirmed mapping key is missing."""
    pass


# ============================================================
# INTERNAL DETERMINISTIC RULE TYPES
# ============================================================

@dataclass(frozen=True)
class AtomicRecipeRule:
    metric_id: str
    title: str
    mapping_key: str
    aggregation: str
    format: str = "number"
    description: str | None = None


@dataclass(frozen=True)
class RatioRecipeRule:
    metric_id: str
    title: str
    numerator_mapping_key: str
    numerator_aggregation: str
    denominator_mapping_key: str
    denominator_aggregation: str
    format: str = "ratio"
    description: str | None = None


@dataclass(frozen=True)
class DifferenceRecipeRule:
    metric_id: str
    title: str
    left_mapping_key: str
    left_aggregation: str
    right_mapping_key: str
    right_aggregation: str
    format: str = "number"
    description: str | None = None


@dataclass(frozen=True)
class DeferredRecipeRule:
    metric_id: str
    title: str
    reason: str


RecipeRule = (
    AtomicRecipeRule
    | RatioRecipeRule
    | DifferenceRecipeRule
    | DeferredRecipeRule
)


# ============================================================
# METRICS REQUIRING FILTER CONDITIONS NOT YET SUPPORTED
# ============================================================

FILTER_REQUIRED_METRIC_IDS: set[str] = {
    "active_subscriptions",
}


# ============================================================
# SIMPLE ATOMIC FORMULA GRAMMAR
# ============================================================

_SIMPLE_ATOMIC_FORMULA_RE = re.compile(
    r"^\s*"
    r"(?:"
        r"(SUM|AVG|MIN|MAX|COUNT_DISTINCT)\s*\(\s*\{([A-Za-z_][A-Za-z0-9_]*)\}\s*\)"
        r"|"
        r"COUNT\s*\(\s*(DISTINCT\s+)?\{([A-Za-z_][A-Za-z0-9_]*)\}\s*\)"
    r")"
    r"\s*$",
    re.IGNORECASE,
)


# ============================================================
# DERIVED RECIPE METADATA (PHASE 2 SPECIALIZATIONS)
# ============================================================

DERIVED_RECIPE_OVERRIDES: dict[str, dict[str, RecipeRule]] = {
    "ecommerce": {
        "aov": RatioRecipeRule(
            metric_id="aov",
            title="Average Order Value",
            numerator_mapping_key="revenue",
            numerator_aggregation="SUM",
            denominator_mapping_key="order_id",
            denominator_aggregation="COUNT_DISTINCT",
            format="currency",
            description="Total revenue divided by distinct orders.",
        ),
    }
}

EXTRA_DERIVED_RULES: dict[str, tuple[RecipeRule, ...]] = {
    "ecommerce": (
        DifferenceRecipeRule(
            metric_id="gross_profit",
            title="Gross Profit",
            left_mapping_key="revenue",
            left_aggregation="SUM",
            right_mapping_key="cost",
            right_aggregation="SUM",
            format="currency",
            description="Revenue minus cost.",
        ),
    )
}


# ============================================================
# SOURCE-OF-TRUTH DOMAIN TEMPLATE RULE ADAPTER
# ============================================================

def _atomic_rule_from_template(
    kpi_recipe: KpiRecipe,
) -> AtomicRecipeRule | DeferredRecipeRule:
    """
    Constructs an AtomicRecipeRule directly from a domain template KpiRecipe
    only when formula_template is provably a simple single atomic aggregation.
    Otherwise returns a DeferredRecipeRule describing the reason.
    """
    required_variables = list(kpi_recipe.required_variables or [])
    formula = (kpi_recipe.formula_template or "").strip()
    aggregation = (kpi_recipe.aggregation or "").strip().upper()

    # 1. Current atomic contract requires exactly one confirmed semantic variable.
    if len(required_variables) != 1:
        return DeferredRecipeRule(
            metric_id=kpi_recipe.id,
            title=kpi_recipe.title,
            reason="Template requires multiple semantic variables and needs a typed derived recipe.",
        )

    # 2. Formula must match the exact atomic grammar.
    match = _SIMPLE_ATOMIC_FORMULA_RE.fullmatch(formula)
    if not match:
        return DeferredRecipeRule(
            metric_id=kpi_recipe.id,
            title=kpi_recipe.title,
            reason="Template formula contains semantics not supported by a simple atomic MetricRecipe.",
        )

    if match.group(1):
        formula_aggregation = match.group(1).upper()
        formula_variable = match.group(2)
    else:
        formula_aggregation = "COUNT_DISTINCT" if match.group(3) else "COUNT"
        formula_variable = match.group(4)

    required_variable = required_variables[0]

    # 3. Template formula aggregation must agree with declared aggregation.
    if formula_aggregation != aggregation:
        return DeferredRecipeRule(
            metric_id=kpi_recipe.id,
            title=kpi_recipe.title,
            reason="Template formula aggregation does not match the declared aggregation.",
        )

    # 4. Template formula variable must agree with required_variables.
    if formula_variable != required_variable:
        return DeferredRecipeRule(
            metric_id=kpi_recipe.id,
            title=kpi_recipe.title,
            reason="Template formula variable does not match required_variables.",
        )

    # 5. Aggregation must be in canonical whitelist.
    if aggregation not in ALLOWED_AGGREGATIONS:
        return DeferredRecipeRule(
            metric_id=kpi_recipe.id,
            title=kpi_recipe.title,
            reason=f"Aggregation '{aggregation}' is not supported by the canonical metric policy.",
        )

    fmt = (
        kpi_recipe.format
        if kpi_recipe.format in {"number", "integer", "currency", "percentage", "ratio"}
        else "number"
    )

    return AtomicRecipeRule(
        metric_id=kpi_recipe.id,
        title=kpi_recipe.title,
        mapping_key=required_variable,
        aggregation=aggregation,
        format=fmt,
        description=kpi_recipe.description or None,
    )


def build_domain_recipe_rules(domain_key: str) -> tuple[RecipeRule, ...]:
    """
    Constructs deterministic RecipeRules using domain_templates.py as the primary source of truth.
    Unknown or generic domains return empty rules (zero business KPI fabrication).
    """
    normalized_domain = domain_key.strip().lower() if domain_key else "generic"

    if normalized_domain == "generic":
        return ()

    template = get_domain_template(normalized_domain)
    if template is None or template.id.lower() != normalized_domain or template.is_fallback:
        return ()

    rules: list[RecipeRule] = []
    domain_overrides = DERIVED_RECIPE_OVERRIDES.get(normalized_domain, {})

    for kpi in template.kpis:
        if kpi.id in FILTER_REQUIRED_METRIC_IDS:
            rules.append(
                DeferredRecipeRule(
                    metric_id=kpi.id,
                    title=kpi.title,
                    reason="Metric requires a status/filter condition not supported by the Phase 2A recipe contract.",
                )
            )
            continue

        if kpi.id in domain_overrides:
            rules.append(domain_overrides[kpi.id])
            continue

        rules.append(_atomic_rule_from_template(kpi))

    for extra_rule in EXTRA_DERIVED_RULES.get(normalized_domain, ()):
        rules.append(extra_rule)

    return tuple(rules)


# ============================================================
# SAFE MAPPING HELPER (NO FUZZY MATCHING, NO FALLBACKS)
# ============================================================

def _get_confirmed_ref(
    confirmed_mapping: Mapping[str, str],
    key: str,
) -> str | None:
    """
    Retrieves the confirmed target reference for the exact key.
    Performs zero fuzzy matching, zero substring guessing, and zero fallback substitution.
    """
    value = confirmed_mapping.get(key)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


# ============================================================
# RECIPE BUILDERS
# ============================================================

def _build_atomic_recipe(
    rule: AtomicRecipeRule,
    confirmed_mapping: Mapping[str, str],
) -> AtomicMetricRecipe:
    target_ref = _get_confirmed_ref(confirmed_mapping, rule.mapping_key)
    if target_ref is None:
        raise MissingMappingError(
            f"Required confirmed mapping '{rule.mapping_key}' is missing."
        )

    return AtomicMetricRecipe(
        metric_id=rule.metric_id,
        title=rule.title,
        description=rule.description,
        format=rule.format,  # type: ignore[arg-type]
        reasoning=f"Generated deterministically from confirmed mapping '{rule.mapping_key}'.",
        operand=AtomicMetricOperand(
            target_ref=target_ref,
            aggregation=rule.aggregation,  # type: ignore[arg-type]
        ),
    )


def _build_ratio_recipe(
    rule: RatioRecipeRule,
    confirmed_mapping: Mapping[str, str],
) -> RatioMetricRecipe:
    numerator_ref = _get_confirmed_ref(confirmed_mapping, rule.numerator_mapping_key)
    if numerator_ref is None:
        raise MissingMappingError(
            f"Required confirmed mapping '{rule.numerator_mapping_key}' is missing."
        )

    denominator_ref = _get_confirmed_ref(confirmed_mapping, rule.denominator_mapping_key)
    if denominator_ref is None:
        raise MissingMappingError(
            f"Required confirmed mapping '{rule.denominator_mapping_key}' is missing."
        )

    return RatioMetricRecipe(
        metric_id=rule.metric_id,
        title=rule.title,
        description=rule.description,
        format=rule.format,  # type: ignore[arg-type]
        reasoning="Generated deterministically from explicitly confirmed semantic mappings.",
        numerator=AtomicMetricOperand(
            target_ref=numerator_ref,
            aggregation=rule.numerator_aggregation,  # type: ignore[arg-type]
        ),
        denominator=AtomicMetricOperand(
            target_ref=denominator_ref,
            aggregation=rule.denominator_aggregation,  # type: ignore[arg-type]
        ),
        zero_division="null",
    )


def _build_difference_recipe(
    rule: DifferenceRecipeRule,
    confirmed_mapping: Mapping[str, str],
) -> DifferenceMetricRecipe:
    left_ref = _get_confirmed_ref(confirmed_mapping, rule.left_mapping_key)
    if left_ref is None:
        raise MissingMappingError(
            f"Required confirmed mapping '{rule.left_mapping_key}' is missing."
        )

    right_ref = _get_confirmed_ref(confirmed_mapping, rule.right_mapping_key)
    if right_ref is None:
        raise MissingMappingError(
            f"Required confirmed mapping '{rule.right_mapping_key}' is missing."
        )

    return DifferenceMetricRecipe(
        metric_id=rule.metric_id,
        title=rule.title,
        description=rule.description,
        format=rule.format,  # type: ignore[arg-type]
        reasoning="Generated deterministically from explicitly confirmed semantic mappings.",
        left=AtomicMetricOperand(
            target_ref=left_ref,
            aggregation=rule.left_aggregation,  # type: ignore[arg-type]
        ),
        right=AtomicMetricOperand(
            target_ref=right_ref,
            aggregation=rule.right_aggregation,  # type: ignore[arg-type]
        ),
    )


def _build_recipe_from_rule(
    rule: RecipeRule,
    confirmed_mapping: Mapping[str, str],
) -> MetricRecipe:
    if isinstance(rule, AtomicRecipeRule):
        return _build_atomic_recipe(rule, confirmed_mapping)
    if isinstance(rule, RatioRecipeRule):
        return _build_ratio_recipe(rule, confirmed_mapping)
    if isinstance(rule, DifferenceRecipeRule):
        return _build_difference_recipe(rule, confirmed_mapping)

    raise TypeError(f"Unsupported deterministic recipe rule: {type(rule).__name__}")


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_metric_recipes(
    *,
    domain_key: str,
    confirmed_mapping: Mapping[str, str],
    registry_entries: Sequence[Any],
) -> MetricRecipeGenerationResult:
    """
    Transforms an already-confirmed semantic mapping into validated typed MetricRecipe objects
    using deterministic domain rules derived directly from domain_templates.py.

    Strict Data Flow:
    Confirmed Mapping -> Domain Template Rule -> Typed MetricRecipe -> Phase 2A Schema Validation -> Result
    """
    rules = build_domain_recipe_rules(domain_key)
    return _generate_metric_recipes_from_rules(
        rules=rules,
        confirmed_mapping=confirmed_mapping,
        registry_entries=registry_entries,
    )


def _generate_metric_recipes_from_rules(
    *,
    rules: Sequence[RecipeRule],
    confirmed_mapping: Mapping[str, str],
    registry_entries: Sequence[Any],
) -> MetricRecipeGenerationResult:
    """
    Internal generator executing a sequence of deterministic recipe rules.
    Used by generate_metric_recipes() and available for testing rule variations.
    """
    recipes: list[MetricRecipe] = []
    skipped: list[SkippedMetric] = []
    seen_ids: set[str] = set()

    for rule in rules:
        if rule.metric_id in seen_ids:
            skipped.append(
                SkippedMetric(
                    metric_id=rule.metric_id,
                    reason=f"Duplicate metric_id '{rule.metric_id}'.",
                )
            )
            continue

        seen_ids.add(rule.metric_id)

        if isinstance(rule, DeferredRecipeRule):
            skipped.append(
                SkippedMetric(
                    metric_id=rule.metric_id,
                    reason=rule.reason,
                )
            )
            continue

        if rule.metric_id in FILTER_REQUIRED_METRIC_IDS:
            skipped.append(
                SkippedMetric(
                    metric_id=rule.metric_id,
                    reason="Metric requires a status/filter condition not supported by the Phase 2A recipe contract.",
                )
            )
            continue

        try:
            recipe = _build_recipe_from_rule(rule, confirmed_mapping)
            validate_recipe_against_registry(recipe, registry_entries)

        except (
            ValidationError,
            MetricRecipeValidationError,
            MissingMappingError,
        ) as exc:
            skipped.append(
                SkippedMetric(
                    metric_id=rule.metric_id,
                    reason=str(exc),
                )
            )
            continue

        recipes.append(recipe)

    return MetricRecipeGenerationResult(
        recipes=recipes,
        skipped=skipped,
    )
