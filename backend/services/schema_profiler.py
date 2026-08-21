import os, base64, hashlib
from cryptography.fernet import Fernet
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

ENCRYPTION_SECRET = os.getenv("SECRET_KEY", "dataspeakai-default-encryption-secret-key-32b")
_FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(ENCRYPTION_SECRET.encode()).digest())
_fernet = Fernet(_FERNET_KEY)

def decrypt_password(enc_pwd: str) -> str:
    if not enc_pwd:
        return enc_pwd
    try:
        return _fernet.decrypt(enc_pwd.encode()).decode()
    except Exception:
        return enc_pwd

def get_connection_url(db_conn: models.DatabaseConnection) -> str | None:
    pwd = decrypt_password(db_conn.password)
    if db_conn.db_type == "postgresql":
        return f"postgresql://{db_conn.username}:{pwd}@{db_conn.host}/{db_conn.database}"
    elif db_conn.db_type in ("mysql", "mariadb"):
        return f"mysql+pymysql://{db_conn.username}:{pwd}@{db_conn.host}/{db_conn.database}"
    elif db_conn.db_type == "sqlite":
        path = (db_conn.database if db_conn.database else db_conn.host) or ""
        path = path.strip('"\'').replace("\\", "/")
        return f"sqlite:///{path}"
    return None



def profile_database_schema(db_conn: models.DatabaseConnection, db: Session) -> list[models.SchemaRegistry]:
    """
    Introspects tables & columns for a DatabaseConnection, computes lightweight statistical metrics
    (min, max, mean, null_pct), auto-tags measures/dimensions/time_axes, and saves to SchemaRegistry.
    """
    url = get_connection_url(db_conn)
    registry_entries = []

    # If simulated DB type or URL not supported, create baseline simulated schema entries
    if not url:
        mock_tables = {
            "users": [
                ("id", "INTEGER", False, True, False),
                ("email", "VARCHAR", False, True, False),
                ("created_at", "DATETIME", False, False, True),
            ],
            "orders": [
                ("id", "INTEGER", False, True, False),
                ("total_amount", "DECIMAL", True, False, False),
                ("order_date", "DATETIME", False, False, True),
                ("status", "VARCHAR", False, True, False),
            ],
        }
        for table_name, columns in mock_tables.items():
            for col_name, dtype, is_meas, is_dim, is_time in columns:
                reg = models.SchemaRegistry(
                    connection_id=db_conn.id,
                    table_name=table_name,
                    column_name=col_name,
                    data_type=dtype,
                    is_measure=is_meas,
                    is_dimension=is_dim,
                    is_time_axis=is_time,
                    null_percentage=0.0,
                )
                db.add(reg)
                registry_entries.append(reg)
        db.commit()
        return registry_entries

    try:
        from sqlalchemy.pool import NullPool
        engine = create_engine(url, poolclass=NullPool)
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # Clear existing entries for this connection before re-profiling
        db.query(models.SchemaRegistry).filter(models.SchemaRegistry.connection_id == db_conn.id).delete()
        db.commit()

        for table in tables:
            columns = inspector.get_columns(table)
            for col in columns:
                col_name = col["name"]
                raw_type = str(col["type"]).upper()

                # Semantic type categorization
                is_id = col_name.lower() == "id" or col_name.lower().endswith("id") or col_name.lower().endswith("_id")
                is_num = any(t in raw_type for t in ["INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL"])
                is_measure = is_num and not is_id
                is_time = any(t in raw_type for t in ["DATE", "TIME", "TIMESTAMP"])
                is_dim = not is_measure and not is_time


                min_val, max_val, mean_val, null_pct = None, None, None, 0.0

                # Compute fast stats for numeric columns
                if is_measure:
                    try:
                        with engine.connect() as conn:
                            query = text(f"""
                                SELECT 
                                    MIN({col_name}), 
                                    MAX({col_name}), 
                                    AVG({col_name}),
                                    COUNT(*) - COUNT({col_name}),
                                    COUNT(*)
                                FROM {table}
                            """)
                            row = conn.execute(query).fetchone()
                            if row and row[4] > 0:
                                min_val = float(row[0]) if row[0] is not None else None
                                max_val = float(row[1]) if row[1] is not None else None
                                mean_val = float(row[2]) if row[2] is not None else None
                                null_pct = round((row[3] / row[4]) * 100, 2)
                    except Exception as ex:
                        logger.warning(f"Could not compute stats for {table}.{col_name}: {ex}")

                reg_entry = models.SchemaRegistry(
                    connection_id=db_conn.id,
                    table_name=table,
                    column_name=col_name,
                    data_type=raw_type,
                    is_measure=is_measure,
                    is_dimension=is_dim,
                    is_time_axis=is_time,
                    min_value=min_val,
                    max_value=max_val,
                    mean_value=mean_val,
                    null_percentage=null_pct,
                )
                db.add(reg_entry)
                registry_entries.append(reg_entry)

        engine.dispose()
        db.commit()
        return registry_entries

    except Exception as e:
        logger.error(f"Schema profiling failed for connection {db_conn.id}: {e}")
        db.rollback()
        raise e
