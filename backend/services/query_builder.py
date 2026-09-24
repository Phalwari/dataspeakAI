def quote_ident(ident: str, db_type: str = "sqlite") -> str:
    """Quotes SQL identifier based on dialect (backticks for MySQL/MariaDB, double-quotes for PG/SQLite)."""
    if not ident or ident == "*":
        return ident or ""
    clean = ident.replace('"', '').replace('`', '')
    if (db_type or "").lower() in ("mysql", "mariadb"):
        return f"`{clean}`"
    return f'"{clean}"'

def cast_text_expr(ident_quoted: str, db_type: str = "sqlite") -> str:
    """Generates dialect-appropriate text casting expression (CHAR for MySQL, TEXT for PG/SQLite)."""
    if (db_type or "").lower() in ("mysql", "mariadb"):
        return f"CAST({ident_quoted} AS CHAR)"
    return f"CAST({ident_quoted} AS TEXT)"

def build_aggregated_chart_query(
    table: str, 
    target_col: str, 
    dim_col: str | None = None, 
    agg_func: str = "SUM", 
    limit: int = 10,
    secondary_col: str | None = None,
    target_value: str | None = None,
    where_clauses: list[str] | None = None,
    db_type: str = "sqlite"
) -> str:
    limit = min(limit or 10, 1000)   # hard cap
    agg_clean = (agg_func or "SUM").upper().strip()
    
    t_q = quote_ident(table, db_type)
    target_clean = (target_col or "").strip()
    is_wildcard = target_clean in ("*", "all", "")
    target_q = quote_ident(target_col, db_type) if not is_wildcard else "*"
    sec_q = quote_ident(secondary_col, db_type) if secondary_col else None
    dim_q = quote_ident(dim_col, db_type) if dim_col else None
    cast_expr = cast_text_expr(target_q, db_type) if not is_wildcard else ""

    if is_wildcard:
        if agg_clean != "COUNT":
            raise ValueError(
                f"Aggregation '{agg_clean}' cannot be applied to wildcard target '{target_col}'. "
                f"Only 'COUNT' is allowed."
            )
        agg_expr = "COUNT(*)"
    elif agg_clean in ("COUNT_DISTINCT", "DISTINCT_COUNT"):
        agg_expr = f"COUNT(DISTINCT {target_q})"
    elif agg_clean in ("DIFFERENCE", "SUBTRACT") and sec_q:
        agg_expr = f"SUM({target_q}) - SUM({sec_q})"
    elif agg_clean in ("PROFIT_MARGIN", "MARGIN_PERCENT", "RATIO") and sec_q:
        agg_expr = f"ROUND((SUM({target_q}) - SUM({sec_q})) * 100.0 / NULLIF(SUM({target_q}), 0), 2)"
    elif agg_clean in ("COMPUTED", "RATIO", "CONVERSION_RATE"):
        if target_value:
            clean_val = target_value.replace("'", "''")
            agg_expr = f"ROUND(COUNT(CASE WHEN UPPER({cast_expr}) = UPPER('{clean_val}') THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2)"
        else:
            agg_expr = f"ROUND(COUNT(CASE WHEN UPPER({cast_expr}) IN ('PAID', 'YES', '1', 'TRUE', 'COMPLETED', 'ACTIVE', 'ADMITTED') THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2)"
    elif agg_clean in ("SUM", "AVG", "COUNT", "MAX", "MIN"):
        agg_expr = f"{agg_clean}({target_q})"
    else:
        raise ValueError(
            f"Unsupported aggregation function '{agg_func}'. "
            f"Allowed aggregations: SUM, AVG, MIN, MAX, COUNT, COUNT_DISTINCT."
        )

    where_parts = []
    if dim_q:
        where_parts.append(f"{dim_q} IS NOT NULL")
    if where_clauses:
        where_parts.extend(where_clauses)

    where_sql = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""

    if dim_q:
        return (f"SELECT {dim_q}, {agg_expr} AS val "
                f"FROM {t_q}{where_sql} "
                f"GROUP BY {dim_q} ORDER BY val DESC LIMIT {limit}")
    return f"SELECT {agg_expr} AS val FROM {t_q}{where_sql} LIMIT {limit}"

def validate_column(column_name: str, table_registries: list) -> bool:
    """Column sirf tabhi allowed hai agar schema_registry me exist karta ho."""
    if not column_name or column_name == "*":
        return True  # None or '*' allowed
    valid_names = {r.column_name for r in table_registries}
    return column_name in valid_names

def parse_column_ref(ref: str) -> tuple[str, str]:
    """
    Parses a strictly qualified 'table.column' reference.
    Raises ValueError if reference is missing or not qualified.
    Supports 'table.*' and 'table.all' canonical row count wildcards.
    """
    if not ref or not isinstance(ref, str) or "." not in ref:
        raise ValueError(f"Qualified column reference required (table.column): '{ref}'")
    table, column = ref.split(".", 1)
    table = table.strip()
    column = column.strip()
    if not table or not column:
        raise ValueError(f"Invalid qualified column reference: '{ref}'")
    if column == "all":
        column = "*"
    return table, column

