"""
Deterministic & Heuristic Mapping Matcher for DataSpeakAI / NexaBI.

Pairs columns profiled in SchemaRegistry with the Essential Variables of a selected
DomainTemplate (or Generic Fallback).

Key Safety & Intelligence Features:
1. Datatype & Semantic Type Compatibility checks.
2. ID and Primary/Foreign Key Isolation:
   - IDs are NEVER mapped to numeric business measures (e.g. revenue, cost).
   - IDs are NEVER mapped to regular categorical dimensions unless explicitly allowed.
3. Unit Price vs Total Revenue Penalization:
   - If a table has both `total`/`amount` and `unit_price`/`price`, `total` gets top priority.
   - Price alone receives reduced confidence and clear reasoning warnings.
4. Confidence Scoring (0.0 to 1.0) with plain-English reasoning.
5. Fallback for Unknown / Generic Domains:
   - Safely selects the best additive measure (non-ID numeric), date axis, and low-cardinality dimension.
"""

from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import models
from services.domain_templates import (
    DomainTemplate,
    EssentialVariable,
    get_domain_template,
)


def suggest_mappings(
    db_conn: models.DatabaseConnection,
    domain_id: Optional[str],
    db: Session,
) -> Dict[str, Any]:
    """
    Computes suggested mappings between the connection's profiled columns and the
    essential variables of the specified domain template (or Generic fallback).
    """
    template = get_domain_template(domain_id)

    # Fetch all profiled columns from SchemaRegistry
    registry_entries = (
        db.query(models.SchemaRegistry)
        .filter(models.SchemaRegistry.connection_id == db_conn.id)
        .all()
    )

    if not registry_entries:
        return {
            "domain": template.id,
            "domain_name": template.name,
            "is_fallback": template.is_fallback,
            "suggestions": [],
            "warnings": ["Database schema has not been profiled yet. Please profile the database first."],
            "available_columns": [],
        }

    # Format available columns for frontend dropdowns
    available_columns = [
        {
            "key": f"{r.table_name}.{r.column_name}",
            "table_name": r.table_name,
            "column_name": r.column_name,
            "data_type": r.data_type,
            "semantic_type": getattr(r, "semantic_type", "UNKNOWN") or "UNKNOWN",
            "is_primary_key": bool(getattr(r, "is_primary_key", False)),
            "is_foreign_key": bool(getattr(r, "is_foreign_key", False)),
            "is_measure": bool(r.is_measure),
            "is_dimension": bool(r.is_dimension),
            "is_time_axis": bool(r.is_time_axis),
            "cardinality": r.cardinality,
            "null_percentage": float(r.null_percentage or 0.0),
        }
        for r in registry_entries
    ]

    suggestions = []
    used_columns = set()

    # Match each essential variable in the template
    for var in template.essential_variables:
        match_result = _find_best_column_for_variable(
            var=var,
            columns=registry_entries,
            used_columns=used_columns,
            is_generic=template.is_fallback,
        )
        if match_result and match_result["column"]:
            used_columns.add(match_result["column"])
            suggestions.append(match_result)
        else:
            suggestions.append({
                "variable": var.name,
                "display_name": var.display_name,
                "description": var.description,
                "required": var.required,
                "column": None,
                "confidence": 0.0,
                "reasoning": f"No compatible column found for concept '{var.display_name}'. Please select manually.",
                "semantic_type": "UNKNOWN",
            })

    return {
        "domain": template.id,
        "domain_name": template.name,
        "is_fallback": template.is_fallback,
        "suggestions": suggestions,
        "available_columns": available_columns,
        "warnings": [],
    }


def _find_best_column_for_variable(
    var: EssentialVariable,
    columns: List[models.SchemaRegistry],
    used_columns: set,
    is_generic: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates all candidate columns against an essential variable and returns the highest-scoring candidate.
    """
    candidates = []

    for col in columns:
        col_key = f"{col.table_name}.{col.column_name}"
        col_name_lower = str(col.column_name).lower()
        table_name_lower = str(col.table_name).lower()
        col_type_upper = str(col.data_type or "TEXT").upper()
        sem_type = getattr(col, "semantic_type", "UNKNOWN") or "UNKNOWN"
        is_pk = bool(getattr(col, "is_primary_key", False))
        is_fk = bool(getattr(col, "is_foreign_key", False))
        c_null = getattr(col, "null_percentage", 0.0)
        c_card = getattr(col, "cardinality", None)
        null_pct = float(c_null or 0.0)
        cardinality = int(c_card) if c_card is not None else 1000


        # Disqualify 100% NULL columns
        if null_pct >= 99.0:
            continue

        # RULE: Never treat ID/UUID as business measure or non-ID dimension
        if any(ft in sem_type for ft in var.forbidden_types) or (is_pk and "ID" in var.forbidden_types) or (is_fk and "ID" in var.forbidden_types):
            continue

        score = 0.0
        reasons = []

        # 1. Semantic Type Compatibility
        if sem_type in var.expected_semantic_types:
            score += 0.4
            reasons.append(f"Semantic type '{sem_type}' matches expected types")
        elif any(t in col_type_upper for t in ["INT", "FLOAT", "NUMERIC", "DECIMAL", "DOUBLE"]) and any("NUMERIC" in et or "CURRENCY" in et for et in var.expected_semantic_types):
            score += 0.25
            reasons.append("Underlying numeric data type is compatible")
        elif any(t in col_type_upper for t in ["DATE", "TIME", "TIMESTAMP"]) and any("DATE" in et or "DATETIME" in et for et in var.expected_semantic_types):
            score += 0.3
            reasons.append("Temporal data type matches date requirement")
        elif any(t in col_type_upper for t in ["CHAR", "TEXT", "VARCHAR", "STRING"]) and any("CATEGORY" in et or "TEXT" in et for et in var.expected_semantic_types):
            score += 0.2
            reasons.append("Textual data type matches category requirement")
        elif var.name in ["order_id", "subscription_id", "encounter_id", "shipment_id", "transaction_id", "primary_record_id"] and (is_pk or is_fk or "ID" in sem_type):
            score += 0.4
            reasons.append("Identified as an entity primary or foreign key")
        else:
            # Type mismatch
            continue

        # 2. Exact or Alias Name Matching
        name_matched = False
        if col_name_lower == var.name.lower():
            score += 0.5
            name_matched = True
            reasons.append(f"Exact column name match '{col.column_name}'")
        else:
            for alias in var.aliases:
                if alias == col_name_lower:
                    score += 0.45
                    name_matched = True
                    reasons.append(f"Matches canonical synonym '{alias}'")
                    break
                elif alias in col_name_lower:
                    score += 0.3
                    name_matched = True
                    reasons.append(f"Contains matching term '{alias}'")
                    break

        # 3. Domain/Table context boost
        if any(t in table_name_lower for t in ["order", "sale", "trans", "sub", "patient", "ship", "fact", "line"]):
            score += 0.1
            reasons.append(f"Table '{col.table_name}' matches core transactional domain")

        # 3b. For primary entity identifier (e.g. order_id), give strong preference to the table's Primary Key over Foreign Keys
        if var.name in ["order_id", "subscription_id", "encounter_id", "shipment_id", "transaction_id", "primary_record_id"]:
            if is_pk:
                score += 0.15
                reasons.append("Primary key of origin entity table")
            elif is_fk:
                score -= 0.05
                reasons.append("Foreign key reference")

        # 4. Critical Safety Guard: Unit Price vs Revenue Penalization
        if var.name in ["revenue", "billing_amount", "transaction_amount", "mrr", "shipping_cost"]:
            if "unit" in col_name_lower or col_name_lower in ["price", "unitprice", "unit_price", "rate"]:
                score -= 0.25
                reasons.append("Penalized: appears to be an un-aggregated Unit Price rather than total order/transaction amount")

        # 4b. Critical Safety Guard: Non-Additive Measure Guard (_pct, _rate, percentage, ratio)
        # Prevents SUM({rate}) errors in Generic Fallback and additive metric generation
        if var.name in ["primary_measure", "revenue", "billing_amount", "transaction_amount", "mrr", "shipping_cost"]:
            is_rate_or_pct = any(p in col_name_lower for p in ["pct", "percent", "percentage", "rate", "ratio", "margin", "index", "prob"])
            if is_rate_or_pct:
                score -= 0.35
                reasons.append("Penalized: non-additive rate/percentage metric is unsafe for default SUM aggregation")


        # 5. Low cardinality boost for categorical dimensions
        if any("CATEGORY" in et for et in var.expected_semantic_types):
            if 1 < cardinality <= 50:
                score += 0.15
                reasons.append(f"Optimal categorical cardinality ({cardinality} distinct values)")
            elif cardinality > 100:
                score -= 0.15
                reasons.append(f"High cardinality ({cardinality} values) may not be a good slice dimension")

        # Cap confidence between 0.1 and 0.99
        confidence = min(max(round(score, 2), 0.1), 0.99)
        
        # Don't pick previously used columns if alternative exists
        if col_key in used_columns:
            confidence -= 0.3

        candidates.append({
            "variable": var.name,
            "display_name": var.display_name,
            "description": var.description,
            "required": var.required,
            "column": col_key,
            "table_name": col.table_name,
            "column_name": col.column_name,
            "confidence": confidence,
            "semantic_type": sem_type,
            "reasoning": "; ".join(reasons),
        })

    if not candidates:
        return {
            "variable": var.name,
            "display_name": var.display_name,
            "description": var.description,
            "required": var.required,
            "column": None,
            "confidence": 0.0,
            "semantic_type": "UNKNOWN",
            "reasoning": "No candidate column met data type and semantic criteria.",
        }

    # Sort candidates by confidence descending
    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    return candidates[0]
