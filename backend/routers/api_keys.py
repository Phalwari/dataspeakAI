from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from dependencies import get_current_user
import uuid
import string
import random
import secrets
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/api/keys", tags=["api_keys"])

def generate_secure_key():
    # Format: omq_pk_live_[32 random chars]
    chars = string.ascii_lowercase + string.digits
    random_str = ''.join(random.choice(chars) for _ in range(32))
    return f"omq_pk_live_{random_str}"

def generate_public_widget_key():
    # Format: pk_live_[32 hex chars]
    return f"pk_live_{secrets.token_hex(16)}"


@router.get("", response_model=List[schemas.ApiKeyResponse])
def get_api_keys(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    keys = db.query(models.ApiKey).filter(models.ApiKey.tenant_id == current_user.tenant_id).all()
    return keys

@router.post("", response_model=schemas.ApiKeyResponse)
def create_api_key(
    key_data: schemas.ApiKeyCreate,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    
    new_key = models.ApiKey(
        tenant_id=current_user.tenant_id,
        name=key_data.name,
        description=key_data.description,
        key=generate_secure_key()
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    return new_key

@router.put("/{key_id}/revoke", response_model=schemas.ApiKeyResponse)
def revoke_api_key(
    key_id: int,
    current_user: models.User = Depends(get_current_user), 
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
    return api_key

@router.delete("/{key_id}")
def delete_api_key(
    key_id: int,
    current_user: models.User = Depends(get_current_user), 
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    return db.query(models.WidgetKey).filter(models.WidgetKey.tenant_id == current_user.tenant_id).all()

@router.post("/widget", response_model=schemas.WidgetKeyResponse)
def create_widget_key(
    key_data: schemas.WidgetKeyCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    if not key_data.allowed_origins:
        raise HTTPException(status_code=400, detail="allowed_origins cannot be empty")
    for o in key_data.allowed_origins:
        if o == "*":
            raise HTTPException(status_code=400, detail="Wildcard origins ('*') are strictly disallowed")

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
    current_user: models.User = Depends(get_current_user),
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
        widget_key.allowed_database_ids = key_data.allowed_database_ids
    if key_data.allowed_tables is not None:
        widget_key.allowed_tables = key_data.allowed_tables

    db.commit()
    db.refresh(widget_key)
    return widget_key

@router.post("/widget/{key_id}/rotate", response_model=schemas.WidgetKeyRotateResponse)
def rotate_widget_key(
    key_id: int,
    current_user: models.User = Depends(get_current_user),
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
    current_user: models.User = Depends(get_current_user),
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
    current_user: models.User = Depends(get_current_user),
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

