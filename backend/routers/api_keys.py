from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from dependencies import get_current_user
import uuid
import string
import random

router = APIRouter(prefix="/api/keys", tags=["api_keys"])

def generate_secure_key():
    # Format: omq_pk_live_[32 random chars]
    chars = string.ascii_lowercase + string.digits
    random_str = ''.join(random.choice(chars) for _ in range(32))
    return f"omq_pk_live_{random_str}"

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
