"""
backend/services/metric_semantics.py

Canonical Semantic Policy for Analytics Metric Aggregations.
Central authority determining whether a mathematical aggregation is valid
for a specific column based on semantic types, data types, and structural flags.
"""

from typing import Optional, Set
import re
import models
from services.schema_profiler import is_id_column

ALLOWED_AGGREGATIONS: Set[str] = {
    "SUM",
    "AVG",
    "MIN",
    "MAX",
    "COUNT",
    "COUNT_DISTINCT",
}

NON_ADDITIVE_NAME_PATTERNS = [
    r"_pct$",
    r"_percent$",
    r"_percentage$",
    r"_rate$",
    r"_ratio$",
    r"^pct_",
    r"^rate_",
    r"^ratio_",
    r"margin_pct",
    r"error_rate",
    r"churn_rate",
    r"bounce_rate",
    r"discount_rate",
    r"tax_rate",
    r"conversion_rate",
]


def is_ratio_or_rate_column(col_name: str, semantic_type: Optional[str] = None) -> bool:
    """Detects ratio, rate, percentage, or non-additive fractional measures."""
    if semantic_type and semantic_type.upper() in ("PERCENTAGE", "RATE", "RATIO"):
        return True
    lname = col_name.lower().strip()
    return any(bool(re.search(pat, lname)) for pat in NON_ADDITIVE_NAME_PATTERNS)


def is_identifier_column(
    col_name: str,
    col_reg: Optional[models.SchemaRegistry] = None
) -> bool:
    """Determines whether a column represents an entity identifier or key."""
    if col_reg is not None:
        if getattr(col_reg, "is_primary_key", False) or getattr(col_reg, "is_foreign_key", False):
            return True
        sem = (getattr(col_reg, "semantic_type", "") or "").upper()
        if sem in ("ID", "UUID"):
            return True
    return is_id_column(col_name)


def validate_metric_aggregation(
    target_ref: str,
    aggregation: str,
    col_reg: Optional[models.SchemaRegistry] = None,
) -> None:
    """
    Validates whether an aggregation is mathematically and semantically sound
    for the specified column.

    Raises:
        ValueError: with a clear descriptive message if the aggregation is
                    unsupported or semantically invalid.
    """
    if not aggregation or not isinstance(aggregation, str):
        raise ValueError("Aggregation function is required and must be a string.")

    agg_clean = aggregation.strip().upper()

    # 1. Whitelist enforcement - NEVER silently fallback to SUM
    if agg_clean not in ALLOWED_AGGREGATIONS:
        allowed_list = ", ".join(sorted(ALLOWED_AGGREGATIONS))
        raise ValueError(
            f"Unsupported aggregation '{aggregation}'. Allowed aggregations: {allowed_list}."
        )

    # 2. Wildcard / Row-count sentinel enforcement (* or all)
    target_clean = (target_ref or "").strip()
    is_wildcard = target_clean in ("*", "all", "") or target_clean.endswith(".*") or target_clean.endswith(".all")

    if is_wildcard:
        if agg_clean != "COUNT":
            raise ValueError(
                f"Wildcard target '{target_ref}' is only valid for COUNT aggregation. "
                f"Cannot apply '{agg_clean}' to wildcard."
            )
        return

    # Extract bare column name from qualified target_ref (e.g. orders.total_amount -> total_amount)
    col_name = target_ref.split(".", 1)[1] if "." in target_ref else target_ref

    # 3. Identifier Guard
    if is_identifier_column(col_name, col_reg):
        if agg_clean in ("SUM", "AVG"):
            sem_info = getattr(col_reg, "semantic_type", "ID") if col_reg else "ID"
            raise ValueError(
                f"Cannot apply '{agg_clean}' to identifier column '{target_ref}' ({sem_info}). "
                f"Identifiers are non-arithmetic; use COUNT or COUNT_DISTINCT instead."
            )

    # 4. Non-Additive Measure Guard (Ratio / Rate / Percentage)
    sem_type = getattr(col_reg, "semantic_type", None) if col_reg else None
    if is_ratio_or_rate_column(col_name, sem_type):
        if agg_clean == "SUM":
            raise ValueError(
                f"Cannot apply SUM to non-additive ratio/rate/percentage column '{target_ref}'. "
                f"Summing percentages or rates yields mathematically incorrect results. Use AVG, MIN, or MAX."
            )

    # 5. Type-Specific Guard (when SchemaRegistry is available)
    if col_reg is not None:
        raw_type = (getattr(col_reg, "data_type", "") or "").upper()
        sem = (getattr(col_reg, "semantic_type", "") or "").upper()
        is_time = getattr(col_reg, "is_time_axis", False) or sem in ("DATE", "DATETIME") or any(
            t in raw_type for t in ["DATE", "TIME", "TIMESTAMP"]
        )

        # Date / Time columns
        if is_time:
            if agg_clean in ("SUM", "AVG"):
                raise ValueError(
                    f"Cannot apply arithmetic aggregation '{agg_clean}' to temporal column '{target_ref}' ({raw_type}). "
                    f"Use MIN, MAX, or COUNT."
                )

        # Non-numeric string / category columns
        is_textual = sem in ("TEXT", "CATEGORY", "BOOLEAN") or any(
            t in raw_type for t in ["VARCHAR", "CHAR", "TEXT", "STRING", "BOOL"]
        )
        if is_textual and not is_time:
            if agg_clean in ("SUM", "AVG"):
                raise ValueError(
                    f"Cannot apply arithmetic aggregation '{agg_clean}' to text/categorical column '{target_ref}' ({raw_type}). "
                    f"Use COUNT or COUNT_DISTINCT."
                )
