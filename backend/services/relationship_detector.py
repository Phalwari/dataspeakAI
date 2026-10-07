"""
Relationship Detector Service
Automatically detects foreign key relationships between multiple CSV files
by comparing column names and data patterns.

Example:
  orders.csv   → columns: order_id, customer_id, ...
  customers.csv → columns: customer_id, ...
  → Detected: orders.customer_id → customers.customer_id  (confidence: 0.95)
"""
import os
import pandas as pd
from typing import Dict, List, Any


def profile_csv(file_path: str) -> Dict[str, Any]:
    """
    Read a CSV and return its schema profile:
    { column_name: { dtype, sample_values, unique_count, null_count } }
    """
    try:
        try:
            df = pd.read_csv(file_path, encoding='utf-8', encoding_errors='replace', nrows=500)
        except Exception:
            df = pd.read_csv(file_path, encoding='latin-1', nrows=500)

        schema = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            col_type = "numeric" if ("int" in dtype or "float" in dtype) else "categorical"
            if any(kw in col.lower() for kw in ["date", "time", "created", "updated"]):
                col_type = "date"

            sample_vals = df[col].dropna().head(5).tolist()
            schema[col] = {
                "dtype": dtype,
                "col_type": col_type,
                "unique_count": int(df[col].nunique()),
                "null_count": int(df[col].isnull().sum()),
                "sample_values": [str(v)[:50] for v in sample_vals],
            }
        return schema
    except Exception as e:
        print(f"[RelationDetector] Error profiling {file_path}: {e}")
        return {}


def _normalize_col_name(col: str) -> str:
    """Normalize column name for comparison (lowercase, strip underscores/spaces)."""
    return col.lower().replace("_", "").replace(" ", "").replace("-", "")


def detect_relationships(
    table_schemas: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Detect foreign key relationships between tables.

    Args:
        table_schemas: { table_name: { col_name: col_profile } }

    Returns:
        List of relationships:
        [
          {
            "from_table": "orders",
            "from_col":   "customer_id",
            "to_table":   "customers",
            "to_col":     "customer_id",
            "confidence": 0.95,
            "match_type": "exact_name"  | "normalized_name" | "sample_overlap"
          }
        ]
    """
    relationships = []
    table_names = list(table_schemas.keys())

    for i, table_a in enumerate(table_names):
        for table_b in table_names[i + 1:]:
            schema_a = table_schemas[table_a]
            schema_b = table_schemas[table_b]

            cols_a = list(schema_a.keys())
            cols_b = list(schema_b.keys())

            for col_a in cols_a:
                for col_b in cols_b:
                    confidence = 0.0
                    match_type = None

                    # --- Match 1: Exact column name match ---
                    if col_a.lower() == col_b.lower():
                        confidence = 0.95
                        match_type = "exact_name"

                    # --- Match 2: Normalized name match ---
                    elif _normalize_col_name(col_a) == _normalize_col_name(col_b):
                        confidence = 0.88
                        match_type = "normalized_name"

                    # --- Match 3: One is a suffix/prefix of other (e.g. order_id vs id) ---
                    elif _is_suffix_match(col_a, col_b, table_a, table_b):
                        confidence = 0.75
                        match_type = "suffix_match"

                    # Skip if no name match at all
                    if confidence == 0.0:
                        continue

                    # --- Boost confidence if column ends with _id or _key ---
                    if col_a.lower().endswith(("_id", "_key", "_code", "id")):
                        confidence = min(confidence + 0.03, 0.99)

                    # --- Boost if sample values overlap ---
                    try:
                        samples_a = set(str(v) for v in schema_a[col_a].get("sample_values", []))
                        samples_b = set(str(v) for v in schema_b[col_b].get("sample_values", []))
                        if samples_a and samples_b:
                            overlap = len(samples_a & samples_b) / max(len(samples_a), len(samples_b))
                            if overlap > 0.2:
                                confidence = min(confidence + overlap * 0.1, 0.99)
                    except Exception:
                        pass

                    # Only include if confident enough
                    if confidence >= 0.70:
                        relationships.append({
                            "from_table": table_a,
                            "from_col":   col_a,
                            "to_table":   table_b,
                            "to_col":     col_b,
                            "confidence": round(confidence, 3),
                            "match_type": match_type
                        })

    # Deduplicate — keep highest confidence for each (table_a, col_a, table_b, col_b) pair
    seen = {}
    for rel in relationships:
        key = (rel["from_table"], rel["from_col"], rel["to_table"], rel["to_col"])
        if key not in seen or rel["confidence"] > seen[key]["confidence"]:
            seen[key] = rel

    result = sorted(seen.values(), key=lambda x: x["confidence"], reverse=True)
    return result


def _is_suffix_match(col_a: str, col_b: str, table_a: str, table_b: str) -> bool:
    """
    Check if one column name is table-prefixed version of other.
    e.g. table='orders', col_a='order_id', col_b='id' → True
    """
    norm_a = _normalize_col_name(col_a)
    norm_b = _normalize_col_name(col_b)
    name_a = _normalize_col_name(table_a.rstrip("s"))  # remove trailing 's' (orders→order)
    name_b = _normalize_col_name(table_b.rstrip("s"))

    # e.g. orderid == order + id
    if norm_a == name_b + "id" or norm_b == name_a + "id":
        return True
    if norm_a == name_b + "key" or norm_b == name_a + "key":
        return True
    return False


def build_unified_schema(
    table_schemas: Dict[str, Dict[str, Any]],
    relationships: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Build a unified data model describing all tables and their relationships.
    This is what AI agents receive to understand the full database.
    """
    tables = {}
    for table_name, schema in table_schemas.items():
        tables[table_name] = {
            "columns": list(schema.keys()),
            "column_details": {
                col: {
                    "type": info.get("col_type", "categorical"),
                    "unique_count": info.get("unique_count", 0),
                }
                for col, info in schema.items()
            }
        }

    return {
        "tables": tables,
        "relationships": relationships,
        "table_count": len(tables),
        "relationship_count": len(relationships),
    }
