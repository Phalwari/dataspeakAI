"""
backend/services/erd_service.py
-------------------------------
Core service for Entity-Relationship Diagram (ERD) generation, schema reflection,
relational constraint parsing, catalog synchronization, and inferred relationship detection.
"""
import os
import re
import time
import socket
import logging
import ipaddress
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

import models
from crypto import decrypt_password

logger = logging.getLogger("dataspeak.erd_service")

ERD_MAX_TABLES = int(os.getenv("ERD_MAX_TABLES", "300"))
ERD_REFRESH_COOLDOWN_SECONDS = int(os.getenv("ERD_REFRESH_COOLDOWN_SECONDS", "30"))
ALLOW_PRIVATE_DB_HOSTS = os.getenv("ALLOW_PRIVATE_DB_HOSTS", "false").lower() in ("true", "1", "yes")

# In-memory cooldown tracker: (tenant_id, database_id) -> timestamp
_refresh_cooldowns: Dict[Tuple[int, int], float] = {}


def check_refresh_cooldown(tenant_id: int, database_id: int) -> Optional[int]:
    """Returns seconds remaining if cooldown is active, else None."""
    now = time.time()
    last = _refresh_cooldowns.get((tenant_id, database_id))
    if last is not None:
        elapsed = now - last
        if elapsed < ERD_REFRESH_COOLDOWN_SECONDS:
            return max(1, int(ERD_REFRESH_COOLDOWN_SECONDS - elapsed))
    return None


def record_refresh_cooldown(tenant_id: int, database_id: int) -> None:
    _refresh_cooldowns[(tenant_id, database_id)] = time.time()


def clear_cooldowns_for_testing() -> None:
    _refresh_cooldowns.clear()


# ── Host & Path Security Validation (D5) ───────────────────────────────────────

def validate_db_host_security(host: Optional[str], allow_private: bool = False) -> None:
    """
    Rejects loopback (127.0.0.1, localhost), link-local (169.254.0.0/16), and private ranges
    unless allow_private is True.
    """
    if not host:
        return
    h = host.strip().lower()

    if h in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        if not allow_private:
            raise ValueError("Connection to localhost/loopback is not permitted for ERD")
        return

    # Try IP parsing directly
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        # Try DNS resolution
        try:
            resolved_ip_str = socket.gethostbyname(h)
            ip = ipaddress.ip_address(resolved_ip_str)
        except Exception:
            return

    if not allow_private:
        if ip.is_loopback:
            raise ValueError(f"Connection to loopback IP ({ip}) is not permitted for ERD")
        if ip.is_link_local:
            raise ValueError(f"Connection to link-local IP ({ip}) is not permitted for ERD")
        if ip.is_private:
            raise ValueError(f"Connection to private network IP ({ip}) is not permitted for ERD")
        if ip.is_reserved or ip.is_multicast:
            raise ValueError(f"Connection to reserved/multicast IP ({ip}) is not permitted for ERD")


def validate_sqlite_path_security(path: Optional[str]) -> None:
    """
    Validates SQLite path: must not be empty, must not contain '..', and must exist.
    """
    if not path:
        raise ValueError("SQLite database path cannot be empty")
    cleaned = path.strip().strip('"\'').replace("\\", "/")
    if ".." in cleaned:
        raise ValueError("Directory traversal ('..') is strictly prohibited in SQLite database paths")
    if cleaned != ":memory:" and not os.path.exists(cleaned):
        raise ValueError(f"SQLite database file not found at path")


def build_erd_connection_url(db_conn: models.DatabaseConnection) -> str:
    """
    Constructs dialect-specific connection URL with decrypted password.
    Performs host / path security validation beforehand.
    """
    db_type = (db_conn.db_type or "").lower()
    allow_private = ALLOW_PRIVATE_DB_HOSTS or os.getenv("ALLOW_PRIVATE_DB_HOSTS", "false").lower() in ("true", "1", "yes")

    if db_type == "sqlite":
        db_path = (db_conn.database if db_conn.database else db_conn.host) or ""
        validate_sqlite_path_security(db_path)
        cleaned = db_path.strip('"\'').replace("\\", "/")
        return f"sqlite:///{cleaned}"

    # For network DBs, validate host
    validate_db_host_security(db_conn.host, allow_private=allow_private)

    raw_password = decrypt_password(db_conn.password) if db_conn.password else ""
    port_str = f":{db_conn.port}" if db_conn.port else ""

    if db_type == "postgresql":
        return f"postgresql://{db_conn.username}:{raw_password}@{db_conn.host}{port_str}/{db_conn.database}"
    elif db_type in ("mysql", "mariadb"):
        return f"mysql+pymysql://{db_conn.username}:{raw_password}@{db_conn.host}{port_str}/{db_conn.database}"
    else:
        raise ValueError(f"ERD is supported only for relational databases (got: {db_type})")


def create_erd_engine(connection_url: str, db_type: str) -> Engine:
    """Creates a temporary Engine with NullPool and strict 10s connect timeout."""
    connect_args = {"timeout": 10} if db_type == "sqlite" else {"connect_timeout": 10}
    return create_engine(connection_url, poolclass=NullPool, connect_args=connect_args)


# ── In-Memory Reflected Graph Data Classes ─────────────────────────────────────

class ReflectedColumn:
    def __init__(self, name: str, col_type: str, nullable: bool = True, is_pk: bool = False, is_fk: bool = False, is_unique: bool = False):
        self.name = name
        self.type = col_type
        self.nullable = nullable
        self.is_pk = is_pk
        self.is_fk = is_fk
        self.is_unique = is_unique

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "is_pk": self.is_pk,
            "is_fk": self.is_fk,
            "is_unique": self.is_unique
        }


class ReflectedTable:
    def __init__(self, name: str, schema: Optional[str] = None, kind: str = "table", columns: Optional[List[ReflectedColumn]] = None):
        self.name = name
        self.schema = schema
        self.kind = kind
        self.columns = columns or []

    @property
    def id(self) -> str:
        return f"{self.schema}.{self.name}" if self.schema else self.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "schema": self.schema,
            "kind": self.kind,
            "columns": [c.to_dict() for c in self.columns]
        }


class ReflectedRelationship:
    def __init__(
        self,
        id: str,
        kind: str,
        source_table: str,
        source_columns: List[str],
        target_table: str,
        target_columns: List[str],
        constraint_name: Optional[str] = None,
        source_schema: Optional[str] = None,
        target_schema: Optional[str] = None,
        confidence: Optional[float] = None,
        reason: Optional[str] = None
    ):
        self.id = id
        self.kind = kind
        self.source_table = source_table
        self.source_schema = source_schema
        self.source_columns = source_columns
        self.target_table = target_table
        self.target_schema = target_schema
        self.target_columns = target_columns
        self.constraint_name = constraint_name
        self.confidence = confidence
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "constraint_name": self.constraint_name,
            "source_table": self.source_table,
            "source_columns": self.source_columns,
            "target_table": self.target_table,
            "target_columns": self.target_columns
        }
        if self.confidence is not None:
            res["confidence"] = self.confidence
        if self.reason is not None:
            res["reason"] = self.reason
        return res


class ReflectedSchemaResult:
    def __init__(self):
        self.tables: List[ReflectedTable] = []
        self.relationships: List[ReflectedRelationship] = []
        self.warnings: List[str] = []


# ── Schema Reflection Engine (D3) ─────────────────────────────────────────────

def reflect_schema(engine: Engine, schema: Optional[str] = None, inspector_override=None) -> ReflectedSchemaResult:
    """
    Reflects tables, views, columns, PKs, and foreign keys using SQLAlchemy 2.0 bulk methods:
    `get_multi_columns`, `get_multi_pk_constraint`, `get_multi_foreign_keys`.
    Falls back to per-table calls only if NotImplementedError or AttributeError is raised.
    """
    result = ReflectedSchemaResult()
    insp = inspector_override if inspector_override is not None else inspect(engine)

    try:
        table_names = insp.get_table_names(schema=schema) or []
    except Exception as e:
        logger.warning(f"Error inspecting table names: {e}")
        table_names = []

    try:
        view_names = insp.get_view_names(schema=schema) or []
    except Exception:
        view_names = []

    all_entity_names = list(table_names) + list(view_names)
    if not all_entity_names:
        return result

    # 1. Bulk Columns Reflection
    multi_cols: Dict[str, List[Dict[str, Any]]] = {}
    try:
        multi_cols = insp.get_multi_columns(schema=schema)
    except (NotImplementedError, AttributeError, Exception):
        for name in all_entity_names:
            try:
                multi_cols[name] = insp.get_columns(name, schema=schema)
            except Exception:
                multi_cols[name] = []

    # 2. Bulk PK Constraints Reflection (tables only, not views)
    multi_pks: Dict[str, Dict[str, Any]] = {}
    try:
        multi_pks = insp.get_multi_pk_constraint(schema=schema)
    except (NotImplementedError, AttributeError, Exception):
        for name in table_names:
            try:
                multi_pks[name] = insp.get_pk_constraint(name, schema=schema)
            except Exception:
                multi_pks[name] = {}

    # 3. Bulk Foreign Keys Reflection (tables only)
    multi_fks: Dict[str, List[Dict[str, Any]]] = {}
    try:
        multi_fks = insp.get_multi_foreign_keys(schema=schema)
    except (NotImplementedError, AttributeError, Exception):
        for name in table_names:
            try:
                multi_fks[name] = insp.get_foreign_keys(name, schema=schema)
            except Exception:
                multi_fks[name] = []

    # 4. Unique Constraints
    multi_unique: Dict[str, List[Dict[str, Any]]] = {}
    try:
        multi_unique = insp.get_multi_unique_constraints(schema=schema)
    except (NotImplementedError, AttributeError, Exception):
        for name in table_names:
            try:
                multi_unique[name] = insp.get_unique_constraints(name, schema=schema)
            except Exception:
                multi_unique[name] = []

    def _normalize_multi_dict(d: Dict[Any, Any]) -> Dict[str, Any]:
        norm: Dict[str, Any] = {}
        for k, v in d.items():
            if isinstance(k, tuple) and len(k) >= 2:
                norm[k[1]] = v
            else:
                norm[k] = v
        return norm

    multi_cols = _normalize_multi_dict(multi_cols)
    multi_pks = _normalize_multi_dict(multi_pks)
    multi_fks = _normalize_multi_dict(multi_fks)
    multi_unique = _normalize_multi_dict(multi_unique)

    # Dialects like SQLite exclude views from get_multi_columns. Ensure view columns are populated.
    for name in all_entity_names:
        if name not in multi_cols or not multi_cols[name]:
            try:
                entity_cols = insp.get_columns(name, schema=schema)
                if entity_cols:
                    multi_cols[name] = entity_cols
            except Exception:
                pass

    # Index of reflected entity names for dangling FK verification
    # Store both raw names and lowercase names to handle cross-dialect casing
    entity_name_set = set(all_entity_names)
    entity_name_lower = {n.lower(): n for n in all_entity_names}

    # Build ReflectedTable objects
    tables_by_name: Dict[str, ReflectedTable] = {}
    for name in all_entity_names:
        is_view = name in view_names
        kind = "view" if is_view else "table"

        pk_info = multi_pks.get(name) or {}
        pk_cols = set(pk_info.get("constrained_columns") or [])

        # Collect columns with FKs in this table
        table_fks = multi_fks.get(name) or []
        fk_cols = set()
        for fk in table_fks:
            for c in fk.get("constrained_columns") or []:
                fk_cols.add(c)

        # Collect single-column unique constraints
        unique_cols = set()
        for u in multi_unique.get(name) or []:
            u_cols = u.get("column_names") or []
            if len(u_cols) == 1:
                unique_cols.add(u_cols[0])

        col_objs: List[ReflectedColumn] = []
        raw_cols = multi_cols.get(name) or []
        for c_dict in raw_cols:
            c_name = c_dict.get("name", "")
            try:
                type_str = str(c_dict.get("type", "UNKNOWN"))
            except Exception:
                type_str = "UNKNOWN"

            nullable = bool(c_dict.get("nullable", True))
            is_pk = c_name in pk_cols
            is_fk = c_name in fk_cols
            is_unique = (c_name in unique_cols) or bool(c_dict.get("unique", False))

            col_objs.append(ReflectedColumn(
                name=c_name,
                col_type=type_str,
                nullable=nullable,
                is_pk=is_pk,
                is_fk=is_fk,
                is_unique=is_unique
            ))

        refl_table = ReflectedTable(name=name, schema=schema, kind=kind, columns=col_objs)
        tables_by_name[name] = refl_table
        result.tables.append(refl_table)

    # Build ReflectedRelationship objects
    rel_counter = 1
    for src_name in table_names:
        table_fks = multi_fks.get(src_name) or []
        for fk in table_fks:
            target_raw = fk.get("referred_table")
            if not target_raw:
                continue

            # Resolve target table in entity list
            target_table_name = target_raw
            if target_raw not in entity_name_set and target_raw.lower() in entity_name_lower:
                target_table_name = entity_name_lower[target_raw.lower()]

            # Check Dangling FK
            if target_table_name not in entity_name_set:
                c_name = fk.get("name") or f"fk_{src_name}_{target_raw}"
                result.warnings.append(
                    f"Dangling foreign key '{c_name}' in table '{src_name}': referenced target '{target_raw}' does not exist in reflected schema."
                )
                continue

            src_cols = list(fk.get("constrained_columns") or [])
            tgt_cols = list(fk.get("referred_columns") or [])
            ref_schema = fk.get("referred_schema") or schema
            c_name = fk.get("name")

            rel_id = f"rel_{src_name}_{target_table_name}_{rel_counter}"
            rel_counter += 1

            result.relationships.append(ReflectedRelationship(
                id=rel_id,
                kind="foreign_key",
                source_table=src_name,
                source_schema=schema,
                source_columns=src_cols,
                target_table=target_table_name,
                target_schema=ref_schema,
                target_columns=tgt_cols,
                constraint_name=c_name
            ))

    return result


# ── Inferred Relationship Engine ──────────────────────────────────────────────

GENERIC_COLUMN_NAMES = {"id", "code", "status", "name", "type", "created_at", "updated_at", "key", "value", "state", "description"}

def detect_inferred_relationships(
    tables: List[ReflectedTable],
    existing_relationships: List[ReflectedRelationship]
) -> List[ReflectedRelationship]:
    """
    Infers candidate relationships based on naming conventions (e.g. customer_id, customerId -> customers.id).
    Strict constraints:
    - Target table must have a single-column primary key.
    - Column must NOT already be part of a real foreign key in source_table.
    - Match must be unambiguous (exactly 1 candidate target table).
    - Generic names (id, code, status, name) are ignored.
    """
    inferred: List[ReflectedRelationship] = []

    # Map existing FK covered columns: (source_table, column_name)
    fk_covered: Set[Tuple[str, str]] = set()
    for rel in existing_relationships:
        for c in rel.source_columns:
            fk_covered.add((rel.source_table, c))

    # Index candidate targets by normalized names
    # e.g. "customers" -> target_table, "customer" -> target_table
    target_candidates: Dict[str, List[ReflectedTable]] = {}
    for t in tables:
        if t.kind == "view":
            continue
        pk_cols = [c for c in t.columns if c.is_pk]
        if len(pk_cols) == 1:
            raw = t.name.lower()
            clean = raw.replace("_", "").replace("-", "")
            singular = raw.rstrip("s")
            clean_sing = singular.replace("_", "").replace("-", "")

            for key in (raw, clean, singular, clean_sing):
                target_candidates.setdefault(key, [])
                if t not in target_candidates[key]:
                    target_candidates[key].append(t)

    rel_idx = 1
    for src in tables:
        for col in src.columns:
            if col.is_pk or (src.name, col.name) in fk_covered:
                continue

            col_raw = col.name.lower()
            if col_raw in GENERIC_COLUMN_NAMES:
                continue

            # Candidate prefixes e.g. customer_id -> "customer"
            candidate_keys = []
            if col_raw.endswith("_id"):
                candidate_keys.append(col_raw[:-3])
            elif col_raw.endswith("id") and len(col_raw) > 2:
                candidate_keys.append(col_raw[:-2])

            matching_targets: List[ReflectedTable] = []
            for k in candidate_keys:
                clean_k = k.replace("_", "")
                targets = target_candidates.get(k) or target_candidates.get(clean_k) or []
                for tgt in targets:
                    if tgt.name != src.name and tgt not in matching_targets:
                        matching_targets.append(tgt)

            # Require unambiguous single match
            if len(matching_targets) == 1:
                target = matching_targets[0]
                target_pk = [c for c in target.columns if c.is_pk][0]

                inferred.append(ReflectedRelationship(
                    id=f"inferred_{src.name}_{target.name}_{rel_idx}",
                    kind="inferred",
                    source_table=src.name,
                    source_schema=src.schema,
                    source_columns=[col.name],
                    target_table=target.name,
                    target_schema=target.schema,
                    target_columns=[target_pk.name],
                    confidence=0.85,
                    reason=f"Column '{col.name}' matches primary key '{target_pk.name}' of table '{target.name}'"
                ))
                rel_idx += 1

    return inferred


# ── Catalog Synchronization Engine (D1 / D2) ───────────────────────────────────

def sync_schema_catalog(
    db: Session,
    db_conn: models.DatabaseConnection,
    schema_name: Optional[str],
    reflected: ReflectedSchemaResult
) -> models.DatabaseSchema:
    """
    Atomically syncs the reflected graph into database_schemas, table_metadata,
    column_metadata, and table_relationships models within a single database transaction.
    """
    target_schema_name = schema_name or db_conn.database or "public"

    # 1. Load or initialize DatabaseSchema record
    db_schema = db.query(models.DatabaseSchema).filter(
        models.DatabaseSchema.connection_id == db_conn.id,
        models.DatabaseSchema.schema_name == target_schema_name
    ).first()

    now_time = datetime.now(timezone.utc)

    if not db_schema:
        db_schema = models.DatabaseSchema(
            connection_id=db_conn.id,
            schema_name=target_schema_name,
            last_sync=now_time
        )
        db.add(db_schema)
        db.flush()
    else:
        db_schema.last_sync = now_time
        # Clean existing children in strict cascade order: ColumnMetadata, TableRelationship, then TableMetadata
        old_table_ids = [
            t.id for t in db.query(models.TableMetadata.id)
            .filter(models.TableMetadata.schema_id == db_schema.id).all()
        ]
        if old_table_ids:
            db.query(models.ColumnMetadata).filter(
                models.ColumnMetadata.table_id.in_(old_table_ids)
            ).delete(synchronize_session=False)

        db.query(models.TableRelationship).filter(
            models.TableRelationship.schema_id == db_schema.id
        ).delete(synchronize_session=False)

        db.query(models.TableMetadata).filter(
            models.TableMetadata.schema_id == db_schema.id
        ).delete(synchronize_session=False)

        db.flush()

    # 2. Persist TableMetadata & ColumnMetadata
    pii_patterns = re.compile(r"(email|password|secret|ssn|token|phone|credit|card|cvv|hash|salary|auth)", re.IGNORECASE)

    table_id_map: Dict[str, int] = {}
    for tbl in reflected.tables:
        tbl_meta = models.TableMetadata(
            schema_id=db_schema.id,
            table_name=tbl.name,
            kind=tbl.kind,
            semantic_description=f"{tbl.kind.capitalize()} {tbl.name} in {db_conn.name}",
            is_fact_table=bool(re.search(r"(log|event|order|transaction|sale|history|metric)", tbl.name, re.IGNORECASE)),
            row_count_estimate=0
        )
        db.add(tbl_meta)
        db.flush()
        table_id_map[tbl.name] = tbl_meta.id

        for col in tbl.columns:
            is_pii = bool(pii_patterns.search(col.name))
            col_meta = models.ColumnMetadata(
                table_id=tbl_meta.id,
                column_name=col.name,
                data_type=col.type,
                is_pii=is_pii,
                is_primary_key=col.is_pk,
                is_foreign_key=col.is_fk,
                is_nullable=col.nullable,
                is_unique=col.is_unique,
                foreign_key_target=None
            )
            db.add(col_meta)

    # 3. Persist TableRelationship records (foreign_key kind only in catalog)
    for rel in reflected.relationships:
        if rel.kind == "foreign_key":
            rel_rec = models.TableRelationship(
                schema_id=db_schema.id,
                kind="foreign_key",
                constraint_name=rel.constraint_name,
                source_table=rel.source_table,
                source_schema=rel.source_schema,
                source_columns=rel.source_columns,
                target_table=rel.target_table,
                target_schema=rel.target_schema,
                target_columns=rel.target_columns
            )
            db.add(rel_rec)

    db.commit()
    db.refresh(db_schema)
    return db_schema


def load_erd_from_catalog(
    db: Session,
    db_conn: models.DatabaseConnection,
    schema_name: Optional[str]
) -> Optional[Dict[str, Any]]:
    """
    Loads ERD data directly from cached catalog tables (DatabaseSchema, TableMetadata,
    ColumnMetadata, TableRelationship). Returns None if not cached.
    """
    target_schema_name = schema_name or db_conn.database or "public"

    db_schema = db.query(models.DatabaseSchema).filter(
        models.DatabaseSchema.connection_id == db_conn.id,
        models.DatabaseSchema.schema_name == target_schema_name
    ).first()

    if not db_schema or not db_schema.tables:
        return None

    tables_out: List[Dict[str, Any]] = []
    for tbl in sorted(db_schema.tables, key=lambda t: t.table_name):
        cols_out: List[Dict[str, Any]] = []
        for c in tbl.columns:
            cols_out.append({
                "name": c.column_name,
                "type": c.data_type,
                "nullable": c.is_nullable if c.is_nullable is not None else True,
                "is_pk": bool(c.is_primary_key),
                "is_fk": bool(c.is_foreign_key),
                "is_unique": bool(c.is_unique)
            })

        table_id = f"{db_schema.schema_name}.{tbl.table_name}" if db_schema.schema_name and db_schema.schema_name != "public" else tbl.table_name
        tables_out.append({
            "id": table_id,
            "name": tbl.table_name,
            "schema": db_schema.schema_name,
            "kind": getattr(tbl, "kind", "table") or "table",
            "columns": cols_out
        })

    relationships_out: List[Dict[str, Any]] = []
    rel_rows = db.query(models.TableRelationship).filter(
        models.TableRelationship.schema_id == db_schema.id
    ).all()

    for idx, r in enumerate(rel_rows, 1):
        relationships_out.append({
            "id": f"rel_{r.source_table}_{r.target_table}_{idx}",
            "kind": r.kind,
            "constraint_name": r.constraint_name,
            "source_table": r.source_table,
            "source_columns": r.source_columns or [],
            "target_table": r.target_table,
            "target_columns": r.target_columns or []
        })

    return {
        "database_id": db_conn.id,
        "dialect": (db_conn.db_type or "sqlite").lower(),
        "schema": db_schema.schema_name,
        "last_sync": db_schema.last_sync,
        "source": "catalog",
        "tables": tables_out,
        "relationships": relationships_out,
        "warnings": []
    }
