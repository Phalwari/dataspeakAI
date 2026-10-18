from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from dependencies import get_current_user, require_key_manager
import uuid
import string
import random
import secrets
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/api/keys", tags=["api_keys"])

def generate_secure_key() -> str:
    # Format: omq_live_[32 urlsafe characters]
    return f"omq_live_{secrets.token_urlsafe(32)}"

def hash_key(raw_key: str) -> str:
    import hashlib
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

def generate_public_widget_key():
    # Format: pk_live_[32 hex chars]
    return f"pk_live_{secrets.token_hex(16)}"


@router.get("", response_model=List[schemas.ApiKeyResponse])
def get_api_keys(
    current_user: models.User = Depends(require_key_manager), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    keys = db.query(models.ApiKey).filter(models.ApiKey.tenant_id == current_user.tenant_id).all()
    response_items = []
    for k in keys:
        if k.key_prefix:
            masked = f"{k.key_prefix}***"
            prefix = k.key_prefix
        elif k.key:
            masked = f"{k.key[:10]}***"
            prefix = k.key[:10]
        else:
            masked = "omq_live_***"
            prefix = "omq_live_"
        response_items.append(
            schemas.ApiKeyResponse(
                id=k.id,
                name=k.name,
                description=k.description,
                key=masked,
                key_prefix=prefix,
                status=k.status,
                total_requests=k.total_requests or 0,
                last_used_at=k.last_used_at,
                created_at=k.created_at,
            )
        )
    return response_items

@router.post("", response_model=schemas.ApiKeyCreateResponse)
def create_api_key(
    key_data: schemas.ApiKeyCreate,
    current_user: models.User = Depends(require_key_manager), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    
    raw_key = generate_secure_key()
    prefix = raw_key[:12]
    hashed = hash_key(raw_key)

    new_key = models.ApiKey(
        tenant_id=current_user.tenant_id,
        name=key_data.name,
        description=key_data.description,
        key=None,
        key_prefix=prefix,
        hashed_key=hashed,
        status="active"
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    return schemas.ApiKeyCreateResponse(
        id=new_key.id,
        name=new_key.name,
        description=new_key.description,
        key=raw_key,
        key_prefix=prefix,
        status=new_key.status,
        total_requests=new_key.total_requests or 0,
        created_at=new_key.created_at
    )

@router.put("/{key_id}/revoke", response_model=schemas.ApiKeyResponse)
def revoke_api_key(
    key_id: int,
    current_user: models.User = Depends(require_key_manager), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    api_key = db.query(models.ApiKey).filter(
        models.ApiKey.id == key_id,
        models.ApiKey.tenant_id == current_user.tenant_id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key not found")
        
    api_key.status = "revoked"
    db.commit()
    db.refresh(api_key)
    
    prefix = api_key.key_prefix or (api_key.key[:10] if api_key.key else "omq_live_")
    masked = f"{prefix}***"
    return schemas.ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        key=masked,
        key_prefix=prefix,
        status=api_key.status,
        total_requests=api_key.total_requests or 0,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
    )

@router.delete("/{key_id}")
def delete_api_key(
    key_id: int,
    current_user: models.User = Depends(require_key_manager), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    api_key = db.query(models.ApiKey).filter(
        models.ApiKey.id == key_id,
        models.ApiKey.tenant_id == current_user.tenant_id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key not found")
        
    db.delete(api_key)
    db.commit()
    return {"message": "API Key deleted successfully"}


# -------------------------------------------------------------
# Standalone Widget Publishable Keys (Phase 2)
# -------------------------------------------------------------

@router.get("/widget", response_model=List[schemas.WidgetKeyResponse])
def get_widget_keys(
    current_user: models.User = Depends(require_key_manager),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    return db.query(models.WidgetKey).filter(models.WidgetKey.tenant_id == current_user.tenant_id).all()

@router.post("/widget", response_model=schemas.WidgetKeyResponse)
def create_widget_key(
    key_data: schemas.WidgetKeyCreate,
    current_user: models.User = Depends(require_key_manager),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    if not key_data.allowed_origins:
        raise HTTPException(status_code=400, detail="allowed_origins cannot be empty")
    for o in key_data.allowed_origins:
        if o == "*":
            raise HTTPException(status_code=400, detail="Wildcard origins ('*') are strictly disallowed")

    # Strict Tenant Scoping: Verify any assigned database IDs belong to the current tenant
    if key_data.allowed_database_ids:
        valid_db_count = db.query(models.DatabaseConnection.id).filter(
            models.DatabaseConnection.id.in_(key_data.allowed_database_ids),
            models.DatabaseConnection.tenant_id == current_user.tenant_id
        ).count()
        if valid_db_count != len(set(key_data.allowed_database_ids)):
            raise HTTPException(status_code=404, detail="Database connection not found")

    new_key = models.WidgetKey(
        tenant_id=current_user.tenant_id,
        public_key=generate_public_widget_key(),
        name=key_data.name,
        allowed_origins=key_data.allowed_origins,
        enabled=True,
        monthly_message_cap=key_data.monthly_message_cap or 1000,
        allow_sql=key_data.allow_sql or False,
        allowed_database_ids=key_data.allowed_database_ids or [],
        allowed_tables=key_data.allowed_tables or []
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    return new_key

@router.put("/widget/{key_id}", response_model=schemas.WidgetKeyResponse)
def update_widget_key(
    key_id: int,
    key_data: schemas.WidgetKeyUpdate,
    current_user: models.User = Depends(require_key_manager),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    widget_key = db.query(models.WidgetKey).filter(
        models.WidgetKey.id == key_id,
        models.WidgetKey.tenant_id == current_user.tenant_id
    ).first()

    if not widget_key:
        raise HTTPException(status_code=404, detail="Widget key not found")

    if key_data.name is not None:
        widget_key.name = key_data.name
    if key_data.allowed_origins is not None:
        for o in key_data.allowed_origins:
            if o == "*":
                raise HTTPException(status_code=400, detail="Wildcard origins ('*') are strictly disallowed")
        widget_key.allowed_origins = key_data.allowed_origins
    if key_data.enabled is not None:
        widget_key.enabled = key_data.enabled
    if key_data.monthly_message_cap is not None:
        widget_key.monthly_message_cap = key_data.monthly_message_cap
    if key_data.allow_sql is not None:
        widget_key.allow_sql = key_data.allow_sql
    if key_data.allowed_database_ids is not None:
        if key_data.allowed_database_ids:
            valid_db_count = db.query(models.DatabaseConnection.id).filter(
                models.DatabaseConnection.id.in_(key_data.allowed_database_ids),
                models.DatabaseConnection.tenant_id == current_user.tenant_id
            ).count()
            if valid_db_count != len(set(key_data.allowed_database_ids)):
                raise HTTPException(status_code=404, detail="Database connection not found")
        widget_key.allowed_database_ids = key_data.allowed_database_ids
    if key_data.allowed_tables is not None:
        widget_key.allowed_tables = key_data.allowed_tables

    db.commit()
    db.refresh(widget_key)
    return widget_key

@router.post("/widget/{key_id}/rotate", response_model=schemas.WidgetKeyRotateResponse)
def rotate_widget_key(
    key_id: int,
    current_user: models.User = Depends(require_key_manager),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    widget_key = db.query(models.WidgetKey).filter(
        models.WidgetKey.id == key_id,
        models.WidgetKey.tenant_id == current_user.tenant_id
    ).first()

    if not widget_key:
        raise HTTPException(status_code=404, detail="Widget key not found")

    now = datetime.now(timezone.utc)
    old_key = widget_key.public_key
    new_key = generate_public_widget_key()

    widget_key.previous_key = old_key
    widget_key.previous_key_expires_at = now + timedelta(hours=24)
    widget_key.public_key = new_key
    widget_key.enabled = True

    db.commit()
    db.refresh(widget_key)

    return schemas.WidgetKeyRotateResponse(
        id=widget_key.id,
        new_key=widget_key.public_key,
        previous_key=widget_key.previous_key,
        previous_key_expires_at=widget_key.previous_key_expires_at,
        message="Widget key rotated successfully. Previous key will remain valid for 24 hours."
    )

@router.put("/widget/{key_id}/revoke", response_model=schemas.WidgetKeyResponse)
def revoke_widget_key(
    key_id: int,
    current_user: models.User = Depends(require_key_manager),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    widget_key = db.query(models.WidgetKey).filter(
        models.WidgetKey.id == key_id,
        models.WidgetKey.tenant_id == current_user.tenant_id
    ).first()

    if not widget_key:
        raise HTTPException(status_code=404, detail="Widget key not found")

    widget_key.enabled = False
    widget_key.previous_key_expires_at = None
    db.commit()
    db.refresh(widget_key)
    return widget_key

@router.delete("/widget/{key_id}")
def delete_widget_key(
    key_id: int,
    current_user: models.User = Depends(require_key_manager),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    widget_key = db.query(models.WidgetKey).filter(
        models.WidgetKey.id == key_id,
        models.WidgetKey.tenant_id == current_user.tenant_id
    ).first()

    if not widget_key:
        raise HTTPException(status_code=404, detail="Widget key not found")

    db.query(models.QueryLog).filter(models.QueryLog.widget_key_id == widget_key.id).update(
        {"widget_key_id": None}, synchronize_session=False
    )
    db.delete(widget_key)
    db.commit()
    return {"message": "Widget key deleted successfully"}


@router.get("/widget/{key_id}/documents", response_model=schemas.WidgetKeyDocumentResponse)
def get_widget_key_documents(
    key_id: int,
    current_user: models.User = Depends(require_key_manager),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    widget_key = db.query(models.WidgetKey).filter(
        models.WidgetKey.id == key_id,
        models.WidgetKey.tenant_id == current_user.tenant_id
    ).first()
    if not widget_key:
        raise HTTPException(status_code=404, detail="Widget key not found")

    docs = db.query(models.WidgetKeyDocument.document_id).join(
        models.Document, models.WidgetKeyDocument.document_id == models.Document.id
    ).filter(
        models.WidgetKeyDocument.widget_key_id == key_id,
        models.Document.is_deleted == False
    ).all()
    return schemas.WidgetKeyDocumentResponse(
        widget_key_id=key_id,
        published_document_ids=[d[0] for d in docs]
    )


@router.post("/widget/{key_id}/documents", response_model=schemas.WidgetKeyDocumentResponse)
def assign_widget_key_documents(
    key_id: int,
    assign_req: schemas.WidgetKeyDocumentAssignRequest,
    current_user: models.User = Depends(require_key_manager),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    widget_key = db.query(models.WidgetKey).filter(
        models.WidgetKey.id == key_id,
        models.WidgetKey.tenant_id == current_user.tenant_id
    ).first()
    if not widget_key:
        raise HTTPException(status_code=404, detail="Widget key not found")

    target_ids = list(assign_req.document_ids or [])
    if assign_req.document_id is not None and assign_req.document_id not in target_ids:
        target_ids.append(assign_req.document_id)

    if not target_ids:
        raise HTTPException(
            status_code=400,
            detail="No document IDs provided to assign"
        )

    tenant_docs = db.query(models.Document.id).filter(
        models.Document.id.in_(target_ids),
        models.Document.tenant_id == current_user.tenant_id
    ).all()
    valid_doc_ids = {d[0] for d in tenant_docs}

    for doc_id in target_ids:
        if doc_id not in valid_doc_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Document ID {doc_id} does not belong to your tenant or does not exist"
            )
        existing = db.query(models.WidgetKeyDocument).filter(
            models.WidgetKeyDocument.widget_key_id == key_id,
            models.WidgetKeyDocument.document_id == doc_id
        ).first()
        if not existing:
            assoc = models.WidgetKeyDocument(
                widget_key_id=key_id,
                document_id=doc_id
            )
            db.add(assoc)

    db.commit()

    docs = db.query(models.WidgetKeyDocument.document_id).join(
        models.Document, models.WidgetKeyDocument.document_id == models.Document.id
    ).filter(
        models.WidgetKeyDocument.widget_key_id == key_id,
        models.Document.is_deleted == False
    ).all()
    return schemas.WidgetKeyDocumentResponse(
        widget_key_id=key_id,
        published_document_ids=[d[0] for d in docs]
    )


@router.delete("/widget/{key_id}/documents")
def unpublish_all_widget_key_documents(
    key_id: int,
    current_user: models.User = Depends(require_key_manager),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    widget_key = db.query(models.WidgetKey).filter(
        models.WidgetKey.id == key_id,
        models.WidgetKey.tenant_id == current_user.tenant_id
    ).first()
    if not widget_key:
        raise HTTPException(status_code=404, detail="Widget key not found")

    deleted_count = db.query(models.WidgetKeyDocument).filter(
        models.WidgetKeyDocument.widget_key_id == key_id
    ).delete(synchronize_session=False)
    db.commit()

    return {"message": f"Unpublished {deleted_count} documents from widget key {key_id}", "deleted_count": deleted_count}


@router.delete("/widget/{key_id}/documents/{document_id}")
def unpublish_widget_key_document(
    key_id: int,
    document_id: int,
    current_user: models.User = Depends(require_key_manager),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    widget_key = db.query(models.WidgetKey).filter(
        models.WidgetKey.id == key_id,
        models.WidgetKey.tenant_id == current_user.tenant_id
    ).first()
    if not widget_key:
        raise HTTPException(status_code=404, detail="Widget key not found")

    assoc = db.query(models.WidgetKeyDocument).filter(
        models.WidgetKeyDocument.widget_key_id == key_id,
        models.WidgetKeyDocument.document_id == document_id
    ).first()
    if assoc:
        db.delete(assoc)
        db.commit()

    return {"message": f"Document {document_id} unpublished from widget key {key_id}"}


