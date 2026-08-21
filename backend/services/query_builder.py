def build_aggregated_chart_query(table, target_col, dim_col, agg_func, limit=10):
    limit = min(int(limit or 10), 1000)   # hard cap
    agg_func = agg_func if agg_func in ("SUM","AVG","COUNT","MAX","MIN") else "SUM"
    if dim_col:
        return (f'SELECT "{dim_col}", {agg_func}("{target_col}") AS val '
                f'FROM "{table}" WHERE "{dim_col}" IS NOT NULL '
                f'GROUP BY "{dim_col}" ORDER BY val DESC LIMIT {limit}')
    return f'SELECT {agg_func}("{target_col}") AS val FROM "{table}" LIMIT {limit}'

def validate_column(column_name: str, table_registries: list) -> bool:
    """Column sirf tabhi allowed hai agar schema_registry me exist karta ho."""
    if not column_name or column_name == "*":
        return True  # None or '*' allowed
    valid_names = {r.column_name for r in table_registries}
    return column_name in valid_names
