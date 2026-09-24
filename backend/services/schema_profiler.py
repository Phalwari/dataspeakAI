import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Any
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
import models
from services.db_utils import get_connection_url
from services.db_pool import get_engine
from services.query_builder import quote_ident

logger = logging.getLogger(__name__)

@dataclass
class ColumnProfile:
    name: str
    data_type: str
    semantic_type: str = "UNKNOWN"  # ID, UUID, DATE, DATETIME, NUMERIC_MEASURE, CURRENCY/AMOUNT, CATEGORY, TEXT, BOOLEAN, UNKNOWN
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_target: Optional[str] = None
    is_measure: bool = False
    is_dimension: bool = False
    is_time_axis: bool = False
    cardinality: Optional[int] = None
    null_percentage: float = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    top_values: List[Any] = field(default_factory=list)

    @property
    def role(self) -> str:
        if self.is_measure:
            return "measure"
        if self.is_time_axis:
            return "time"
        if self.is_dimension:
            return "dimension"
        return "ignore"

@dataclass
class TableProfile:
    table_name: str
    row_count: int = 0
    columns: List[ColumnProfile] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[dict] = field(default_factory=list)


SAFE_WORDS_ENDING_ID = {
    "paid", "valid", "grid", "solid", "arid", "avid", "rapid", 
    "liquid", "humid", "frigid", "torrid", "splendid", "horrid", 
    "sordid", "placid", "acid", "lucid", "timid", "morbid", "rabid", 
    "candid", "vivid", "hybrid", "pyramid", "eyelid", "mid", "android"
}

def is_id_column(col_name: str) -> bool:
    """
    Detects identifier columns across naming styles (snake_case, camelCase, PascalCase)
    without triggering false positives on real words like 'PAID', 'VALID', or 'GRID'.
    """
    clean = col_name.strip()
    lname = clean.lower()
    
    # 1. Immediate exclusion for safe regular words ending in 'id'
    if lname in SAFE_WORDS_ENDING_ID:
        return False
    
    # 2. Exact identifier matches
    if lname in ("id", "pk", "uuid", "guid", "rowid", "key"):
        return True
    
    # 3. snake_case: user_id, order_id, id_order, customer_id
    if bool(re.search(r'(_id$|^id_|_id_)', lname)):
        return True
        
    # 4. camelCase / PascalCase: AlbumId, ArtistId, customerId, TrackId (letter before capital Id/ID)
    if bool(re.search(r'[a-zA-Z]Id$', clean)) or (bool(re.search(r'[a-zA-Z]ID$', clean)) and lname not in SAFE_WORDS_ENDING_ID):
        return True
        
    return False


CURRENCY_AMOUNT_KEYWORDS = {
    "amount", "revenue", "total", "subtotal", "price", "cost", "fee", "tax", 
    "charge", "payment", "salary", "wage", "balance", "profit", "margin", 
    "discount", "budget", "billing", "gross", "net", "fare", "tariff"
}

def infer_semantic_type(
    col_name: str, 
    raw_type: str = "TEXT", 
    is_pk: bool = False, 
    is_fk: bool = False, 
    is_id: Optional[bool] = None, 
    is_measure: Optional[bool] = None, 
    is_dim: Optional[bool] = None, 
    is_time: Optional[bool] = None,
    cardinality: Optional[int] = None
) -> str:
    lname = col_name.lower().strip()
    u_type = raw_type.upper()
    
    if is_id is None:
        is_id = is_pk or is_fk or is_id_column(col_name)
    if is_time is None:
        is_time = any(t in u_type for t in ["DATE", "TIME", "TIMESTAMP"])
    if is_measure is None:
        is_measure = any(t in u_type for t in ["INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL"]) and not is_id
    if is_dim is None:
        is_dim = not is_measure and not is_time and not is_id

    
    if any(k in lname for k in ["uuid", "guid"]) or "UUID" in u_type:
        return "UUID"
    if is_pk or is_fk or is_id:
        return "ID"

    if any(t in u_type for t in ["BOOL", "BOOLEAN", "TINYINT(1)"]) or lname.startswith(("is_", "has_", "can_")):
        return "BOOLEAN"
    if is_time:
        if any(t in u_type for t in ["TIME", "TIMESTAMP"]) or "time" in lname:
            return "DATETIME"
        return "DATE"
    if is_measure:
        if any(k in lname for k in CURRENCY_AMOUNT_KEYWORDS) or any(t in u_type for t in ["MONEY", "CURRENCY", "DECIMAL", "NUMERIC"]):
            return "CURRENCY/AMOUNT"
        return "NUMERIC_MEASURE"
    if is_dim:
        return "CATEGORY"
    if any(t in u_type for t in ["CHAR", "TEXT", "CLOB", "STRING"]):
        return "TEXT"
    return "UNKNOWN"


def profile_database_schema(db_conn: models.DatabaseConnection, db: Session) -> list[models.SchemaRegistry]:
    """
    Introspects tables & columns for a DatabaseConnection, computes statistical metrics,
    cardinality, auto-tags measures/dimensions/time_axes, detects PK/FK relationships,
    normalizes semantic types, and saves to SchemaRegistry.
    """
    url = get_connection_url(db_conn)
    registry_entries = []

    # If document store (MongoDB, Firestore, Firebase), use document profiling adapter
    if (db_conn.db_type or "").lower() in ("mongodb", "firestore", "firebase"):
        from services.document_db_profiler import profile_document_database
        return profile_document_database(db_conn, db)

    # If connection URL could not be resolved (unsupported or invalid config)
    if not url:
        raise ValueError(
            f"Could not resolve database connection URL for connection {db_conn.id} (db_type: {db_conn.db_type})"
        )

    try:
        engine = get_engine(url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # Clear existing entries for this connection before re-profiling
        db.query(models.SchemaRegistry).filter(models.SchemaRegistry.connection_id == db_conn.id).delete()
        db.commit()

        db_type = str(db_conn.db_type or "sqlite").lower()

        with engine.connect() as conn:
            for table in tables:
                t_q = quote_ident(table, db_type)

                # 1. Detect Primary Keys & Foreign Keys
                pk_cols = set()
                try:
                    pk_info = inspector.get_pk_constraint(table)
                    pk_cols = set(pk_info.get("constrained_columns") or [])
                except Exception:
                    pass

                fk_dict = {}
                try:
                    fks = inspector.get_foreign_keys(table) or []
                    for fk in fks:
                        ref_tbl = fk.get("referred_table", "")
                        ref_cols = fk.get("referred_columns") or []
                        for idx, c_name in enumerate(fk.get("constrained_columns") or []):
                            r_col = ref_cols[idx] if idx < len(ref_cols) else "id"
                            fk_dict[c_name] = f"{ref_tbl}.{r_col}"
                except Exception:
                    pass

                columns = inspector.get_columns(table)
                for col in columns:
                    col_name = col["name"]
                    col_q = quote_ident(col_name, db_type)
                    raw_type = str(col.get("type", "TEXT")).upper()
                    
                    is_pk = col_name in pk_cols
                    is_fk = col_name in fk_dict
                    fk_target = fk_dict.get(col_name)

                    # Check JSON, Array, Binary, Blobs
                    is_json_blob = any(t in raw_type for t in ["JSON", "JSONB", "ARRAY", "OBJECT", "BLOB", "BINARY", "BYTEA", "STRUCT"]) or col_name.lower().endswith(("_json", "_payload", "_metadata", "_raw"))

                    is_id = is_pk or is_fk or is_id_column(col_name)
                    is_num = any(t in raw_type for t in ["INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL"]) and not is_json_blob
                    is_measure = is_num and not is_id
                    is_time = any(t in raw_type for t in ["DATE", "TIME", "TIMESTAMP"]) and not is_json_blob
                    
                    is_dim = not is_measure and not is_time and not is_id and not is_json_blob

                    min_val, max_val, mean_val, null_pct, cardinality = None, None, None, 0.0, None

                    # Universal null percentage calculation
                    try:
                        null_q = text(f"SELECT COUNT(*) - COUNT({col_q}), COUNT(*) FROM {t_q}")
                        nrow = conn.execute(null_q).fetchone()
                        if nrow and nrow[1] > 0:
                            null_pct = round((nrow[0] / nrow[1]) * 100, 2)
                            if null_pct >= 99.9:
                                # 100% NULL column cannot be a measure or dimension
                                is_measure = False
                                is_dim = False
                    except Exception as ex:
                        logger.warning(f"Could not compute null pct for {table}.{col_name}: {ex}")

                    # 1. Compute stats for numeric measures
                    if is_measure:
                        try:
                            query = text(f"""
                                SELECT 
                                    MIN({col_q}), 
                                    MAX({col_q}), 
                                    AVG({col_q})
                                FROM {t_q}
                            """)
                            row = conn.execute(query).fetchone()
                            if row:
                                min_val = float(row[0]) if row[0] is not None else None
                                max_val = float(row[1]) if row[1] is not None else None
                                mean_val = float(row[2]) if row[2] is not None else None
                        except Exception as ex:
                            logger.warning(f"Could not compute stats for {table}.{col_name}: {ex}")

                    # 2. Compute cardinality and apply threshold for dimensions
                    if is_dim:
                        try:
                            card_query = text(f"SELECT COUNT(DISTINCT {col_q}), COUNT(*) FROM {t_q}")
                            card_row = conn.execute(card_query).fetchone()
                            if card_row:
                                cardinality = int(card_row[0]) if card_row[0] is not None else None
                                tot_rows = int(card_row[1]) if card_row[1] is not None else 0
                                
                                # High cardinality text fields (e.g. full names, comments, hashes) are not categorical dimensions
                                if cardinality is not None:
                                    if cardinality > 50 or (tot_rows > 10 and (cardinality / tot_rows) > 0.85):
                                        is_dim = False
                        except Exception as ex:
                            logger.warning(f"Could not compute cardinality for {table}.{col_name}: {ex}")

                    sem_type = infer_semantic_type(
                        col_name=col_name,
                        raw_type=raw_type,
                        is_pk=is_pk,
                        is_fk=is_fk,
                        is_id=is_id,
                        is_measure=is_measure,
                        is_dim=is_dim,
                        is_time=is_time,
                        cardinality=cardinality
                    )

                    reg_entry = models.SchemaRegistry(
                        connection_id=db_conn.id,
                        table_name=table,
                        column_name=col_name,
                        data_type=raw_type,
                        semantic_type=sem_type,
                        is_primary_key=is_pk,
                        is_foreign_key=is_fk,
                        foreign_key_target=fk_target,
                        is_measure=is_measure,
                        is_dimension=is_dim,
                        is_time_axis=is_time,
                        cardinality=cardinality,
                        min_value=min_val,
                        max_value=max_val,
                        mean_value=mean_val,
                        null_percentage=null_pct,
                    )
                    db.add(reg_entry)
                    registry_entries.append(reg_entry)

        db.commit()
        return registry_entries

    except Exception as e:
        logger.error(f"Schema profiling failed for connection {db_conn.id}: {e}")
        db.rollback()
        raise e


def get_table_profiles_for_agents(db_conn: models.DatabaseConnection, db: Session) -> list[TableProfile]:
    """
    Constructs TableProfile and ColumnProfile objects from SchemaRegistry entries
    and database sample values to pass into the Multi-Agent LLM pipeline.
    """
    registries = db.query(models.SchemaRegistry).filter(
        models.SchemaRegistry.connection_id == db_conn.id
    ).all()

    if not registries:
        registries = profile_database_schema(db_conn, db)

    url = get_connection_url(db_conn)
    engine = get_engine(url) if url else None

    # Group columns by table
    tables_map: dict[str, list[models.SchemaRegistry]] = {}
    for r in registries:
        t_key = str(r.table_name)
        tables_map.setdefault(t_key, []).append(r)

    table_profiles = []
    for t_name, cols in tables_map.items():
        row_count = 0
        samples_by_col: dict[str, list] = {}

        if engine:
            try:
                db_type = str(db_conn.db_type or "sqlite").lower()
                t_q = quote_ident(t_name, db_type)
                with engine.connect() as conn:
                    cnt_res = conn.execute(text(f"SELECT COUNT(*) FROM {t_q}")).fetchone()
                    row_count = int(cnt_res[0]) if cnt_res and cnt_res[0] is not None else 0

                    # Fetch a small sample of top distinct values for dimensions
                    for c in cols:
                        col_str = str(c.column_name)
                        col_q = quote_ident(col_str, db_type)
                        if c.is_dimension:
                            try:
                                sample_res = conn.execute(
                                    text(f"SELECT DISTINCT {col_q} FROM {t_q} WHERE {col_q} IS NOT NULL LIMIT 10")
                                ).fetchall()
                                samples_by_col[col_str] = [str(r[0]) for r in sample_res if r[0] is not None]
                            except Exception:
                                pass
            except Exception as ex:
                logger.warning(f"Failed to fetch sample data for table {t_name}: {ex}")

        col_profiles = []
        pks = []
        fks_list = []
        for c in cols:
            col_str = str(c.column_name)
            is_pk = bool(getattr(c, "is_primary_key", False))
            is_fk = bool(getattr(c, "is_foreign_key", False))
            fk_target = getattr(c, "foreign_key_target", None)
            sem_type = getattr(c, "semantic_type", "UNKNOWN") or "UNKNOWN"
            if is_pk:
                pks.append(col_str)
            if is_fk and fk_target:
                fks_list.append({"column": col_str, "target": fk_target})

            c_card = getattr(c, "cardinality", None)
            c_null = getattr(c, "null_percentage", 0.0)
            c_min = getattr(c, "min_value", None)
            c_max = getattr(c, "max_value", None)
            c_mean = getattr(c, "mean_value", None)

            cp = ColumnProfile(
                name=col_str,
                data_type=str(c.data_type or "TEXT"),
                semantic_type=sem_type,
                is_primary_key=is_pk,
                is_foreign_key=is_fk,
                foreign_key_target=fk_target,
                is_measure=bool(c.is_measure),
                is_dimension=bool(c.is_dimension),
                is_time_axis=bool(c.is_time_axis),
                cardinality=int(c_card) if c_card is not None else None,
                null_percentage=float(c_null or 0.0),
                min_value=float(c_min) if c_min is not None else None,
                max_value=float(c_max) if c_max is not None else None,
                mean_value=float(c_mean) if c_mean is not None else None,
                top_values=samples_by_col.get(col_str, []),
            )
            col_profiles.append(cp)


        table_profiles.append(TableProfile(
            table_name=t_name, 
            row_count=row_count, 
            columns=col_profiles,
            primary_keys=pks,
            foreign_keys=fks_list
        ))

    return table_profiles

