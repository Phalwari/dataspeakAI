"""
backend/routers/erd.py
----------------------
Router providing Entity-Relationship Diagram (ERD) schema data for connected databases.
Implements catalog-first caching, on-demand re-sync, host security validation, and inferred foreign keys.
"""
import os
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from dependencies import get_current_user
from services.erd_service import (
    load_erd_from_catalog,
    build_erd_connection_url,
    create_erd_engine,
    reflect_schema,
    sync_schema_catalog,
    detect_inferred_relationships,
    check_refresh_cooldown,
    record_refresh_cooldown,
    ReflectedTable,
    ReflectedColumn,
    ReflectedRelationship,
    ERD_MAX_TABLES,
)

logger = logging.getLogger("dataspeak.erd_router")

router = APIRouter(prefix="/api/databases", tags=["Databases ERD"])

RELATIONAL_DIALECTS = {"postgresql", "mysql", "mariadb", "sqlite"}


@router.get(
    "/{id}/erd",
    response_model=schemas.DatabaseErdResponse,
    operation_id="get_database_erd_data"
)
def get_database_erd(
    id: int,
    schema: Optional[str] = Query(None, description="Database schema name to inspect (e.g. 'public')"),
    refresh: bool = Query(False, description="Force re-sync against physical database bypassing cached catalog"),
    include_inferred: bool = Query(False, description="Include name-inferred relationship candidates"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the Entity-Relationship Diagram (ERD) structure for a connected relational database.
    - Uses catalog-first caching: reads from database_schemas unless refresh=true or catalog is empty.
    - Strictly scoped to tenant: accessing another tenant's database ID yields HTTP 404.
    - Enforces SSRF and path traversal defenses (D5).
    - Rate-limits refresh via cooldown returning HTTP 429 with Retry-After header (D7).
    """
    # 1. Auth & Tenant Verification
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to an active tenant."
        )

    tenant_id = current_user.tenant_id

    # 2. Tenant-Scoped Database Load (404 on IDOR or missing)
    db_conn = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == id,
        models.DatabaseConnection.tenant_id == tenant_id
    ).first()

    if not db_conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found."
        )

    # 3. Dialect Validation (D4: Relational only)
    db_type = (db_conn.db_type or "").lower()
    if db_type not in RELATIONAL_DIALECTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ERD is supported only for relational databases"
        )

    # 4. Refresh Cooldown Check (D7)
    if refresh:
        cooldown_remaining = check_refresh_cooldown(tenant_id, id)
        if cooldown_remaining is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Refresh cooldown active. Please wait {cooldown_remaining} seconds before refreshing.",
                headers={"Retry-After": str(cooldown_remaining)}
            )

    erd_data: Optional[Dict[str, Any]] = None

    # 5. Catalog-First Check (D1)
    if not refresh:
        erd_data = load_erd_from_catalog(db, db_conn, schema)

    # 6. Live Reflection if catalog is missing or refresh=True
    if not erd_data:
        try:
            conn_url = build_erd_connection_url(db_conn)
        except ValueError as ve:
            # Host or path security validation failure
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(ve)
            )

        engine = None
        try:
            engine = create_erd_engine(conn_url, db_type)
            reflected = reflect_schema(engine, schema=schema)
        except HTTPException:
            raise
        except Exception as ex:
            logger.error(f"[ERD Engine Error] Connection failed: {type(ex).__name__}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to establish connection to database server. Please verify database connectivity and credentials."
            )
        finally:
            if engine is not None:
                try:
                    engine.dispose()
                except Exception:
                    pass

        # Persist into catalog
        try:
            sync_schema_catalog(db, db_conn, schema, reflected)
            if refresh:
                record_refresh_cooldown(tenant_id, id)
        except Exception as sync_err:
            logger.error(f"[ERD Catalog Sync Error] {sync_err}")
            db.rollback()

        # Build output structure from reflected result
        tables_list = [t.to_dict() for t in reflected.tables]
        rels_list = [r.to_dict() for r in reflected.relationships]

        erd_data = {
            "database_id": db_conn.id,
            "dialect": db_type,
            "schema": schema or db_conn.database or "public",
            "last_sync": models.utc_now(),
            "source": "live",
            "tables": tables_list,
            "relationships": rels_list,
            "warnings": reflected.warnings
        }

    # 7. Inferred Relationships (if requested)
    if include_inferred and erd_data:
        # Convert dicts back to lightweight objects for inference engine
        refl_tables = [
            ReflectedTable(
                name=t["name"],
                schema=t.get("schema"),
                kind=t.get("kind", "table"),
                columns=[
                    ReflectedColumn(
                        name=c["name"],
                        col_type=c["type"],
                        nullable=c.get("nullable", True),
                        is_pk=c.get("is_pk", False),
                        is_fk=c.get("is_fk", False),
                        is_unique=c.get("is_unique", False)
                    )
                    for c in t.get("columns", [])
                ]
            )
            for t in erd_data["tables"]
        ]
        existing_rels = [
            ReflectedRelationship(
                id=r["id"],
                kind=r.get("kind", "foreign_key"),
                source_table=r["source_table"],
                source_columns=r["source_columns"],
                target_table=r["target_table"],
                target_columns=r["target_columns"]
            )
            for r in erd_data["relationships"]
        ]

        inferred = detect_inferred_relationships(refl_tables, existing_rels)
        for inf in inferred:
            erd_data["relationships"].append(inf.to_dict())

    # 8. Truncation Limit (ERD_MAX_TABLES)
    total_tables = len(erd_data["tables"])
    is_truncated = False
    warnings = list(erd_data.get("warnings") or [])

    if total_tables > ERD_MAX_TABLES:
        is_truncated = True
        warnings.append(
            f"Schema exceeds maximum ERD display limit of {ERD_MAX_TABLES} tables. Truncated to first {ERD_MAX_TABLES} tables."
        )
        kept_tables = erd_data["tables"][:ERD_MAX_TABLES]
        kept_names = {t["name"] for t in kept_tables}
        # Filter relationships so both ends exist in visible tables
        kept_rels = [
            r for r in erd_data["relationships"]
            if r["source_table"] in kept_names and r["target_table"] in kept_names
        ]
        erd_data["tables"] = kept_tables
        erd_data["relationships"] = kept_rels

    return schemas.DatabaseErdResponse(
        database_id=erd_data["database_id"],
        dialect=erd_data["dialect"],
        schema=erd_data.get("schema"),
        last_sync=erd_data.get("last_sync"),
        source=erd_data.get("source", "catalog"),
        truncated=is_truncated,
        table_count=total_tables,
        warnings=warnings,
        tables=[schemas.ErdTable.model_validate(t) for t in erd_data["tables"]],
        relationships=[schemas.ErdRelationship.model_validate(r) for r in erd_data["relationships"]]
    )
